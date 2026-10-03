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
#   4. La sonrisa SSVI se calibra en una ventana de vencimientos (no en todos
#      los LEAPs) y la perdida se normaliza por vencimiento, para que un plazo
#      largo no domine el residuo en varianza total.
# ==============================================================================

import math

import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator
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
    "ssvi_degeneracy",
    "ssvi_surface_decision",
    "seleccionar_vencimientos",
    "ssvi_monotone_mask",
    "forward_por_paridad",
    "calibrar_superficie_ssvi",
    "momentos_fallback",
    "elegir_spot_momentos",
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


def _grupos_vencimiento(slice_index):
    """Indices de cada vencimiento, en el orden en que aparecen tras el sort."""
    grupos = []
    for sl in np.unique(slice_index):
        grupos.append(np.flatnonzero(slice_index == sl))
    return grupos


def _thetas_gatheral(slice_index, theta_por_fila, theta_fijo):
    """Theta ATM de cada vencimiento presente, para la cota de Gatheral-Jacquier."""
    thetas = []
    for sl in np.unique(slice_index):
        sl_f = float(sl)
        sl_i = int(sl_f) if math.isfinite(sl_f) and sl_f.is_integer() else None
        if sl_i is not None and 0 <= sl_i < len(theta_fijo):
            thetas.append(float(theta_fijo[sl_i]))
        else:
            thetas.append(float(np.median(theta_por_fila[slice_index == sl])))
    return np.maximum(np.asarray(thetas, dtype=float), 1e-12)


