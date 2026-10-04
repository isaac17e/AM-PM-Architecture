import numpy as np
import pandas as pd
import pytest
from scipy import integrate, stats
from scipy.stats import norm

import risk_estimators as rk


# ------------------------------------------------------------------------------
# 0. Compatibilidad numerica
# ------------------------------------------------------------------------------

def test_trapezoid_compat_matches_numpy():
    x = np.linspace(0.0, 2.0, 11)
    y = x ** 2
    esperado = np.trapezoid(y, x) if hasattr(np, "trapezoid") else np.trapz(y, x)
    assert rk.trapezoid(y, x) == pytest.approx(esperado)
    assert rk.trapezoid(y, x) == pytest.approx(8.0 / 3.0, rel=2e-2)


# ------------------------------------------------------------------------------
# 1. EWMA + Ledoit-Wolf
# ------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def retornos():
    rng = np.random.default_rng(42)
    n, T = 8, 300
    L = rng.normal(size=(n, n))
    C = L @ L.T / n + np.eye(n) * 0.5
    return rng.multivariate_normal(np.zeros(n), C, size=T) * 0.01


def _lw_constant_correlation_referencia(X):
    """Implementacion independiente, con bucles, de Ledoit & Wolf (2003)."""
    T, n = X.shape
    Xc = X - X.mean(axis=0)
    S = Xc.T @ Xc / T
    sd = np.sqrt(np.diag(S))
    rbar = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            rbar += S[i, j] / (sd[i] * sd[j])
    rbar = rbar * 2.0 / (n * (n - 1))

    F = np.empty((n, n))
    for i in range(n):
        for j in range(n):
            F[i, j] = S[i, i] if i == j else rbar * sd[i] * sd[j]

    pi = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            pi[i, j] = np.mean((Xc[:, i] * Xc[:, j] - S[i, j]) ** 2)
    pi_hat = pi.sum()

    rho_hat = np.trace(pi)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            th_ii = np.mean((Xc[:, i] ** 2 - S[i, i]) * (Xc[:, i] * Xc[:, j] - S[i, j]))
            th_jj = np.mean((Xc[:, j] ** 2 - S[j, j]) * (Xc[:, i] * Xc[:, j] - S[i, j]))
            rho_hat += (rbar / 2.0) * (np.sqrt(S[j, j] / S[i, i]) * th_ii
                                       + np.sqrt(S[i, i] / S[j, j]) * th_jj)

    gamma_hat = np.sum((F - S) ** 2)
    delta = max(0.0, min(1.0, (pi_hat - rho_hat) / gamma_hat / T))
    return delta * F + (1 - delta) * S, delta, F


def test_ewma_weights_sum_to_one_and_reduce_to_equal():
    w = rk.ewma_weights(100, 20)
    assert w.sum() == pytest.approx(1.0)
    assert w[-1] > w[0]
    assert np.allclose(rk.ewma_weights(10, None), 0.1)
    assert rk.effective_sample_size(rk.ewma_weights(10, None)) == pytest.approx(10.0)
    assert rk.effective_sample_size(w) < 100


def test_ledoit_wolf_matches_independent_reference(retornos):
    S_ref, delta_ref, F_ref = _lw_constant_correlation_referencia(retornos)
    S_mod, delta_mod, F_mod = rk.ledoit_wolf_constant_correlation(retornos)
    assert delta_mod == pytest.approx(delta_ref, rel=1e-10)
    assert np.allclose(F_mod, F_ref, rtol=1e-10, atol=1e-14)
    assert np.allclose(S_mod, S_ref, rtol=1e-10, atol=1e-14)
    assert 0.0 < delta_mod < 1.0


def test_ledoit_wolf_standard_case_regression(retornos):
    # Valor obtenido con el modulo antes del cambio de gamma (B-7): el caso
    # S=None no debe moverse ni en ruido numerico.
    _, delta, _ = rk.ledoit_wolf_constant_correlation(retornos)
    assert delta == pytest.approx(0.09860432701604373, abs=1e-12)


