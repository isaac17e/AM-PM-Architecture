# ==============================================================================
# MARKET_DATA - Preparacion de precios multi-mercado compartida por los optimizadores
# ==============================================================================
# Logica extraida de minimum_variance.py (y su version estacional) para que
# sea testeable sin ejecutar el script completo:
#
#   1. Moneda por ticker: la que reporta el proveedor (yfinance) manda; el
#      sufijo del ticker (.TO, .L, .T, ...) es el respaldo y un override
#      manual solo se usa si el proveedor no informa. Si un override o un
#      sufijo contradicen al proveedor se devuelve el conflicto para avisar
#      (A-2: HSBC y BP son ADRs en USD, no GBP).
#   2. Alineacion de precios diarios de varios mercados a un calendario
#      maestro con ffill acotado (M-1): un festivo en Tokio ya no borra el
#      dia para los ~200 tickers.
#   3. Semana parcial: la ultima observacion de un resample("W") se descarta
#      si la semana no esta completa (B-6).
#   4. Orden de los internacionales por market cap en USD antes de tomar el
#      top N: la lista fija ponia primero los 15 .TO.
# ==============================================================================

import json
import math
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import yfinance as yf

__all__ = [
    "normalize_currency",
    "price_scale_factor",
    "currency_from_suffix",
    "resolve_currencies",
    "es_ticker_formato_us",
    "region_de_ticker",
    "combinar_tickers",
    "convertir_serie_a_usd",
    "align_prices_to_calendar",
    "drop_partial_last_week",
    "resolve_execution_months",
    "dedupe_share_classes",
    "frames_from_yf_download",
    "yfinance_spot_batch",
    "yfinance_spot_single",
    "default_spot_providers",
    "get_spot_history",
    "spot_series_for",
    "default_market_cap_cache_path",
    "yfinance_market_caps",
    "yfinance_fx_rates",
    "market_caps_usd",
    "ordenar_por_market_cap",
    "tabla_market_cap_texto",
]

# Un solo hilo toca el reintento de un ticker. La descarga en bloque va
# aparte, antes de cualquier pool.
_SPOT_SINGLE_LOCK = threading.Lock()

# Codigos que yfinance usa para unidades menores (peniques, centimos de rand).
_MINOR_UNITS = {"GBP": "GBP", "GBX": "GBP", "ZAC": "ZAR", "ILA": "ILS"}
_MINOR_UNIT_RAW = {"GBp", "GBX", "ZAc", "ILA"}


def normalize_currency(code):
    """Codigo ISO en mayusculas; GBp/GBX -> GBP, ZAc -> ZAR. None si vacio."""
    if code is None:
        return None
    texto = str(code).strip()
    if not texto or texto.lower() in ("nan", "none"):
        return None
    up = texto.upper()
    return _MINOR_UNITS.get(up, up)


def price_scale_factor(code):
    """0.01 si el proveedor cotiza en unidad menor (GBp, ZAc), 1.0 en otro caso."""
    if code is None:
        return 1.0
    return 0.01 if str(code).strip() in _MINOR_UNIT_RAW else 1.0


def currency_from_suffix(ticker, suffix_map):
    """Moneda por sufijo del ticker (p. ej. {'.TO': 'CAD'}); None si no hay sufijo conocido.

    El sufijo mas largo que coincida gana: .TO es CAD y no JPY, aunque el
    mapa liste .T despues. endswith(".T") es falso para SHOP.TO.
    """
    t = str(ticker)
    mejor = None
    for suf, cur in suffix_map.items():
        if t.endswith(suf) and (mejor is None or len(suf) > len(mejor[0])):
            mejor = (suf, cur)
    return None if mejor is None else mejor[1]