def fit_ssvi(k, w, theta_por_fila, theta_fijo, slice_index=None,
             gtol=1e-5, maxiter=2000, rmse_rel_max=0.20,
             weights=None, k_abs_max=0.5, normalizar_vencimiento=True):
    """Calibra (rho, eta, gamma) y acepta el ajuste por residuo, no por opt.success.

    L-BFGS-B con tolerancia laxa: BFGS a gtol=1e-10 marcaba 'precision loss' en
    casi toda la cadena y el script igual usaba el resultado. Aqui el ajuste
    entra solo si el RMSE relativo es <= rmse_rel_max y no hay arbitraje de
    calendario (GJ <= 4).

    Las filas se ordenan por (vencimiento, k) antes de sumar el error, para que
    el mismo insumo de siempre el mismo parametro aunque la cadena llegue
    desordenada.

    `k_abs_max` deja fuera las alas profundas (un put de $5 con k ~ -5). El
    peso de cada strike sigue siendo vega * sqrt(OI). Con
    `normalizar_vencimiento` (el default) cada plazo pesa igual y el residuo
    se mide en unidades de theta, la varianza ATM de ese vencimiento: un LEAP,
    con w = sigma^2 T grande, deja de aportar casi toda la perdida.
    `rmse_rel` es entonces el promedio entre vencimientos de RMSE(w) / theta.
    Sin normalizar, rmse_rel vuelve a ser el RMSE global partido por la media
    ponderada de |w| (un plazo largo domina numerador y denominador).

    `n_strikes`, `k_min` y `k_max` son los de la ventana filtrada, que es la
    que usa BKM. `k_abs_max=None` ajusta todo el rango.
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
    slice_index = np.ascontiguousarray(slice_index[order])
    if k_abs_max is not None:
        dentro = np.abs(k) <= float(k_abs_max) + 1e-12
        k = k[dentro]
        w = w[dentro]
        theta_por_fila = theta_por_fila[dentro]
        weights = weights[dentro]
        slice_index = slice_index[dentro]
    if len(k) == 0:
        return _ssvi_vacio(0, np.nan, np.nan)
    k_min = float(np.min(k))
    k_max = float(np.max(k))
    if len(k) < 4:
        return _ssvi_vacio(len(k), k_min, k_max)

    pesos = np.where(np.isfinite(weights) & (weights > 0), weights, 0.0)
    grupos = _grupos_vencimiento(slice_index)
    for g in grupos:
        if float(pesos[g].sum()) <= 0:
            pesos[g] = 1.0
    if float(pesos.sum()) <= 0:
        pesos = np.ones(len(k))
    suma_pesos = float(pesos.sum())
    theta_gj = _thetas_gatheral(slice_index, theta_por_fila, theta_fijo)

    def _sigmoid(x):
        return 1.0 / (1.0 + math.exp(-float(x)))

    def _params(u):
        rho = math.tanh(float(u[0]))
        eta = math.exp(float(u[1]))
        gamma = _sigmoid(u[2]) * 0.9 + 0.05
        return rho, eta, gamma

    def _penalty(rho, eta, gamma):
        phi = eta * np.power(theta_gj, -gamma)
        gj = theta_gj * phi * (1.0 + abs(rho))
        return float(np.sum(np.maximum(0.0, gj - 4.0) ** 2)) * 1e3, gj

    def _relativos(modelo):
        """RMSE/theta de cada vencimiento. El peso vega/OI se respeta adentro."""
        rels = []
        rmses = []
        for g in grupos:
            th = max(float(np.median(theta_por_fila[g])), 1e-12)
            sw = float(pesos[g].sum())
            rmse_g = math.sqrt(float(np.sum(pesos[g] * (modelo[g] - w[g]) ** 2)) / sw)
            rmses.append(rmse_g)
            rels.append(rmse_g / th)
        return rels, rmses

    p0 = (0.3 - 0.05) / 0.9
    u0 = np.array([0.0, 0.0, math.log(p0 / (1.0 - p0))])
    bounds = [(-3.8, 3.8), (-10.0, 8.0), (-12.0, 12.0)]

    def objetivo(u):
        rho, eta, gamma = _params(u)
        modelo = ssvi_total_variance(k, theta_por_fila, rho, eta, gamma)
        if normalizar_vencimiento:
            rels, _ = _relativos(modelo)
            error = float(np.mean(np.square(rels)))
        else:
            error = float(np.sum(pesos * (modelo - w) ** 2))
        pena, _ = _penalty(rho, eta, gamma)
        return error + pena

    opt = minimize(objetivo, u0, method="L-BFGS-B", bounds=bounds,
                   options={"maxiter": int(maxiter), "ftol": float(gtol), "gtol": float(gtol)})
    rho, eta, gamma = _params(opt.x)
    modelo = ssvi_total_variance(k, theta_por_fila, rho, eta, gamma)
    rels, rmses = _relativos(modelo)
    if normalizar_vencimiento:
        rel = float(np.mean(rels))
        rmse = float(np.mean(rmses))
    else:
        rmse = float(np.sqrt(np.sum(pesos * (modelo - w) ** 2) / suma_pesos))
        escala = float(np.sum(pesos * np.abs(w)) / suma_pesos)
        rel = rmse / escala if escala > 0 else float("inf")
    _, gj = _penalty(rho, eta, gamma)
    gj_max = float(np.max(gj))
    aceptado = bool(np.isfinite(rel) and rel <= float(rmse_rel_max) and gj_max <= 4.0 + 1e-6)
    return {
        "rho": rho, "eta": eta, "gamma": gamma,
        "rmse": rmse, "rmse_rel": rel, "gj_max": gj_max,
        "aceptado": aceptado, "success": bool(opt.success),
        "metodo": "ssvi_conjunto" if aceptado else "ssvi_rechazado",
        "n_strikes": int(len(k)),
        "k_min": k_min, "k_max": k_max,
        "n_vencimientos": int(len(grupos)),
        "rmse_rel_por_vencimiento": [float(x) for x in rels],
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


def ssvi_row_mask(precio=None, open_interest=None, n=None,
                  precio_min=0.10, oi_min=10.0):
    """True en las filas que entran al ajuste.

    Se tira un precio no positivo, y tambien el que queda bajo `precio_min`
    (opciones de unos centavos con IV disparada). OI conocido por debajo de
    `oi_min` se tira; OI ausente se conserva. `precio_min` <= 0 desactiva el
    piso en dolares y solo descarta precios no positivos.
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
        fuera = np.isfinite(px) & (px <= 0)
        if precio_min is not None and float(precio_min) > 0:
            fuera |= np.isfinite(px) & (px < float(precio_min))
        mask &= ~fuera
    if open_interest is not None:
        oi = np.asarray(open_interest, dtype=float).ravel()
        if len(oi) != len(mask):
            raise ValueError("open_interest debe medir n")
        fuera_oi = np.isfinite(oi) & (oi <= 0)
        if oi_min is not None and float(oi_min) > 0:
            fuera_oi |= np.isfinite(oi) & (oi < float(oi_min))
        mask &= ~fuera_oi
    return mask


