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

import math

import numpy as np
import pandas as pd
from scipy.optimize import minimize

import risk_estimators as rk

__all__ = [
    "vol_annual_to_horizon",
    "variance_annual_to_horizon",
    "iv_vol_at_horizon",
    "mfiv_or_horizon_variance",
    "market_delta",
    "mdd_from_log_returns",
    "log_portfolio_return",
    "ssvi_total_variance",
    "fit_ssvi",
    "integration_strike_bounds",
    "mfiv_vs_atm",
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


def ssvi_total_variance(k, theta, rho, eta, gamma):
    """Varianza total SSVI (Gatheral-Jacquier) en log-moneyness k."""
    k = np.asarray(k, dtype=float)
    theta = np.asarray(theta, dtype=float)
    phi = float(eta) * np.power(theta, -float(gamma))
    rho = float(rho)
    return theta / 2.0 * (
        1.0 + rho * phi * k + np.sqrt((phi * k + rho) ** 2 + (1.0 - rho ** 2))
    )


def fit_ssvi(k, w, theta_por_fila, theta_fijo, slice_index=None,
             gtol=1e-5, maxiter=2000, rmse_rel_max=0.20):
    """Calibra (rho, eta, gamma) y acepta el ajuste por residuo, no por opt.success.

    L-BFGS-B con tolerancia laxa: BFGS a gtol=1e-10 marcaba 'precision loss' en
    casi toda la cadena y el script igual usaba el resultado. Aqui el ajuste
    entra solo si el RMSE relativo de la varianza total es <= rmse_rel_max y
    no hay arbitraje de calendario (GJ <= 4).

    Las filas se ordenan por (vencimiento, k) antes de sumar el error, para que
    el mismo insumo de siempre el mismo parametro aunque la cadena llegue
    desordenada.
    """
    k = np.asarray(k, dtype=float).ravel()
    w = np.asarray(w, dtype=float).ravel()
    theta_por_fila = np.asarray(theta_por_fila, dtype=float).ravel()
    theta_fijo = np.asarray(theta_fijo, dtype=float).ravel()
    if slice_index is None:
        slice_index = np.zeros(len(k))
    slice_index = np.asarray(slice_index).ravel()
    if not (len(k) == len(w) == len(theta_por_fila) == len(slice_index)):
        raise ValueError("k, w, theta_por_fila y slice_index deben medir lo mismo")
    if len(k) == 0 or len(theta_fijo) == 0:
        raise ValueError("SSVI sin observaciones")

    order = np.lexsort((k, slice_index.astype(float)))
    k = np.ascontiguousarray(k[order])
    w = np.ascontiguousarray(w[order])
    theta_por_fila = np.ascontiguousarray(theta_por_fila[order])

    def _sigmoid(x):
        return 1.0 / (1.0 + math.exp(-float(x)))

    p0 = (0.3 - 0.05) / 0.9
    u0 = np.array([0.0, 0.0, math.log(p0 / (1.0 - p0))])
    bounds = [(-3.8, 3.8), (-10.0, 8.0), (-12.0, 12.0)]

    def objetivo(u):
        rho = math.tanh(u[0])
        eta = math.exp(u[1])
        gamma = _sigmoid(u[2]) * 0.9 + 0.05
        modelo = ssvi_total_variance(k, theta_por_fila, rho, eta, gamma)
        error = float(np.sum((modelo - w) ** 2))
        phi = eta * np.power(theta_fijo, -gamma)
        gj = theta_fijo * phi * (1.0 + abs(rho))
        return error + float(np.sum(np.maximum(0.0, gj - 4.0) ** 2)) * 1e3

    opt = minimize(objetivo, u0, method="L-BFGS-B", bounds=bounds,
                   options={"maxiter": int(maxiter), "ftol": float(gtol), "gtol": float(gtol)})
    rho = float(math.tanh(opt.x[0]))
    eta = float(math.exp(opt.x[1]))
    gamma = float(_sigmoid(opt.x[2]) * 0.9 + 0.05)
    modelo = ssvi_total_variance(k, theta_por_fila, rho, eta, gamma)
    rmse = float(np.sqrt(np.mean((modelo - w) ** 2)))
    escala = float(np.mean(np.abs(w)))
    rel = rmse / escala if escala > 0 else float("inf")
    phi = eta * np.power(theta_fijo, -gamma)
    gj_max = float(np.max(theta_fijo * phi * (1.0 + abs(rho))))
    aceptado = bool(np.isfinite(rel) and rel <= float(rmse_rel_max) and gj_max <= 4.0 + 1e-6)
    return {
        "rho": rho, "eta": eta, "gamma": gamma,
        "rmse": rmse, "rmse_rel": rel, "gj_max": gj_max,
        "aceptado": aceptado, "success": bool(opt.success),
        "metodo": "ssvi_conjunto" if aceptado else "ssvi_rechazado",
        "n_strikes": int(len(k)),
        "k_min": float(np.min(k)), "k_max": float(np.max(k)),
    }


def integration_strike_bounds(forward, sigma_atm, horizon_years, n_std=3.0,
                              k_min=None, k_max=None):
    """Strikes de la integral BKM: +/- n_std y, si hay cadena, el k observado.

    Integrar las alas SSVI hasta +/-6 sigma mete varianza que el mercado no
    cotiza. El cruce con [k_min, k_max] se queda dentro de los strikes vistos.
    """
    forward = float(forward)
    wing = float(n_std) * float(sigma_atm) * math.sqrt(float(horizon_years))
    lo = forward * math.exp(-wing)
    hi = forward * math.exp(wing)
    if k_min is not None and np.isfinite(k_min):
        lo = max(lo, forward * math.exp(float(k_min)))
    if k_max is not None and np.isfinite(k_max):
        hi = min(hi, forward * math.exp(float(k_max)))
    if not (np.isfinite(lo) and np.isfinite(hi)) or hi <= lo:
        lo = forward * math.exp(-wing)
        hi = forward * math.exp(wing)
    return float(lo), float(hi)


def mfiv_vs_atm(mfiv, atm_var, lo=0.8, hi=2.0):
    """Comprueba MFIV / varianza ATM. Fuera de banda, sustituye por la ATM.

    Devuelve el MFIV a usar y, si se descarta, MFIS/MFIK neutros (0 y 3).
    """
    if not (np.isfinite(mfiv) and np.isfinite(atm_var) and atm_var > 0 and mfiv > 0):
        return {"ok": False, "ratio": np.nan, "mfiv": np.nan,
                "mfis": 0.0, "mfik": 3.0, "motivo": "mfiv_no_finita"}
    ratio = float(mfiv) / float(atm_var)
    if float(lo) <= ratio <= float(hi):
        return {"ok": True, "ratio": ratio, "mfiv": float(mfiv), "motivo": "ok"}
    return {"ok": False, "ratio": ratio, "mfiv": float(atm_var),
            "mfis": 0.0, "mfik": 3.0, "motivo": "mfiv_fuera_de_banda"}