def test_ledoit_wolf_ewma_target_is_built_from_shrunk_matrix(retornos):
    cov_e, w = rk.ewma_cov(retornos, halflife=60)
    S_shr, delta, F = rk.ledoit_wolf_constant_correlation(
        retornos, S=cov_e, t_eff=rk.effective_sample_size(w))
    assert 0.0 <= delta <= 1.0
    # F conserva las varianzas de la matriz que se encoge (EWMA), no las muestrales
    assert np.allclose(np.diag(F), np.diag(cov_e))
    assert F[0, 1] == pytest.approx(rk.average_correlation(cov_e) * np.sqrt(cov_e[0, 0] * cov_e[1, 1]))
    # S_shrunk es la combinacion convexa exacta con la misma F y delta
    assert np.allclose(S_shr, delta * F + (1 - delta) * cov_e)


def test_cov_ewma_shrunk_pipeline(retornos):
    cov, info = rk.cov_ewma_shrunk(retornos, halflife=60, scale=5.0)
    assert cov.shape == (8, 8)
    assert info["method"] == "ewma+lw"
    assert 0 < info["delta"] < 1
    assert info["t_eff"] < info["n_obs"]
    vals = np.linalg.eigvalsh(cov)
    assert vals.min() > 0
    cov_sin_escala, _ = rk.cov_ewma_shrunk(retornos, halflife=60, scale=1.0)
    assert np.allclose(cov, 5.0 * cov_sin_escala)


def test_nearest_psd_repairs_negative_eigenvalue():
    A = np.array([[1.0, 0.99, 0.0], [0.99, 1.0, 0.99], [0.0, 0.99, 1.0]])
    assert np.linalg.eigvalsh(A).min() < 0
    B = rk.nearest_psd(A)
    assert np.linalg.eigvalsh(B).min() >= 0
    assert np.allclose(B, B.T)


def test_seasonal_vol_ratio_scales_vol_and_keeps_correlation():
    rng = np.random.default_rng(7)
    idx = pd.date_range("2018-01-07", periods=420, freq="W")
    z = rng.multivariate_normal([0, 0], [[1, 0.6], [0.6, 1]], size=len(idx))
    octubre = idx.month == 10
    z[octubre, 0] *= 1.3                      # A mas volatil en octubre
    r = pd.DataFrame(z * 0.02, index=idx, columns=["A", "B"])
    r["C"] = np.nan
    r.loc[idx[octubre][:4], "C"] = 0.01       # C: pocas semanas en temporada

    ratio = rk.seasonal_vol_ratio(r, octubre, bounds=(0.70, 1.50), min_obs=10)
    esperado_a = r.loc[octubre, "A"].std() / r["A"].std()
    assert ratio["A"] == pytest.approx(esperado_a)
    assert ratio["A"] > 1.1
    assert ratio["C"] == 1.0

    S = r[["A", "B"]].cov().values
    S_est = S * np.outer(ratio[["A", "B"]], ratio[["A", "B"]])
    corr = lambda M: M[0, 1] / np.sqrt(M[0, 0] * M[1, 1])
    assert corr(S_est) == pytest.approx(corr(S))
    assert np.sqrt(S_est[0, 0]) == pytest.approx(np.sqrt(S[0, 0]) * ratio["A"])


def test_seasonal_vol_ratio_clips_to_bounds():
    idx = pd.date_range("2018-01-07", periods=300, freq="W")
    rng = np.random.default_rng(3)
    r = pd.DataFrame({"A": rng.normal(0, 0.01, len(idx))}, index=idx)
    temporada = idx.month == 10
    r.loc[temporada, "A"] *= 10
    assert rk.seasonal_vol_ratio(r, temporada, bounds=(0.70, 1.50))["A"] == pytest.approx(1.50)
    with pytest.raises(ValueError):
        rk.seasonal_vol_ratio(r, temporada[:-1])