def ssvi_monotone_mask(strike, precio, tipo, open_interest=None):
    """True donde el precio no rompe la monotonia por strike.

    Calls: el precio no crece con el strike. Puts: no decrece. En el par que
    viola se tira el de menor OI; a igualdad de OI, el de strike mas alto. Se
    repite hasta que el lado queda monotono. Un precio ausente no se compara
    y se conserva. Un tipo distinto de call/put tambien se conserva.
    """
    strike = np.asarray(strike, dtype=float).ravel()
    precio = np.asarray(precio, dtype=float).ravel()
    tipo = np.asarray(tipo, dtype=object).ravel()
    n = len(strike)
    if not (len(precio) == n and len(tipo) == n):
        raise ValueError("strike, precio y tipo deben medir lo mismo")
    if open_interest is None:
        oi = np.full(n, np.nan)
    else:
        oi = np.asarray(open_interest, dtype=float).ravel()
        if len(oi) != n:
            raise ValueError("open_interest debe medir lo mismo que strike")
    tipo_l = np.array([str(t).lower() if t is not None else "" for t in tipo])
    keep = np.ones(n, dtype=bool)
    for lado, creciente in (("call", False), ("put", True)):
        idx = [int(i) for i in np.flatnonzero(tipo_l == lado)]
        vivos = set(idx)
        while True:
            ordenados = sorted(vivos, key=lambda i: (strike[i], i))
            con_precio = [i for i in ordenados if np.isfinite(precio[i])]
            violacion = None
            for a, b in zip(con_precio, con_precio[1:]):
                if creciente:
                    malo = precio[b] < precio[a] - 1e-8
                else:
                    malo = precio[b] > precio[a] + 1e-8
                if malo:
                    violacion = (a, b)
                    break
            if violacion is None:
                break
            a, b = violacion
            liq_a = float(oi[a]) if np.isfinite(oi[a]) else 0.0
            liq_b = float(oi[b]) if np.isfinite(oi[b]) else 0.0
            vivos.remove(b if liq_b <= liq_a else a)
        for i in idx:
            if i not in vivos:
                keep[i] = False
    return keep


def ssvi_degeneracy(ajuste, rho_abs_max=0.95, k_side_min=0.10, min_per_side=2,
                    n_put=None, n_call=None):
    """True si la sonrisa no debe alimentar las alas de BKM.

    `|rho|` cerca de 1 es el borde de tanh (el optimizador se clava en la
    cota). Una sola ala, o menos de `min_per_side` strikes de ese lado,
    tampoco identifica rho. `ok` es False y `motivos` dice por que.
    """
    motivos = []
    ajuste = ajuste or {}
    rho = ajuste.get("rho", np.nan)
    if rho is not None and np.isfinite(rho) and abs(float(rho)) >= float(rho_abs_max):
        motivos.append("rho_en_cota")
    k_min = ajuste.get("k_min", np.nan)
    k_max = ajuste.get("k_max", np.nan)
    if k_min is not None and np.isfinite(k_min) and float(k_min) > -float(k_side_min):
        motivos.append("sin_ala_put")
    if k_max is not None and np.isfinite(k_max) and float(k_max) < float(k_side_min):
        motivos.append("sin_ala_call")
    if n_put is not None and int(n_put) < int(min_per_side):
        motivos.append("pocos_puts")
    if n_call is not None and int(n_call) < int(min_per_side):
        motivos.append("pocas_calls")
    return {"ok": len(motivos) == 0, "motivos": motivos}


