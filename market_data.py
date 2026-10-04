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

import re
import threading
import time

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
# ==============================================================================

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
