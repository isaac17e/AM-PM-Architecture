# ==============================================================================
# POLYGON_CLIENT - Acceso compartido a la API de Polygon.io
# ==============================================================================
# Modulo comun a minimum_variance.py, quadratic_utility.py, black_litterman.py
# y sus versiones estacionales. Centraliza:
#
#   1. Limitador de tasa global y seguro entre hilos (POLYGON_CALLS_PER_MIN).
#   2. Reintentos con backoff ante 429 / 5xx / errores de red, respetando
#      Retry-After.
#   3. Paginacion completa via next_url, con indicador de completitud: una
#      cadena a la que le falta una pagina NUNCA se devuelve como completa.
#   4. Cache en disco: permanente para datos historicos (no cambian) y con
#      TTL para snapshots del dia.
#   5. Diagnostico acumulado de llamadas.
#   6. Descarga de la cadena OTM de un unico vencimiento para BKM.
#   7. Formato de tickers para Polygon (BRK-B -> BRK.B), unico para todos
#      los scripts.
#
# Configuracion por variables de entorno (.env):
#   POLYGON_API_KEY           clave de la API. Sin clave, toda consulta
#                             devuelve status "sin_api_key" de forma
#                             DEFINITIVA (no se reintenta ni se trata como
#                             fallo transitorio) y se emite un aviso una vez.
#   POLYGON_CALLS_PER_MIN     tope de llamadas por minuto. Default
#                             DEFAULT_CALLS_PER_MIN (300 = 5/s), un ritmo
#                             conservador para los planes de pago (Starter o
#                             superior), que no imponen tope duro pero si
#                             devuelven 429 ante rafagas. Valores:
#                               5                 plan gratuito
#                               0 / none / unlimited   sin limitador
#   POLYGON_SNAPSHOT_TTL_MIN  vigencia en minutos de la cache de snapshots
#                             (default 60; 0 la desactiva)
#   POLYGON_CACHE_DIR         carpeta de la cache (default .cache/polygon)
#
# El tope tambien puede cambiarse en tiempo de ejecucion con set_rate_limit().
# ==============================================================================

import hashlib
import json
import os
import re
import threading
import time
import warnings
from datetime import date

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

__all__ = [
    "API_KEY",
    "CALLS_PER_MIN",
    "DEFAULT_CALLS_PER_MIN",
    "set_rate_limit",
    "polygon_format_ticker",
    "get_json",
    "get_all",
    "es_transitorio",
    "cache_get",
    "cache_set",
    "estimate_minutes",
    "fetch_otm_chain",
    "diag",
    "print_diagnostics",
    "n_fallos_transitorios",
]

API_KEY = os.environ.get("POLYGON_API_KEY")

# Ritmo por defecto para planes de pago. Polygon no publica un tope duro en
# esos planes, pero responde 429 ante rafagas sostenidas; 5 llamadas/s cubre
# una cadena de ~200 tickers (2 consultas por ticker) en poco mas de un
# minuto sin provocarlos.
DEFAULT_CALLS_PER_MIN = 300.0
_SIN_TOPE = {"0", "none", "null", "unlimited", "inf", "sin_tope", "ilimitado"}


def _env_float(nombre, default=None):
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        return default
    try:
        return float(valor)
    except ValueError:
        return default


def _parse_calls_per_min(valor, default=DEFAULT_CALLS_PER_MIN):
    """Interpreta el tope de llamadas: None/float. Vacio -> default; 0 o
    'unlimited' -> None (sin limitador); numero invalido -> default."""
    if valor is None:
        return default
    if isinstance(valor, (int, float)):
        return None if valor <= 0 or not np.isfinite(valor) else float(valor)
    texto = str(valor).strip().lower()
    if not texto:
        return default
    if texto in _SIN_TOPE:
        return None
    try:
        num = float(texto)
    except ValueError:
        return default
    return None if num <= 0 or not np.isfinite(num) else num