def ssvi_surface_decision(ajuste, sigma_atm_annual, n_put=None, n_call=None,
                          rho_abs_max=0.95, k_side_min=0.10, min_per_side=2):
    """La vol ATM de theta se conserva aunque la sonrisa se rechace.

    `fuente` es ssvi (alas usables), atm (theta sin alas) o historica.
    Una sonrisa aceptada por RMSE pero degenerada (rho en la cota o una
    sola ala) cae a atm: la vol se queda y BKM no integra esas alas.
    """
    atm = float(sigma_atm_annual) if sigma_atm_annual is not None else np.nan
    atm_ok = bool(np.isfinite(atm) and atm > 0)
    aceptado = bool(ajuste is not None and ajuste.get("aceptado"))
    degen = ssvi_degeneracy(
        ajuste, rho_abs_max=rho_abs_max, k_side_min=k_side_min,
        min_per_side=min_per_side, n_put=n_put, n_call=n_call)
    if aceptado and atm_ok and degen["ok"]:
        return {"usar_alas": True, "sigma_atm_annual": atm, "fuente": "ssvi",
                "motivos": []}
    if atm_ok:
        return {"usar_alas": False, "sigma_atm_annual": atm, "fuente": "atm",
                "motivos": degen["motivos"]}
    return {"usar_alas": False, "sigma_atm_annual": np.nan, "fuente": "historica",
            "motivos": degen["motivos"]}


def seleccionar_vencimientos(dias, max_dias, min_keep=3):
    """Mascara de vencimientos a calibrar.

    Se queda con los de DTE <= `max_dias`. Si son menos de `min_keep`, se
    agregan los mas cortos por encima del tope hasta completar el minimo (o
    hasta agotar la cadena). `max_dias` None no recorta. Los DTE no finitos
    quedan fuera.
    """
    dias = np.asarray(dias, dtype=float).ravel()
    finito = np.isfinite(dias)
    if max_dias is None or not np.isfinite(max_dias):
        return finito.copy()
    max_dias = float(max_dias)
    min_keep = max(int(min_keep), 0)
    dentro = finito & (dias <= max_dias + 1e-9)
    if int(dentro.sum()) >= min_keep or int(dentro.sum()) == int(finito.sum()):
        return dentro
    orden = np.argsort(np.where(finito, dias, np.inf), kind="mergesort")
    faltan = min_keep - int(dentro.sum())
    out = dentro.copy()
    for i in orden:
        if not finito[i] or out[i]:
            continue
        out[i] = True
        faltan -= 1
        if faltan <= 0:
            break
    return out


def forward_por_paridad(df_exp):
    """Forward por regresion call - put sobre el strike. NaN si no identifica."""
    anchos = df_exp[["strike", "tipo", "precio"]].pivot_table(
        index="strike", columns="tipo", values="precio", aggfunc="mean"
    ).reset_index()
    if not {"call", "put"}.issubset(anchos.columns):
        return np.nan
    anchos = anchos.dropna(subset=["call", "put"])
    if len(anchos) < 4:
        return np.nan
    y = (anchos["call"] - anchos["put"]).to_numpy(dtype=float)
    x = anchos["strike"].to_numpy(dtype=float)
    try:
        b1, b0 = np.polyfit(x, y, 1)
    except Exception:
        return np.nan
    if b1 >= 0:
        return np.nan
    f_est = -b0 / b1
    if not np.isfinite(f_est) or f_est <= 0:
        return np.nan
    return float(f_est)


def _fecha_naive(hoy):
    hoy = pd.Timestamp(hoy)
    if hoy.tzinfo is not None:
        hoy = hoy.tz_localize(None)
    return hoy.normalize()