# ------------------------------------------------------------------------------
# 2. Q -> P
# ------------------------------------------------------------------------------

def test_q_to_p_vol_bounds_and_fallback():
    sigma_p, ratio = rk.q_to_p_vol(0.30, 0.20)
    assert ratio == pytest.approx(0.70)          # 0.2/0.3 < lo -> cota inferior
    assert sigma_p == pytest.approx(0.21)
    sigma_p, ratio = rk.q_to_p_vol(0.30, 0.40)
    assert ratio == pytest.approx(1.0)           # P no excede a Q por defecto
    sigma_p, ratio = rk.q_to_p_vol(0.30, np.nan)
    assert ratio == pytest.approx(0.90) and sigma_p == pytest.approx(0.27)
    arr, _ = rk.q_to_p_vol(np.array([0.3, np.nan]), np.array([0.27, 0.22]))
    assert arr[0] == pytest.approx(0.27) and arr[1] == pytest.approx(0.22)


def test_q_to_p_correlation_clips():
    rho_p, ratio = rk.q_to_p_correlation(0.6, 0.3)
    assert ratio == pytest.approx(0.6) and rho_p == pytest.approx(0.36)
    rho_p, ratio = rk.q_to_p_correlation(0.6, 0.9)
    assert ratio == pytest.approx(1.0) and rho_p == pytest.approx(0.6)


# ------------------------------------------------------------------------------
# 3. Panel y co-momentos
# ------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def panel():
    rng = np.random.default_rng(7)
    J, n = 2000, 5
    Z = rng.standard_t(df=5, size=(J, n))
    Z[:, 0] = -np.abs(Z[:, 0]) + 0.3 * Z[:, 1]   # asimetria negativa fuerte
    return Z


def test_portfolio_moments_match_direct_computation(panel):
    w = np.array([0.4, 0.2, 0.2, 0.1, 0.1])
    r = panel @ w
    m = rk.portfolio_moments(w, panel)
    assert m["mean"] == pytest.approx(r.mean())
    assert m["sd"] == pytest.approx(r.std(ddof=0))
    assert m["skew"] == pytest.approx(stats.skew(r, bias=True))
    assert m["exkurt"] == pytest.approx(stats.kurtosis(r, bias=True, fisher=True))


def test_portfolio_moment_gradients_vs_finite_differences(panel):
    w = np.array([0.3, 0.3, 0.2, 0.1, 0.1])
    g = rk.portfolio_moment_gradients(w, panel)
    h = 1e-6
    for clave, nombre in (("d_sd_dw", "sd"), ("d_skew_dw", "skew"), ("d_exkurt_dw", "exkurt")):
        fd = np.empty_like(w)
        for i in range(w.size):
            e = np.zeros_like(w)
            e[i] = h
            fd[i] = (rk.portfolio_moments(w + e, panel)[nombre]
                     - rk.portfolio_moments(w - e, panel)[nombre]) / (2 * h)
        assert np.allclose(g[clave], fd, rtol=1e-5, atol=1e-7), clave


def test_rescale_panel_preserves_standardized_moments(panel):
    Z, _ = rk.standardized_panel(panel)
    X = rk.rescale_panel(Z, mu_target=np.full(5, 0.01), sd_target=np.full(5, 0.05))
    assert np.allclose(X.mean(axis=0), 0.01)
    assert np.allclose(X.std(axis=0, ddof=1), 0.05)
    assert np.allclose(stats.skew(X, axis=0), stats.skew(Z, axis=0))
    assert np.allclose(np.corrcoef(X.T), np.corrcoef(Z.T))


# ------------------------------------------------------------------------------
# 4. Cornish-Fisher
# ------------------------------------------------------------------------------

