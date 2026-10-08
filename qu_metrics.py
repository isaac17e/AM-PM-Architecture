# ==============================================================================
# QU_METRICS - Logica testeable de quadratic_utility (y su version estacional)
# ==============================================================================
# Extraida para poder probarla sin ejecutar los scripts (descargas, Polygon,
# quadprog). Los scripts conservan el flujo; aqui viven las reglas:
#
#   M-5  correlacion absoluta promedio de la fila completa, sin la diagonal
#   M-6  anos de historia hasta el ultimo mes completo de as_of
#   M-7  anualizacion mensual via risk_estimators.annualize
#   M-8  lambda anual -> lambda mensual (opt-in; el default no cambia)
#   M-9  cola del z-score de MFIS: upper / lower / both
#   M-1  longitud minima por ticker, sin recortar el panel a la serie mas corta
#   M-10 cesta de dispersion: componentes con IV, cap-weighted si hay caps
#   A-5  seleccion historica de cadena OTM con strikes y DTE reales
#   E-1  piso de ETF alcanzable, reposiciones que respetan los filtros duros
#        y chequeo de factibilidad de las restricciones antes de quadprog
# ==============================================================================

import math
import os
from datetime import date, timedelta

import numpy as np
import pandas as pd

import market_data as md
import polygon_client as pc
import portfolio_constraints as pq
import risk_estimators as rk

# Reexportadas desde market_data para no romper `import qu_metrics as qm`.
es_ticker_formato_us = md.es_ticker_formato_us
region_de_ticker = md.region_de_ticker
combinar_tickers = md.combinar_tickers

__all__ = [
    "average_abs_correlation",
    "history_window",
    "annualize_monthly",
    "lambda_monthly_from_annual",
    "utility_terms",
    "mfis_tail_decision",
    "columns_with_min_obs",
    "covariance_min_history",
    "portfolio_returns_skipna",
    "dispersion_weights",
    "dispersion_usable",
    "clip_implied_correlation",
    "scale_option_deltas",
    "bs_call_delta_from_vol",
    "otm_log_moneyness",
    "delta_cushion",
    "es_ticker_formato_us",
    "combinar_tickers",
    "region_de_ticker",
    "evaluar_delta_candidato",
    "pasa_filtro_delta",
    "sector_implied_ready",
    "align_daily_panel",
    "stitch_covariance",
    "select_historical_otm",
    "summarize_yearly_mdd",
    "estimate_bkm_history_calls",
    "close_near_from_bars",
    "contract_agg_ranges",
    "plan_bkm_history_budget",
    "mfis_max_minutes_from_env",
    "orden_prioridad_mfis",
    "frontier_lambda_grid",
    "portfolio_mu_final_metrics",
    "frontier_curve",
    "comparison_lambdas",
    "score_candidate_portfolios",
    "mfiv_annual_vol",
    "etfs_necesarios",
    "contar_etfs",
    "reserva_etf",
    "candidatos_reposicion",
    "completar_etfs",
    "siguiente_reposicion",
    "restricciones_factibles",
    "diagnostico_banda_etf",
    "relajar_banda_etf",
    "filtro_delta_otm",
]


def average_abs_correlation(corr):
    """|rho| medio de cada fila, diagonal excluida (M-5).

    El calculo anterior apilaba solo Var1 < Var2 y agrupaba por Var1: el
    primer ticker alfabetico promediaba n-1 pares y el ultimo quedaba en NaN.
    """
    if not isinstance(corr, pd.DataFrame):
        corr = pd.DataFrame(corr)
    arr = np.array(corr.abs(), dtype=float, copy=True)
    if arr.ndim != 2 or arr.shape[0] != arr.shape[1]:
        raise ValueError("corr debe ser una matriz cuadrada")
    n = arr.shape[0]
    if n < 2:
        return pd.Series(np.nan, index=corr.index)
    np.fill_diagonal(arr, np.nan)
    with np.errstate(all="ignore"):
        avg = np.nanmean(arr, axis=1)
    return pd.Series(avg, index=corr.index, name="avg_cor")


def history_window(as_of, start_year):
    """Anos inclusivos y fechas de descarga hasta el ultimo mes completo (M-6).

    yfinance trata `end` como exclusivo. Devolver el dia 1 del mes de `as_of`
    deja fuera el mes en curso (un octubre a medio formar no entra en la media).
    El ano de ese ultimo mes completo si entra: con as_of en 2026 ya no se
    tira el ano en curso.

    Devuelve (years, start_iso, end_exclusive_iso).
    """
    as_of = pd.Timestamp(as_of).date()
    start_year = int(start_year)
    end_exclusive = date(as_of.year, as_of.month, 1)
    last_included = end_exclusive - timedelta(days=1)
    if last_included.year < start_year:
        raise ValueError(f"history_start_year={start_year} es posterior a {last_included}")
    years = list(range(start_year, last_included.year + 1))
    return years, f"{start_year}-01-01", end_exclusive.isoformat()


def annualize_monthly(mu=None, sd=None):
    """Anualiza media y desviacion de retornos mensuales (M-7).

    Retorno x12, volatilidad x sqrt(12), via rk.annualize. No usa el horizonte
    del portafolio: un retorno mensual no es un retorno a `horizon_months`.
    """
    return rk.annualize(rk.to_years(months=1), mu=mu, sd=sd)


def lambda_monthly_from_annual(lambda_annual, periods_per_year=12):
    """lambda mensual = lambda_annual * periodos por ano (M-8).

    Opt-in. Con mu y Sigma mensuales, U = mu'w - lambda/2 w'Sigma w. Si lambda
    anual esta definido en la MISMA convencion sobre mu y Sigma anuales
    (ambos x12), el 12 se cancela y el lambda que preserva el ranking es el
    propio lambda_annual. La conversion de esta funcion es la otra: trata la
    aversion como si hubiera que inflarla para que la penalizacion mensual no
    sea despreciable frente a mu'w (el caso lambda=0.5). Solo se usa cuando
    el script recibe lambda_annual distinto de None.
    """
    if lambda_annual is None:
        return None
    valor = float(lambda_annual)
    periodos = float(periods_per_year)
    if valor <= 0 or periodos <= 0:
        raise ValueError("lambda_annual y periods_per_year deben ser positivos")
    return valor * periodos


