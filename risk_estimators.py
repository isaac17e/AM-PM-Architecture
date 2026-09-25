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
#
# Todo es forma cerrada salvo la inversion momentos -> parametros de
# Cornish-Fisher, un ajuste 2x2 con scipy.optimize.least_squares.
# ==============================================================================

import numpy as np
import pandas as pd
from scipy.stats import norm

__all__ = [
    "ewma_weights",
    "effective_sample_size",
    "ewma_cov",
    "average_correlation",
    "ledoit_wolf_constant_correlation",
    "cov_ewma_shrunk",
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
]


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


def ledoit_wolf_constant_correlation(returns, S=None, t_eff=None):
    """Intensidad de shrinkage optima hacia el objetivo de correlacion constante.

    Ledoit & Wolf (2003), "Honey, I Shrunk the Sample Covariance Matrix".
    El objetivo F tiene las varianzas muestrales en la diagonal y, fuera de
    ella, la correlacion promedio reescalada: f_ij = rbar * sqrt(s_ii * s_jj).

    delta* = max(0, min(1, (pi - rho) / gamma / T))

    Parametros
    ----------
    returns : (T, n) retornos. Se usan para los momentos de orden 4 que
        entran en pi y rho; no se les aplican pesos EWMA porque la formula de
        Ledoit-Wolf supone muestreo iid.
    S : covarianza a encoger. Si es None se usa la muestral (MLE, divide por T).
        Pasar aqui la matriz EWMA es la combinacion recomendada.
    t_eff : tamano de muestra a usar en delta. Si se encogio una matriz EWMA,
        pasar effective_sample_size(w); si es None se usa T.

    Devuelve (S_shrunk, delta, F).
    """
    X = np.asarray(returns, dtype=float)
    T, n = X.shape
    Xc = X - X.mean(axis=0)

    S_sample = (Xc.T @ Xc) / T
    if S is None:
        S = S_sample
    S = np.asarray(S, dtype=float)

    if n < 2 or T < 4:
        return S, 0.0, S

    var = np.clip(np.diag(S), 1e-300, None)
    sd = np.sqrt(var)
    rbar = average_correlation(S)

    # Objetivo F: correlacion constante
    F = rbar * np.outer(sd, sd)
    np.fill_diagonal(F, var)

    # pi_ij = (1/T) sum_t (x_ti x_tj - s_ij)^2
    Y = Xc ** 2
    pi_mat = (Y.T @ Y) / T - S_sample ** 2
    pi_hat = float(pi_mat.sum())

    # theta_ii,ij = (1/T) sum_t (x_ti^2 - s_ii)(x_ti x_tj - s_ij)
    #             = (1/T) sum_t x_ti^3 x_tj - s_ii * s_ij
    cube = (Xc ** 3).T @ Xc / T
    var_s = np.diag(S_sample)
    theta_ii = cube - var_s[:, None] * S_sample
    theta_jj = cube.T - var_s[None, :] * S_sample

    sd_s = np.sqrt(np.clip(var_s, 1e-300, None))
    ratio = np.outer(sd_s, 1.0 / sd_s)          # sqrt(s_ii / s_jj)
    rho_off = (rbar / 2.0) * ((1.0 / ratio) * theta_ii + ratio * theta_jj)
    np.fill_diagonal(rho_off, 0.0)
    rho_hat = float(np.trace(pi_mat) + rho_off.sum())

    gamma_hat = float(np.sum((F - S_sample) ** 2))

    if gamma_hat <= 0 or not np.isfinite(gamma_hat):
        return S, 0.0, F

    T_use = float(t_eff) if (t_eff is not None and t_eff > 1) else float(T)
    delta = (pi_hat - rho_hat) / gamma_hat / T_use
    delta = float(min(1.0, max(0.0, delta)))

    S_shrunk = delta * F + (1.0 - delta) * S
    S_shrunk = (S_shrunk + S_shrunk.T) / 2.0
    return S_shrunk, delta, F


def cov_ewma_shrunk(returns, halflife=None, scale=1.0, demean=True,
                    shrink=True, min_obs=60):
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

    Devuelve (cov, info) donde info trae delta, t_eff y n_obs.
    """
    if isinstance(returns, pd.DataFrame):
        cols = list(returns.columns)
        X = returns.dropna().values
    else:
        cols = None
        X = np.asarray(returns, dtype=float)
        X = X[np.isfinite(X).all(axis=1)]

    T = X.shape[0]
    info = {"n_obs": T, "delta": 0.0, "t_eff": float(T), "halflife": halflife,
            "method": "ewma+lw"}

    if T < max(min_obs, 4):
        cov = np.cov(X, rowvar=False, ddof=1) if T > 1 else np.zeros((X.shape[1],) * 2)
        info["method"] = "muestral (pocas observaciones)"
        cov = np.atleast_2d(cov) * scale
        return (pd.DataFrame(cov, index=cols, columns=cols) if cols else cov), info

    cov, w = ewma_cov(X, halflife=halflife, demean=demean)
    info["t_eff"] = effective_sample_size(w)

    if shrink:
        cov, delta, _ = ledoit_wolf_constant_correlation(X, S=cov, t_eff=info["t_eff"])
        info["delta"] = delta
    else:
        info["method"] = "ewma"

    cov = cov * scale
    if cols:
        cov = pd.DataFrame(cov, index=cols, columns=cols)
    return cov, info


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