def test_higher_moments_admissible_pearson():
    assert rk.higher_moments_admissible(0.0, 3.0)
    assert rk.higher_moments_admissible(-1.0, 2.0)          # K = 1 + S^2 justo
    assert not rk.higher_moments_admissible(-1.5, 3.0)      # 3 < 1 + 2.25
    assert not rk.higher_moments_admissible(0.0, 50.0, kurt_max=30.0)
    assert not rk.higher_moments_admissible(np.nan, 3.0)


@pytest.mark.parametrize("skew,exkurt", [(0.0, 0.0), (-0.5, 1.0), (-0.8, 2.0),
                                         (0.7, 3.0), (-1.2, 4.0), (-0.3, 0.5)])
def test_cornish_fisher_params_reproduce_target_moments(skew, exkurt):
    s, k, exacto = rk.cornish_fisher_params(skew, exkurt)
    assert exacto
    _, sk, ek = rk.cornish_fisher_moments(s, k)
    assert sk == pytest.approx(skew, abs=1e-3)
    assert ek == pytest.approx(exkurt, abs=1e-3)
    k_lo, k_hi = rk.cornish_fisher_domain(s)
    assert k_lo <= k <= k_hi                         # dentro del dominio monotono


def test_cornish_fisher_params_unreachable_returns_nearest():
    # Asimetria alta con exceso de curtosis casi nulo no es alcanzable por la familia
    s, k, exacto = rk.cornish_fisher_params(-2.0, 0.1)
    assert not exacto
    assert abs(s) < rk.CF_SKEW_PARAM_MAX
    assert np.isfinite(k)


@pytest.mark.parametrize("alpha,skew,exkurt", [(0.05, -0.8, 2.0), (0.01, -0.5, 1.0),
                                               (0.025, 0.6, 2.5), (0.05, 0.0, 0.0)])
def test_cornish_fisher_es_matches_numerical_integration(alpha, skew, exkurt):
    cola = rk.cornish_fisher_tail(alpha, skew, exkurt)
    s, k = cola["s"], cola["k"]
    sd = rk.cornish_fisher_moments(s, k)[0]
    z_a = norm.ppf(alpha)
    # Y = z_cf(Z)/sd es creciente en Z: el cuantil alpha es z_cf(z_alpha)/sd y
    # ES = E[Y | Z <= z_alpha] = (1/alpha) int_{-inf}^{z_alpha} z_cf(u)/sd phi(u) du
    assert cola["q"] == pytest.approx(float(rk.cornish_fisher_z(z_a, s, k)) / sd)
    es_num, _ = integrate.quad(lambda u: float(rk.cornish_fisher_z(u, s, k)) / sd * norm.pdf(u),
                               -np.inf, z_a)
    assert cola["es"] == pytest.approx(es_num / alpha, rel=1e-7, abs=1e-9)
    assert cola["es"] < cola["q"] < 0


def test_cornish_fisher_tail_known_value():
    # Valor de referencia verificado contra integracion numerica en la revision
    assert rk.cornish_fisher_tail(0.05, -0.8, 2.0)["es"] == pytest.approx(-2.5273, abs=5e-4)


def test_cornish_fisher_gaussian_limit():
    # La inversion numerica ajusta los momentos con tolerancia 1e-3, asi que el
    # limite gaussiano se recupera a ~1e-5 en el cuantil, no exactamente.
    cola = rk.cornish_fisher_tail(0.05, 0.0, 0.0)
    assert cola["q"] == pytest.approx(norm.ppf(0.05), abs=1e-4)
    assert cola["es"] == pytest.approx(-norm.pdf(norm.ppf(0.05)) / 0.05, abs=1e-4)
    out = rk.var_cvar_cornish_fisher(0.01, 0.05, 0.0, 0.0, confidence=0.95)
    assert out["var"] == pytest.approx(out["var_gaussian"], abs=1e-5)
    assert out["cvar"] == pytest.approx(out["cvar_gaussian"], abs=1e-5)


