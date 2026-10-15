"""Contrato JSON v1: portafolio de cada optimizador y entrada opcional de Black-Litterman.

Escritura atomica (archivo.tmp + os.replace). Si el directorio no se puede
crear o escribir, se avisa y se sigue: la corrida no se cae por la exportacion.
"""

import calendar
import json
import math
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DEFAULT_PORTFOLIO_DIR = "/workspace/pipeline/portfolio"
SOURCE_REPO = "AM-PM-Architecture"
BOGOTA = ZoneInfo("America/Bogota")
RISK_PROFILE_NAMES = ("conservador", "moderado", "agresivo")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_OPTIMIZER = re.compile(r"[A-Za-z0-9_]+")


def resolve_risk_profile(default, allowed=RISK_PROFILE_NAMES, argv=None):
    """Nombre de perfil: `--risk-profile` gana a `RISK_PROFILE`, y ambos al default.

    Acepta mayusculas y espacios. Un nombre fuera de `allowed` lanza ValueError.
    """
    elegido = _cli_risk_profile(sys.argv[1:] if argv is None else argv)
    if elegido is None:
        elegido = os.environ.get("RISK_PROFILE")
    if elegido is None or not str(elegido).strip():
        elegido = default
    nombre = str(elegido).strip().lower()
    permitidos = tuple(allowed)
    if nombre not in permitidos:
        raise ValueError(
            f"perfil de riesgo invalido: {elegido!r}. "
            f"Use uno de: {', '.join(permitidos)} (--risk-profile o RISK_PROFILE)."
        )
    return nombre


def resolve_risk_free_rate(default, env=None):
    """Tasa libre de riesgo anual (decimal): `RISK_FREE_RATE` si esta, si no `default`.

    Se lee una vez al inicio del script; todo lo derivado (rf semanal/mensual,
    rf al horizonte, griegas BS, calibracion del acarreo de la IV) parte de
    este valor. Un valor no numerico o fuera de [0, 0.5) lanza ValueError.
    """
    crudo = (os.environ if env is None else env).get("RISK_FREE_RATE")
    if crudo is None or not str(crudo).strip():
        return float(default)
    try:
        tasa = float(str(crudo).strip())
    except ValueError:
        raise ValueError(
            f"RISK_FREE_RATE invalido: {crudo!r}. Use un decimal anual, p. ej. 0.052."
        ) from None
    if not math.isfinite(tasa) or not 0.0 <= tasa < 0.5:
        raise ValueError(
            f"RISK_FREE_RATE fuera de rango: {crudo!r}. Debe cumplir 0 <= rf < 0.5 "
            "(decimal anual: 0.052 es 5.2%)."
        )
    return tasa


HORIZON_MONTHS_MIN = 1
HORIZON_MONTHS_MAX = 12
HORIZON_ENV_VAR = "BL_HORIZON_MONTHS"
BL_MODES = ("full", "previews")
PREVIEWS_SCHEMA_VERSION = 1


class InvalidHorizonError(ValueError):
    """`BL_HORIZON_MONTHS` o `horizon_months` fuera de 1..12 o no entero."""


def parse_horizon_months(value, origin):
    """Entero 1..12 a partir de un int, un float entero o un texto de enteros.

    `origin` nombra de donde viene el valor para el mensaje de error. Un bool,
    un decimal con parte fraccionaria o un valor fuera de 1..12 lanza
    InvalidHorizonError.
    """
    aviso = (f"{origin} invalido: {value!r}. Use un entero entre "
             f"{HORIZON_MONTHS_MIN} y {HORIZON_MONTHS_MAX} (meses).")
    if isinstance(value, bool):
        raise InvalidHorizonError(aviso)
    if isinstance(value, str):
        texto = value.strip()
        if not re.fullmatch(r"[+-]?\d+", texto):
            raise InvalidHorizonError(aviso)
        meses = int(texto)
    elif isinstance(value, int):
        meses = value
    elif isinstance(value, float):
        if not math.isfinite(value) or value != int(value):
            raise InvalidHorizonError(aviso)
        meses = int(value)
    else:
        raise InvalidHorizonError(aviso)
    if not HORIZON_MONTHS_MIN <= meses <= HORIZON_MONTHS_MAX:
        raise InvalidHorizonError(aviso)
    return meses