CALLS_PER_MIN = _parse_calls_per_min(os.environ.get("POLYGON_CALLS_PER_MIN"))
SNAPSHOT_TTL_SEC = _env_float("POLYGON_SNAPSHOT_TTL_MIN", 60.0) * 60.0
CACHE_DIR = os.environ.get("POLYGON_CACHE_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".cache", "polygon")

BASE_URL = "https://api.polygon.io"
STATUS_TRANSITORIOS = {429, 500, 502, 503, 504}


# ==============================================================================
# 1. LIMITADOR DE TASA
# ==============================================================================
# Espaciado uniforme entre llamadas (60 / CALLS_PER_MIN segundos), compartido
# por todos los hilos. Las respuestas servidas desde cache no lo consumen.
# ==============================================================================

class _Limitador:
    def __init__(self, llamadas_por_min):
        self.lock = threading.Lock()
        self.proxima = 0.0
        self.configurar(llamadas_por_min)

    def configurar(self, llamadas_por_min):
        with self.lock:
            self.intervalo = 60.0 / llamadas_por_min if llamadas_por_min else 0.0

    def esperar(self):
        if self.intervalo <= 0:
            return
        with self.lock:
            ahora = time.monotonic()
            turno = max(ahora, self.proxima)
            self.proxima = turno + self.intervalo
        if turno > ahora:
            time.sleep(turno - ahora)


_limitador = _Limitador(CALLS_PER_MIN)


def set_rate_limit(calls_per_min):
    """Cambia el tope de llamadas por minuto en tiempo de ejecucion.

    Acepta lo mismo que la variable de entorno: un numero, 0/None/'unlimited'
    para desactivar el limitador. Devuelve el tope efectivo (None = sin tope).
    """
    global CALLS_PER_MIN
    CALLS_PER_MIN = _parse_calls_per_min(calls_per_min, default=None)
    _limitador.configurar(CALLS_PER_MIN)
    return CALLS_PER_MIN


def estimate_minutes(n_llamadas):
    """Minutos minimos que toman n llamadas bajo el tope configurado (None si no hay tope)."""
    if not CALLS_PER_MIN:
        return None
    return n_llamadas / CALLS_PER_MIN


# ==============================================================================
# 2. DIAGNOSTICO
# ==============================================================================

diag = {
    "status_counts": {},
    "sample_errors": [],
    "http_calls": 0,
    "cache_hits": 0,
    "incompletas": 0,
    "truncadas_max_pages": 0,
}
_diag_lock = threading.Lock()


def _registrar(status, cuerpo=None):
    with _diag_lock:
        clave = str(status)
        diag["status_counts"][clave] = diag["status_counts"].get(clave, 0) + 1
        if status != 200 and len(diag["sample_errors"]) < 5:
            diag["sample_errors"].append({"status": status, "body": (cuerpo or "")[:200]})


def _sumar(clave, n=1):
    with _diag_lock:
        diag[clave] += n


def print_diagnostics(prefijo="  "):
    """Resumen de llamadas a Polygon: codigos HTTP, cache y cadenas incompletas."""
    tope = f"{CALLS_PER_MIN:g}/min" if CALLS_PER_MIN else "sin tope"
    print(f"{prefijo}Llamadas HTTP a Polygon: {diag['http_calls']} (limitador: {tope}) | "
          f"respuestas desde cache: {diag['cache_hits']}")
    for k, v in sorted(diag["status_counts"].items()):
        print(f"{prefijo}   status {k}: {v}")
    if diag["incompletas"] or diag["truncadas_max_pages"]:
        print(f"{prefijo}Consultas paginadas incompletas (descartadas): {diag['incompletas']} | "
              f"truncadas por max_pages: {diag['truncadas_max_pages']}")
    if diag["sample_errors"]:
        print(f"{prefijo}Ejemplos de error (hasta 5):")
        for e in diag["sample_errors"]:
            print(f"{prefijo}   status={e['status']} | {e['body'] or '(sin cuerpo)'}")


def n_fallos_transitorios():
    """Llamadas que terminaron en 429/5xx/red tras agotar los reintentos."""
    return sum(v for k, v in diag["status_counts"].items()
               if k in {str(s) for s in STATUS_TRANSITORIOS} or k == "red")


# ==============================================================================
# 3. CACHE EN DISCO
# ==============================================================================
# Cada entrada es un JSON {"ts": epoch, "data": ...}. Las entradas
# permanentes ignoran la antiguedad; las de snapshot vencen tras
# SNAPSHOT_TTL_SEC. La escritura es atomica (archivo temporal + replace), de
# modo que varios hilos pueden escribir sin corromper la cache.
# ==============================================================================

def _ruta_cache(clave):
    h = hashlib.sha1(clave.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, h[:2], h + ".json")


def cache_get(clave, permanente=True):
    ruta = _ruta_cache(clave)
    try:
        with open(ruta, "r", encoding="utf-8") as fh:
            entrada = json.load(fh)
    except (OSError, ValueError):
        return None
    if not permanente and time.time() - entrada.get("ts", 0) > SNAPSHOT_TTL_SEC:
        return None
    return entrada.get("data")


def cache_set(clave, data):
    ruta = _ruta_cache(clave)
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        tmp = f"{ruta}.{threading.get_ident()}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"ts": time.time(), "data": data}, fh)
        os.replace(tmp, ruta)
    except OSError:
        pass


def _sin_api_key(url):
    return re.sub(r"([?&])apiKey=[^&]*&?", r"\1", url).rstrip("?&")


def _con_api_key(url, api_key):
    return f"{url}{'&' if '?' in url else '?'}apiKey={api_key}"


_aviso_api_key_emitido = False


def _avisar_sin_api_key():
    global _aviso_api_key_emitido
    if _aviso_api_key_emitido:
        return
    _aviso_api_key_emitido = True
    warnings.warn(
        "POLYGON_API_KEY no esta definida: todas las consultas a Polygon fallaran "
        "con status 'sin_api_key' y los scripts usaran sus estimadores historicos.",
        RuntimeWarning, stacklevel=3)


def polygon_format_ticker(ticker):
    """Ticker en el formato que espera Polygon para acciones de EE. UU.

    Yahoo separa las clases de accion con guion (BRK-B, BF-B); Polygon usa
    punto (BRK.B, BF.B). Antes esta traduccion solo existia en
    quadratic_utility.py: en minimum_variance.py esos tickers no encontraban
    cadena y caian al estimador historico sin aviso (M-14).
    """
    if ticker is None:
        return ticker
    return str(ticker).strip().replace("-", ".")


# ==============================================================================
# 4. PETICIONES
# ==============================================================================

def get_json(url, api_key=None, permanente=False, max_retries=5, timeout=20, backoff=1.0):
    """GET con cache, limitador y reintentos. `url` va SIN apiKey.

    Devuelve (data, status). data es None si la respuesta no fue 200.
    status es el codigo HTTP final, o "red" si nunca hubo respuesta.
    Solo se guardan en cache las respuestas 200: un 429 o un timeout no deja
    marcado el recurso como inexistente.
    """
    api_key = api_key or API_KEY
    clave = _sin_api_key(url)
    usar_cache = permanente or SNAPSHOT_TTL_SEC > 0
    if usar_cache:
        data = cache_get(clave, permanente=permanente)
        if data is not None:
            _sumar("cache_hits")
            return data, 200
    if not api_key:
        _registrar("sin_api_key")
        _avisar_sin_api_key()
        return None, "sin_api_key"

    status = "red"
    for intento in range(1, max_retries + 1):
        _limitador.esperar()
        _sumar("http_calls")
        try:
            resp = requests.get(_con_api_key(clave, api_key), timeout=timeout)
        except requests.RequestException:
            status = "red"
            time.sleep(backoff * 2 ** (intento - 1))
            continue
        status = resp.status_code
        if status == 200:
            _registrar(200)
            try:
                data = resp.json()
            except ValueError:
                _registrar("json_invalido")
                return None, "json_invalido"
            if usar_cache:
                cache_set(clave, data)
            return data, 200
        if status in STATUS_TRANSITORIOS:
            espera = None
            try:
                espera = float(resp.headers.get("retry-after"))
            except (TypeError, ValueError):
                pass
            time.sleep(espera if espera and espera > 0 else backoff * 2 ** (intento - 1))
            continue
        _registrar(status, resp.text)
        return None, status

    _registrar(status, "reintentos agotados")
    return None, status


def get_all(url, api_key=None, permanente=False, max_pages=40, **kwargs):
    """Todas las paginas de un endpoint v3 siguiendo next_url.

    Devuelve (results, completo, status). completo es False si alguna pagina
    fallo o si se alcanzo max_pages con paginas pendientes; en ese caso el
    llamador NO debe usar `results` como si fuera la cadena completa.
    """
    resultados = []
    siguiente = url
    for _ in range(max_pages):
        data, status = get_json(siguiente, api_key=api_key, permanente=permanente, **kwargs)
        if data is None:
            _sumar("incompletas")
            return resultados, False, status
        resultados.extend(data.get("results") or [])
        siguiente = data.get("next_url")
        if not siguiente:
            return resultados, True, 200
    _sumar("truncadas_max_pages")
    return resultados, False, "max_pages"


def es_transitorio(status):
    """True si el fallo puede resolverse reintentando (429/5xx, red, paginas
    truncadas). La ausencia de API key NO es transitoria: reintentar no la
    resuelve y marcarla asi hacia que los scripts contaran esos fallos como
    "limite de tasa o red" (B-11)."""
    return status in STATUS_TRANSITORIOS or status in ("red", "max_pages")


# ==============================================================================
# 5. CADENA OTM DE UN UNICO VENCIMIENTO (BKM)
# ==============================================================================
# La integracion BKM supone un unico horizonte T. Mezclar vencimientos y
# quedarse con el primer contrato de cada strike (drop_duplicates) combinaba
# precios de plazos distintos. Aqui se toma el vencimiento mas cercano al DTE
# objetivo que tenga calls OTM y puts OTM, y solo sus contratos.
# ==============================================================================

_COLS_CADENA = ["strike", "iv", "type"]


def fetch_otm_chain(underlying, S, fecha_min, fecha_max, strike_min, strike_max,
                    target_dte, api_key=None, strike_fmt="{:.2f}", max_pages=40):
    """Cadena OTM (calls K >= S, puts K < S) de un unico vencimiento.

    Devuelve (calls_df, puts_df, info). info trae completo (False si la
    descarga quedo incompleta por un fallo transitorio), status, expiracion
    elegida y dte.
    """
    vacio = pd.DataFrame(columns=_COLS_CADENA)
    info = {"completo": True, "status": 200, "expiracion": None, "dte": np.nan}
    if S is None or not np.isfinite(S) or S <= 0:
        return vacio, vacio.copy(), info

    filas = []
    for tipo in ("call", "put"):
        url = (
            f"{BASE_URL}/v3/snapshot/options/{underlying}?"
            f"contract_type={tipo}&"
            f"strike_price.gte={strike_fmt.format(strike_min)}&"
            f"strike_price.lte={strike_fmt.format(strike_max)}&"
            f"expiration_date.gte={fecha_min}&expiration_date.lte={fecha_max}&"
            f"limit=250"
        )
        results, completo, status = get_all(url, api_key=api_key, max_pages=max_pages)
        if not completo:
            info.update(completo=False, status=status)
            return vacio, vacio.copy(), info
        for c in results:
            det = c.get("details") or {}
            iv = c.get("implied_volatility")
            if iv is None or not np.isfinite(iv) or iv <= 0:
                continue
            filas.append(dict(strike=det.get("strike_price"), iv=iv, type=tipo,
                              expiracion=det.get("expiration_date")))

    if not filas:
        return vacio, vacio.copy(), info

    df = pd.DataFrame(filas).dropna(subset=["strike", "expiracion"])
    df = df[((df["type"] == "call") & (df["strike"] >= S))
            | ((df["type"] == "put") & (df["strike"] < S))]
    if df.empty:
        return vacio, vacio.copy(), info

    hoy = pd.Timestamp(date.today())
    por_venc = df.groupby("expiracion").agg(
        n_call=("type", lambda s: int((s == "call").sum())),
        n_put=("type", lambda s: int((s == "put").sum())),
    ).reset_index()
    por_venc = por_venc[(por_venc["n_call"] > 0) & (por_venc["n_put"] > 0)]
    if por_venc.empty:
        return vacio, vacio.copy(), info
    por_venc["dte"] = (pd.to_datetime(por_venc["expiracion"]) - hoy).dt.days
    por_venc["_dist"] = (por_venc["dte"] - target_dte).abs()
    por_venc["_n"] = -(por_venc["n_call"] + por_venc["n_put"])
    elegido = por_venc.sort_values(["_dist", "_n"]).iloc[0]

    df = df[df["expiracion"] == elegido["expiracion"]]
    calls = df[df["type"] == "call"][_COLS_CADENA].drop_duplicates("strike").reset_index(drop=True)
    puts = df[df["type"] == "put"][_COLS_CADENA].drop_duplicates("strike").reset_index(drop=True)
    info.update(expiracion=elegido["expiracion"], dte=int(elegido["dte"]))
    return calls, puts, info
