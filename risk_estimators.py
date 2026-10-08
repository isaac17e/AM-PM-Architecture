# ==============================================================================
# RISK_ESTIMATORS - Estimadores de riesgo compartidos por los optimizadores
# ==============================================================================
# Modulo comun a minimum_variance.py, quadratic_utility.py, black_litterman.py
# y sus versiones estacionales. Centraliza:
#
#   1. Covarianza historica EWMA + shrinkage Ledoit-Wolf (objetivo de
#      correlacion constante). Reemplaza a la covarianza muestral con pesos
#      iguales, que es el estimador mas ruidoso del pipeline.
#   2. Correccion Q -> P de la volatilidad implicita (prima de riesgo de
#      varianza) y de la correlacion implicita (prima de riesgo de correlacion).
#   3. Panel de escenarios y momentos de portafolio en O(J*n), para calcular
#      asimetria y curtosis del portafolio SIN promediar los momentos
#      marginales (que ignora la diversificacion).
#   4. Admisibilidad de momentos (K >= 1 + S^2) y Cornish-Fisher con
#      momentos reales (Maillard, 2012): monotono en S y K por construccion.
#   5. Retorno esperado via SVIX (Martin-Wagner) - EXPERIMENTAL, ver aviso.
#   6. Escalado temporal unico (anualizar, llevar al horizonte, escalado iid
#      de asimetria y curtosis) con el DTE real de la cadena de opciones.
#   0. Compatibilidad numerica (trapezoid para numpy < 2.0).
#
# Todo es forma cerrada salvo la inversion momentos -> parametros de
# Cornish-Fisher, un ajuste 2x2 con scipy.optimize.least_squares.
# ==============================================================================

import logging

import numpy as np
import pandas as pd
from scipy.stats import norm

# Los optimizadores silencian `warnings` (filterwarnings("ignore")); los avisos
# del estimador van por logging para que sigan llegando a la consola.
logger = logging.getLogger(__name__)

__all__ = [
    "trapezoid",
    "ewma_weights",
    "effective_sample_size",
    "ewma_cov",
    "average_correlation",
    "ledoit_wolf_constant_correlation",
    "cov_ewma_shrunk",
    "texto_delta_shrinkage",
    "LW_DELTA_MAX",
    "scale_cov",
    "nearest_psd",
    "q_to_p_vol",
    "q_to_p_correlation",
    "standardized_panel",
    "rescale_panel",
    "portfolio_moments",
    "portfolio_moment_gradients",
    "higher_moments_admissible",
    "cornish_fisher_z",
    "cornish_fisher_domain",
    "cornish_fisher_moments",
    "cornish_fisher_params",
    "cornish_fisher_tail",
    "cornish_fisher_es_gradient",
    "var_cvar_cornish_fisher",
    "martin_wagner_excess_return",
    "DAYS_PER_YEAR",
    "TRADING_DAYS_PER_YEAR",
    "WEEKS_PER_YEAR",
    "MONTHS_PER_YEAR",
    "to_years",
    "scale_moments",
    "scale_bkm_moments",
    "mfik_cap",
    "mfik_cap_tenor",
    "annualize",
    "implied_variance_to_horizon",
    "max_drawdown",
    "portfolio_log_returns",
]


# ==============================================================================
# 0. COMPATIBILIDAD NUMERICA
# ==============================================================================
# numpy 2.0 renombro np.trapz a np.trapezoid (y numpy 2.x emite aviso de
# obsolescencia por np.trapz). Los optimizadores integran BKM con esta
# funcion; ninguno llama np.trapezoid directo, asi que numpy 1.24+ basta.
# ==============================================================================

trapezoid = np.trapezoid if hasattr(np, "trapezoid") else np.trapz  # noqa: NPY201


# ==============================================================================
# 1. COVARIANZA HISTORICA: EWMA + SHRINKAGE
# ==============================================================================

def ewma_weights(n_obs, halflife):
    """Pesos EWMA normalizados, del mas antiguo al mas reciente.

    halflife se expresa en el mismo numero de periodos que las filas de la
    muestra (dias si los retornos son diarios). halflife=None devuelve pesos
    iguales, lo que reduce el estimador a la covarianza muestral clasica.
    """
    if halflife is None or halflife <= 0:
        return np.full(n_obs, 1.0 / n_obs)
    lam = 0.5 ** (1.0 / float(halflife))
    exponents = np.arange(n_obs - 1, -1, -1, dtype=float)
    w = lam ** exponents
    return w / w.sum()


def effective_sample_size(w):
    """Tamano de muestra efectivo de Kish: 1 / sum(w^2).

    Con pesos iguales devuelve n. Con EWMA devuelve el numero de observaciones
    "equivalentes", que es lo que corresponde usar en la intensidad de
    shrinkage de Ledoit-Wolf en lugar de T.
    """
    w = np.asarray(w, dtype=float)
    return float(1.0 / np.sum(w ** 2))


def ewma_cov(returns, halflife=None, demean=True):
    """Covarianza EWMA.

    Parametros
    ----------
    returns : DataFrame o array (T, n) de retornos en la frecuencia nativa.
    halflife : vida media en periodos. None -> pesos iguales.
    demean : si False asume media cero (convencion RiskMetrics). Con datos
        diarios la diferencia es menor, pero demean=True es el default seguro.

    Devuelve (cov, w) con cov en la misma frecuencia que los retornos.
    """
    X = np.asarray(returns, dtype=float)
    if X.ndim != 2:
        raise ValueError("returns debe ser bidimensional (T, n)")
    T = X.shape[0]
    if T < 2:
        raise ValueError("se requieren al menos 2 observaciones")

    w = ewma_weights(T, halflife)
    mu = w @ X if demean else np.zeros(X.shape[1])
    Xc = X - mu
    cov = (Xc * w[:, None]).T @ Xc
    cov = (cov + cov.T) / 2.0
    return cov, w


def average_correlation(S):
    """Correlacion promedio fuera de la diagonal de una matriz de covarianza."""
    d = np.sqrt(np.clip(np.diag(S), 1e-300, None))
    R = S / np.outer(d, d)
    n = S.shape[0]
    if n < 2:
        return 0.0
    iu = np.triu_indices(n, k=1)
    vals = R[iu]
    vals = vals[np.isfinite(vals)]
    return float(vals.mean()) if vals.size else 0.0


