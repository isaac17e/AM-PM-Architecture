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
    "ssvi_weights",
    "ssvi_row_mask",
    "ssvi_surface_decision",
    "apply_vol_q_to_p",
    "clip_negligible_weights",
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


def _ssvi_vacio(n_strikes, k_min, k_max):
    return {
        "rho": np.nan, "eta": np.nan, "gamma": np.nan,
        "rmse": np.nan, "rmse_rel": float("inf"), "gj_max": np.nan,
        "aceptado": False, "success": False, "metodo": "ssvi_rechazado",
        "n_strikes": int(n_strikes), "k_min": k_min, "k_max": k_max,
    }


def fit_ssvi(k, w, theta_por_fila, theta_fijo, slice_index=None,
             gtol=1e-5, maxiter=2000, rmse_rel_max=0.20,
             weights=None, k_abs_max=0.5):
    """Calibra (rho, eta, gamma) y acepta el ajuste por residuo, no por opt.success.

    L-BFGS-B con tolerancia laxa: BFGS a gtol=1e-10 marcaba 'precision loss' en
    casi toda la cadena y el script igual usaba el resultado. Aqui el ajuste
    entra solo si el RMSE relativo de la varianza total es <= rmse_rel_max y
    no hay arbitraje de calendario (GJ <= 4).

    Las filas se ordenan por (vencimiento, k) antes de sumar el error, para que
    el mismo insumo de siempre el mismo parametro aunque la cadena llegue
    desordenada.

    `k_abs_max` deja fuera las alas profundas (un put de $5 con k ~ -5). El
    RMSE es ponderado: sqrt(sum(peso * e^2) / sum(peso)). `n_strikes`, `k_min`
    y `k_max` son los de la ventana filtrada, que es la que usa BKM.
    `k_abs_max=None` ajusta todo el rango.
    """
    k = np.asarray(k, dtype=float).ravel()
    w = np.asarray(w, dtype=float).ravel()
    theta_por_fila = np.asarray(theta_por_fila, dtype=float).ravel()
    theta_fijo = np.asarray(theta_fijo, dtype=float).ravel()
    if slice_index is None:
        slice_index = np.zeros(len(k))
    slice_index = np.asarray(slice_index).ravel()
    if weights is None:
        weights = np.ones(len(k))
    weights = np.asarray(weights, dtype=float).ravel()
    if not (len(k) == len(w) == len(theta_por_fila) == len(slice_index) == len(weights)):
        raise ValueError("k, w, theta_por_fila, slice_index y weights deben medir lo mismo")
    if len(k) == 0 or len(theta_fijo) == 0:
        raise ValueError("SSVI sin observaciones")

    order = np.lexsort((k, slice_index.astype(float)))
    k = np.ascontiguousarray(k[order])
    w = np.ascontiguousarray(w[order])
    theta_por_fila = np.ascontiguousarray(theta_por_fila[order])
    weights = np.ascontiguousarray(weights[order])
    if k_abs_max is not None:
        dentro = np.abs(k) <= float(k_abs_max) + 1e-12
        k = k[dentro]
        w = w[dentro]
        theta_por_fila = theta_por_fila[dentro]
        weights = weights[dentro]
    if len(k) == 0:
        return _ssvi_vacio(0, np.nan, np.nan)
    k_min = float(np.min(k))
    k_max = float(np.max(k))
    if len(k) < 4:
        return _ssvi_vacio(len(k), k_min, k_max)

    pesos = np.where(np.isfinite(weights) & (weights > 0), weights, 0.0)
    if float(pesos.sum()) <= 0:
        pesos = np.ones(len(k))
    suma_pesos = float(pesos.sum())

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
        error = float(np.sum(pesos * (modelo - w) ** 2))
        phi = eta * np.power(theta_fijo, -gamma)
        gj = theta_fijo * phi * (1.0 + abs(rho))
        return error + float(np.sum(np.maximum(0.0, gj - 4.0) ** 2)) * 1e3

    opt = minimize(objetivo, u0, method="L-BFGS-B", bounds=bounds,
                   options={"maxiter": int(maxiter), "ftol": float(gtol), "gtol": float(gtol)})
    rho = float(math.tanh(opt.x[0]))
    eta = float(math.exp(opt.x[1]))
    gamma = float(_sigmoid(opt.x[2]) * 0.9 + 0.05)
    modelo = ssvi_total_variance(k, theta_por_fila, rho, eta, gamma)
    rmse = float(np.sqrt(np.sum(pesos * (modelo - w) ** 2) / suma_pesos))
    escala = float(np.sum(pesos * np.abs(w)) / suma_pesos)
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
        "k_min": k_min, "k_max": k_max,
    }