def test_cornish_fisher_es_monotone_in_moments():
    es = lambda s, k: rk.cornish_fisher_tail(0.01, s, k)["es"]
    assert es(-1.0, 3.0) < es(-0.5, 3.0) < es(0.0, 3.0)     # mas asimetria negativa -> peor cola
    assert es(-0.5, 5.0) < es(-0.5, 2.0) < es(-0.5, 0.5)     # mas curtosis -> peor cola al 1%


def test_cornish_fisher_es_gradient_vs_finite_differences():
    es, d_s, d_k = rk.cornish_fisher_es_gradient(0.05, -0.6, 1.5)
    h = 1e-3
    fd_s = (rk.cornish_fisher_tail(0.05, -0.6 + h, 1.5)["es"]
            - rk.cornish_fisher_tail(0.05, -0.6 - h, 1.5)["es"]) / (2 * h)
    fd_k = (rk.cornish_fisher_tail(0.05, -0.6, 1.5 + h)["es"]
            - rk.cornish_fisher_tail(0.05, -0.6, 1.5 - h)["es"]) / (2 * h)
    assert d_s == pytest.approx(fd_s, rel=1e-3)
    assert d_k == pytest.approx(fd_k, rel=1e-3)
    assert d_s > 0 and d_k < 0


def test_var_cvar_cornish_fisher_nan_moments():
    out = rk.var_cvar_cornish_fisher(0.0, 0.05, np.nan, 1.0)
    assert np.isnan(out["var"]) and np.isnan(out["cvar"]) and not out["exact"]
    assert np.isfinite(out["var_gaussian"])


# ------------------------------------------------------------------------------
# 6. Escalado temporal
# ------------------------------------------------------------------------------

def test_to_years_forms():
    assert rk.to_years(dte=30) == pytest.approx(30 / 365)
    assert rk.to_years(dte=30, days_per_year=360) == pytest.approx(30 / 360)
    assert rk.to_years(trading_days=21) == pytest.approx(21 / 252)
    assert rk.to_years(weeks=52) == pytest.approx(1.0)
    assert rk.to_years(months=3) == pytest.approx(0.25)
    assert rk.to_years(periods=5, periods_per_year=52) == pytest.approx(5 / 52)
    arr = rk.to_years(dte=np.array([30, 60]))
    assert np.allclose(arr, [30 / 365, 60 / 365])


@pytest.mark.parametrize("kwargs", [dict(), dict(dte=30, months=1), dict(periods=5),
                                    dict(dte=0), dict(months=-1), dict(dte=np.nan)])
def test_to_years_invalid(kwargs):
    with pytest.raises(ValueError):
        rk.to_years(**kwargs)


def test_scale_moments_identity_and_basic_rules():
    out = rk.scale_moments(0.25, 0.25, mu=0.01, var=0.04, sd=0.2, skew=-0.5, exkurt=2.0)
    assert out["h"] == pytest.approx(1.0)
    assert out["mu"] == 0.01 and out["var"] == 0.04 and out["sd"] == 0.2
    assert out["skew"] == -0.5 and out["exkurt"] == 2.0

    out = rk.scale_moments(rk.to_years(months=1), 1.0, mu=0.01, var=0.0025, sd=0.05)
    assert out["h"] == pytest.approx(12.0)
    assert out["mu"] == pytest.approx(0.12)
    assert out["var"] == pytest.approx(0.03)
    assert out["sd"] == pytest.approx(0.05 * np.sqrt(12))
    assert out["sd"] ** 2 == pytest.approx(out["var"])
    assert set(out) == {"h", "mu", "var", "sd"}