def resolve_horizon(default, bl_input=None, env=None):
    """Horizonte en meses y su fuente: BL_INPUT_FILE > BL_HORIZON_MONTHS > `default`.

    `bl_input` es lo que devuelve `load_bl_input` (o None). Devuelve
    (meses, fuente) con fuente en {"BL_INPUT_FILE", "BL_HORIZON_MONTHS",
    "default"}. Un valor invalido lanza InvalidHorizonError, tambien el del
    default.
    """
    del_archivo = (bl_input or {}).get("horizon_months")
    if del_archivo is not None:
        return parse_horizon_months(del_archivo, "horizon_months (BL_INPUT_FILE)"), "BL_INPUT_FILE"
    crudo = (os.environ if env is None else env).get(HORIZON_ENV_VAR)
    if crudo is not None and str(crudo).strip():
        return parse_horizon_months(crudo, HORIZON_ENV_VAR), HORIZON_ENV_VAR
    return parse_horizon_months(default, "horizonte por defecto"), "default"


def resolve_horizon_months(default, bl_input=None, env=None):
    """Como `resolve_horizon` pero devuelve solo los meses."""
    return resolve_horizon(default, bl_input, env)[0]


def resolve_bl_mode(argv=None, env=None):
    """Modo de black_litterman.py: "previews" (`--previews` o BL_MODE=previews) o "full".

    El flag gana a la variable. BL_MODE acepta `full` o `previews` (sin
    distinguir mayusculas); vacio o ausente es `full`. Otro valor lanza ValueError.
    """
    argumentos = sys.argv[1:] if argv is None else argv
    if "--previews" in argumentos:
        return "previews"
    crudo = (os.environ if env is None else env).get("BL_MODE")
    if crudo is None or not str(crudo).strip():
        return "full"
    modo = str(crudo).strip().lower()
    if modo not in BL_MODES:
        raise ValueError(
            f"BL_MODE invalido: {crudo!r}. Use uno de: {', '.join(BL_MODES)} "
            "(o el flag --previews)."
        )
    return modo


def _moment_source_or_none(info):
    if not info:
        return None
    fuente = str(info.get("source"))
    if fuente not in ("iv", "hist"):
        raise ValueError(f"moment_source.source invalido: {fuente!r} (use 'iv' o 'hist')")
    return {"source": fuente, "reason": str(info.get("reason", ""))}