def es_ticker_formato_us(ticker):
    """Formato de ticker estadounidense: largo 1-5, sin ^/$, sin digito inicial.

    No decide la bolsa. BRK-B pasa; SHOP.TO, 7203.T y ULVR.L no. Esos
    ultimos son internacionales y no deben entrar a este predicado.
    """
    if ticker is None:
        return False
    t = str(ticker).strip()
    if not t or re.search(r"\^|\$", t):
        return False
    if not (1 <= len(t) <= 5):
        return False
    if re.match(r"^[0-9]", t):
        return False
    return True


def region_de_ticker(ticker):
    """Region para el tope max_region_weight. ADRs sin sufijo (HSBC, BP) quedan en US.

    .TO no cae en Japon: el sufijo japones es .T, y .TO no termina en .T.
    """
    t = "" if ticker is None else str(ticker)
    if t.endswith(".TO"):
        return "Canada"
    if re.search(r"\.(DE|L|PA|MC)$", t):
        return "Europa"
    if t.endswith(".T"):
        return "Japon"
    return "US"


def combinar_tickers(domesticos, internacionales):
    """Filtra el formato US solo en domesticos y luego concatena internacionales.

    Aplicar el filtro a la lista ya mezclada elimina los sufijos de bolsa
    (.DE, .TO, .L, .PA, .MC) y los tickers japoneses que empiezan por digito.
    """
    ok = [t for t in domesticos if es_ticker_formato_us(t)]
    return list(dict.fromkeys(list(ok) + list(internacionales)))


def convertir_serie_a_usd(precios, fx):
    """Precios en moneda local por el FX (USD por unidad local), con ffill.

    Si el FX no cubre el arranque, esas fechas quedan NaN. Sin serie FX se
    devuelve el precio tal cual.
    """
    if precios is None or fx is None:
        return precios
    fx = pd.Series(fx).dropna().sort_index()
    if len(fx) == 0:
        return precios
    union = fx.index.union(precios.index)
    alineado = fx.reindex(union).sort_index().ffill().reindex(precios.index)
    return precios * alineado


def resolve_currencies(tickers, suffix_map, overrides=None, provider=None, default="USD"):
    """Moneda final por ticker y lista de conflictos.

    Precedencia: proveedor > override manual > sufijo > default.

    Parametros
    ----------
    tickers : iterable de tickers.
    suffix_map : {sufijo: moneda}.
    overrides : {ticker: moneda} manual. Solo se aplica si el proveedor no
        informa; si lo contradice se registra un conflicto con fuente
        "override".
    provider : {ticker: codigo del proveedor} (p. ej. history_metadata
        ["currency"] de yfinance). Puede faltar para algunos tickers.

    Devuelve (currency_map, conflicts). Cada conflicto es un dict con ticker,
    fuente ("override" o "sufijo"), manual y proveedor.
    """
    overrides = overrides or {}
    provider = provider or {}
    out, conflicts = {}, []
    for t in tickers:
        prov = normalize_currency(provider.get(t))
        manual = overrides.get(t)
        sufijo = currency_from_suffix(t, suffix_map)
        if prov is not None:
            out[t] = prov
            if manual is not None and normalize_currency(manual) != prov:
                conflicts.append({"ticker": t, "fuente": "override", "manual": manual, "proveedor": prov})
            elif sufijo is not None and normalize_currency(sufijo) != prov:
                conflicts.append({"ticker": t, "fuente": "sufijo", "manual": sufijo, "proveedor": prov})
        elif manual is not None:
            out[t] = normalize_currency(manual)
        elif sufijo is not None:
            out[t] = normalize_currency(sufijo)
        else:
            out[t] = default
    return out, conflicts