def test_scale_moments_iid_skew_kurt_exact_for_gamma_sums():
    # Suma de h variables Gamma(a) iid es Gamma(h a): sus momentos estandarizados
    # son exactamente S/sqrt(h) y K/h. Verifica la regla iid sin Monte Carlo.
    a, h = 2.0, 4.33
    _, _, S1, K1 = stats.gamma.stats(a, moments="mvsk")
    _, _, Sh, Kh = stats.gamma.stats(a * h, moments="mvsk")
    out = rk.scale_moments(1.0, h, skew=float(S1), exkurt=float(K1))
    assert out["skew"] == pytest.approx(float(Sh))
    assert out["exkurt"] == pytest.approx(float(Kh))


def test_scale_moments_weekly_to_month_arrays():
    S = np.array([-0.8, 0.2])
    K = np.array([3.0, 1.0])
    out = rk.scale_moments(rk.to_years(weeks=1), rk.to_years(weeks=4.33), skew=S, exkurt=K)
    assert np.allclose(out["skew"], S / np.sqrt(4.33))
    assert np.allclose(out["exkurt"], K / 4.33)


def test_annualize_shortcut():
    assert rk.annualize(rk.to_years(weeks=1), sd=0.02)["sd"] == pytest.approx(0.02 * np.sqrt(52))


def test_implied_variance_to_horizon_uses_real_dte():
    mfiv = 0.0036                     # varianza integrada sobre 30 dias (vol anual ~20.9%)
    out = rk.implied_variance_to_horizon(mfiv, dte=30, horizon_years=3 / 12)
    assert out["years_chain"] == pytest.approx(30 / 365)
    assert out["annual_var"] == pytest.approx(mfiv * 365 / 30)
    assert out["annual_vol"] == pytest.approx(np.sqrt(mfiv * 365 / 30))
    assert out["horizon_var"] == pytest.approx(mfiv * (3 / 12) / (30 / 365))
    assert out["horizon_vol"] ** 2 == pytest.approx(out["horizon_var"])
    # A-3: dividir por el horizonte (3 meses) en lugar del DTE real subestima la vol anual
    vol_erronea = np.sqrt(mfiv / (3 / 12))
    assert vol_erronea / out["annual_vol"] == pytest.approx(np.sqrt(30 / (365 * 3 / 12)))


def test_implied_variance_to_horizon_arrays_and_nan():
    out = rk.implied_variance_to_horizon(np.array([0.0036, np.nan, 0.01]),
                                         dte=np.array([30, 30, 0]), horizon_years=1 / 12)
    assert np.isfinite(out["annual_vol"][0])
    assert np.isnan(out["annual_vol"][1]) and np.isnan(out["horizon_vol"][2])


def test_scale_moments_weekly_skew_to_optimizer_horizon():
    """A-4: asimetria y exceso de curtosis semanales al horizonte de 13 semanas."""
    semanas = 13
    out = rk.scale_moments(rk.to_years(weeks=1), rk.to_years(weeks=semanas),
                           skew=-0.8, exkurt=3.0)
    assert out["h"] == pytest.approx(semanas)
    assert out["skew"] == pytest.approx(-0.8 / np.sqrt(semanas))
    assert out["exkurt"] == pytest.approx(3.0 / semanas)
    assert abs(out["skew"]) < 0.8 and out["exkurt"] < 3.0


# ------------------------------------------------------------------------------
# 7. Drawdown y log-retorno del portafolio (B-1, B-2)
# ------------------------------------------------------------------------------

def test_max_drawdown_log_returns_known_path():
    # Riqueza 1 -> e^0.5 -> e^{-0.5}. Pico e^0.5, dd = e^{-1} - 1.
    assert rk.max_drawdown([0.5, -1.0], log_returns=True) == pytest.approx(np.exp(-1.0) - 1.0)


def test_max_drawdown_simple_returns_known_path():
    # 1 -> 1.5 -> 0.75. dd = (0.75 - 1.5) / 1.5 = -0.5.
    assert rk.max_drawdown([0.5, -0.5], log_returns=False) == pytest.approx(-0.5)


def test_max_drawdown_log_and_simple_differ():
    r = [0.20, -0.30, 0.10]
    assert rk.max_drawdown(r, log_returns=True) != pytest.approx(
        rk.max_drawdown(r, log_returns=False))