def ledoit_wolf_constant_correlation(returns, S=None, t_eff=None, weights=None,
                                     demean=True, delta_max=1.0, return_info=False):
    """Intensidad de shrinkage optima hacia el objetivo de correlacion constante.

    Ledoit & Wolf (2003), "Honey, I Shrunk the Sample Covariance Matrix".
    El objetivo F tiene las varianzas muestrales en la diagonal y, fuera de
    ella, la correlacion promedio reescalada: f_ij = rbar * sqrt(s_ii * s_jj).

    delta* = max(0, min(delta_max, (pi - rho) / gamma / T))

    Parametros
    ----------
    returns : (T, n) retornos. Se usan para los momentos de orden 4 que
        entran en pi y rho.
    S : covarianza a encoger. Si es None se usa la muestral con `weights`
        (MLE, divide por T con pesos iguales). Pasar aqui la matriz EWMA es la
        combinacion recomendada, junto con sus pesos.
    t_eff : tamano de muestra a usar en delta. Si es None se usa el de Kish
        de `weights` (T con pesos iguales).
    weights : pesos de las filas (suman 1), los MISMOS con los que se calculo S.
        None -> pesos iguales: Ledoit-Wolf clasico.
    demean : centrar con la media ponderada (igual que ewma_cov).
    delta_max : cota superior de delta. Si el delta bruto la supera (o supera
        1) se registra un aviso con el valor bruto.
    return_info : si True devuelve ademas un dict con delta_raw y delta.

    Consistencia cuando S es la EWMA:
      - El objetivo F (varianzas y correlacion promedio) y gamma = ||F - S||^2
        se construyen con la MISMA matriz S que se encoge.
      - pi y rho (y la S_sample que entra en ellos) se calculan con los MISMOS
        pesos EWMA, y el divisor es t_eff (Kish). Antes pi y rho eran los de la
        muestra completa sin pesos divididos por t_eff: con un shock aislado
        (COVID, marzo 2020) lejos en el pasado, pi quedaba ~3 veces inflado y
        delta se saturaba en 1 (diagnostico mv_shrinkage_diag, variante D).
    Con weights=None y S=None es exactamente el Ledoit-Wolf clasico.

    Devuelve (S_shrunk, delta, F), o (S_shrunk, delta, F, info) si return_info.
    """
    X = np.asarray(returns, dtype=float)
    T, n = X.shape
    if weights is None:
        w = np.full(T, 1.0 / T)
    else:
        w = np.asarray(weights, dtype=float)
        if w.shape != (T,):
            raise ValueError("weights debe tener una entrada por fila de returns")
        w = w / w.sum()
    Xc = X - (w @ X) if demean else X

    S_sample = (Xc * w[:, None]).T @ Xc
    if S is None:
        S = S_sample
    S = np.asarray(S, dtype=float)

    info = {"delta_raw": 0.0, "delta": 0.0, "delta_max": float(delta_max)}

    def _out(S_out, delta, F_out):
        return (S_out, delta, F_out, info) if return_info else (S_out, delta, F_out)

    if n < 2 or T < 4:
        return _out(S, 0.0, S)

    var = np.clip(np.diag(S), 1e-300, None)
    sd = np.sqrt(var)
    rbar = average_correlation(S)

    # Objetivo F: correlacion constante
    F = rbar * np.outer(sd, sd)
    np.fill_diagonal(F, var)

    # pi_ij = sum_t w_t (x_ti x_tj - s_ij)^2   (w_t = 1/T en el caso clasico)
    Y = Xc ** 2
    pi_mat = (Y * w[:, None]).T @ Y - S_sample ** 2
    pi_hat = float(pi_mat.sum())

    # theta_ii,ij = sum_t w_t (x_ti^2 - s_ii)(x_ti x_tj - s_ij)
    #             = sum_t w_t x_ti^3 x_tj - s_ii * s_ij
    cube = (Xc ** 3 * w[:, None]).T @ Xc
    var_s = np.diag(S_sample)
    theta_ii = cube - var_s[:, None] * S_sample
    theta_jj = cube.T - var_s[None, :] * S_sample

    sd_s = np.sqrt(np.clip(var_s, 1e-300, None))
    ratio = np.outer(sd_s, 1.0 / sd_s)          # sqrt(s_ii / s_jj)
    rho_off = (rbar / 2.0) * ((1.0 / ratio) * theta_ii + ratio * theta_jj)
    np.fill_diagonal(rho_off, 0.0)
    rho_hat = float(np.trace(pi_mat) + rho_off.sum())

    gamma_hat = float(np.sum((F - S) ** 2))

    if gamma_hat <= 0 or not np.isfinite(gamma_hat):
        return _out(S, 0.0, F)

    T_use = float(t_eff) if (t_eff is not None and t_eff > 1) else effective_sample_size(w)
    delta_raw = float((pi_hat - rho_hat) / gamma_hat / T_use)
    cota = min(1.0, float(delta_max))
    delta = float(min(cota, max(0.0, delta_raw)))
    if delta_raw > cota:
        logger.warning(
            "Ledoit-Wolf: delta bruto %.3f supera la cota %.2f; se aplica %.3f "
            "(t_eff=%.1f). Revisar la muestra (shocks aislados) o el halflife.",
            delta_raw, cota, delta, T_use)
    info.update(delta_raw=delta_raw, delta=delta)

    S_shrunk = delta * F + (1.0 - delta) * S
    S_shrunk = (S_shrunk + S_shrunk.T) / 2.0
    return _out(S_shrunk, delta, F)


# Cota de delta en el pipeline EWMA + LW. Con el estimador consistente el delta
# no deberia acercarse a 1; si lo hace se avisa y se recorta aqui.
LW_DELTA_MAX = 0.9


def cov_ewma_shrunk(returns, halflife=None, scale=1.0, demean=True,
                    shrink=True, min_obs=60, lw_delta_max=LW_DELTA_MAX):
    """Pipeline completo: EWMA -> shrinkage Ledoit-Wolf -> reescalado.

    Es el reemplazo directo de `returns.cov() * factor` en los optimizadores.

    Parametros
    ----------
    returns : DataFrame (T, n). Idealmente DIARIO: la precision de la
        covarianza crece con la frecuencia de muestreo (Merton, 1980), a
        diferencia de la media.
    halflife : vida media en periodos de `returns`.
    scale : factor para llevar la covarianza a la frecuencia objetivo
        (p.ej. 5 para pasar de diaria a semanal, 252 para anual).
    shrink : aplicar Ledoit-Wolf sobre la matriz EWMA.
    min_obs : por debajo de este numero de filas se devuelve la covarianza
        muestral simple reescalada, sin EWMA ni shrinkage.
    lw_delta_max : cota del delta de Ledoit-Wolf (aviso si el bruto la supera).

    Devuelve (cov, info) donde info trae delta (aplicado), delta_raw, t_eff y
    n_obs.
    """
    if isinstance(returns, pd.DataFrame):
        cols = list(returns.columns)
        X = returns.dropna().values
    else:
        cols = None
        X = np.asarray(returns, dtype=float)
        X = X[np.isfinite(X).all(axis=1)]

    T = X.shape[0]
    info = {"n_obs": T, "delta": 0.0, "delta_raw": 0.0, "t_eff": float(T),
            "halflife": halflife, "method": "ewma+lw"}

    if T < max(min_obs, 4):
        cov = np.cov(X, rowvar=False, ddof=1) if T > 1 else np.zeros((X.shape[1],) * 2)
        info["method"] = "muestral (pocas observaciones)"
        cov = np.atleast_2d(cov) * scale
        return (pd.DataFrame(cov, index=cols, columns=cols) if cols else cov), info

    cov, w = ewma_cov(X, halflife=halflife, demean=demean)
    info["t_eff"] = effective_sample_size(w)

    if shrink:
        cov, delta, _, lw = ledoit_wolf_constant_correlation(
            X, S=cov, t_eff=info["t_eff"], weights=w, demean=demean,
            delta_max=lw_delta_max, return_info=True)
        info["delta"] = delta
        info["delta_raw"] = lw["delta_raw"]
        info["delta_max"] = lw["delta_max"]
    else:
        info["method"] = "ewma"

    cov = cov * scale
    if cols:
        cov = pd.DataFrame(cov, index=cols, columns=cols)
    return cov, info