def align_prices_to_calendar(prices, calendar, max_ffill=2, min_coverage=0.80):
    """Alinea precios diarios de varios mercados a un calendario maestro.

    1. Se rellena hacia adelante cada ticker como maximo `max_ffill` dias
       sobre la union de fechas (un festivo local se cubre con el ultimo
       cierre disponible; una laguna larga no).
    2. Se reindexa al `calendar` (p. ej. dias de negociacion del benchmark).
       Los cierres en fechas fuera del calendario no se pierden: el siguiente
       dia del calendario arrastra el nivel acumulado.
    3. Se descartan los tickers con cobertura < min_coverage y, por ultimo,
       las filas que aun tengan NaN (inicio de historia, lagunas largas).

    Devuelve (aligned, info) con info = {n_filled: Series por ticker,
    dropped_low_coverage: list, n_rows_dropped: int, n_rows: int,
    coverage: Series}.
    """
    if not isinstance(prices.index, pd.DatetimeIndex):
        raise TypeError("prices debe tener DatetimeIndex")
    calendar = pd.DatetimeIndex(calendar).sort_values().unique()
    if len(calendar) == 0:
        raise ValueError("calendar vacio")

    union = prices.index.union(calendar)
    full = prices.reindex(union)
    if max_ffill and max_ffill > 0:
        filled = full.ffill(limit=int(max_ffill))
    else:
        filled = full
    on_cal = filled.reindex(calendar)
    raw_on_cal = full.reindex(calendar)
    n_filled = (on_cal.notna() & raw_on_cal.isna()).sum()

    coverage = on_cal.notna().mean()
    keep = coverage[coverage >= min_coverage].index.tolist()
    dropped = [c for c in on_cal.columns if c not in keep]
    on_cal = on_cal[keep]

    aligned = on_cal.dropna(how="any")
    info = {
        "n_filled": n_filled.reindex(keep),
        "dropped_low_coverage": dropped,
        "n_rows_dropped": int(len(on_cal) - len(aligned)),
        "n_rows": int(len(aligned)),
        "coverage": coverage,
    }
    return aligned, info


def drop_partial_last_week(weekly, last_daily_date, trading_days_per_week=5):
    """Descarta la ultima fila de un resample("W") si la semana no esta completa.

    resample("W") etiqueta cada semana con su domingo. La semana se considera
    completa si el ultimo dato diario llega al viernes (etiqueta - 2 dias) o
    mas tarde. Devuelve (weekly_sin_parcial, descartada: bool).
    """
    if weekly is None or len(weekly) == 0:
        return weekly, False
    last_label = pd.Timestamp(weekly.index[-1])
    last_daily = pd.Timestamp(last_daily_date)
    friday = last_label - pd.Timedelta(days=7 - trading_days_per_week)
    if last_daily < friday:
        return weekly.iloc[:-1], True
    return weekly, False


def resolve_execution_months(months, as_of=None, n_months=1):
    """Meses de la corrida estacional.

    `months=None` arma `n_months` meses consecutivos desde el mes de `as_of`
    (octubre -> [10], o [10, 11] si n_months=2). Una lista explicita se
    devuelve igual. Si esa lista no contiene el mes en curso, el segundo
    valor es un aviso: el default no se reescribe solo.
    """
    as_of = pd.Timestamp.today() if as_of is None else pd.Timestamp(as_of)
    n_months = int(n_months)
    if n_months < 1:
        raise ValueError("n_months debe ser >= 1")
    if months is None:
        start = int(as_of.month)
        return [((start - 1 + i) % 12) + 1 for i in range(n_months)], None
    out = [int(m) for m in months]
    aviso = None
    if int(as_of.month) not in out:
        aviso = (
            f"los meses configurados {out} no incluyen el mes en curso "
            f"({int(as_of.month)}). El horizonte no cambia solo; "
            f"pasa None para usar el mes de la corrida."
        )
    return out, aviso