def build_previews_payload(*, as_of, horizon_months, horizon_trading_days, risk_profile,
                           tau, delta_mkt, tickers, pi_eq, mu_historico, vol_horizon,
                           w_mkt, iv_horizon=None, iv_source=None, universe_requested=None,
                           delta_mode=None, vol_hist_horizon=None, moment_source=None,
                           source_repo=SOURCE_REPO, now=None):
    """Diccionario del JSON de pre-views (BL_MODE=previews), listo para `json.dumps`.

    `tickers`, `pi_eq`, `mu_historico`, `vol_horizon` y `w_mkt` van alineados
    por posicion. `iv_horizon` es opcional: dict ticker -> vol implicita al
    horizonte (solo los tickers con superficie SSVI/ATM; el resto, None);
    `iv_source` dict ticker -> "ssvi" | "atm". Todo retorno y toda volatilidad
    estan al horizonte configurado, no anualizados.

    `vol_horizon` es la vol implicita/ajustada a P (sqrt(diag(Sigma_P))), la
    que usa el modelo; `vol_hist_horizon` es la vol historica pura al mismo
    horizonte (sqrt(diag(Sigma_hist))), sin ajuste por IV. Opcional y alineada
    por posicion; sin ella el campo va en null. `moment_source` es un dict
    ticker -> {"source": "iv" | "hist", "reason": str} con el origen de los
    momentos superiores (MFIS/MFIK); sin el ticker, null.
    """
    ahora = now or datetime.now(BOGOTA)
    nombres = [str(t) for t in tickers]
    columnas = {
        "pi_eq": list(pi_eq), "mu_historico": list(mu_historico),
        "vol_horizon": list(vol_horizon), "w_mkt": list(w_mkt),
    }
    for nombre, valores in columnas.items():
        if len(valores) != len(nombres):
            raise ValueError(f"{nombre} tiene {len(valores)} valores y hay {len(nombres)} tickers")
    if vol_hist_horizon is not None and len(vol_hist_horizon) != len(nombres):
        raise ValueError(
            f"vol_hist_horizon tiene {len(vol_hist_horizon)} valores y hay {len(nombres)} tickers")
    iv_horizon = iv_horizon or {}
    iv_source = iv_source or {}
    moment_source = moment_source or {}
    dias, fin = horizon_from_months(as_of, horizon_months)
    por_ticker = {}
    for i, ticker in enumerate(nombres):
        pi = _num_or_none(columnas["pi_eq"][i])
        mu = _num_or_none(columnas["mu_historico"][i])
        iv = _num_or_none(iv_horizon.get(ticker))
        por_ticker[ticker] = {
            "pi_eq": pi,
            "mu_historico": mu,
            "diff": None if pi is None or mu is None else mu - pi,
            "vol_horizon": _num_or_none(columnas["vol_horizon"][i]),
            "vol_hist_horizon": (None if vol_hist_horizon is None
                                 else _num_or_none(vol_hist_horizon[i])),
            "iv_horizon": iv,
            "iv_source": iv_source.get(ticker) if iv is not None else None,
            "w_mkt": _num_or_none(columnas["w_mkt"][i]),
            "moment_source": _moment_source_or_none(moment_source.get(ticker)),
        }
    pedido = [str(t) for t in (universe_requested if universe_requested is not None else nombres)]
    return {
        "schema_version": PREVIEWS_SCHEMA_VERSION,
        "kind": "bl_previews",
        "source_repo": source_repo,
        "generated_at": ahora.isoformat(timespec="seconds"),
        "as_of": _date_or_none(as_of),
        "horizon_months": int(horizon_months),
        "horizon_days": dias,
        "horizon_end": fin,
        "horizon_trading_days": _int_or_none(horizon_trading_days),
        "risk_profile": _profile(risk_profile),
        "tau": _num_or_none(tau),
        "delta_mkt": _num_or_none(delta_mkt),
        "delta_mkt_mode": delta_mode,
        "units": {
            "returns": (f"decimal log-return accumulated over the configured horizon "
                        f"({int(horizon_months)} month(s)); not annualized"),
            "volatility": (f"decimal standard deviation over the configured horizon "
                           f"({int(horizon_months)} month(s)); not annualized"),
            "w_mkt": "fraction of the market-cap weights; sums to 1 over `universe`",
            "diff": "mu_historico - pi_eq (> 0: historical return above equilibrium)",
            "vol_horizon": ("implied/P-adjusted vol: sqrt(diag(Sigma_P)) at the horizon "
                            "(Q->P adjusted covariance; the vol the model uses)"),
            "vol_hist_horizon": ("historical vol: sqrt(diag(Sigma_hist)) at the horizon "
                                 "(EWMA+shrinkage covariance scaled to horizon_months; "
                                 "no implied-vol adjustment)"),
            "moment_source": ("origin of the higher moments (MFIS/MFIK): source 'iv' only when "
                              "implied moments from the ticker's own SSVI smile were used, "
                              "'hist' otherwise (any fallback: historical, sector or neutral); "
                              "`reason` names the actual cause"),
            "iv_horizon": ("ATM implied vol at the horizon from the SSVI/ATM block; "
                           "null when the ticker has no usable option surface"),
        },
        "universe": nombres,
        "universe_requested": pedido,
        "universe_excluded": [t for t in pedido if t not in set(nombres)],
        "tickers": por_ticker,
    }