def texto_delta_shrinkage(info):
    """'delta shrinkage: 0.212 (delta_raw: 0.245, cota delta_max: 0.90)' para el log.

    Muestra el delta aplicado, el bruto de Ledoit-Wolf y la cota si `info`
    (de cov_ewma_shrunk) los trae; marca cuando el bruto fue recortado.
    """
    texto = f"delta shrinkage: {float(info.get('delta', 0.0)):.3f}"
    extras = []
    if info.get("delta_raw") is not None:
        extras.append(f"delta_raw: {float(info['delta_raw']):.3f}")
    if info.get("delta_max") is not None:
        extras.append(f"cota delta_max: {float(info['delta_max']):.2f}")
        if info.get("delta_raw") is not None and float(info["delta_raw"]) > float(info["delta_max"]):
            extras.append("recortado a la cota")
    return texto + (f" ({', '.join(extras)})" if extras else "")


def scale_cov(cov, factor):
    """Reescala una covarianza por un factor temporal (raiz del tiempo en vol)."""
    return cov * factor


def nearest_psd(cov, eps_rel=1e-8):
    """Proyeccion PSD por recorte de autovalores.

    Mantiene la escala: el piso es relativo a la varianza media.
    """
    A = np.asarray(cov, dtype=float)
    A = (A + A.T) / 2.0
    vals, vecs = np.linalg.eigh(A)
    # El piso se ancla al mayor autovalor en magnitud, no a la media de la
    # diagonal: esta ultima puede ser negativa en una matriz mal condicionada
    # y produciria un piso negativo, que no corrige nada.
    scale = float(np.max(np.abs(vals)))
    floor = eps_rel * scale if scale > 0 else 0.0
    if np.all(vals >= floor):
        return cov
    vals = np.maximum(vals, floor)
    out = vecs @ np.diag(vals) @ vecs.T
    out = (out + out.T) / 2.0
    if isinstance(cov, pd.DataFrame):
        return pd.DataFrame(out, index=cov.index, columns=cov.columns)
    return out


def seasonal_vol_ratio(returns, in_season, bounds=(0.70, 1.50), min_obs=10):
    """Ratio vol estacional / vol de todo el historial, por columna.

    ratio_i = clip(sd(r_i | temporada) / sd(r_i), lo, hi)

    Escala una covarianza historica con D Sigma D (D = diag(ratio)): cambia la
    vol de cada activo en la temporada y conserva las correlaciones del
    historial completo. Estimar n ratios aguanta pocas semanas estacionales;
    estimar n(n-1)/2 correlaciones no. Con menos de `min_obs` observaciones en
    temporada, o sin vol finita, el ratio es 1 (sin ajuste).
    """
    r = pd.DataFrame(returns)
    mask = np.asarray(in_season, dtype=bool)
    if mask.shape[0] != len(r):
        raise ValueError("in_season debe tener una entrada por fila de returns")
    lo, hi = bounds
    sd_total = r.std()
    r_est = r.loc[mask]
    sd_est = r_est.std()
    n_est = r_est.notna().sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = sd_est / sd_total
    valido = (n_est >= min_obs) & np.isfinite(ratio) & (sd_total > 0)
    ratio = ratio.where(valido, 1.0)
    return ratio.clip(lo, hi).astype(float)


# ==============================================================================
# 2. CORRECCION Q -> P (PRIMAS DE RIESGO)
# ==============================================================================
# La densidad implicita es la fisica ponderada por el nucleo de precios. Sus
# momentos NO son los momentos fisicos:
#
#   sigma_Q^2 = sigma_P^2 + VRP,  con VRP > 0 en promedio
#   rho_Q     > rho_P             (prima de riesgo de correlacion)
#
# Optimizar con momentos Q sobrestima el riesgo y subestima la diversificacion.
# La correccion se estima con el ratio realizado/implicito acotado, que es el
# mismo criterio que ya usaba black_litterman.py (COTA_RATIO_VOL_P).
# ==============================================================================

def q_to_p_vol(iv_q, hv, ratio_bounds=(0.70, 1.00), fallback_ratio=0.90):
    """Convierte volatilidad implicita (medida Q) a volatilidad fisica (P).

    sigma_P = sigma_Q * clip(hv / sigma_Q, lo, hi)

    El ratio se estima con la volatilidad historica del propio activo, no con
    una constante: si la IV de un activo esta muy por encima de su realizada,
    el recorte es mayor. Las cotas evitan que el ratio se dispare cuando la IV
    es ruidosa o el activo tiene pocos datos.

    ratio_bounds : (lo, hi). hi=1.0 impone que la vol fisica no exceda a la
        implicita, que es el signo esperado del VRP. Subir hi por encima de 1
        desactiva ese supuesto.
    fallback_ratio : ratio usado cuando hv no esta disponible.

    Devuelve (sigma_P, ratio). Acepta escalares o arrays.
    """
    lo, hi = ratio_bounds
    iv = np.asarray(iv_q, dtype=float)
    h = np.asarray(hv, dtype=float)

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where((iv > 0) & np.isfinite(iv) & np.isfinite(h) & (h > 0),
                         h / iv, np.nan)
    ratio = np.where(np.isfinite(ratio), ratio, fallback_ratio)
    ratio = np.clip(ratio, lo, hi)

    sigma_p = np.where((iv > 0) & np.isfinite(iv), iv * ratio, h)
    if np.isscalar(iv_q):
        return float(sigma_p), float(ratio)
    return sigma_p, ratio


def q_to_p_correlation(rho_q, rho_realized, ratio_bounds=(0.60, 1.00),
                       fallback_ratio=0.85):
    """Corrige la prima de riesgo de correlacion.

    La correlacion implicita extraida por dispersion excede sistematicamente a
    la realizada (Driessen, Maenhout & Vilkov, 2009). Sin esta correccion el
    optimizador subestima el beneficio de diversificacion.

    rho_P = rho_Q * clip(rho_realized / rho_Q, lo, hi)
    """
    lo, hi = ratio_bounds
    rq = np.asarray(rho_q, dtype=float)
    rr = np.asarray(rho_realized, dtype=float)

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where((np.abs(rq) > 1e-6) & np.isfinite(rq) & np.isfinite(rr),
                         rr / rq, np.nan)
    ratio = np.where(np.isfinite(ratio), ratio, fallback_ratio)
    ratio = np.clip(ratio, lo, hi)

    rho_p = np.clip(rq * ratio, -0.999, 0.999)
    if np.isscalar(rho_q):
        return float(rho_p), float(ratio)
    return rho_p, ratio