def dedupe_share_classes(tickers, groups=(("GOOGL", "GOOG"),)):
    """Deja una sola clase cuando el grupo esta repetido.

    Cada grupo es una tupla: el primer ticker presente es el que se queda
    (GOOGL antes que GOOG). El orden del resto de la lista no cambia.
    Devuelve (lista, notas). Cada nota es (se_queda, [se_van]).
    """
    presentes = set(tickers)
    drop = set()
    notas = []
    for group in groups:
        encontrados = [t for t in group if t in presentes]
        if len(encontrados) <= 1:
            continue
        se_queda = encontrados[0]
        se_van = encontrados[1:]
        drop.update(se_van)
        notas.append((se_queda, se_van))
    kept = [t for t in tickers if t not in drop]
    return kept, notas


# ==============================================================================
# CIERRES SIN AJUSTAR PARA EL FILTRO HISTORICO DE MFIS
# ==============================================================================
# yfinance, llamado desde varios hilos, responde "possibly delisted" y el
# ticker pasa el filtro sin historia. La descarga es una sola llamada para
# todos los tickers; lo que falte se reintenta en serie, bajo un lock.
# Otro proveedor (FMP, mas adelante) entra como otro elemento de `providers`:
# {"name", "batch", "single"}. No hay un segundo proveedor cableado ahora.

def _naive_dates(values):
    dt = pd.to_datetime(values)
    tz = getattr(dt.dt, "tz", None) if isinstance(dt, pd.Series) else getattr(dt, "tz", None)
    if tz is not None:
        dt = dt.dt.tz_localize(None) if isinstance(dt, pd.Series) else dt.tz_localize(None)
    return dt


def _frame_from_close(close):
    """Serie de cierres -> DataFrame con columnas date y close, o None."""
    if close is None:
        return None
    serie = pd.Series(close).dropna()
    if serie.empty:
        return None
    frame = serie.rename("close").reset_index()
    frame.columns = ["date", "close"]
    frame["date"] = _naive_dates(frame["date"])
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna(subset=["date", "close"])
    if frame.empty:
        return None
    return frame.reset_index(drop=True)


def _usable_spot(frame, min_obs):
    if frame is None or not isinstance(frame, pd.DataFrame):
        return False
    if "date" not in frame.columns or "close" not in frame.columns:
        return False
    cierres = pd.to_numeric(frame["close"], errors="coerce")
    return int(cierres.notna().sum()) >= int(min_obs)


def frames_from_yf_download(raw, tickers):
    """Parte un `yf.download` (uno o varios tickers) en {ticker: frame}.

    Acepta columnas planas (Close) y MultiIndex en los dos ordenes que ha
    usado yfinance: (campo, ticker) o (ticker, campo). Un ticker ausente o
    con el cierre vacio queda en None.
    """
    tickers = list(tickers)
    vacio = {t: None for t in tickers}
    if raw is None or not isinstance(raw, pd.DataFrame) or raw.empty:
        return vacio
    campos = {"Open", "High", "Low", "Close", "Adj Close", "Volume",
              "open", "high", "low", "close", "adj close", "volume"}

    def _cerrar(columna):
        nombre = str(columna)
        return nombre == "Close" or nombre.lower() == "close"

    if isinstance(raw.columns, pd.MultiIndex):
        nivel0 = [str(v) for v in raw.columns.get_level_values(0)]
        if any(v in campos for v in nivel0):
            nivel_campo, nivel_ticker = 0, 1
        else:
            nivel_campo, nivel_ticker = 1, 0
        presentes = set(raw.columns.get_level_values(nivel_ticker))
        for ticker in tickers:
            if ticker not in presentes:
                continue
            try:
                bloque = raw.xs(ticker, axis=1, level=nivel_ticker)
            except KeyError:
                continue
            if isinstance(bloque, pd.Series):
                vacio[ticker] = _frame_from_close(bloque)
                continue
            col = next((c for c in bloque.columns if _cerrar(c)), None)
            if col is None:
                continue
            vacio[ticker] = _frame_from_close(bloque[col])
        return vacio

    if len(tickers) == 1:
        col = next((c for c in raw.columns if _cerrar(c)), None)
        if col is not None:
            vacio[tickers[0]] = _frame_from_close(raw[col])
    return vacio