def write_previews(payload, out=None, env=None, now=None):
    """Escribe el JSON de pre-views y devuelve su ruta.

    Destino: `out` (o BL_PREVIEWS_OUT). Si es un directorio existente, termina
    en `/` o no tiene extension, se crea `previews_<YYYYMMDDTHHMMSS>.json`
    dentro; si no, se toma como la ruta del archivo. Sin destino, el directorio
    es el mismo de los portafolios (PORTFOLIO_OUT_DIR o el default). A diferencia
    de `export_portfolio`, un fallo de escritura lanza: el JSON es el unico
    producto de esa corrida.
    """
    entorno = os.environ if env is None else env
    crudo = out if out is not None else entorno.get("BL_PREVIEWS_OUT")
    sello = (now or datetime.now(BOGOTA)).strftime("%Y%m%dT%H%M%S")
    nombre = f"previews_{sello}.json"
    if crudo is None or not str(crudo).strip():
        destino = Path(entorno.get("PORTFOLIO_OUT_DIR") or DEFAULT_PORTFOLIO_DIR) / nombre
    else:
        texto = str(crudo).strip()
        ruta = Path(texto)
        es_dir = ruta.is_dir() or texto.endswith(("/", os.sep)) or ruta.suffix == ""
        destino = ruta / nombre if es_dir else ruta
    destino.parent.mkdir(parents=True, exist_ok=True)
    texto_json = json.dumps(_jsonify(payload), indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    _atomic_write(destino, texto_json)
    return str(destino)


def _cli_risk_profile(argv):
    for i, arg in enumerate(argv):
        if arg == "--risk-profile":
            if i + 1 >= len(argv) or str(argv[i + 1]).startswith("-"):
                raise ValueError(
                    "--risk-profile necesita un valor: conservador, moderado o agresivo"
                )
            return argv[i + 1]
        if arg.startswith("--risk-profile="):
            return arg.split("=", 1)[1]
    return None


def horizon_from_months(as_of, n_months):
    """Dias de calendario y fecha final al correr `n_months` meses desde `as_of`."""
    try:
        n = int(n_months)
        if n < 0 or not isinstance(as_of, date):
            return None, None
        end = _add_months(as_of, n)
        return (end - as_of).days, end.isoformat()
    except (TypeError, ValueError, OverflowError):
        return None, None


def horizon_from_month_list(as_of, months):
    """Dias de calendario (inclusive) y ultimo dia de la ventana de meses de ejecucion.

    Si `as_of` cae dentro de la ventana, usa esa. Si no, la proxima ventana
    cuyo fin no haya pasado. Los meses pueden cruzar el ano ([11, 12, 1]).
    """
    try:
        months = [int(m) for m in months]
    except (TypeError, ValueError):
        return None, None
    if not months or any(m < 1 or m > 12 for m in months) or not isinstance(as_of, date):
        return None, None

    def window(year):
        y, m = year, months[0]
        start = date(y, m, 1)
        for nxt in months[1:]:
            if nxt <= m:
                y += 1
            m = nxt
        end = date(y, m, calendar.monthrange(y, m)[1])
        return start, end

    try:
        windows = [window(as_of.year + k) for k in (-1, 0, 1)]
    except (ValueError, OverflowError):
        return None, None
    chosen = next((w for w in windows if w[0] <= as_of <= w[1]), None)
    if chosen is None:
        future = [w for w in windows if w[1] >= as_of]
        if not future:
            return None, None
        chosen = min(future, key=lambda w: w[0])
    start, end = chosen
    return (end - start).days + 1, end.isoformat()


def export_portfolio(optimizer, weights, *, risk_profile=None, horizon_days=None,
                     horizon_end=None, params=None, metrics=None,
                     source_repo=SOURCE_REPO, out_dir=None):
    """Escribe portfolio_latest.json y portfolio_<optimizer>_<YYYYMMDDTHHMMSS>.json.

    Devuelve la ruta de portfolio_latest.json, o None si no se pudo exportar.
    Nunca lanza: un directorio imposible de escribir solo imprime una advertencia.
    """
    try:
        return _export_portfolio(
            optimizer, weights, risk_profile=risk_profile, horizon_days=horizon_days,
            horizon_end=horizon_end, params=params, metrics=metrics,
            source_repo=source_repo, out_dir=out_dir)
    except Exception as exc:
        print(f"ADVERTENCIA: no se exporto el portafolio ({exc}). La corrida continua.")
        return None


def load_bl_input(path):
    """Lee BL_INPUT_FILE. None si no hay ruta, si falta el archivo o si el JSON no es valido.

    Acepta un universo (solo se usa `tickers`; `views` queda None) o un archivo
    de views. Puede traer `horizon_months` (entero 1..12; None si falta).
    No lanza, salvo InvalidHorizonError: un horizonte invalido no se degrada a
    un aviso porque cambiaria en silencio todo el calculo.
    """
    if path is None:
        return None
    path = str(path).strip()
    if not path:
        return None
    archivo = Path(path)
    if not archivo.is_file():
        print(f"ADVERTENCIA: BL_INPUT_FILE={path} no existe o no es un archivo. "
              "Se usan los TICKERS y las views fijos del script.")
        return None
    try:
        data = json.loads(archivo.read_text(encoding="utf-8"))
        return _validate_bl_input(data)
    except InvalidHorizonError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"ADVERTENCIA: BL_INPUT_FILE={path} invalido ({exc}). "
              "Se usan los TICKERS y las views fijos del script.")
        return None