# ==============================================================================
# 3. PANEL DE ESCENARIOS Y MOMENTOS DEL PORTAFOLIO
# ==============================================================================
# La asimetria y curtosis de un portafolio NO son el promedio ponderado de las
# marginales: dependen de los co-momentos (tensores M3 y M4). Construir esos
# tensores es O(n^3) y O(n^4); evaluarlos sobre un panel de escenarios es
# O(J*n) y da exactamente w'M3(w x w) y w'M4(w x w x w).
#
# El panel se arma con los retornos historicos estandarizados: preserva la
# copula empirica y la forma de las marginales (que estan bajo la medida
# fisica, que es la correcta para medir riesgo), y solo se reescalan media y
# volatilidad hacia los objetivos prospectivos.
# ==============================================================================

def standardized_panel(returns, ddof=1):
    """Estandariza cada columna a media 0 y desviacion 1.

    Conserva la dependencia empirica entre activos y la asimetria/curtosis
    marginal de cada uno.
    """
    if isinstance(returns, pd.DataFrame):
        X = returns.dropna().values
        cols = list(returns.columns)
    else:
        X = np.asarray(returns, dtype=float)
        X = X[np.isfinite(X).all(axis=1)]
        cols = None
    mu = X.mean(axis=0)
    sd = X.std(axis=0, ddof=ddof)
    sd = np.where(sd > 0, sd, 1.0)
    Z = (X - mu) / sd
    return Z, cols


def rescale_panel(Z, mu_target, sd_target):
    """Lleva un panel estandarizado a (mu_target, sd_target) por columna.

    Transformacion afin: no altera correlaciones ni momentos estandarizados.
    """
    Z = np.asarray(Z, dtype=float)
    mu_t = np.asarray(mu_target, dtype=float).reshape(1, -1)
    sd_t = np.asarray(sd_target, dtype=float).reshape(1, -1)
    return Z * sd_t + mu_t


def portfolio_moments(w, panel, probs=None):
    """Momentos centrales 1 a 4 del retorno del portafolio, en O(J*n).

    Equivale a w'mu, w'Sigma w, w'M3(w (x) w) y w'M4(w (x) w (x) w) sin
    construir los tensores de co-momentos.

    Devuelve dict con mean, var, sd, skew (estandarizada) y exkurt (exceso).
    """
    w = np.asarray(w, dtype=float)
    X = np.asarray(panel, dtype=float)
    J = X.shape[0]
    p = np.full(J, 1.0 / J) if probs is None else np.asarray(probs, dtype=float)
    p = p / p.sum()

    r = X @ w
    mu = float(p @ r)
    d = r - mu
    m2 = float(p @ d ** 2)
    m3 = float(p @ d ** 3)
    m4 = float(p @ d ** 4)

    sd = float(np.sqrt(max(m2, 1e-18)))
    skew = m3 / sd ** 3 if sd > 0 else 0.0
    exkurt = (m4 / sd ** 4 - 3.0) if sd > 0 else 0.0
    return {"mean": mu, "var": m2, "sd": sd,
            "skew": float(skew), "exkurt": float(exkurt),
            "m3": m3, "m4": m4}


def portfolio_moment_gradients(w, panel, probs=None):
    """Gradientes analiticos de sd, asimetria y exceso de curtosis respecto a w.

    Necesarios para la contribucion marginal al CVaR (descomposicion de Euler)
    cuando los momentos vienen de co-momentos y no de un promedio de marginales.

    Con d = (X - mu) w:
        dm2/dw = 2 C'(p . d)
        dm3/dw = 3 C'(p . d^2)
        dm4/dw = 4 C'(p . d^3)
        dS/dw  = dm3/dw / sd^3 - 3 m3 (dsd/dw) / sd^4
        dK/dw  = dm4/dw / sd^4 - 4 m4 (dsd/dw) / sd^5
    """
    w = np.asarray(w, dtype=float)
    X = np.asarray(panel, dtype=float)
    J = X.shape[0]
    p = np.full(J, 1.0 / J) if probs is None else np.asarray(probs, dtype=float)
    p = p / p.sum()

    C = X - (p @ X)
    d = C @ w
    m2 = float(p @ d ** 2)
    m3 = float(p @ d ** 3)
    m4 = float(p @ d ** 4)
    sd = float(np.sqrt(max(m2, 1e-18)))

    g2 = 2.0 * (C.T @ (p * d))
    g3 = 3.0 * (C.T @ (p * d ** 2))
    g4 = 4.0 * (C.T @ (p * d ** 3))

    d_sd = g2 / (2.0 * sd)
    skew = m3 / sd ** 3
    exkurt = m4 / sd ** 4 - 3.0
    d_skew = g3 / sd ** 3 - 3.0 * m3 * d_sd / sd ** 4
    d_exkurt = g4 / sd ** 4 - 4.0 * m4 * d_sd / sd ** 5

    return {"sd": sd, "skew": float(skew), "exkurt": float(exkurt),
            "d_sd_dw": d_sd, "d_skew_dw": d_skew, "d_exkurt_dw": d_exkurt}


# ==============================================================================
# 4. MOMENTOS DE ORDEN SUPERIOR Y CORNISH-FISHER
# ==============================================================================
# Antes se recortaban S y K por separado, lo que dejaba dos problemas:
#
#  a) Admisibilidad. Toda distribucion cumple K >= 1 + S^2 (desigualdad de
#     Pearson, K = curtosis total). Un par (MFIS, MFIK) que la viola no es una
#     cola gorda: delata una integracion BKM defectuosa (pocos strikes, MFIV
#     diminuta en el denominador). Se anula en vez de recortarse.
#
#  b) Cornish-Fisher. En z_cf = z + (z^2-1)s/6 + (z^3-3z)k/24 - (2z^3-5z)s^2/36,
#     s y k son PARAMETROS de la transformacion, no la asimetria ni la curtosis
#     de la distribucion que produce. Enchufar los momentos observados como
#     parametros (i) sale del dominio de monotonia con |S| o K grandes, y ahi
#     el "cuantil" puede cambiar de signo, y (ii) aun dentro del dominio
#     invierte el orden: con exceso de curtosis 6, el cuantil al 1% es menos
#     severo con S = -1.5 que con S = -1. Siguiendo a Maillard (2012) se buscan
#     los parametros cuya transformacion reproduce los momentos observados; si
#     el par no es alcanzable por la familia, se usa el alcanzable mas cercano.
# ==============================================================================

# |s| maximo con dominio de monotonia no vacio: raiz de 1 - s^2/6 + s^4/1296 = 0
CF_SKEW_PARAM_MAX = float(np.sqrt(108.0 - 72.0 * np.sqrt(2.0)))   # ~2.486

# Gauss-Hermite (probabilistas) de 16 nodos: exacto hasta grado 31, sobra para
# los momentos de orden 4 de un polinomio cubico en Z.
_GH_Z, _GH_W = np.polynomial.hermite_e.hermegauss(16)
_GH_W = _GH_W / _GH_W.sum()