def shrink_mu_to_prior(mu_hist, mu_prior, n_obs, k):
    """Encoge la media historica hacia un retorno de modelo, por activo.

    mu_i = w_i mu_hist_i + (1 - w_i) mu_prior_i,  w_i = n_i / (n_i + k)

    `k` son los meses de historia que pesan lo mismo que el modelo: con
    n_i = k el peso es 50/50, y un activo con poca historia se apoya mas en
    el modelo. Sin prior finito el activo conserva su media historica
    (w = 1). Devuelve (mu, w) con el indice de `mu_hist`.
    """
    k = float(k)
    if not (math.isfinite(k) and k >= 0):
        raise ValueError("k debe ser finito y >= 0")
    hist = pd.Series(mu_hist, dtype=float)
    prior = pd.Series(mu_prior, dtype=float).reindex(hist.index)
    n = pd.Series(n_obs, dtype=float).reindex(hist.index).fillna(0.0).clip(lower=0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        w = n / (n + k)
    w = w.where(np.isfinite(w), 1.0)
    w = w.where(np.isfinite(prior), 1.0)
    mu = w * hist + (1.0 - w) * prior.fillna(0.0)
    return mu, w


def utility_terms(expected_return, variance, lambda_):
    """mu'w y (lambda/2) w'Sigma w ya evaluados en el optimo, y la utilidad."""
    mu_term = float(expected_return)
    var = float(variance)
    risk_term = float(lambda_) / 2.0 * var
    return {"mu_term": mu_term, "risk_term": risk_term, "utility": mu_term - risk_term}


def mfis_tail_decision(z, threshold, mode="upper"):
    """Decision del filtro de MFIS (M-9).

    mode:
      upper  descarta z > umbral. Es el comportamiento historico (el motivo
             se llamaba cobertura_anomala). Financiariamente es un sesgo
             implicito anormalmente positivo: demanda de calls, no de puts.
      lower  descarta z < -umbral. Demanda anormal de puts (cobertura).
      both   descarta cualquiera de las dos colas, con la etiqueta del lado.

    Devuelve (decision, motivo) con decision en {descartar, mantener}.
    """
    modo = str(mode).lower()
    if modo not in ("upper", "lower", "both"):
        raise ValueError("mode debe ser 'upper', 'lower' o 'both'")
    if not np.isfinite(z):
        return "mantener", "z_no_finito"
    umbral = float(threshold)
    cola_alta = z > umbral
    cola_baja = z < -umbral
    if modo in ("upper", "both") and cola_alta:
        return "descartar", "cola_superior"
    if modo in ("lower", "both") and cola_baja:
        return "descartar", "cola_inferior"
    return "mantener", "dentro_de_banda"


def columns_with_min_obs(frame, min_obs):
    """Quita columnas con menos de min_obs datos. No borra filas (M-1)."""
    counts = frame.notna().sum()
    keep = counts[counts >= min_obs].index.tolist()
    dropped = [c for c in frame.columns if c not in keep]
    return frame.loc[:, keep], dropped


def covariance_min_history(returns, min_periods):
    """Covarianza por pares. Cada serie usa su propia historia (M-1).

    Una columna con menos de min_periods observaciones se excluye. Pares con
    solapamiento insuficiente heredan la covarianza fuera de diagonal media
    de los pares validos; la diagonal es la varianza de la serie completa.
    """
    sub, dropped = columns_with_min_obs(returns, min_periods)
    if sub.shape[1] == 0:
        return sub, dropped
    cov = sub.cov(min_periods=int(min_periods))
    vals = cov.to_numpy(dtype=float).copy()
    var = sub.var().to_numpy(dtype=float)
    n = vals.shape[0]
    off = ~np.eye(n, dtype=bool)
    finite_off = vals[off]
    finite_off = finite_off[np.isfinite(finite_off)]
    fill = float(np.mean(finite_off)) if len(finite_off) else 0.0
    vals = np.where(np.isfinite(vals), vals, fill)
    np.fill_diagonal(vals, np.where(np.isfinite(var), var, np.diag(vals)))
    out = pd.DataFrame(vals, index=cov.index, columns=cov.columns)
    return out, dropped


def portfolio_returns_skipna(returns_df, weights):
    """Retorno del portafolio por fecha, renormalizando el peso presente (M-1).

    Un mes en el que falta un ticker no borra la fila para el resto: el peso
    de los que si tienen retorno se reescala a 1. Fechas sin ningun dato se omiten.
    """
    w = weights.reindex(returns_df.columns).fillna(0.0) if isinstance(weights, pd.Series) else pd.Series(
        np.asarray(weights, dtype=float), index=returns_df.columns)
    valores = returns_df.to_numpy(dtype=float)
    ww = w.to_numpy(dtype=float)
    mask = np.isfinite(valores)
    num = np.where(mask, valores, 0.0) @ ww
    denom = mask @ ww
    out = np.divide(num, denom, out=np.full(len(denom), np.nan), where=denom > 1e-12)
    return pd.Series(out, index=returns_df.index, name="portfolio_return").dropna()


def dispersion_weights(assets, has_iv, components, caps=None):
    """Pesos de la cesta de correlacion implicita por dispersion (M-10).

    Entran solo nombres que estan en `components` (constituyentes de SPY que
    el script conoce) y tienen IV propia (`has_iv`). Si todos ellos tienen
    capitalizacion positiva, los pesos son de capitalizacion renormalizada;
    si falta alguna, equiponderados, y `info["mode"]` lo dice.

    Devuelve (weights alineados a `assets`, info). weights suma 1 sobre la
    cesta y 0 fuera. mode es "cap", "equal" o "insuficiente" (menos de 2 nombres).
    """
    assets = list(assets)
    has = set(has_iv)
    comps = set(components)
    caps = caps or {}
    cesta = [a for a in assets if a in comps and a in has]
    info = {"n": len(cesta), "tickers": cesta, "mode": "insuficiente", "missing_caps": []}
    w = pd.Series(0.0, index=assets, dtype=float)
    if len(cesta) < 2:
        return w, info
    cap_vals = []
    missing = []
    for t in cesta:
        c = caps.get(t)
        if c is None or not np.isfinite(c) or c <= 0:
            missing.append(t)
        else:
            cap_vals.append(float(c))
    info["missing_caps"] = missing
    if missing:
        info["mode"] = "equal"
        for t in cesta:
            w[t] = 1.0 / len(cesta)
    else:
        info["mode"] = "cap"
        total = float(sum(cap_vals))
        for t, c in zip(cesta, cap_vals):
            w[t] = c / total
    conocidos = []
    for nombre, c in caps.items():
        if nombre in comps and c is not None and np.isfinite(c) and c > 0:
            conocidos.append(float(c))
    info["n_caps_conocidas"] = len(conocidos)
    total_conocido = float(sum(conocidos))
    cesta_conocida = 0.0
    for t in cesta:
        c = caps.get(t)
        if c is not None and np.isfinite(c) and c > 0:
            cesta_conocida += float(c)
    info["cap_share"] = (cesta_conocida / total_conocido) if total_conocido > 0 else 0.0
    return w, info


def dispersion_usable(info, min_cap_share=0.40, min_known_caps=50):
    """True si la cesta cubre bastante capitalizacion conocida de SPY.

    Una cesta de 13 nombres puede sumar el 100% de SUS caps y aun asi ser una
    fraccion pequena del indice; `cap_share` es caps de la cesta / caps
    conocidas de los componentes. El fallback de ~20 nombres no llega a
    `min_known_caps`, asi que no se disfraza de cobertura total.
    """
    if not info or info.get("mode") == "insuficiente":
        return False
    if int(info.get("n_caps_conocidas") or 0) < int(min_known_caps):
        return False
    share = info.get("cap_share")
    return bool(share is not None and np.isfinite(share) and float(share) >= float(min_cap_share))


def scale_option_deltas(delta, mode="direct", delta_min=0.30,
                        fixed_lo=0.45, fixed_hi=0.55):
    """Multiplicador de mu a partir de la delta de la call.

    `direct` usa la delta, recortada a [delta_min, 1]. Una delta ausente
    queda en 1 (no hay informacion, no se recorta el retorno).
    `fixed` mapea el rango absoluto [fixed_lo, fixed_hi] a [delta_min, 1],
    sin mirar el minimo y el maximo de la corrida.
    `minmax` estira el rango observado de la corrida a [delta_min, 1].
    Con deltas 0.48-0.56 eso convierte 0.03 de delta en decenas de puntos
    del multiplicador.
    `relative` divide por la mediana de la corrida y recorta a
    [fixed_lo, fixed_hi]. La mediana queda en 1, asi que el nivel no
    reescala lambda; solo inclina entre nombres.
    """
    d = np.asarray(delta, dtype=float)
    modo = str(mode)
    piso = float(delta_min)
    if modo == "minmax":
        valid = d[np.isfinite(d)]
        if len(valid) >= 2 and float(valid.max()) > float(valid.min()):
            span = float(valid.max()) - float(valid.min())
            scaled = (d - float(valid.min())) / span * (1.0 - piso) + piso
        else:
            scaled = np.ones(np.shape(d), dtype=float)
    elif modo == "fixed":
        span = float(fixed_hi) - float(fixed_lo)
        if span <= 0:
            raise ValueError("fixed_hi debe ser mayor que fixed_lo")
        scaled = (d - float(fixed_lo)) / span * (1.0 - piso) + piso
        scaled = np.clip(scaled, piso, 1.0)
    elif modo == "direct":
        scaled = np.clip(d, piso, 1.0)
    elif modo == "relative":
        if float(fixed_hi) <= float(fixed_lo):
            raise ValueError("fixed_hi debe ser mayor que fixed_lo")
        valid = d[np.isfinite(d)]
        med = float(np.median(valid)) if len(valid) else float("nan")
        if not (math.isfinite(med) and med > 0):
            scaled = np.ones(np.shape(d), dtype=float)
        else:
            scaled = np.clip(d / med, float(fixed_lo), float(fixed_hi))
    else:
        raise ValueError(f"modo de delta desconocido: {mode}")
    return np.where(np.isfinite(d), scaled, 1.0)


def bs_call_delta_from_vol(vol, years, rate, log_moneyness=0.0):
    """Delta N(d1) con K = S * exp(log_moneyness) y q = 0. El spot se cancela.

    NaN si la vol o el plazo no son positivos.
    """
    try:
        vol = float(vol)
        years = float(years)
        rate = float(rate)
        m = float(log_moneyness)
    except (TypeError, ValueError):
        return float("nan")
    if not (math.isfinite(vol) and math.isfinite(years) and math.isfinite(rate) and math.isfinite(m)):
        return float("nan")
    if vol <= 0 or years <= 0:
        return float("nan")
    return pq.bs_call_delta(1.0, math.exp(m), years, rate, vol)


def otm_log_moneyness(log_m, years, ref_years):
    """Log-moneyness OTM escalada con sqrt(plazo / plazo de referencia).

    `log_m` es el desplazamiento en el horizonte de referencia. Sin la
    escala, el mismo 8% es cerca de un sigma a 2 meses y una fraccion de
    sigma a un ano, y un umbral fijo deja de separar.
    """
    try:
        log_m = float(log_m)
        years = float(years)
        ref_years = float(ref_years)
    except (TypeError, ValueError):
        return float("nan")
    if not (math.isfinite(log_m) and years > 0 and ref_years > 0):
        return float("nan")
    return log_m * math.sqrt(years / ref_years)


def delta_cushion(vol, years, rate, log_m, ref_years=None):
    """Caida de la delta de la call entre K = S y el strike OTM.

    Alta cuando la vol es baja (el strike fijo queda a muchos sigma) y baja
    cuando la vol es alta (el mismo strike sigue cerca del dinero). El filtro
    conserva cushion >= delta_min: un umbral alto se queda con la vol baja.
    `ref_years` None usa el plazo tal cual, sin reescalar la moneyness.
    """
    if ref_years is None:
        ref_years = years
    m = otm_log_moneyness(log_m, years, ref_years)
    atm = bs_call_delta_from_vol(vol, years, rate, 0.0)
    otm = bs_call_delta_from_vol(vol, years, rate, m)
    if not (math.isfinite(atm) and math.isfinite(otm)):
        return float("nan")
    return float(atm - otm)


def _finito(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return float("nan")
    return numero if math.isfinite(numero) else float("nan")


def evaluar_delta_candidato(
    vol_hist,
    years,
    rate,
    mode="otm",
    log_m=0.08,
    ref_years=None,
    mu_sobre_horizonte=0.0,
    usar_delta_polygon=False,
    polygon_delta=None,
    polygon_iv=None,
):
    """Delta o colchon de un nombre para el filtro.

    En `otm` la delta ATM de Polygon no se usa: ronda 0.5 y no separa
    perfiles, aunque `usar_delta_polygon` venga en True. El colchon se
    calcula con la IV de Polygon si es positiva y, si no, con `vol_hist`.
    Sin vol positiva el valor es NaN y el nombre se conserva.

    En `atm` / `mu` / `rf`, si `usar_delta_polygon` es True se devuelve la
    delta de Polygon tal cual (aunque sea NaN). Si no, delta BS con
    K = S * exp(drift). `mu_sobre_horizonte` es mu del periodo por el
    numero de periodos (el drift del modo mu). El modo rf usa r * T.
    """
    modo = str(mode)
    poly_d = _finito(polygon_delta)
    poly_iv = _finito(polygon_iv)
    hist = _finito(vol_hist)

    if modo != "otm" and usar_delta_polygon:
        return {"delta": poly_d, "strike_mode": "polygon_real", "iv_used": poly_iv}

    if modo == "otm" and math.isfinite(poly_iv) and poly_iv > 0:
        iv, fuente = poly_iv, "polygon_iv"
    elif math.isfinite(hist) and hist > 0:
        iv, fuente = hist, "hist"
    else:
        return {"delta": float("nan"), "strike_mode": "sin_datos", "iv_used": float("nan")}

    if modo == "otm":
        delta_i = delta_cushion(iv, years, rate, log_m, ref_years=ref_years)
        return {"delta": delta_i, "strike_mode": f"bs_otm_{fuente}", "iv_used": iv}

    if modo == "mu":
        drift = _finito(mu_sobre_horizonte)
        if not math.isfinite(drift):
            drift = 0.0
    elif modo == "rf":
        anios = _finito(years)
        tasa = _finito(rate)
        drift = tasa * anios if math.isfinite(tasa) and math.isfinite(anios) else 0.0
    else:
        drift = 0.0
    delta_i = bs_call_delta_from_vol(iv, years, rate, drift)
    return {"delta": delta_i, "strike_mode": f"bs_{modo}", "iv_used": iv}


def pasa_filtro_delta(delta, delta_min):
    """True si no hay vol (NaN, se conserva) o el valor supera el umbral."""
    valor = _finito(delta)
    if not math.isfinite(valor):
        return True
    return valor >= float(delta_min)


def filtro_delta_otm(tickers, iv_polygon, vol_hist, years, rate, delta_min, log_m=0.08, ref_years=None):
    """Colchon OTM por ticker y si pasa `delta_min` (filtro de minimum_variance).

    `iv_polygon` y `vol_hist` son {ticker: vol anual}. La IV de Polygon manda
    si es positiva; si no, la vol historica; sin ninguna el colchon es NaN y
    el nombre se conserva. Columnas: symbol, delta, strike_mode, iv_used, pasa.
    """
    iv_polygon = iv_polygon or {}
    vol_hist = vol_hist or {}
    filas = []
    for t in dict.fromkeys(tickers):
        fila = evaluar_delta_candidato(
            vol_hist.get(t), years, rate, mode="otm", log_m=log_m, ref_years=ref_years,
            polygon_iv=iv_polygon.get(t))
        filas.append(dict(symbol=t, **fila, pasa=pasa_filtro_delta(fila["delta"], delta_min)))
    return pd.DataFrame(filas, columns=["symbol", "delta", "strike_mode", "iv_used", "pasa"])


def sector_implied_ready(n_names, min_names=4):
    """True si el sector tiene bastantes acciones para una correlacion implicita.

    Con dos nombres la dispersion del ETF se clava en el techo (rho_Q 0.999).
    """
    return int(n_names) >= int(min_names)


def clip_implied_correlation(rho, floor=0.0, ceiling=0.999):
    """Recorta una correlacion implicita. El piso por defecto es 0.

    Una cesta corta puede dar correlacion implicita negativa. Eso no es una
    prima utilizable: se deja en `floor` (y nunca por encima de `ceiling`).
    """
    if rho is None or not np.isfinite(rho):
        return float("nan")
    return float(min(float(ceiling), max(float(floor), float(rho))))


def align_daily_panel(price_wide, assets, spy_col="SPY", max_ffill=2, min_coverage=0.80):
    """Alinea precios diarios al calendario de SPY y descarta colas cortas.

    El calendario es la columna `spy_col` si existe. Si no, la serie con mas
    observaciones, y `info["calendar"]` lo dice. Las columnas bajo
    `min_coverage` salen de `info["dropped_low_coverage"]`; el resto se
    conserva. No exige que sobrevivan todos los activos.
    """
    import market_data as md

    assets = [a for a in list(assets) if a in price_wide.columns]
    wide = price_wide.sort_index()
    if spy_col in wide.columns and int(wide[spy_col].notna().sum()) >= 2:
        calendar = wide.index[wide[spy_col].notna()]
        calendar_name = spy_col
    else:
        sub = wide.reindex(columns=assets) if assets else wide
        ref = sub.notna().sum().idxmax() if sub.shape[1] else None
        calendar = sub.index[sub[ref].notna()] if ref is not None else sub.index[:0]
        calendar_name = f"mas_largo:{ref}"
    aligned, info = md.align_prices_to_calendar(
        wide.reindex(columns=assets), calendar, max_ffill=max_ffill, min_coverage=min_coverage)
    info = dict(info)
    info["calendar"] = calendar_name
    info["kept"] = list(aligned.columns)
    return aligned, info


def stitch_covariance(assets, daily_cov, daily_names, monthly_cov):
    """Covarianzas diarias entre los nombres largos; el resto, de la mensual.

    Parte de `monthly_cov` (todos los activos) y pisa el bloque de
    `daily_names` con `daily_cov`. Un nombre de historia corta no tira
    la matriz diaria entera: solo sus pares siguen en la mensual.
    """
    assets = list(assets)
    out = monthly_cov.reindex(index=assets, columns=assets).astype(float).copy()
    daily_names = [a for a in assets if a in set(daily_names)
                   and a in daily_cov.index and a in daily_cov.columns]
    if len(daily_names) >= 2:
        bloque = np.asarray(daily_cov.loc[daily_names, daily_names], dtype=float)
        out.loc[daily_names, daily_names] = bloque
    return out


def select_historical_otm(contracts, spot, as_of, target_dte, dte_tol,
                          moneyness_lo, moneyness_hi, min_dte=21):
    """Cadena OTM historica con strikes y DTE reales (A-5).

    Misma regla que polygon_client.fetch_otm_chain, sobre el dataframe de
    contratos de referencia (no sobre una rejilla de moneyness sintetica):

      * un solo vencimiento dentro de +/- dte_tol, prefiriendo DTE >= min_dte
        y DTE >= target_dte (el mensual largo, no el de 15 dias mas cercano);
      * calls con K >= spot y puts con K < spot;
      * moneyness K/S dentro de [moneyness_lo, moneyness_hi], los mismos
        limites que la cadena en vivo.

    `contracts` necesita strike_price, expiration_date, contract_type y ticker.
    Devuelve {"calls": [{strike, ticker}], "puts": [...], "dte": int|None,
    "expiracion": str|None}. dte es el del vencimiento elegido, no target_dte.
    """
    vacio = {"calls": [], "puts": [], "dte": None, "expiracion": None}
    if contracts is None or len(contracts) == 0:
        return vacio
    if spot is None or not np.isfinite(spot) or spot <= 0:
        return vacio

    df = contracts.copy()
    df["strike_price"] = pd.to_numeric(df["strike_price"], errors="coerce")
    df["expiration_date"] = pd.to_datetime(df["expiration_date"])
    df = df.dropna(subset=["strike_price", "expiration_date", "contract_type", "ticker"])
    if df.empty:
        return vacio

    as_of_ts = pd.Timestamp(as_of).normalize()
    df["dte"] = (df["expiration_date"].dt.normalize() - as_of_ts).dt.days
    df["moneyness"] = df["strike_price"] / float(spot)
    df = df[(df["dte"] - int(target_dte)).abs() <= int(dte_tol)]
    df = df[(df["moneyness"] >= float(moneyness_lo)) & (df["moneyness"] <= float(moneyness_hi))]
    tipo = df["contract_type"].astype(str).str.lower()
    otm = ((tipo == "call") & (df["strike_price"] >= spot)) | ((tipo == "put") & (df["strike_price"] < spot))
    df = df.loc[otm].copy()
    df["contract_type"] = tipo.loc[df.index]
    if df.empty:
        return vacio

    por_venc = df.groupby(df["expiration_date"].dt.strftime("%Y-%m-%d")).agg(
        n_call=("contract_type", lambda s: int((s == "call").sum())),
        n_put=("contract_type", lambda s: int((s == "put").sum())),
        dte=("dte", "min"),
    ).reset_index()
    por_venc = por_venc[(por_venc["n_call"] > 0) & (por_venc["n_put"] > 0)]
    if por_venc.empty:
        return vacio
    rango = pc.expiry_rank_columns(
        por_venc["dte"], int(target_dte), por_venc["n_call"] + por_venc["n_put"], min_dte)
    por_venc = por_venc.assign(**rango)
    elegido = por_venc.sort_values(pc.EXPIRY_SORT_COLS).iloc[0]
    df = df[df["expiration_date"].dt.strftime("%Y-%m-%d") == elegido["expiration_date"]]

    def _lado(nombre):
        sub = df[df["contract_type"] == nombre].drop_duplicates("strike_price")
        return [{"strike": float(k), "ticker": str(t)}
                for k, t in zip(sub["strike_price"], sub["ticker"])]

    return {
        "calls": _lado("call"),
        "puts": _lado("put"),
        "dte": int(elegido["dte"]),
        "expiracion": str(elegido["expiration_date"]),
    }


def summarize_yearly_mdd(yearly_mdd):
    """Resumen de MDD anuales. Los valores son negativos (peor = mas chico).

    El peor y el mejor ano salen de la serie completa. El escenario
    conservador es el percentil 10 de esa serie (la cola mala), no el 90,
    que en un MDD negativo es el ano mas suave. El filtro IQR solo entra
    en la mediana y el promedio.
    """
    s = pd.Series(yearly_mdd, dtype=float).dropna()
    s = s[np.isfinite(s.to_numpy(dtype=float))]
    if len(s) == 0:
        return None
    peor = float(s.min())
    mejor = float(s.max())
    if len(s) >= 3:
        conservador = float(s.quantile(0.10))
        q1 = float(s.quantile(0.25))
        q3 = float(s.quantile(0.75))
        iqr = q3 - q1
        filtrado = s[(s >= q1 - 1.5 * iqr) & (s <= q3 + 1.5 * iqr)]
        clean = filtrado if len(filtrado) >= 2 else s
        mediana = float(clean.median())
    else:
        conservador = peor
        clean = s
        mediana = float(s.mean())
    return {
        "peor": peor,
        "mejor": mejor,
        "conservador": conservador,
        "mediana": mediana,
        "promedio": float(clean.mean()),
        "n": int(len(s)),
        "n_iqr": int(len(clean)),
    }


def estimate_bkm_history_calls(n_tickers, n_pending_dates, contracts_per_date,
                               n_unique_contracts=None):
    """Llamadas Polygon aproximadas del bloque MFIS.

    2 por ticker para la cadena actual (call y put), 1 lista de contratos por
    fecha pendiente y los cierres. Sin `n_unique_contracts` cada fecha paga
    `contracts_per_date` agregados (techo). Con el rango por contrato unico
    el agregado se cuenta una sola vez.
    """
    actuales = 2 * int(n_tickers)
    listas = int(n_pending_dates)
    if n_unique_contracts is None:
        aggs = int(contracts_per_date) * int(n_pending_dates)
    else:
        aggs = int(n_unique_contracts)
    return actuales + listas + aggs


def close_near_from_bars(results, target_date, window_days=5):
    """Cierre del dia mas cercano a `target_date` dentro de ±window_days.

    `results` es la lista de agregados de Polygon (`t` en milisegundos, `c`
    el cierre). La misma regla sirve para la consulta de un solo dia y para
    recortar el rango largo de un contrato: una barra fuera de la ventana
    no entra, aunque el rango descargado la traiga.
    """
    if not results:
        return np.nan
    target = pd.Timestamp(target_date).normalize()
    limite = int(window_days)
    mejor = None
    mejor_dist = None
    for barra in results:
        t = barra.get("t")
        cierre = barra.get("c")
        if t is None or cierre is None:
            continue
        try:
            fecha = pd.to_datetime(t, unit="ms").normalize()
            dist = abs(int((fecha - target).days))
            precio = float(cierre)
        except (TypeError, ValueError, OverflowError):
            continue
        if dist > limite or not np.isfinite(precio):
            continue
        if mejor_dist is None or dist < mejor_dist:
            mejor_dist = dist
            mejor = precio
    return np.nan if mejor is None else mejor


def contract_agg_ranges(needed, window_days=5):
    """Un rango de agregados por contrato, cubriendo todas las fechas en que se usa.

    `needed` es una lista de (ticker_opcion, fecha). El rango va de la primera
    fecha menos la ventana a la ultima mas la ventana, que es lo que pedia
    cada consulta diaria de ±window_days. Recortar despues con
    close_near_from_bars deja el mismo precio.
    """
    tramo = {}
    for contrato, fecha in needed:
        if not contrato:
            continue
        ts = pd.Timestamp(fecha).normalize()
        previo = tramo.get(contrato)
        if previo is None:
            tramo[contrato] = (ts, ts)
        else:
            tramo[contrato] = (min(previo[0], ts), max(previo[1], ts))
    ventana = pd.Timedelta(days=int(window_days))
    return {
        contrato: (
            (lo - ventana).strftime("%Y-%m-%d"),
            (hi + ventana).strftime("%Y-%m-%d"),
        )
        for contrato, (lo, hi) in tramo.items()
    }


def plan_bkm_history_budget(ranked, contracts_per_date=26, calls_per_min=1200.0,
                            max_minutes=60.0, spent_calls=0):
    """Que tickers entran a la historia de MFIS con el presupuesto de llamadas.

    `ranked` va en orden de prioridad (el de los candidatos). Cada fila trae
    ticker, us, mfis_ok y n_pending (fechas que no estan en cache). Solo un
    ticker de EE. UU. con MFIS actual finito gasta historia. El costo es
    (1 + contratos por fecha) * fechas pendientes: la lista de contratos por
    fecha y el techo de agregados. Un acierto de cache (n_pending 0) no gasta.

    No es todo o nada. Se recorre el ranking y entra el que cabe. El que no
    cabe queda con motivo historia_no_procesada_presupuesto. Si sobran
    llamadas para alguna fecha de ese ticker, `calentar` dice cuantas fechas
    bajar para dejar la cache tibia; el ticker sigue marcado como no procesado.
    """
    elegibles = []
    fuera = []
    for row in ranked:
        ticker = row["ticker"]
        if not row.get("us"):
            fuera.append({"ticker": ticker, "motivo": "sin_opciones_us"})
            continue
        if not row.get("mfis_ok"):
            fuera.append({
                "ticker": ticker,
                "motivo": row.get("motivo") or "sin_mfis_actual",
            })
            continue
        elegibles.append(row)

    if not calls_per_min or max_minutes is None:
        presupuesto = None
    else:
        presupuesto = float(max_minutes) * float(calls_per_min) - float(spent_calls)
        if presupuesto < 0:
            presupuesto = 0.0

    unit = 1 + int(contracts_per_date)
    procesar = []
    omitidos = []
    usadas = 0.0
    calentar = None
    calentado = False
    for row in elegibles:
        n_pend = int(row.get("n_pending") or 0)
        costo = unit * n_pend
        cabe = presupuesto is None or usadas + costo <= presupuesto + 1e-9
        if cabe:
            procesar.append(row["ticker"])
            usadas += costo
            continue
        omitidos.append({
            "ticker": row["ticker"],
            "motivo": "historia_no_procesada_presupuesto",
        })
        if calentado or presupuesto is None or n_pend <= 0:
            calentado = True
            continue
        restante = presupuesto - usadas
        n_fechas = int(restante // unit)
        if n_fechas > 0:
            n_fechas = min(n_pend, n_fechas)
            calentar = {"ticker": row["ticker"], "n_fechas": int(n_fechas)}
            usadas += unit * n_fechas
        calentado = True

    minutos = None
    if calls_per_min:
        minutos = (float(spent_calls) + usadas) / float(calls_per_min)
    return {
        "procesar": procesar,
        "omitidos": omitidos,
        "fuera_de_historia": fuera,
        "calentar": calentar,
        "llamadas": int(round(usadas)),
        "minutos": minutos,
        "n_us_mfis": len(elegibles),
    }


_SIN_PRESUPUESTO = {"0", "none", "null", "unlimited", "inf", "sin_tope", "ilimitado"}


def mfis_max_minutes_from_env(default=60.0, env=None):
    """Presupuesto del bloque MFIS en minutos: `MFIS_MAX_MINUTES` o `default`.

    0 / none / unlimited -> None (sin presupuesto: entra todo el que tenga
    MFIS actual). Un valor no numerico o negativo avisa y usa `default`.
    El ritmo de llamadas sale de POLYGON_CALLS_PER_MINUTE (polygon_client).
    """
    crudo = (os.environ if env is None else env).get("MFIS_MAX_MINUTES")
    if crudo is None or not str(crudo).strip():
        return default
    texto = str(crudo).strip().lower()
    if texto in _SIN_PRESUPUESTO:
        return None
    try:
        minutos = float(texto)
    except ValueError:
        minutos = float("nan")
    if not math.isfinite(minutos) or minutos < 0:
        print(f"ADVERTENCIA: MFIS_MAX_MINUTES={crudo!r} invalido; se usan {default:g} min.")
        return default
    return None if minutos == 0 else minutos


def _clave_cap(ticker, market_caps):
    texto = str(ticker).strip().upper()
    for clave in (texto, texto.replace("-", "."), texto.replace(".", "-")):
        cap = market_caps.get(clave)
        if cap is not None and np.isfinite(cap) and cap > 0:
            return float(cap)
    return None


def orden_prioridad_mfis(tickers, market_caps=None, ranking=None):
    """Cola del MFIS por relevancia, para que un corte de presupuesto deje
    fuera a los menos relevantes y no a los grandes (LLY).

    Primero los que tienen market cap, de mayor a menor; despues el orden de
    `ranking` (p. ej. el h_score del pre-filtro); el empate queda en el orden
    recibido. No cambia que tickers se evaluan, solo el turno.
    """
    market_caps = market_caps or {}
    posicion = {str(t): i for i, t in enumerate(ranking or [])}
    unicos = list(dict.fromkeys(tickers))

    def clave(par):
        i, ticker = par
        cap = _clave_cap(ticker, market_caps)
        return (cap is None, -(cap or 0.0), posicion.get(str(ticker), len(posicion)), i)

    return [t for _, t in sorted(enumerate(unicos), key=clave)]


def frontier_lambda_grid(lambda_ref=None, n=60, lo=0.1, hi=200.0):
    """Lambdas del barrido de la frontera. Incluye el lambda del portafolio."""
    rejilla = np.logspace(np.log10(float(lo)), np.log10(float(hi)), int(n))
    if lambda_ref is not None and np.isfinite(lambda_ref) and float(lambda_ref) > 0:
        rejilla = np.append(rejilla, float(lambda_ref))
    return np.unique(np.sort(rejilla.astype(float)))


def portfolio_mu_final_metrics(weights, mu_final, cov, lambda_ref, rf=0.0):
    """Riesgo, retorno w'μ_final y utilidad con un unico lambda de referencia."""
    w = np.asarray(weights, dtype=float).reshape(-1)
    mu_v = np.asarray(mu_final, dtype=float).reshape(-1)
    cov_m = np.asarray(cov, dtype=float)
    ret = float(w @ mu_v)
    var = float(w @ cov_m @ w)
    if not np.isfinite(var) or var < 0:
        var = 0.0
    vol = float(np.sqrt(var))
    utilidad = ret - (float(lambda_ref) / 2.0) * var
    sharpe = (ret - float(rf)) / vol if vol > 0 else np.nan
    return {"ret": ret, "vol": vol, "var": var, "utilidad": utilidad, "sharpe": sharpe}


def frontier_curve(solve_fn, cov, mu_final, lambdas, lambda_utility=None):
    """Frontera exacta: cada punto es el QP a ese lambda, medido con μ_final.

    risk = sqrt(w'Σw), ret = w'μ_final. La utilidad del color usa
    lambda_utility (el lambda configurado) para que los puntos se comparen
    entre si. El optimo del libro es el punto cuyo lambda es el configurado.
    """
    cov_m = np.asarray(cov, dtype=float)
    mu_v = np.asarray(mu_final, dtype=float).reshape(-1)
    filas = []
    for lam in lambdas:
        w = solve_fn(float(lam))
        if w is None:
            continue
        w = np.asarray(w, dtype=float).reshape(-1)
        if w.shape[0] != mu_v.shape[0] or not np.isfinite(w).all() or float(np.nansum(w)) <= 0:
            continue
        ref = float(lam if lambda_utility is None else lambda_utility)
        met = portfolio_mu_final_metrics(w, mu_v, cov_m, ref)
        filas.append({
            "lambda_": float(lam),
            "risk": met["vol"],
            "ret": met["ret"],
            "utility": met["utilidad"],
        })
    return pd.DataFrame(filas)


def comparison_lambdas(lambda_ref, base=None):
    """Rejilla de la figura de lambdas, con el lambda configurado incluido."""
    if base is None:
        base = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.5, 10.0]
    valores = [float(v) for v in base]
    if lambda_ref is not None and np.isfinite(lambda_ref) and float(lambda_ref) > 0:
        valores.append(float(lambda_ref))
    ordenados = []
    for valor in sorted(valores):
        if not any(abs(valor - previo) < 1e-9 for previo in ordenados):
            ordenados.append(valor)
    return ordenados


def score_candidate_portfolios(solved, mu_final, cov, lambda_ref, rf=0.0):
    """Puntua cada portafolio candidato con el mismo lambda y con μ_final.

    `solved` es una lista de (lambda_con_el_que_se_resolvio, pesos). La
    utilidad no usa el lambda de esa fila: si lo hiciera, el lambda mas
    chico ganaria siempre. El retorno es w'μ_final, el mismo vector que ve
    el optimizador.

    `pen_ret` si usa el lambda de la fila: (lambda/2 w'Σw) / w'μ_final, el
    peso que tiene el riesgo frente al retorno en el objetivo con el que se
    resolvio ese portafolio. Cerca de 0 el QP casi solo maximiza retorno;
    cerca de 1 la penalizacion se come el retorno. NaN si w'μ_final <= 0.
    """
    filas = []
    for lam, w in solved:
        if w is None:
            continue
        w = np.asarray(w, dtype=float).reshape(-1)
        if not np.isfinite(w).all() or float(np.nansum(w)) <= 0.9:
            continue
        met = portfolio_mu_final_metrics(w, mu_final, cov, lambda_ref, rf=rf)
        terms = utility_terms(met["ret"], met["var"], lam)
        pen_ret = terms["risk_term"] / terms["mu_term"] if terms["mu_term"] > 0 else np.nan
        filas.append({
            "lambda_": float(lam),
            "retorno": met["ret"] * 100.0,
            "volatilidad": met["vol"] * 100.0,
            "sharpe": met["sharpe"],
            "utilidad": met["utilidad"],
            "pen_ret": pen_ret,
            "ret": met["ret"],
            "risk": met["vol"],
            "n_activos": int(np.sum(w > 0.01)),
            "max_peso": float(np.max(w) * 100.0) if w.size else np.nan,
        })
    return pd.DataFrame(filas)


def mfiv_annual_vol(mfiv, dte):
    """Vol anual de una MFIV integrada, con el DTE real de la cadena."""
    vol = rk.implied_variance_to_horizon(mfiv, dte, 1.0)["annual_vol"]
    if np.ndim(vol) == 0:
        vol = float(vol)
    return vol


# ==============================================================================
# E-1 PISO DE ETF, REPOSICIONES Y FACTIBILIDAD DE RESTRICCIONES
# ==============================================================================
# Precedencia (la misma que documenta quadratic_utility.py):
#   1. Los descartes de los filtros duros (delta, IV vs vol. reciente y MFIS)
#      no se revierten: ni la reposicion por piso de sobrevivientes ni la de
#      ETF puede traer de vuelta un nombre que uno de ellos ya saco.
#   2. El umbral de vol. reciente y el techo n_filter_candidates son blandos,
#      igual que en su propio piso de sobrevivientes: la reposicion toma
#      candidatos en orden ascendente de ratio aunque esten por encima.
#   3. Si faltan ETF para el piso de la banda, la reposicion prioriza ETF.
#   4. Si aun asi el piso no es alcanzable, el chequeo de factibilidad lo
#      relaja al maximo alcanzable (o detiene la corrida) con un aviso claro.

def etfs_necesarios(etf_floor, max_weight, tol=1e-9):
    """ETF minimos para que el piso de la banda sea alcanzable.

    Con tope por activo `max_weight`, n ETF suman como mucho n * max_weight.
    Piso 0.45 y tope 0.12 piden ceil(3.75) = 4. Piso <= 0 no pide ninguno.
    """
    floor = float(etf_floor)
    if not math.isfinite(floor) or floor <= tol:
        return 0
    mw = float(max_weight)
    if not (math.isfinite(mw) and mw > 0):
        raise ValueError("max_weight debe ser finito y > 0")
    return int(math.ceil(floor / mw - tol))


def contar_etfs(tickers, etf_set):
    """Cuantos de `tickers` (sin repetir) son ETF o commodities."""
    etf_set = set(etf_set)
    return sum(1 for t in dict.fromkeys(tickers) if t in etf_set)


def reserva_etf(ranking, seleccionados, etf_set, n_objetivo):
    """ETF de una etapa previa que no entraron a la seleccion.

    Recorre `ranking` en orden y devuelve los ETF que faltan para que la
    seleccion mas la reserva sumen `n_objetivo` ETF. La reserva no entra al
    flujo: solo se usa si el piso de ETF la necesita.
    """
    falta = int(n_objetivo) - contar_etfs(seleccionados, etf_set)
    if falta <= 0:
        return []
    etf_set = set(etf_set)
    sel = set(seleccionados)
    out = []
    for t in dict.fromkeys(ranking):
        if t in etf_set and t not in sel:
            out.append(t)
            if len(out) >= falta:
                break
    return out


def candidatos_reposicion(ordenados, actuales, descartados=(), rechaza=None):
    """Orden de reposicion sin los actuales ni los descartados por filtros duros.

    `descartados` son nombres que un filtro duro ya saco (por ejemplo IV vs
    vol. reciente). `rechaza(t)`, si se da, aplica ese mismo filtro a nombres
    que nunca pasaron por el, y los saca si no lo superan.
    """
    act = set(actuales)
    desc = set(descartados)
    out = []
    for t in dict.fromkeys(ordenados):
        if t in act or t in desc:
            continue
        if rechaza is not None and rechaza(t):
            continue
        out.append(t)
    return out


def completar_etfs(actuales, candidatos, etf_set, n_necesarios):
    """ETF a agregar, en el orden de `candidatos`, hasta tener `n_necesarios`."""
    falta = int(n_necesarios) - contar_etfs(actuales, etf_set)
    if falta <= 0:
        return []
    etf_set = set(etf_set)
    act = set(actuales)
    out = []
    for t in dict.fromkeys(candidatos):
        if t in etf_set and t not in act:
            out.append(t)
            if len(out) >= falta:
                break
    return out


def siguiente_reposicion(pool, usados, etf_set=(), priorizar_etf=False, solo_etf=False):
    """Siguiente reemplazo del pool que aun no se uso.

    priorizar_etf: el primer ETF libre si lo hay; si no, el primero libre.
    solo_etf: solo un ETF (None si no queda ninguno).
    """
    etf_set = set(etf_set)
    usados = set(usados)
    libres = [t for t in dict.fromkeys(pool) if t not in usados]
    if priorizar_etf or solo_etf:
        for t in libres:
            if t in etf_set:
                return t
        if solo_etf:
            return None
    return libres[0] if libres else None


def restricciones_factibles(Amat, bvec, meq=0, tol=1e-9):
    """True si existe w con A[:, :meq].T w == b[:meq] y A[:, meq:].T w >= b[meq:].

    Mismo formato que quadprog.solve_qp (columnas = restricciones). Se resuelve
    un LP sin objetivo con HiGHS; `tol` absorbe redondeo en las cotas.
    """
    from scipy.optimize import linprog

    A = np.asarray(Amat, dtype=float)
    b = np.asarray(bvec, dtype=float)
    if A.ndim != 2 or A.shape[1] != b.size:
        raise ValueError("Amat debe ser n x m y bvec de largo m")
    n = A.shape[0]
    meq = int(meq)
    kwargs = {}
    if meq > 0:
        kwargs["A_eq"] = A[:, :meq].T
        kwargs["b_eq"] = b[:meq]
    if A.shape[1] > meq:
        kwargs["A_ub"] = -A[:, meq:].T
        kwargs["b_ub"] = -b[meq:] + tol
    res = linprog(np.zeros(n), bounds=[(None, None)] * n, method="highs", **kwargs)
    return bool(res.status == 0)


def diagnostico_banda_etf(n_etf, n_acciones, max_weight, etf_lo, etf_hi, tol=1e-9):
    """Razones legibles por las que la banda de ETF y los topes no cierran.

    Lista vacia si los conteos alcanzan (la combinacion con los topes
    regionales puede seguir fallando; eso lo decide restricciones_factibles).
    """
    mw = float(max_weight)
    cap_etf = n_etf * mw
    cap_acc = n_acciones * mw
    razones = []
    if (n_etf + n_acciones) * mw < 1 - tol:
        razones.append(
            f"{n_etf + n_acciones} activos x max_weight {mw:.2f} = {(n_etf + n_acciones) * mw:.0%} "
            f"no alcanza el 100% del portafolio")
    if cap_etf < etf_lo - tol:
        razones.append(
            f"piso de ETF {etf_lo:.0%} inalcanzable: {n_etf} ETF x max_weight {mw:.2f} = {cap_etf:.0%} "
            f"(se necesitan al menos {etfs_necesarios(etf_lo, mw)} ETF)")
    stk_lo = 1 - etf_hi
    if cap_acc < stk_lo - tol:
        razones.append(
            f"piso de acciones {stk_lo:.0%} (1 - techo ETF {etf_hi:.0%}) inalcanzable: "
            f"{n_acciones} acciones x max_weight {mw:.2f} = {cap_acc:.0%}")
    return razones


def relajar_banda_etf(n_etf, n_acciones, max_weight, etf_lo, etf_hi):
    """Banda de ETF mas cercana a la pedida que los conteos pueden cumplir.

    El piso baja a n_etf * max_weight si no se alcanza; el techo sube a
    1 - n_acciones * max_weight si las acciones no llenan su parte. Lo que ya
    era alcanzable no cambia.
    """
    mw = float(max_weight)
    cap_etf = min(1.0, n_etf * mw)
    cap_acc = min(1.0, n_acciones * mw)
    lo = min(float(etf_lo), cap_etf)
    hi = min(1.0, max(float(etf_hi), 1.0 - cap_acc))
    lo = min(lo, hi)
    return lo, hi


def resumen_ajuste_iv(momentos):
    """Resumen del ajuste IV/tasa sobre momentos BKM (dicts con carry, carry_ok...).

    Cuenta solo las cadenas consultadas (las que traen `carry`). Medianas sobre
    las calibradas (carry_ok). Brechas en puntos de vol (0.05 = 5 puntos).
    """
    filas = [m for m in momentos if isinstance(m, dict) and "carry" in m]
    ok = [m for m in filas if m.get("carry_ok")]

    def _mediana(clave):
        vals = [float(m[clave]) for m in ok if m.get(clave) is not None and np.isfinite(m[clave])]
        return float(np.median(vals)) if vals else float("nan")

    return {"n": len(filas), "n_ok": len(ok), "carry_mediana": _mediana("carry"),
            "brecha_antes": _mediana("iv_gap_antes"), "brecha_despues": _mediana("iv_gap_despues")}


def texto_ajuste_iv(resumen, rate):
    """Linea de consola para `resumen_ajuste_iv`."""
    if not resumen["n"]:
        return "Ajuste IV/tasa: sin cadenas consultadas"
    if not resumen["n_ok"]:
        return (f"Ajuste IV/tasa: 0 de {resumen['n']} cadenas con pares call/put; "
                f"se reprecia a la tasa del script ({rate:.2%})")
    return (f"Ajuste IV/tasa: {resumen['n_ok']} de {resumen['n']} cadenas calibradas | "
            f"acarreo implicito mediano de Polygon {resumen['carry_mediana']:+.2%} (script {rate:.2%}) | "
            f"brecha IV call-put mediana {resumen['brecha_antes'] * 100:.1f} -> "
            f"{resumen['brecha_despues'] * 100:.1f} puntos")