def select_views(views, universe):
    """Conserva una view solo si todos los tickers de `p` estan en el universo.

    Devuelve (kept, skipped). `skipped` es una lista de {name, missing}.
    Los nombres de views repetidos se desambiguan.
    """
    by_upper = {}
    for ticker in universe:
        key = str(ticker).strip().upper()
        if key and key not in by_upper:
            by_upper[key] = ticker
    kept, skipped, used = [], [], set()
    for i, view in enumerate(views or []):
        raw_name = str(view.get("name") or f"View_{i + 1}")
        coefs = {}
        missing = []
        for ticker, coef in view.get("p", {}).items():
            key = str(ticker).strip().upper()
            if key in by_upper:
                coefs[by_upper[key]] = float(coef)
            else:
                missing.append(str(ticker).strip().upper())
        if missing or not coefs:
            skipped.append({"name": raw_name, "missing": missing or list(view.get("p", {}))})
            continue
        name = raw_name
        n = 2
        while name in used:
            name = f"{raw_name}_{n}"
            n += 1
        used.add(name)
        kept.append({"name": name, "p": coefs, "q": float(view["q"])})
    return kept, skipped


def _add_months(d, months):
    month0 = d.month - 1 + months
    year = d.year + month0 // 12
    month = month0 % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _export_portfolio(optimizer, weights, *, risk_profile, horizon_days, horizon_end,
                      params, metrics, source_repo, out_dir):
    nombre = str(optimizer)
    if not _OPTIMIZER.fullmatch(nombre):
        raise ValueError(f"optimizer invalido: {optimizer!r}")
    normalizados = _normalize_weights(weights)
    if not normalizados:
        raise ValueError("no hay pesos finitos que sumen distinto de cero")
    directory = Path(out_dir if out_dir else os.environ.get("PORTFOLIO_OUT_DIR") or DEFAULT_PORTFOLIO_DIR)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"ADVERTENCIA: no se pudo crear el directorio de portafolio {directory} ({exc}). "
              "La corrida continua sin exportar JSON.")
        return None
    ahora = datetime.now(BOGOTA)
    run_ts = ahora.isoformat(timespec="seconds")
    sello = ahora.strftime("%Y%m%dT%H%M%S")
    metricas = _metrics(metrics)
    payload = {
        "schema_version": 1,
        "source_repo": source_repo,
        "optimizer": nombre,
        "risk_profile": _profile(risk_profile),
        "run_ts": run_ts,
        "horizon_days": _int_or_none(horizon_days),
        "horizon_end": _date_or_none(horizon_end),
        "tickers": [t for t, _ in normalizados],
        "weights": {t: w for t, w in normalizados},
        "params": _jsonify(params or {}),
        "metrics": metricas,
    }
    texto = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    latest = directory / "portfolio_latest.json"
    copia = directory / f"portfolio_{nombre}_{sello}.json"
    try:
        _atomic_write(latest, texto)
        _atomic_write(copia, texto)
    except OSError as exc:
        print(f"ADVERTENCIA: no se pudo escribir el portafolio en {directory} ({exc}). "
              "La corrida continua sin exportar JSON.")
        return None
    return str(latest)


