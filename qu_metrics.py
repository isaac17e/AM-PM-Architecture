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
# ==============================================================================

from datetime import date, timedelta

import numpy as np
import pandas as pd

import risk_estimators as rk

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
    "select_historical_otm",
    "estimate_bkm_history_calls",
    "mfiv_annual_vol",
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
    return w, info


def select_historical_otm(contracts, spot, as_of, target_dte, dte_tol,
                          moneyness_lo, moneyness_hi):
    """Cadena OTM historica con strikes y DTE reales (A-5).

    Misma regla que polygon_client.fetch_otm_chain, sobre el dataframe de
    contratos de referencia (no sobre una rejilla de moneyness sintetica):

      * un solo vencimiento, el de DTE mas cercano a target_dte dentro de
        +/- dte_tol (empate: el que tiene mas contratos);
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
    por_venc["_dist"] = (por_venc["dte"] - int(target_dte)).abs()
    por_venc["_n"] = -(por_venc["n_call"] + por_venc["n_put"])
    elegido = por_venc.sort_values(["_dist", "_n"]).iloc[0]
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


def estimate_bkm_history_calls(n_tickers, n_pending_dates, contracts_per_date):
    """Llamadas Polygon aproximadas del bloque MFIS.

    2 por ticker para la cadena actual (call y put) mas, por fecha pendiente,
    1 consulta de contratos y `contracts_per_date` cierres. El minuto lo pone
    polygon_client.estimate_minutes con POLYGON_CALLS_PER_MIN: si el producto
    supera bkm_hist_max_minutes el script omite la historia y solo calcula el
    momento actual. La rejilla vieja de 7 puntos subestimaba este costo.
    """
    return int(2 * n_tickers + (1 + int(contracts_per_date)) * int(n_pending_dates))


def mfiv_annual_vol(mfiv, dte):
    """Vol anual de una MFIV integrada, con el DTE real de la cadena."""
    vol = rk.implied_variance_to_horizon(mfiv, dte, 1.0)["annual_vol"]
    if np.ndim(vol) == 0:
        vol = float(vol)
    return vol