def yfinance_spot_batch(tickers, start, end):
    """Una descarga de cierres sin ajustar. Sin hilos internos de yfinance."""
    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {}
    raw = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=False,
        progress=False,
        threads=False,
        group_by="column",
    )
    return frames_from_yf_download(raw, tickers)


def yfinance_spot_single(ticker, start, end):
    """Un ticker: primero `download`, y si no hay cierre, `Ticker.history`."""
    try:
        raw = yf.download(
            ticker, start=start, end=end, auto_adjust=False,
            progress=False, threads=False,
        )
        frame = frames_from_yf_download(raw, [ticker]).get(ticker)
        if frame is not None and len(frame):
            return frame
    except Exception:
        frame = None
    try:
        hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
        return frames_from_yf_download(hist, [ticker]).get(ticker)
    except Exception:
        return None


def default_spot_providers():
    """Proveedor por defecto. Un respaldo futuro se agrega a esta lista."""
    return [{
        "name": "yfinance",
        "batch": yfinance_spot_batch,
        "single": yfinance_spot_single,
    }]


def _retry_spot_single(single, ticker, start, end, retries, backoff, sleep, min_obs, stats):
    """Hasta `retries` intentos, en serie y bajo lock. Devuelve el frame o None."""
    espera = float(backoff)
    for intento in range(int(retries)):
        if intento:
            sleep(espera)
            espera *= 2.0
        with _SPOT_SINGLE_LOCK:
            stats["single_calls"] += 1
            try:
                frame = single(ticker, start, end)
            except Exception:
                frame = None
        if _usable_spot(frame, min_obs):
            return frame
    return None


def get_spot_history(tickers, start, end, providers=None, min_obs=20,
                     retries=3, backoff=1.0, sleep=None):
    """Cierres sin ajustar para varios tickers.

    El primer proveedor descarga el bloque entero una vez. Los tickers que
    no vuelven con al menos `min_obs` cierres se reintentan uno por uno
    (`retries` veces, espera `backoff` que se duplica). Si siguen vacios,
    el siguiente proveedor de la lista hace lo mismo solo con esos tickers.
    La lista por defecto es yfinance. FMP, si se agrega, es otro dict
    `{"name", "batch", "single"}` al final.

    Devuelve series (solo las utilizables), missing, recovered, batch_calls
    y single_calls. `recovered` son los que no trajo el primer bloque y si
    entro un reintento o un proveedor posterior.
    """
    if sleep is None:
        sleep = time.sleep
    if providers is None:
        providers = default_spot_providers()
    orden = list(dict.fromkeys(tickers))
    series = {}
    pending = list(orden)
    from_first_batch = set()
    stats = {"batch_calls": 0, "single_calls": 0}
    primer_bloque = True

    for provider in providers:
        if not pending:
            break
        batch = provider.get("batch") if isinstance(provider, dict) else None
        single = provider.get("single") if isinstance(provider, dict) else None
        if batch is not None:
            stats["batch_calls"] += 1
            try:
                obtenido = batch(list(pending), start, end) or {}
            except Exception:
                obtenido = {}
            for ticker in list(pending):
                frame = obtenido.get(ticker)
                if _usable_spot(frame, min_obs):
                    series[ticker] = frame
                    pending.remove(ticker)
                    if primer_bloque:
                        from_first_batch.add(ticker)
        primer_bloque = False
        if single is None or not pending:
            continue
        for ticker in list(pending):
            frame = _retry_spot_single(
                single, ticker, start, end, retries, backoff, sleep, min_obs, stats)
            if frame is not None:
                series[ticker] = frame
                pending.remove(ticker)

    return {
        "series": series,
        "missing": [t for t in orden if t not in series],
        "recovered": [t for t in orden if t in series and t not in from_first_batch],
        "batch_calls": stats["batch_calls"],
        "single_calls": stats["single_calls"],
    }