def higher_moments_admissible(skew, kurt, kurt_max=np.inf):
    """True si (asimetria, curtosis TOTAL) es un par posible y K <= kurt_max."""
    if not (np.isfinite(skew) and np.isfinite(kurt)):
        return False
    return bool(1.0 + skew ** 2 <= kurt <= kurt_max)


def mfik_cap(n_otm, base=20.0, hard=80.0, strikes_at_base=8, strikes_at_hard=60):
    """Tope de MFIK segun la profundidad de la cadena OTM.

    Un indice liquido (SPY) concentra masa en las alas y su MFIK de BKM pasa
    de 20 con una cadena densa; el mismo numero en cinco strikes es ruido.
    Con `strikes_at_base` contratos OTM el tope es `base`. Crece en linea
    hasta `hard` al llegar a `strikes_at_hard`. Por encima se queda en `hard`.
    """
    base = float(base)
    hard = float(hard)
    lo = float(strikes_at_base)
    hi = float(strikes_at_hard)
    if hard < base:
        raise ValueError("hard debe ser >= base")
    if hi <= lo:
        raise ValueError("strikes_at_hard debe ser > strikes_at_base")
    n = 0.0 if n_otm is None or not np.isfinite(n_otm) else float(n_otm)
    if n <= lo:
        return base
    if n >= hi:
        return hard
    return base + (n - lo) / (hi - lo) * (hard - base)


def mfik_cap_tenor(n_otm, dte, ref_dte=30.0, **cap_kwargs):
    """Tope de MFIK (curtosis total) al plazo de la cadena.

    El exceso sobre 3 escala como ref_dte/dte: una cadena corta tiene
    curtosis mecanicamente alta y no se rechaza contra el tope de 30 dias.
    Equivale a llevar el exceso al plazo de referencia y compararlo con
    `mfik_cap` sin escalar.
    """
    cap = mfik_cap(n_otm, **cap_kwargs)
    dte = float(dte)
    ref = float(ref_dte)
    if not (np.isfinite(dte) and dte > 0 and np.isfinite(ref) and ref > 0):
        return cap
    return 3.0 + (cap - 3.0) * (ref / dte)


def cornish_fisher_z(z_alpha, s, k):
    """Transformacion de Cornish-Fisher con parametros (s, k); vectorizada en z."""
    z = np.asarray(z_alpha, dtype=float)
    return (z
            + (z ** 2 - 1) / 6.0 * s
            + (z ** 3 - 3 * z) / 24.0 * k
            - (2 * z ** 3 - 5 * z) / 36.0 * s ** 2)


def cornish_fisher_domain(s):
    """Intervalo (k_lo, k_hi) de k en que z -> z_cf es estrictamente creciente.

    Forma cerrada de la condicion de discriminante negativo de dz_cf/dz
    (Maillard, 2012). Devuelve (nan, nan) si |s| > CF_SKEW_PARAM_MAX.
    """
    x = float(s) ** 2
    b = 1.0 + 11.0 * x / 36.0
    c = 7.0 * x / 36.0 + 5.0 * x ** 2 / 216.0
    disc = b ** 2 - 4.0 * c
    if disc <= 0.0:
        return np.nan, np.nan
    r = np.sqrt(disc)
    return 4.0 * (b - r), 4.0 * (b + r)


def cornish_fisher_moments(s, k):
    """(sd, asimetria, exceso de curtosis) de z_cf(Z), Z ~ N(0,1). Media = 0."""
    y = cornish_fisher_z(_GH_Z, s, k)
    m2 = float(_GH_W @ y ** 2)
    sd = np.sqrt(m2)
    return sd, float(_GH_W @ y ** 3) / m2 ** 1.5, float(_GH_W @ y ** 4) / m2 ** 2 - 3.0


def cornish_fisher_params(skew, exkurt):
    """Parametros (s, k) cuya transformacion CF tiene los momentos pedidos.

    Busca dentro del dominio de monotonia, parametrizado como s en
    [0, CF_SKEW_PARAM_MAX) y k = k_lo(s) + t (k_hi(s) - k_lo(s)), t en (0, 1).
    La asimetria es impar en s, asi que se resuelve para |skew| y se devuelve
    el signo. Si el par no es alcanzable (p. ej. asimetria alta con poca
    curtosis) se devuelve el punto alcanzable mas cercano en el plano de
    momentos. Devuelve (s, k, exacto).
    """
    from scipy.optimize import least_squares

    objetivo = np.array([abs(float(skew)), float(exkurt)])
    s_max = CF_SKEW_PARAM_MAX * (1.0 - 1e-6)

    def a_parametros(p):
        k_lo, k_hi = cornish_fisher_domain(p[0])
        return p[0], k_lo + p[1] * (k_hi - k_lo)

    def residuo(p):
        _, sk, ek = cornish_fisher_moments(*a_parametros(p))
        return np.array([sk, ek]) - objetivo

    mejor = None
    for x0 in ([min(objetivo[0], 1.0), 0.5], [0.1, 0.2], [0.5 * s_max, 0.5]):
        res = least_squares(residuo, x0, bounds=([0.0, 0.0], [s_max, 1.0 - 1e-3]),
                            xtol=1e-12, ftol=1e-12)
        if mejor is None or res.cost < mejor.cost:
            mejor = res
    s, k = a_parametros(mejor.x)
    # Tolerancia de 1e-3 en momentos: por debajo no mueve el cuantil de forma apreciable
    return float(np.sign(skew) * s), float(k), bool(np.max(np.abs(mejor.fun)) < 1e-3)


def cornish_fisher_tail(alpha, skew, exkurt):
    """Cuantil y ES de la cola izquierda (probabilidad alpha), estandarizados.

    La distribucion es la CF con media 0, varianza 1 y los momentos pedidos.
    El ES es cerrado: int_{-inf}^z He_n(u) phi(u) du = -He_{n-1}(z) phi(z).
    Devuelve dict con q, es (ambos negativos en la cola), s, k y exacto.
    """
    s, k, exacto = cornish_fisher_params(skew, exkurt)
    sd = cornish_fisher_moments(s, k)[0]
    z = norm.ppf(alpha)
    c1, c2, c3 = 1.0 - s ** 2 / 36.0, s / 6.0, k / 24.0 - s ** 2 / 18.0
    q = float(cornish_fisher_z(z, s, k)) / sd
    es = -norm.pdf(z) / alpha * (c1 + c2 * z + c3 * (z ** 2 - 1.0)) / sd
    return {"q": q, "es": float(es), "s": s, "k": k, "exact": exacto}


def cornish_fisher_es_gradient(alpha, skew, exkurt, h=1e-4):
    """ES estandarizado y sus derivadas respecto a (skew, exkurt), por diferencias centrales."""
    es = cornish_fisher_tail(alpha, skew, exkurt)["es"]
    d_s = (cornish_fisher_tail(alpha, skew + h, exkurt)["es"]
           - cornish_fisher_tail(alpha, skew - h, exkurt)["es"]) / (2.0 * h)
    d_k = (cornish_fisher_tail(alpha, skew, exkurt + h)["es"]
           - cornish_fisher_tail(alpha, skew, exkurt - h)["es"]) / (2.0 * h)
    return es, d_s, d_k


