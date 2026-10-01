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
# ==============================================================================

import pandas as pd

__all__ = [
    "normalize_currency",
    "price_scale_factor",
    "currency_from_suffix",
    "resolve_currencies",
    "align_prices_to_calendar",
    "drop_partial_last_week",
    "resolve_execution_months",
    "dedupe_share_classes",
]

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
    """Moneda por sufijo del ticker (p. ej. {'.TO': 'CAD'}); None si no hay sufijo conocido."""
    t = str(ticker)
    for suf, cur in suffix_map.items():
        if t.endswith(suf):
            return cur
    return None


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