def spot_series_for(store, ticker):
    """Lee una serie ya precargada. No descarga nada."""
    if not store:
        return None
    return store.get(ticker)


# ==============================================================================
# 4. ORDEN DE INTERNACIONALES POR MARKET CAP (USD)
# ==============================================================================
# yfinance da el market cap en la moneda de cotizacion. fast_info lo calcula
# con el ultimo precio, asi que en unidad menor (GBp) viene x100: AZN.L da
# 1.84e13 en fast_info y 1.84e11 en info. Se escala con price_scale_factor
# de la moneda de fast_info; info ya viene en unidad mayor. La conversion a
# USD usa la moneda del sufijo (currency_from_suffix) y los mismos pares FX
# de los scripts. La cache guarda el cap local y el FX, cada uno con su TTL.

MARKET_CAP_TTL_HORAS = 24 * 7
FX_SPOT_TTL_HORAS = 24
_CACHE_LOCK = threading.Lock()


def default_market_cap_cache_path():
    """Cache compartida entre corridas, fuera del repositorio. "" la desactiva."""
    ruta = os.environ.get("AMPM_MARKET_CAP_CACHE")
    if ruta is not None:
        return ruta or None
    return os.path.join(os.path.expanduser("~"), ".cache", "am-pm", "market_cap.json")


def _leer_cache(ruta):
    if not ruta:
        return {}
    try:
        with open(ruta, encoding="utf-8") as fh:
            datos = json.load(fh)
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def _escribir_cache(ruta, datos):
    if not ruta:
        return
    try:
        os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
        tmp = f"{ruta}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(datos, fh)
        os.replace(tmp, ruta)
    except OSError:
        pass


def _vigente(entrada, ahora, ttl_horas):
    try:
        return ahora - float(entrada["ts"]) <= ttl_horas * 3600.0 and math.isfinite(float(entrada["valor"]))
    except (KeyError, TypeError, ValueError):
        return False


def _positivo(valor):
    try:
        num = float(valor)
    except (TypeError, ValueError):
        return None
    return num if math.isfinite(num) and num > 0 else None


def _campo(obj, *nombres):
    for nombre in nombres:
        try:
            valor = obj[nombre] if hasattr(obj, "__getitem__") else getattr(obj, nombre)
        except Exception:
            valor = getattr(obj, nombre, None)
        if valor is not None:
            return valor
    return None


def _market_cap_yf(ticker_obj):
    """Market cap en unidad mayor de la moneda de cotizacion, o None."""
    try:
        fi = ticker_obj.fast_info
        cap = _positivo(_campo(fi, "marketCap", "market_cap"))
        if cap is not None:
            return cap * price_scale_factor(_campo(fi, "currency"))
    except Exception:
        pass
    try:
        return _positivo((ticker_obj.info or {}).get("marketCap"))
    except Exception:
        return None


def yfinance_market_caps(tickers, max_workers=8):
    """{ticker: cap en unidad mayor local}, todo el lote en hilos.

    Los que no traen dato no aparecen.
    """
    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {}

    def _uno(t):
        return t, _market_cap_yf(yf.Ticker(t))

    with ThreadPoolExecutor(max_workers=max(1, min(int(max_workers), len(tickers)))) as ex:
        return {t: cap for t, cap in ex.map(_uno, tickers) if cap is not None}


def yfinance_fx_rates(fx_pairs):
    """USD por unidad local con el ultimo cierre de cada par, en una descarga."""
    if not fx_pairs:
        return {}
    pares = {cur: info["ticker"] for cur, info in fx_pairs.items()}
    raw = yf.download(list(dict.fromkeys(pares.values())), period="10d", interval="1d",
                      auto_adjust=True, progress=False, threads=False, group_by="column")
    out = {}
    if raw is None or len(raw) == 0:
        return out
    cierre = raw["Close"] if "Close" in raw.columns.get_level_values(0) else raw
    for cur, tk in pares.items():
        try:
            serie = cierre[tk] if isinstance(cierre, pd.DataFrame) else cierre
        except KeyError:
            continue
        serie = pd.to_numeric(serie, errors="coerce").dropna()
        valor = _positivo(serie.iloc[-1]) if len(serie) else None
        if valor is None:
            continue
        out[cur] = 1.0 / valor if fx_pairs[cur].get("invert") else valor
    return out