def var_cvar_cornish_fisher(mu, sd, skew, exkurt, confidence=0.95):
    """VaR y CVaR (como retornos, negativos en perdida) de Cornish-Fisher.

    'exact' es False cuando los momentos no eran alcanzables por la familia CF
    y se usaron los mas cercanos; se reportan tambien los valores gaussianos.
    """
    alpha = 1.0 - confidence
    z_a = norm.ppf(alpha)
    var_g = mu + z_a * sd
    cvar_g = mu - (norm.pdf(z_a) / alpha) * sd

    if not (np.isfinite(skew) and np.isfinite(exkurt)):
        return {"var": np.nan, "cvar": np.nan, "z_cf": np.nan, "exact": False,
                "cf_s": np.nan, "cf_k": np.nan,
                "var_gaussian": float(var_g), "cvar_gaussian": float(cvar_g),
                "skew": float(skew), "exkurt": float(exkurt)}

    cola = cornish_fisher_tail(alpha, skew, exkurt)
    return {"var": float(mu + cola["q"] * sd), "cvar": float(mu + cola["es"] * sd),
            "z_cf": cola["q"], "exact": cola["exact"], "cf_s": cola["s"], "cf_k": cola["k"],
            "var_gaussian": float(var_g), "cvar_gaussian": float(cvar_g),
            "skew": float(skew), "exkurt": float(exkurt)}


# ==============================================================================
# 5. RETORNO ESPERADO VIA SVIX  --  EXPERIMENTAL, SIN VERIFICAR
# ==============================================================================
# AVISO: la especificacion de abajo se escribio de memoria a partir de
# Martin (2017) y Martin & Wagner (2022). NO ha sido verificada contra el
# paper ni validada empiricamente en este repositorio. Esta APAGADA por
# defecto en todos los scripts. Antes de activarla:
#
#   1. Contrastar la formula con Martin & Wagner (2022), "What is the
#      Expected Return on a Stock?", Journal of Finance.
#   2. Confirmar que SVIX^2 se calcula sobre el horizonte correcto y que los
#      pesos w_mkt son los de capitalizacion.
#   3. Backtestear antes de usarla para asignar capital.
#
# Fundamento del interes: Chopra & Ziemba (1993) muestran que los errores en
# mu pesan un orden de magnitud mas que los de covarianza. Las opciones son la
# unica fuente forward-looking disponible para mu.
# ==============================================================================

def martin_wagner_excess_return(svix2_i, svix2_mkt, w_mkt=None, lam=0.5):
    """Exceso de retorno esperado por activo a partir de varianzas neutrales.

    Especificacion implementada:

        E[R_i - R_f] = SVIX^2_mkt + lam * (SVIX^2_i - sum_j w_j SVIX^2_j)

    donde SVIX^2 es la varianza neutral al riesgo al horizonte (proxy directo:
    MFIV). lam = 1/2 en la version del paper.

    EXPERIMENTAL: ver el aviso de la seccion. Devuelve (excess, diagnostico).
    """
    s2_i = np.asarray(svix2_i, dtype=float)
    n = s2_i.shape[0]

    if w_mkt is None:
        w = np.full(n, 1.0 / n)
    else:
        w = np.asarray(w_mkt, dtype=float)
        w = w / w.sum()

    ok = np.isfinite(s2_i)
    if not ok.any():
        return np.full(n, np.nan), {"ok": False, "reason": "sin SVIX valido"}

    s2_fill = np.where(ok, s2_i, np.nanmean(s2_i[ok]))
    avg = float(np.sum(w * s2_fill))

    excess = float(svix2_mkt) + lam * (s2_fill - avg)
    excess = np.where(ok, excess, np.nan)

    return excess, {"ok": True, "svix2_mkt": float(svix2_mkt),
                    "svix2_avg": avg, "lam": lam,
                    "n_valid": int(ok.sum()), "n_total": n,
                    "warning": "formula sin verificar contra el paper"}


# ==============================================================================
# 6. ESCALADO TEMPORAL
# ==============================================================================
# Un unico punto para pasar momentos de un plazo a otro. Los optimizadores
# mezclaban convenciones: MFIV integrada sobre ~30 DTE dividida por el
# horizonte del portafolio, asimetria semanal combinada con sigma al horizonte
# sin escalar, retornos mensuales anualizados con 12/horizonte, volatilidad
# anual en una matriz que debia estar al horizonte. Todas esas operaciones
# son la misma regla con plazos de entrada y salida distintos:
#
#   h = to_years / from_years          (ratio de plazos)
#   mu_h   = mu  * h                   (log-retornos iid; aprox. para simples)
#   var_h  = var * h
#   sd_h   = sd  * sqrt(h)
#   S_h    = S   / sqrt(h)             (asimetria estandarizada, iid)
#   K_h    = K   / h                   (EXCESO de curtosis, iid)
#
# Los plazos se expresan en ANOS y se construyen con `to_years`, que acepta
# el DTE real de la cadena (dias de calendario), semanas, meses o periodos
# de una frecuencia dada. Asi el plazo de una MFIV es el de sus contratos
# (info["dte"] de polygon_client.fetch_otm_chain), no el del portafolio.
#
# El escalado iid de S y K es un supuesto (sin dependencia temporal ni
# clustering de volatilidad). Es el mismo que ya usaba
# `momentos_cola_historicos`; aqui se centraliza para que todos los bloques
# lo apliquen igual.
# ==============================================================================

DAYS_PER_YEAR = 365.0            # calendario: vencimientos de opciones (DTE)
TRADING_DAYS_PER_YEAR = 252.0    # retornos diarios bursatiles
WEEKS_PER_YEAR = 52.0
MONTHS_PER_YEAR = 12.0


def to_years(periods=None, periods_per_year=None, *, dte=None, trading_days=None,
             weeks=None, months=None, days_per_year=DAYS_PER_YEAR):
    """Convierte un plazo a anos. Exactamente UNA forma de expresarlo:

    to_years(dte=30)                       -> 30 / 365    (dias de calendario)
    to_years(trading_days=21)              -> 21 / 252
    to_years(weeks=4.33)                   -> 4.33 / 52
    to_years(months=3)                     -> 3 / 12
    to_years(periods=5, periods_per_year=52) -> 5 / 52     (frecuencia arbitraria)

    Acepta escalares o arrays (p. ej. un DTE distinto por ticker). Lanza
    ValueError si se da mas de una forma, ninguna, o un plazo no positivo.
    """
    formas = {"periods": periods, "dte": dte, "trading_days": trading_days,
              "weeks": weeks, "months": months}
    dadas = [k for k, v in formas.items() if v is not None]
    if len(dadas) != 1:
        raise ValueError(f"to_years: indicar exactamente un plazo, se dieron {dadas or 'ninguno'}")
    nombre = dadas[0]
    valor = np.asarray(formas[nombre], dtype=float)

    if nombre == "periods":
        if periods_per_year is None or periods_per_year <= 0:
            raise ValueError("to_years: `periods` requiere periods_per_year > 0")
        divisor = float(periods_per_year)
    elif nombre == "dte":
        divisor = float(days_per_year)
    elif nombre == "trading_days":
        divisor = TRADING_DAYS_PER_YEAR
    elif nombre == "weeks":
        divisor = WEEKS_PER_YEAR
    else:
        divisor = MONTHS_PER_YEAR

    if np.any(~np.isfinite(valor)) or np.any(valor <= 0):
        raise ValueError(f"to_years: plazo no positivo o no finito en `{nombre}`: {formas[nombre]}")
    anos = valor / divisor
    return float(anos) if anos.ndim == 0 else anos


