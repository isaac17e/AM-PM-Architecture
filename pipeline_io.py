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
    de views. No lanza.
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
    return {"tickers": clean, "views": views, "source": source}


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