def _con_reintentos(funcion, pendientes, retries, backoff, sleep):
    """Llama `funcion(pendientes)` hasta `retries` veces con los que sigan faltando.

    Una excepcion cuenta como intento sin datos. Devuelve el dict acumulado.
    """
    obtenido = {}
    faltan = list(pendientes)
    espera = float(backoff)
    for intento in range(max(1, int(retries))):
        if not faltan:
            break
        if intento:
            sleep(espera)
            espera *= 2.0
        try:
            nuevo = funcion(list(faltan)) or {}
        except Exception:
            nuevo = {}
        for k, v in nuevo.items():
            if k in faltan and _positivo(v) is not None:
                obtenido[k] = float(v)
        faltan = [k for k in faltan if k not in obtenido]
    return obtenido


def market_caps_usd(tickers, suffix_map, fx_pairs, cap_provider=None, fx_provider=None,
                    cache_path="default", retries=3, backoff=1.0, sleep=None, now=None,
                    cap_ttl_hours=MARKET_CAP_TTL_HORAS, fx_ttl_hours=FX_SPOT_TTL_HORAS,
                    monedas=None):
    """Market cap en USD por ticker (None si falta el cap o el FX de su moneda).

    `cap_provider(tickers) -> {ticker: cap local}` se llama en lote solo con
    los que no estan en cache, y se reintenta con los que falten.
    `fx_provider(fx_pairs) -> {moneda: USD por unidad}` igual. Moneda:
    `monedas[ticker]` si se da (la que reporta el proveedor de precios); si
    no, por sufijo; sin sufijo conocido (HSBC, BP) es USD.
    Devuelve {"usd": {...}, "moneda": {...}, "llamadas": n}.
    """
    sleep = time.sleep if sleep is None else sleep
    cap_provider = yfinance_market_caps if cap_provider is None else cap_provider
    fx_provider = yfinance_fx_rates if fx_provider is None else fx_provider
    ruta = default_market_cap_cache_path() if cache_path == "default" else cache_path
    ahora = time.time() if now is None else float(now)
    orden = list(dict.fromkeys(tickers))
    monedas = monedas or {}
    moneda = {t: normalize_currency(monedas.get(t)) or currency_from_suffix(t, suffix_map) or "USD"
              for t in orden}
    llamadas = 0

    with _CACHE_LOCK:
        cache = _leer_cache(ruta)
    caps_cache = cache.get("cap", {}) if isinstance(cache.get("cap"), dict) else {}
    fx_cache = cache.get("fx", {}) if isinstance(cache.get("fx"), dict) else {}

    caps = {t: float(caps_cache[t]["valor"]) for t in orden
            if t in caps_cache and _vigente(caps_cache[t], ahora, cap_ttl_hours)}
    faltan = [t for t in orden if t not in caps]
    if faltan:
        def _llamar_caps(lista):
            nonlocal llamadas
            llamadas += 1
            return cap_provider(lista)
        nuevos = _con_reintentos(_llamar_caps, faltan, retries, backoff, sleep)
        caps.update(nuevos)
        for t, v in nuevos.items():
            caps_cache[t] = {"valor": v, "ts": ahora}

    monedas = sorted({m for m in moneda.values() if m != "USD"})
    fx = {m: float(fx_cache[m]["valor"]) for m in monedas
          if m in fx_cache and _vigente(fx_cache[m], ahora, fx_ttl_hours)}
    fx_faltan = [m for m in monedas if m not in fx and m in (fx_pairs or {})]
    if fx_faltan:
        def _llamar_fx(lista):
            nonlocal llamadas
            llamadas += 1
            return fx_provider({m: fx_pairs[m] for m in lista})
        nuevos_fx = _con_reintentos(_llamar_fx, fx_faltan, retries, backoff, sleep)
        fx.update(nuevos_fx)
        for m, v in nuevos_fx.items():
            fx_cache[m] = {"valor": v, "ts": ahora}
    fx["USD"] = 1.0

    if faltan or fx_faltan:
        with _CACHE_LOCK:
            _escribir_cache(ruta, {"cap": caps_cache, "fx": fx_cache})

    usd = {}
    for t in orden:
        cap, tasa = caps.get(t), fx.get(moneda[t])
        usd[t] = cap * tasa if cap is not None and tasa is not None else None
    return {"usd": usd, "moneda": moneda, "llamadas": llamadas}