def calibrar_superficie_ssvi(df, tau_obj, hoy, min_strikes=5, min_dias=5,
                             max_dias=243, min_vencimientos=3, k_abs_max=0.5,
                             precio_min=0.10, oi_min=10.0, rho_abs_max=0.95,
                             k_side_min=0.10, min_per_side=2, rmse_rel_max=0.20,
                             normalizar_vencimiento=True):
    """Ajusta una SSVI conjunta a una cadena ya parseada.

    `df` lleva strike, expiracion, tipo, iv y, si existen, precio, oi y spot.
    Recorta vencimientos a [min_dias, max_dias], tira precios chicos, OI
    conocido bajo el piso y violaciones de monotonia, y normaliza la perdida
    por vencimiento. Devuelve el mismo dict que usa Black-Litterman. Lanza
    ValueError si no queda volatilidad ATM.
    """
    df = pd.DataFrame(df).copy()
    for col in ("precio", "oi", "spot", "iv"):
        if col not in df.columns:
            df[col] = np.nan
    iv = df["iv"].to_numpy(dtype=float)
    df = df[np.isfinite(iv) & (iv > 0)].copy()
    if len(df) == 0:
        raise ValueError("Sin IVs validas")

    hoy = _fecha_naive(hoy)
    df["expiracion"] = pd.to_datetime(df["expiracion"])
    if getattr(df["expiracion"].dt, "tz", None) is not None:
        df["expiracion"] = df["expiracion"].dt.tz_convert(None)
    df["dias"] = (df["expiracion"] - hoy).dt.days
    df = df[df["dias"] >= int(min_dias)].copy()
    if len(df) == 0:
        raise ValueError("Sin vencimientos dentro del minimo de dias")

    vencimientos = sorted(df["expiracion"].unique())
    dias_venc = np.array([(pd.Timestamp(v) - hoy).days for v in vencimientos], dtype=float)
    mask_v = seleccionar_vencimientos(dias_venc, max_dias, min_vencimientos)
    n_cadena = int(len(vencimientos))
    venc_sel = [v for v, ok in zip(vencimientos, mask_v) if ok]
    df = df[df["expiracion"].isin(venc_sel)].copy()

    spots = df["spot"].to_numpy(dtype=float)
    spots = spots[np.isfinite(spots) & (spots > 0)]
    spot_cadena = float(np.median(spots)) if len(spots) else np.nan

    n_drop_precio = 0
    n_drop_oi = 0
    n_drop_monotonia = 0
    puntos = []
    theta_guess = []
    t_years = []
    dias_usados = []

    for venc in venc_sel:
        df_exp = df[df["expiracion"] == venc].copy()
        T_anios = (pd.Timestamp(venc) - hoy).days / 365.0
        if T_anios <= 0:
            continue

        px = df_exp["precio"].to_numpy(dtype=float)
        oi = df_exp["oi"].to_numpy(dtype=float)
        drop_px = np.isfinite(px) & (px <= 0)
        if precio_min is not None and float(precio_min) > 0:
            drop_px = drop_px | (np.isfinite(px) & (px < float(precio_min)))
        drop_oi = np.isfinite(oi) & (oi <= 0)
        if oi_min is not None and float(oi_min) > 0:
            drop_oi = drop_oi | (np.isfinite(oi) & (oi < float(oi_min)))
        n_drop_precio += int(np.sum(drop_px))
        n_drop_oi += int(np.sum(~drop_px & drop_oi))
        mask = ssvi_row_mask(px, oi, precio_min=precio_min, oi_min=oi_min)
        df_exp = df_exp.loc[mask].copy()
        if len(df_exp) == 0:
            continue
        mask_mono = ssvi_monotone_mask(
            df_exp["strike"].to_numpy(), df_exp["precio"].to_numpy(),
            df_exp["tipo"].to_numpy(), df_exp["oi"].to_numpy())
        n_drop_monotonia += int((~mask_mono).sum())
        df_exp = df_exp.loc[mask_mono].copy()
        if len(df_exp) == 0:
            continue

        f_est = forward_por_paridad(df_exp)
        if not np.isfinite(f_est):
            continue

        df_exp = df_exp.copy()
        df_exp["k"] = np.log(df_exp["strike"].to_numpy(dtype=float) / f_est)
        otm_put = df_exp[(df_exp["tipo"] == "put") & (df_exp["k"] < 0)]
        otm_call = df_exp[(df_exp["tipo"] == "call") & (df_exp["k"] >= 0)]
        otm = pd.concat([otm_put, otm_call]).drop_duplicates(subset="strike")
        ventana = otm[otm["k"].abs() <= float(k_abs_max)].copy()
        if len(ventana) < int(min_strikes):
            continue

        ventana["w"] = ventana["iv"].to_numpy(dtype=float) ** 2 * T_anios
        ventana = ventana.sort_values("k")
        pesos = ssvi_weights(
            ventana["k"].to_numpy(), ventana["w"].to_numpy(), ventana["oi"].to_numpy())

        ancho = otm[otm["k"].abs() <= 1.0]
        if (ancho["k"] < 0).any() and (ancho["k"] >= 0).any():
            base = ancho.sort_values("k")
        else:
            base = otm.sort_values("k")
        base_w = base["iv"].to_numpy(dtype=float) ** 2 * T_anios
        try:
            theta0 = float(np.interp(0.0, base["k"].to_numpy(dtype=float), base_w))
        except Exception:
            theta0 = np.nan
        if not np.isfinite(theta0) or theta0 <= 0:
            continue

        idx = len(puntos)
        puntos.append(pd.DataFrame({
            "k": ventana["k"].to_numpy(), "w": ventana["w"].to_numpy(),
            "slice": idx, "peso": pesos,
        }))
        theta_guess.append(theta0)
        t_years.append(T_anios)
        dias_usados.append(int((pd.Timestamp(venc) - hoy).days))

    if len(puntos) < 2:
        raise ValueError("Menos de 2 vencimientos utilizables")

    tope = float(max_dias) if max_dias is not None and np.isfinite(max_dias) else np.inf
    extendio = bool(any(d > tope + 1e-9 for d in dias_usados))

    datos = pd.concat(puntos, ignore_index=True)
    m = len(theta_guess)
    theta_fijo = np.asarray(theta_guess, dtype=float)
    t_years = np.asarray(t_years, dtype=float)

    order = np.argsort(t_years)
    t_sorted = t_years[order]
    theta_sorted = theta_fijo[order]
    theta_interp = PchipInterpolator(t_sorted, theta_sorted, extrapolate=False)
    tau_obj = float(tau_obj)
    if tau_obj < t_years.min():
        i_min = int(np.argmin(t_years))
        theta_tau = theta_fijo[i_min] * (tau_obj / t_years[i_min])
    elif tau_obj > t_years.max():
        i_max = int(np.argmax(t_years))
        theta_tau = theta_fijo[i_max] * (tau_obj / t_years[i_max])
    else:
        theta_tau = float(theta_interp(tau_obj))

    theta_por_fila = theta_fijo[datos["slice"].to_numpy()]
    ajuste = fit_ssvi(
        datos["k"].to_numpy(), datos["w"].to_numpy(), theta_por_fila, theta_fijo,
        slice_index=datos["slice"].to_numpy(), weights=datos["peso"].to_numpy(),
        k_abs_max=k_abs_max, rmse_rel_max=rmse_rel_max,
        normalizar_vencimiento=normalizar_vencimiento)
    sigma_atm_annual = math.sqrt(theta_tau / tau_obj) if theta_tau > 0 else np.nan
    n_put = int(np.sum(datos["k"].to_numpy(dtype=float) < 0))
    n_call = int(np.sum(datos["k"].to_numpy(dtype=float) >= 0))
    decision = ssvi_surface_decision(
        ajuste, sigma_atm_annual, n_put=n_put, n_call=n_call,
        rho_abs_max=rho_abs_max, k_side_min=k_side_min, min_per_side=min_per_side)
    if decision["fuente"] == "historica":
        raise ValueError(
            f"SSVI sin vol ATM (rmse_rel={ajuste['rmse_rel']:.3f}, "
            f"GJ_max={ajuste['gj_max']:.3f})"
        )

    motivos = list(decision.get("motivos") or [])
    if not ajuste["aceptado"]:
        motivos = [f"rmse_rel={ajuste['rmse_rel']:.3f}>{float(rmse_rel_max):.2f}"] + motivos
    if decision["usar_alas"]:
        motivo_fallback = ""
    else:
        motivo_fallback = ", ".join(motivos) or "sonrisa rechazada"

    return dict(
        sigma_atm_annual=decision["sigma_atm_annual"], theta_j=theta_fijo,
        t_years=t_years, rho=ajuste["rho"], eta=ajuste["eta"], gamma=ajuste["gamma"],
        n_vencimientos=m, metodo=ajuste["metodo"], gj_max=ajuste["gj_max"],
        rmse_rel=ajuste["rmse_rel"], usar_alas=decision["usar_alas"],
        fuente=decision["fuente"], motivos=motivos, aceptado=bool(ajuste["aceptado"]),
        n_put=n_put, n_call=n_call, n_strikes=ajuste["n_strikes"],
        k_min=ajuste["k_min"], k_max=ajuste["k_max"],
        n_vencimientos_cadena=n_cadena, dias_min=int(min(dias_usados)),
        dias_max=int(max(dias_usados)), max_dias=max_dias, min_dias=int(min_dias),
        extendio_tope=bool(extendio), spot_cadena=spot_cadena,
        n_drop_precio=int(n_drop_precio), n_drop_oi=int(n_drop_oi),
        n_drop_monotonia=int(n_drop_monotonia),
        n_drop_higiene=int(n_drop_precio + n_drop_oi + n_drop_monotonia),
        motivo_fallback=motivo_fallback,
    )