def ssvi_weights(k, total_var, open_interest=None):
    """Peso de cada strike: vega relativa de Black-Scholes por sqrt(OI).

    La vega relativa es phi(d1). Un strike con OI conocido y positivo se
    multiplica por sqrt(OI); OI ausente no se tira, entra con liquidez 1.
    """
    k = np.asarray(k, dtype=float).ravel()
    total = np.maximum(np.asarray(total_var, dtype=float).ravel(), 1e-12)
    d1 = -k / np.sqrt(total) + 0.5 * np.sqrt(total)
    vega = np.maximum(np.exp(-0.5 * d1 ** 2), 1e-6)
    if open_interest is None:
        return vega
    oi = np.asarray(open_interest, dtype=float).ravel()
    if len(oi) != len(vega):
        raise ValueError("open_interest debe medir lo mismo que k")
    liq = np.ones(len(vega))
    conocido = np.isfinite(oi) & (oi > 0)
    liq[conocido] = np.sqrt(oi[conocido])
    return vega * liq


def ssvi_row_mask(precio=None, open_interest=None, n=None):
    """True en las filas que entran al ajuste.

    Se tira un precio no positivo cuando el quote existe. OI conocido y <= 0
    tambien se tira; OI ausente se conserva.
    """
    if n is None:
        if precio is not None:
            n = len(np.asarray(precio).ravel())
        elif open_interest is not None:
            n = len(np.asarray(open_interest).ravel())
        else:
            raise ValueError("ssvi_row_mask necesita precio, open_interest o n")
    mask = np.ones(int(n), dtype=bool)
    if precio is not None:
        px = np.asarray(precio, dtype=float).ravel()
        if len(px) != len(mask):
            raise ValueError("precio debe medir n")
        mask &= ~(np.isfinite(px) & (px <= 0))
    if open_interest is not None:
        oi = np.asarray(open_interest, dtype=float).ravel()
        if len(oi) != len(mask):
            raise ValueError("open_interest debe medir n")
        mask &= ~(np.isfinite(oi) & (oi <= 0))
    return mask


def ssvi_surface_decision(ajuste, sigma_atm_annual):
    """La vol ATM de theta se conserva aunque la sonrisa se rechace.

    `fuente` es ssvi (alas usables), atm (theta sin alas) o historica.
    """
    atm = float(sigma_atm_annual) if sigma_atm_annual is not None else np.nan
    atm_ok = bool(np.isfinite(atm) and atm > 0)
    aceptado = bool(ajuste is not None and ajuste.get("aceptado"))
    if aceptado and atm_ok:
        return {"usar_alas": True, "sigma_atm_annual": atm, "fuente": "ssvi"}
    if atm_ok:
        return {"usar_alas": False, "sigma_atm_annual": atm, "fuente": "atm"}
    return {"usar_alas": False, "sigma_atm_annual": np.nan, "fuente": "historica"}


def apply_vol_q_to_p(var_p, mfiv, is_implied, bounds=(0.70, 1.00)):
    """Aplica el ratio sigma_P/sigma_Q solo donde la vol es implicita.

    Una vol historica no trae prima de varianza: recortarla con el ratio de
    Mincer-Zarnowitz la baja dos veces. Esos nombres se quedan con `mfiv`
    (la varianza al horizonte ya colocada ahi). El conteo de cotas solo
    incluye nombres implicitos.
    """
    var_p = np.asarray(var_p, dtype=float).copy()
    mfiv = np.asarray(mfiv, dtype=float)
    implied = np.asarray(is_implied, dtype=bool)
    if not (var_p.shape == mfiv.shape == implied.shape):
        raise ValueError("var_p, mfiv e is_implied deben medir lo mismo")
    lo, hi = float(bounds[0]), float(bounds[1])
    ratio = np.sqrt(np.maximum(var_p, 1e-12) / np.maximum(mfiv, 1e-12))
    fuera = implied & np.isfinite(ratio) & ((ratio < lo) | (ratio > hi))
    ratio = np.clip(ratio, lo, hi)
    ajustada = ratio ** 2 * mfiv
    out = np.where(implied, ajustada, mfiv)
    historica_inutil = (~implied) & ~(np.isfinite(mfiv) & (mfiv > 0))
    out = np.where(historica_inutil, var_p, out)
    return out, int(np.sum(fuera))


def clip_negligible_weights(w, tol=1e-6):
    """Pone en cero el residuo numerico de SLSQP/quadprog y renormaliza."""
    w = np.clip(np.asarray(w, dtype=float).copy(), 0.0, None)
    w[w <= float(tol)] = 0.0
    total = float(w.sum())
    if total <= 0:
        return w
    return w / total


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