def _atomic_write(path, text):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _normalize_weights(weights):
    if weights is None:
        return None
    seq = list(weights.items()) if hasattr(weights, "items") else list(weights)
    merged = {}
    order = []
    for item in seq:
        if isinstance(item, str) or len(item) != 2:
            continue
        ticker, value = item
        key = str(ticker).strip().upper()
        if not key:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(number) or abs(number) < 1e-6:
            continue
        if key not in merged:
            order.append(key)
        merged[key] = merged.get(key, 0.0) + number
    pairs = [(k, merged[k]) for k in order if abs(merged[k]) >= 1e-6]
    if not pairs:
        return None
    total = sum(w for _, w in pairs)
    if not math.isfinite(total) or abs(total) < 1e-12:
        return None
    units = []
    for ticker, value in pairs:
        units.append([ticker, int(round((value / total) * 1_000_000))])
    units = [u for u in units if u[1] != 0]
    if not units:
        return None
    diff = 1_000_000 - sum(u[1] for u in units)
    idx = max(range(len(units)), key=lambda i: (units[i][1], units[i][0]))
    units[idx][1] += diff
    if any(u[1] == 0 for u in units):
        return None
    units.sort(key=lambda u: (-u[1], u[0]))
    return [(ticker, units_i / 1_000_000) for ticker, units_i in units]


def _metrics(metrics):
    raw = metrics or {}
    out = {
        "expected_return": _num_or_none(raw.get("expected_return")),
        "volatility": _num_or_none(raw.get("volatility")),
    }
    for key, value in raw.items():
        if key not in out:
            out[str(key)] = _jsonify(value)
    return out


def _jsonify(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, date):
        return value.isoformat()
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _jsonify(item())
        except Exception:
            pass
    return str(value)


def _num_or_none(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _int_or_none(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _date_or_none(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value)
    return text if _DATE.fullmatch(text) else None


def _profile(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _validate_bl_input(data):
    if not isinstance(data, dict):
        raise ValueError("el JSON debe ser un objeto")
    if "schema_version" in data and data["schema_version"] != 1:
        raise ValueError("schema_version debe ser 1")
    horizon_months = None
    if data.get("horizon_months") is not None:
        horizon_months = parse_horizon_months(data["horizon_months"], "horizon_months (BL_INPUT_FILE)")
    tickers = data.get("tickers")
    if not isinstance(tickers, list) or not tickers:
        raise ValueError("tickers debe ser una lista no vacia")
    clean, seen = [], set()
    for ticker in tickers:
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError("cada ticker debe ser texto")
        key = ticker.strip().upper()
        if key not in seen:
            seen.add(key)
            clean.append(key)
    if "views" in data and data["views"] is not None:
        views = _parse_views(data["views"])
    else:
        views = None
    source = data.get("source")
    if source is not None and not isinstance(source, str):
        raise ValueError("source debe ser texto")
    return {"tickers": clean, "views": views, "source": source, "horizon_months": horizon_months}


def _parse_views(raw):
    if not isinstance(raw, list):
        raise ValueError("views debe ser una lista")
    out = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"views[{i}] debe ser un objeto")
        p_raw = item.get("p")
        if not isinstance(p_raw, dict) or not p_raw:
            raise ValueError(f"views[{i}].p debe ser un objeto ticker -> coeficiente")
        if "q" not in item:
            raise ValueError(f"views[{i}] no trae q")
        try:
            q = float(item["q"])
        except (TypeError, ValueError):
            raise ValueError(f"views[{i}].q debe ser numerico")
        if not math.isfinite(q):
            raise ValueError(f"views[{i}].q no es finito")
        coefs = {}
        for ticker, coef in p_raw.items():
            key = str(ticker).strip().upper()
            if not key:
                raise ValueError(f"views[{i}] tiene un ticker vacio")
            try:
                number = float(coef)
            except (TypeError, ValueError):
                raise ValueError(f"views[{i}].p[{key}] debe ser numerico")
            if not math.isfinite(number):
                raise ValueError(f"views[{i}].p[{key}] no es finito")
            if abs(number) >= 1e-12:
                coefs[key] = number
        if not coefs:
            raise ValueError(f"views[{i}] no tiene coeficientes distintos de cero")
        name = str(item.get("name") or f"View_{i + 1}").strip() or f"View_{i + 1}"
        out.append({"name": name, "p": coefs, "q": q})
    return out