_FALLBACK_MODOS = ("historico", "neutro", "sector")


def momentos_fallback(modo, skew_hist, kurt_hist, skew_sector=None, kurt_sector=None,
                      kurt_max=np.inf):
    """Skew y curtosis cuando la sonrisa no entra a BKM.

    historico  momentos fisicos del ticker al horizonte.
    neutro     MFIS=0, MFIK=3 (el placeholder anterior).
    sector     sonrisa del ETF sectorial si el par es admisible; si no, historico.
    Si el historico tampoco es un par admisible, se vuelve al neutro.
    """
    modo_l = str(modo).lower().strip()
    if modo_l not in _FALLBACK_MODOS:
        raise ValueError("modo debe ser 'historico', 'neutro' o 'sector'")

    def _par(skew, kurt):
        if skew is None or kurt is None:
            return None
        try:
            s, k = float(skew), float(kurt)
        except (TypeError, ValueError):
            return None
        if not rk.higher_moments_admissible(s, k, kurt_max=kurt_max):
            return None
        return s, k

    if modo_l == "neutro":
        return {"mfis": 0.0, "mfik": 3.0, "fuente": "neutro"}
    if modo_l == "sector":
        par = _par(skew_sector, kurt_sector)
        if par is not None:
            return {"mfis": par[0], "mfik": par[1], "fuente": "sector"}
    par = _par(skew_hist, kurt_hist)
    if par is not None:
        return {"mfis": par[0], "mfik": par[1], "fuente": "historico"}
    return {"mfis": 0.0, "mfik": 3.0, "fuente": "neutro"}