def scale_moments(from_years, to_years, mu=None, var=None, sd=None, skew=None, exkurt=None):
    """Escala momentos de un plazo `from_years` a otro `to_years` bajo iid.

    Solo se escalan los momentos que se pasan; el resto no aparece en la
    salida. Todos aceptan escalares o arrays (broadcast con los plazos).

    Devuelve dict con "h" (= to_years/from_years) y las claves pedidas entre
    mu, var, sd, skew, exkurt. `exkurt` es EXCESO de curtosis; la curtosis
    total no escala como K/h (hay que restar 3 antes y sumarlo despues).

    Ejemplos
    --------
    MFIV integrada sobre 30 DTE -> varianza anual:
        scale_moments(to_years(dte=30), 1.0, var=mfiv)["var"]
    Asimetria y exceso de curtosis semanales -> horizonte de 1 mes:
        scale_moments(to_years(weeks=1), to_years(months=1), skew=S, exkurt=K)
    """
    f = np.asarray(from_years, dtype=float)
    t = np.asarray(to_years, dtype=float)
    if np.any(~np.isfinite(f)) or np.any(f <= 0) or np.any(~np.isfinite(t)) or np.any(t <= 0):
        raise ValueError("scale_moments: los plazos deben ser positivos y finitos")
    h = t / f
    out = {"h": float(h) if h.ndim == 0 else h}

    def _f(x, fn):
        x_arr = np.asarray(x, dtype=float)
        y = fn(x_arr)
        return float(y) if y.ndim == 0 else y

    if mu is not None:
        out["mu"] = _f(mu, lambda x: x * h)
    if var is not None:
        out["var"] = _f(var, lambda x: x * h)
    if sd is not None:
        out["sd"] = _f(sd, lambda x: x * np.sqrt(h))
    if skew is not None:
        out["skew"] = _f(skew, lambda x: x / np.sqrt(h))
    if exkurt is not None:
        out["exkurt"] = _f(exkurt, lambda x: x / h)
    return out


def annualize(from_years, **moments):
    """Atajo: scale_moments(from_years, 1.0, **moments)."""
    return scale_moments(from_years, 1.0, **moments)


def scale_bkm_moments(mfiv, mfis, mfik, from_dte, to_dte):
    """Lleva MFIV, MFIS y MFIK del DTE de la cadena al DTE objetivo (iid).

    MFIV es varianza integrada. MFIS es asimetria. MFIK es curtosis TOTAL:
    se escala el exceso (MFIK - 3) y se vuelve a sumar 3. No escala MFIK/h.
    """
    exkurt = np.asarray(mfik, dtype=float) - 3.0
    esc = scale_moments(
        to_years(dte=from_dte), to_years(dte=to_dte),
        var=mfiv, skew=mfis, exkurt=exkurt,
    )
    mfik_out = esc["exkurt"] + 3.0
    return {"mfiv": esc["var"], "mfis": esc["skew"], "mfik": mfik_out, "h": esc["h"]}


