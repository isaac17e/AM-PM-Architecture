# ==============================================================================
# BL_METRICS - Unidades, delta de mercado y drawdown de Black-Litterman
# ==============================================================================
# Extraido de black_litterman.py para probarlo sin Polygon ni el universo:
#
#   1. Toda la cadena Q -> P vive al horizonte (M-11). La vol ATM de SSVI
#      sale anual (sqrt(w/T)); la varianza historica y el MFIV de BKM estan
#      integrados al horizonte. El fallback no puede meter la anual en el MFIV.
#   2. El delta de mercado de pi = delta * Sigma @ w (M-12) tiene tres modos.
#      El default historico no cambia; fixed e implied son opt-in.
#   3. El MDD de una serie de log-retornos usa exp(cumsum), no (1+r).cumprod
#      (B-1). El retorno del portafolio es el log exacto, no la suma de logs.
# ==============================================================================

import numpy as np
import pandas as pd

import risk_estimators as rk

__all__ = [
    "vol_annual_to_horizon",
    "variance_annual_to_horizon",
    "iv_vol_at_horizon",
    "mfiv_or_horizon_variance",
    "market_delta",
    "mdd_from_log_returns",
    "log_portfolio_return",
]

_DELTA_MODES = ("historical", "fixed", "implied")


def vol_annual_to_horizon(vol_annual, horizon_years):
    """Volatilidad anual -> volatilidad del horizonte (sd * sqrt(h))."""
    return rk.scale_moments(1.0, float(horizon_years), sd=vol_annual)["sd"]


def variance_annual_to_horizon(var_annual, horizon_years):
    """Varianza anual -> varianza integrada al horizonte.

    Una varianza anual es la varianza integrada sobre un ano. Llevarla al
    horizonte es lo mismo que rk.implied_variance_to_horizon con DTE = 365.
    """
    out = rk.implied_variance_to_horizon(
        var_annual, dte=rk.DAYS_PER_YEAR, horizon_years=float(horizon_years))
    return out["horizon_var"]


def iv_vol_at_horizon(sigma_annual, var_hist_horizon, horizon_years):
    """Vol al horizonte para armar Sigma (M-11).

    Con SSVI se escala la vol anual. Sin SSVI se usa sqrt(varianza historica),
    que ya esta al horizonte. Las dos ramas quedan en la misma unidad: antes
    la vol anual y la vol historica compartian el mismo vector.
    """
    anual = np.asarray(sigma_annual, dtype=float)
    if np.ndim(anual) == 0 and np.isfinite(anual) and float(anual) > 0:
        return float(vol_annual_to_horizon(float(anual), horizon_years))
    var_h = float(var_hist_horizon)
    if not np.isfinite(var_h) or var_h <= 0:
        return np.nan
    return float(np.sqrt(var_h))


def mfiv_or_horizon_variance(mfiv, var_horizon):
    """MFIV al horizonte, o la varianza al horizonte si BKM no dio un valor.

    MFIV es la varianza integrada entre hoy y el vencimiento. `var_horizon`
    tiene que estar en esa unidad. Meter aqui la varianza anual (sigma_atm^2)
    la infla por 1/tau (M-11, el fallback de la cadena Q -> P).
    """
    valor = float(mfiv) if mfiv is not None else np.nan
    if np.isfinite(valor) and valor > 0:
        return valor
    respaldo = float(var_horizon)
    if not np.isfinite(respaldo) or respaldo <= 0:
        return np.nan
    return respaldo


def market_delta(mode, excess_hist, var_hist, delta_fixed=2.5, var_q=None, var_p=None):
    """Delta de pi = delta * Sigma @ w (M-12).

    historical  exceso historico / varianza historica, ambos al horizonte.
                Es el comportamiento previo. Con dos anos de media puede ser
                negativo; esta funcion no lo recorta (el ancla de Esscher si).
    fixed       `delta_fixed`. No hereda el ruido de la media corta.
    implied     prima implicita / varianza fisica de la cartera de mercado.
                La prima es la varianza neutral al riesgo de esa cartera:
                en Martin el exceso esperado del mercado es SVIX^2, y aqui
                SVIX^2 es la varianza Q al horizonte que ya salio de MFIV.
                delta = var_q / var_p. Si var_p no sirve, se usa el historico
                y se avisa en info["fallback"].

    Devuelve (delta, info) con las tres referencias para poder imprimirlas.
    """
    modo = str(mode).lower()
    if modo not in _DELTA_MODES:
        raise ValueError("mode debe ser 'historical', 'fixed' o 'implied'")
    fijo = float(delta_fixed)
    if not np.isfinite(fijo) or fijo <= 0:
        raise ValueError("delta_fixed debe ser positivo")

    var_h = float(var_hist)
    exc = float(excess_hist)
    historico = exc / var_h if np.isfinite(var_h) and var_h > 0 and np.isfinite(exc) else np.nan

    vq = np.nan if var_q is None else float(var_q)
    vp = np.nan if var_p is None else float(var_p)
    implicito = vq / vp if np.isfinite(vq) and vq >= 0 and np.isfinite(vp) and vp > 0 else np.nan

    info = {
        "mode": modo,
        "historical": historico,
        "fixed": fijo,
        "implied": implicito,
        "fallback": None,
    }
    if modo == "historical":
        return historico, info
    if modo == "fixed":
        return fijo, info
    if np.isfinite(implicito):
        return implicito, info
    info["fallback"] = "implied no calculable (var_p o var_q); se usa el delta historico"
    info["mode"] = "historical"
    return historico, info


def mdd_from_log_returns(returns):
    """Maximo drawdown de log-retornos. Riqueza = exp(cumsum), no (1+r).cumprod."""
    return rk.max_drawdown(returns, log_returns=True)


def log_portfolio_return(log_returns, weights):
    """Log-retorno de un periodo. Omite NaN y renormaliza los pesos presentes.

    r = log(1 + sum_i w_i (exp(r_i) - 1)). La suma ponderada de logs solo
    coincide a primer orden.
    """
    r = pd.Series(log_returns, dtype=float)
    w = pd.Series(weights, dtype=float).reindex(r.index).fillna(0.0)
    mask = np.isfinite(r.to_numpy(dtype=float)) & (w.to_numpy(dtype=float) > 0)
    if not np.any(mask):
        return np.nan
    ww = w[mask]
    ww = ww / ww.sum()
    fila = r[mask].to_frame().T
    return float(rk.portfolio_log_returns(fila, ww).iloc[0])