def elegir_spot_momentos(ultimo_cierre, fecha_cierre, fecha_cadena, spot_cadena=None):
    """Spot del paso de momentos de opciones.

    Si el ultimo cierre cae en la fecha de la cadena, ese cierre. Si la barra
    de ese dia no esta y la cadena trae spot, el de la cadena (es el que vio
    el snapshot). Si tampoco, el ultimo cierre y se avisa con la fuente.
    """
    def _fecha(x):
        if x is None:
            return None
        try:
            if isinstance(x, float) and not np.isfinite(x):
                return None
            ts = pd.Timestamp(x)
        except (TypeError, ValueError):
            return None
        if ts is pd.NaT or pd.isna(ts):
            return None
        if ts.tzinfo is not None:
            ts = ts.tz_localize(None)
        return ts.date()

    fc = _fecha(fecha_cierre)
    fq = _fecha(fecha_cadena)
    try:
        cierre = float(ultimo_cierre) if ultimo_cierre is not None else np.nan
    except (TypeError, ValueError):
        cierre = np.nan
    try:
        cadena = float(spot_cadena) if spot_cadena is not None else np.nan
    except (TypeError, ValueError):
        cadena = np.nan
    cierre_ok = bool(np.isfinite(cierre) and cierre > 0)
    cadena_ok = bool(np.isfinite(cadena) and cadena > 0)
    mismo_dia = fc is not None and fq is not None and fc == fq
    if cierre_ok and mismo_dia:
        fuente, spot = "cierre", cierre
    elif cadena_ok and not mismo_dia:
        fuente, spot = "cadena", cadena
    elif cierre_ok:
        fuente, spot = "cierre_previo", cierre
    else:
        fuente, spot = "sin_spot", np.nan
    return {
        "spot": float(spot) if np.isfinite(spot) else np.nan,
        "fuente": fuente,
        "cierre": float(cierre) if cierre_ok else np.nan,
        "fecha_cierre": fc,
        "spot_cadena": float(cadena) if cadena_ok else np.nan,
    }


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
    """Strikes de la integral BKM: +/- n_std * sigma * sqrt(T).

    El ajuste SSVI vive en |k|<=0.5. La integral no usa esa ventana: las alas
    del modelo, ya chequeadas por arbitraje de calendario (GJ), cubren
    +/- n_std al plazo del horizonte. Pasar k_min/k_max recorta a esos
    strikes; Black-Litterman no los pasa, porque recortar al ajuste deja
    MFIK por debajo de 3.
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