def implied_variance_to_horizon(total_var_q, dte, horizon_years, days_per_year=DAYS_PER_YEAR):
    """Lleva una varianza implicita INTEGRADA (BKM MFIV sobre `dte` dias) al horizonte.

    MFIV, tal como la devuelve la integracion BKM de estos scripts, es la
    varianza neutral al riesgo acumulada entre hoy y el vencimiento, no una
    varianza anual. Anualizarla dividiendo por el horizonte del portafolio
    en lugar de por el plazo de los contratos (A-3 de la revision) la
    subestima en un factor dte/horizonte.

    Devuelve dict con:
      annual_var, annual_vol   : varianza y vol anualizadas con el DTE real
      horizon_var, horizon_vol : varianza y vol al horizonte pedido
      years_chain              : plazo de los contratos en anos
      h                        : horizon_years / years_chain
    Acepta arrays (un DTE por ticker). Donde dte o total_var_q no sean
    validos devuelve NaN en vez de lanzar.
    """
    v = np.asarray(total_var_q, dtype=float)
    d = np.asarray(dte, dtype=float)
    hz = np.asarray(horizon_years, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        years_chain = np.where((d > 0) & np.isfinite(d), d / float(days_per_year), np.nan)
        ok = np.isfinite(v) & (v >= 0) & np.isfinite(years_chain) & np.isfinite(hz) & (hz > 0)
        annual_var = np.where(ok, v / years_chain, np.nan)
        h = np.where(ok, hz / years_chain, np.nan)
        horizon_var = np.where(ok, v * h, np.nan)

    def _s(x):
        x = np.asarray(x, dtype=float)
        return float(x) if x.ndim == 0 else x

    return {"annual_var": _s(annual_var), "annual_vol": _s(np.sqrt(annual_var)),
            "horizon_var": _s(horizon_var), "horizon_vol": _s(np.sqrt(horizon_var)),
            "years_chain": _s(years_chain), "h": _s(h)}


# ==============================================================================
# 7. RETORNOS DE PORTAFOLIO Y DRAWDOWN CON LOG-RETORNOS
# ==============================================================================
# Los optimizadores trabajan con log-retornos pero aplicaban (1+r).cumprod()
# para el drawdown (B-1) y w'r para el retorno del portafolio (B-2). Ambas
# son identidades de retornos SIMPLES: con logs la riqueza es exp(cumsum) y
# el retorno del portafolio es log(1 + sum_i w_i (e^{r_i} - 1)).
# ==============================================================================

def max_drawdown(returns, log_returns=True):
    """Maximo drawdown (negativo) de una serie de retornos.

    log_returns=True : riqueza = exp(cumsum(r)).
    log_returns=False: riqueza = cumprod(1 + r).
    NaN si hay menos de 2 observaciones validas.
    """
    r = pd.Series(returns).dropna()
    if len(r) < 2:
        return np.nan
    wealth = np.exp(r.cumsum()) if log_returns else (1.0 + r).cumprod()
    peak = wealth.cummax()
    return float(((wealth - peak) / peak).min())


def portfolio_log_returns(asset_log_returns, weights):
    """Log-retorno exacto del portafolio a partir de log-retornos por activo.

    r_p = log(1 + sum_i w_i (exp(r_i) - 1)). El capital no invertido
    (1 - sum w) se asume en efectivo con retorno cero. La aproximacion
    w'r (suma ponderada de logs) solo coincide a primer orden.
    """
    if isinstance(asset_log_returns, pd.DataFrame):
        if isinstance(weights, pd.Series):
            weights = weights.reindex(asset_log_returns.columns)
        w = np.asarray(weights, dtype=float)
        simple = np.expm1(asset_log_returns.values) @ w
        return pd.Series(np.log1p(simple), index=asset_log_returns.index)
    X = np.asarray(asset_log_returns, dtype=float)
    w = np.asarray(weights, dtype=float)
    return np.log1p(np.expm1(X) @ w)


# ==============================================================================
# 8. CONSISTENCIA DE LA IV DEL PROVEEDOR CON LA TASA DEL SCRIPT
# ==============================================================================
# Polygon/Massive entrega `implied_volatility` ya invertida con su propio
# modelo (tasa, dividendos, spot), que no publica. Los scripts reprecian esa
# IV con Black-Scholes a la tasa libre del script (r = rf, q = 0) para la
# integral BKM. Si el acarreo del proveedor no es rf, los precios
# reconstruidos no son los del mercado: en MCD (oct-2026) la call ATM salia
# con 25.5% y la put del mismo strike con 22.2%, y la cadena OTM (puts bajo
# el spot, calls encima) tenia un salto en el ATM que inflaba MFIS.
#
# Los precios de mercado cumplen paridad call-put. Con un acarreo b se
# reconstruyen C(b) = BS(iv_call; b) y P(b) = BS(iv_put; b); C(b) - P(b)
# crece con b, asi que hay un unico b que deja C - P = S - K e^{-rT} en los
# strikes con ambos lados. Con ese b los precios quedan sin salto en el ATM
# y consistentes con la convencion del script (sin dividendos). Si no hay
# pares, o b cae en la cota, se usa rf: el comportamiento anterior.
# ==============================================================================

def bs_price(S, K, T, r, sigma, is_call):
    """Precio Black-Scholes europeo (q = 0). Vectorizado; NaN si T o sigma <= 0."""
    S, K, T, r, sigma = (np.asarray(x, dtype=float) for x in (S, K, T, r, sigma))
    is_call = np.asarray(is_call, dtype=bool)
    with np.errstate(divide="ignore", invalid="ignore"):
        sq = sigma * np.sqrt(T)
        d1 = (np.log(S / K) + (r + sigma ** 2 / 2.0) * T) / sq
        d2 = d1 - sq
        df = np.exp(-r * T)
        call = S * norm.cdf(d1) - K * df * norm.cdf(d2)
        put = K * df * norm.cdf(-d2) - S * norm.cdf(-d1)
    out = np.where(is_call, call, put)
    out = np.where((T > 0) & (sigma > 0) & (S > 0) & (K > 0), out, np.nan)
    return float(out) if out.ndim == 0 else out


def bs_implied_vol(price, S, K, T, r, is_call, lo=1e-4, hi=5.0, n_iter=100):
    """IV Black-Scholes (q = 0) por biseccion vectorizada.

    NaN si el precio cae fuera de [precio con lo, precio con hi]: bajo el
    valor intrinseco descontado o por encima del limite de arbitraje.
    """
    price, S, K, T, r = (np.asarray(x, dtype=float) for x in (price, S, K, T, r))
    is_call = np.asarray(is_call, dtype=bool)
    shape = np.broadcast(price, S, K, T, r, is_call).shape
    price, S, K, T, r, is_call = (np.broadcast_to(x, shape) for x in (price, S, K, T, r, is_call))
    a = np.full(shape, lo)
    b = np.full(shape, hi)
    p_lo = bs_price(S, K, T, r, a, is_call)
    p_hi = bs_price(S, K, T, r, b, is_call)
    ok = np.isfinite(price) & (price >= p_lo) & (price <= p_hi)
    for _ in range(n_iter):
        m = (a + b) / 2.0
        alto = bs_price(S, K, T, r, m, is_call) > price
        b = np.where(alto, m, b)
        a = np.where(alto, a, m)
    out = np.where(ok, (a + b) / 2.0, np.nan)
    return float(out) if out.ndim == 0 else out


def calibrate_iv_carry(S, T, rate, strikes, iv_call, iv_put, band=0.10,
                       bounds=(-0.20, 0.20), min_pairs=1):
    """Acarreo con el que la IV del proveedor reproduce precios con paridad.

    strikes, iv_call, iv_put: strikes de UN vencimiento con call y put. Se
    usan los pares con IV positiva y |ln(K/S)| <= band. Minimiza
    sum (C(b) - P(b) - (S - K e^{-rate T}))^2 en b dentro de `bounds`.

    Devuelve dict:
      carry          tasa con la que reconstruir precios desde la IV (rate si no ok)
      ok             False sin pares suficientes o con b en la cota
      n_pairs        pares usados
      iv_gap_before  media de |iv_call - iv_put| tal como vienen
      iv_gap_after   la misma brecha re-invertida a `rate` con `carry`
    """
    from scipy.optimize import minimize_scalar

    out = {"carry": float(rate), "ok": False, "n_pairs": 0,
           "iv_gap_before": float("nan"), "iv_gap_after": float("nan")}
    K = np.asarray(strikes, dtype=float)
    ivc = np.asarray(iv_call, dtype=float)
    ivp = np.asarray(iv_put, dtype=float)
    if not (np.isfinite(S) and S > 0 and np.isfinite(T) and T > 0) or K.size == 0:
        return out
    m = (np.isfinite(K) & (K > 0) & np.isfinite(ivc) & (ivc > 0)
         & np.isfinite(ivp) & (ivp > 0))
    with np.errstate(divide="ignore", invalid="ignore"):
        m &= np.abs(np.log(K / S)) <= band
    K, ivc, ivp = K[m], ivc[m], ivp[m]
    out["n_pairs"] = int(K.size)
    if K.size == 0:
        return out
    out["iv_gap_before"] = float(np.mean(np.abs(ivc - ivp)))
    if K.size < min_pairs:
        return out

    paridad = S - K * np.exp(-rate * T)

    def residuo(b):
        c = bs_price(S, K, T, b, ivc, True)
        p = bs_price(S, K, T, b, ivp, False)
        return float(np.sum(((c - p - paridad) / S) ** 2))

    lo, hi = bounds
    res = minimize_scalar(residuo, bounds=(lo, hi), method="bounded",
                          options={"xatol": 1e-7})
    b = float(res.x)
    if not np.isfinite(b) or min(b - lo, hi - b) < 1e-4:
        return out
    c = bs_implied_vol(bs_price(S, K, T, b, ivc, True), S, K, T, rate, True)
    p = bs_implied_vol(bs_price(S, K, T, b, ivp, False), S, K, T, rate, False)
    out.update(carry=b, ok=True, iv_gap_after=float(np.nanmean(np.abs(c - p))))
    return out


def iv_at_rate(iv, S, K, T, carry, rate, is_call):
    """IV del proveedor (invertida con `carry`) expresada a la tasa `rate`."""
    return bs_implied_vol(bs_price(S, K, T, carry, iv, is_call), S, K, T, rate, is_call)