def test_max_drawdown_monotone_is_zero_and_short_series_is_nan():
    assert rk.max_drawdown([0.01, 0.02, 0.01]) == pytest.approx(0.0)
    assert np.isnan(rk.max_drawdown([0.01]))
    assert np.isnan(rk.max_drawdown([np.nan, np.nan]))


def test_portfolio_log_returns_matches_asset_when_assets_are_equal():
    X = np.array([[0.10, 0.10], [-0.20, -0.20]])
    out = rk.portfolio_log_returns(X, np.array([0.4, 0.6]))
    assert out == pytest.approx(X[:, 0])


def test_portfolio_log_returns_is_not_the_weighted_sum_of_logs():
    X = np.array([[0.50, -0.40]])
    w = np.array([0.5, 0.5])
    exacto = rk.portfolio_log_returns(X, w)
    assert exacto[0] != pytest.approx((X @ w)[0])
    assert exacto[0] == pytest.approx(np.log1p((np.expm1(X) @ w)[0]))


def test_portfolio_log_returns_cash_earns_zero():
    X = np.array([[0.10, 0.10]])
    pleno = rk.portfolio_log_returns(X, np.array([0.5, 0.5]))
    mitad = rk.portfolio_log_returns(X, np.array([0.25, 0.25]))
    assert pleno[0] == pytest.approx(0.10)
    assert mitad[0] == pytest.approx(np.log1p(0.5 * np.expm1(0.10)))


def test_mfik_cap_tenor_loosens_a_short_chain():
    assert rk.mfik_cap_tenor(5, 30) == pytest.approx(20.0)
    assert rk.mfik_cap_tenor(5, 15) == pytest.approx(3.0 + 17.0 * 2.0)
    assert rk.mfik_cap_tenor(5, 15) > rk.mfik_cap_tenor(5, 30)
    assert rk.mfik_cap_tenor(5, 50) < rk.mfik_cap_tenor(5, 30)


def test_scale_bkm_moments_from_15_to_30_days():
    out = rk.scale_bkm_moments(0.02, 2.0, 11.0, 15, 30)
    assert out["h"] == pytest.approx(2.0)
    assert out["mfiv"] == pytest.approx(0.04)
    assert out["mfis"] == pytest.approx(2.0 / np.sqrt(2.0))
    assert out["mfik"] == pytest.approx(3.0 + 8.0 / 2.0)


def test_mfik_cap_rises_with_chain_depth():
    assert rk.mfik_cap(5) == pytest.approx(20.0)
    assert rk.mfik_cap(8) == pytest.approx(20.0)
    assert rk.mfik_cap(60) == pytest.approx(80.0)
    assert rk.mfik_cap(90) == pytest.approx(80.0)
    medio = rk.mfik_cap(40)
    assert 20 < medio < 80
    # SPY 21.5 y BRK-B 48 entran con cadena densa y no con cinco strikes.
    assert rk.higher_moments_admissible(0.0, 21.5, rk.mfik_cap(40))
    assert rk.higher_moments_admissible(0.0, 48.2, rk.mfik_cap(40))
    assert not rk.higher_moments_admissible(0.0, 21.5, rk.mfik_cap(5))
    assert not rk.higher_moments_admissible(0.0, 90.0, rk.mfik_cap(80))


def test_portfolio_log_returns_dataframe_reindexes_weights():
    df = pd.DataFrame({"A": [0.10, -0.05], "B": [0.0, 0.20]})
    w = pd.Series({"B": 0.30, "A": 0.70})
    out = rk.portfolio_log_returns(df, w)
    assert isinstance(out, pd.Series)
    assert list(out.index) == [0, 1]
    manual = np.log1p(np.expm1(df.values) @ np.array([0.70, 0.30]))
    assert out.to_numpy() == pytest.approx(manual)