def ordenar_por_market_cap(tickers, n_top, suffix_map, fx_pairs, **kwargs):
    """Top `n_top` de `tickers` por market cap en USD, de mayor a menor.

    Los que no traen market cap (o FX) van al final en su orden original.
    Si ninguno trae dato (yfinance caido), se conserva el orden de la lista
    y `aviso` lo explica. Los kwargs van a market_caps_usd.
    Devuelve {"seleccion", "orden", "tabla", "aviso"}; `tabla` tiene
    ticker, market_cap_usd, moneda y region de la seleccion.
    """
    orden_original = list(dict.fromkeys(tickers))
    n = max(0, min(int(n_top), len(orden_original)))
    aviso = None
    try:
        res = market_caps_usd(orden_original, suffix_map, fx_pairs, **kwargs)
        usd, moneda = res["usd"], res["moneda"]
    except Exception as exc:
        usd = {t: None for t in orden_original}
        moneda = {t: currency_from_suffix(t, suffix_map) or "USD" for t in orden_original}
        aviso = f"fallo la consulta de market cap ({type(exc).__name__}: {exc})"

    con_dato = [t for t in orden_original if usd.get(t) is not None]
    if not con_dato:
        orden = orden_original
        aviso = (aviso or "yfinance no devolvio market cap para ningun internacional") + \
            "; se usa el orden actual de la lista"
    else:
        pos = {t: i for i, t in enumerate(orden_original)}
        con_dato = sorted(con_dato, key=lambda t: (-usd[t], pos[t]))
        sin_dato = [t for t in orden_original if usd.get(t) is None]
        orden = con_dato + sin_dato
        if sin_dato:
            aviso = (f"{len(sin_dato)} sin market cap en USD (van al final, en el orden de la lista): "
                     + ", ".join(sin_dato))

    seleccion = orden[:n]
    tabla = pd.DataFrame({
        "ticker": seleccion,
        "market_cap_usd": [usd.get(t) for t in seleccion],
        "moneda": [moneda.get(t) for t in seleccion],
        "region": [region_de_ticker(t) for t in seleccion],
    })
    return {"seleccion": seleccion, "orden": orden, "tabla": tabla, "aviso": aviso}


def tabla_market_cap_texto(resultado, sangria="  "):
    """Tabla legible del top elegido: ticker, market cap en USD (miles de millones) y region."""
    disp = resultado["tabla"].copy()
    disp["market_cap_usd"] = disp["market_cap_usd"].map(
        lambda x: f"{x / 1e9:,.1f} B" if x is not None and pd.notna(x) else "sin dato")
    disp = disp.rename(columns={"ticker": "Ticker", "market_cap_usd": "MarketCap_USD",
                                "moneda": "Moneda", "region": "Region"})
    disp.index = range(1, len(disp) + 1)
    return sangria + disp.to_string().replace("\n", "\n" + sangria)
