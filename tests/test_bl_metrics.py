import numpy as np
import pandas as pd
import pytest

import bl_metrics as bm
import risk_estimators as rk


# ------------------------------------------------------------------------------
# M-11 unidades: anual -> horizonte, y el fallback de MFIV
# ------------------------------------------------------------------------------

def test_vol_annual_scales_with_sqrt_horizon():
    assert bm.vol_annual_to_horizon(0.20, 1.0) == pytest.approx(0.20)
    assert bm.vol_annual_to_horizon(0.30, 4 / 12) == pytest.approx(0.30 * np.sqrt(4 / 12))


def test_variance_annual_matches_implied_variance_helper():
    var_h = bm.variance_annual_to_horizon(0.09, 4 / 12)
    via_rk = rk.implied_variance_to_horizon(0.09, dte=365, horizon_years=4 / 12)["horizon_var"]
    assert var_h == pytest.approx(0.09 * (4 / 12))
    assert var_h == pytest.approx(via_rk)


def test_ssvi_and_hist_fallback_share_horizon_units():
    # SSVI anual 30%. Historico ya al horizonte: no es la vol anual.
    anual = 0.30
    h = 4 / 12
    var_hist = (anual * np.sqrt(h)) ** 2
    desde_ssvi = bm.iv_vol_at_horizon(anual, var_hist, h)
    desde_hist = bm.iv_vol_at_horizon(np.nan, var_hist, h)
    assert desde_ssvi == pytest.approx(desde_hist)
    assert desde_ssvi == pytest.approx(anual * np.sqrt(h))


def test_mfiv_fallback_uses_horizon_variance_not_annual():
    anual = 0.30
    h = 4 / 12
    var_anual = anual ** 2
    var_h = bm.variance_annual_to_horizon(var_anual, h)
    # El bug: inyectar var_anual (~3x) donde MFIV es la varianza del horizonte.
    assert bm.mfiv_or_horizon_variance(np.nan, var_h) == pytest.approx(var_h)
    assert bm.mfiv_or_horizon_variance(np.nan, var_h) == pytest.approx(var_anual * h)
    assert bm.mfiv_or_horizon_variance(np.nan, var_h) != pytest.approx(var_anual)
    assert bm.mfiv_or_horizon_variance(0.021, var_h) == pytest.approx(0.021)
    assert np.isnan(bm.mfiv_or_horizon_variance(np.nan, np.nan))


# ------------------------------------------------------------------------------
# M-12 delta de mercado
# ------------------------------------------------------------------------------

def test_delta_historical_is_excess_over_variance():
    delta, info = bm.market_delta("historical", excess_hist=0.02, var_hist=0.01)
    assert delta == pytest.approx(2.0)
    assert info["mode"] == "historical"
    assert info["fallback"] is None


def test_delta_historical_can_be_negative():
    delta, info = bm.market_delta("historical", excess_hist=-0.01, var_hist=0.02)
    assert delta == pytest.approx(-0.5)
    assert info["historical"] == pytest.approx(-0.5)


def test_delta_fixed_ignores_the_sample():
    delta, info = bm.market_delta(
        "fixed", excess_hist=-0.05, var_hist=0.01, delta_fixed=2.5,
        var_q=0.04, var_p=0.02)
    assert delta == pytest.approx(2.5)
    assert info["mode"] == "fixed"
    assert info["historical"] == pytest.approx(-5.0)
    assert info["implied"] == pytest.approx(2.0)


def test_delta_implied_is_market_variance_ratio():
    # Martin: exceso implicito = var_Q. delta = var_Q / var_P.
    delta, info = bm.market_delta(
        "implied", excess_hist=0.08, var_hist=0.02, var_q=0.03, var_p=0.02)
    assert delta == pytest.approx(1.5)
    assert info["mode"] == "implied"
    assert info["historical"] == pytest.approx(4.0)


def test_delta_implied_falls_back_when_physical_variance_missing():
    delta, info = bm.market_delta(
        "implied", excess_hist=0.02, var_hist=0.01, var_q=0.03, var_p=0.0)
    assert delta == pytest.approx(2.0)
    assert info["mode"] == "historical"
    assert info["fallback"]


def test_delta_rejects_unknown_mode_and_nonpositive_fixed():
    with pytest.raises(ValueError):
        bm.market_delta("both", excess_hist=0.01, var_hist=0.01)
    with pytest.raises(ValueError):
        bm.market_delta("fixed", excess_hist=0.01, var_hist=0.01, delta_fixed=0.0)


# ------------------------------------------------------------------------------
# B-1 drawdown de log-retornos
# ------------------------------------------------------------------------------

def test_mdd_log_matches_exp_cumsum_not_simple_compounding():
    r = pd.Series([0.10, -0.50, 0.20])
    wealth = np.exp(np.cumsum(r.to_numpy()))
    esperado = float(((wealth - np.maximum.accumulate(wealth)) / np.maximum.accumulate(wealth)).min())
    assert bm.mdd_from_log_returns(r) == pytest.approx(esperado)
    assert bm.mdd_from_log_returns(r) == pytest.approx(rk.max_drawdown(r, log_returns=True))

    simple = (1.0 + r).cumprod()
    dd_simple = float(((simple - simple.cummax()) / simple.cummax()).min())
    assert bm.mdd_from_log_returns(r) != pytest.approx(dd_simple)


def test_log_portfolio_return_is_not_the_weighted_sum_of_logs():
    r1, r2 = np.log(1.20), np.log(0.80)
    exacto = bm.log_portfolio_return(pd.Series({"A": r1, "B": r2}), pd.Series({"A": 0.5, "B": 0.5}))
    suma_logs = 0.5 * r1 + 0.5 * r2
    assert exacto == pytest.approx(np.log(0.5 * 1.20 + 0.5 * 0.80))
    assert exacto != pytest.approx(suma_logs)


def test_fit_ssvi_is_deterministic_and_ignores_row_order():
    theta = np.array([0.04, 0.06])
    rho, eta, gamma = -0.35, 0.80, 0.40
    filas = []
    for sl, th in enumerate(theta):
        k = np.linspace(-0.4, 0.4, 12)
        w = bm.ssvi_total_variance(k, th, rho, eta, gamma)
        filas.append(pd.DataFrame({"k": k, "w": w, "slice": sl, "theta": th}))
    datos = pd.concat(filas, ignore_index=True)
    revuelto = datos.sample(frac=1.0, random_state=1)
    a = bm.fit_ssvi(datos["k"], datos["w"], datos["theta"], theta, datos["slice"])
    b = bm.fit_ssvi(revuelto["k"], revuelto["w"], revuelto["theta"], theta, revuelto["slice"])
    assert a["aceptado"] and b["aceptado"]
    assert a["metodo"] == "ssvi_conjunto"
    assert a["rho"] == pytest.approx(b["rho"], abs=1e-6)
    assert a["eta"] == pytest.approx(b["eta"], abs=1e-6)
    assert a["gamma"] == pytest.approx(b["gamma"], abs=1e-6)
    assert a["rho"] == pytest.approx(rho, abs=0.05)
    assert a["k_min"] == pytest.approx(-0.4) and a["k_max"] == pytest.approx(0.4)


def test_fit_ssvi_rejects_a_surface_the_residual_cannot_explain():
    k = np.linspace(-0.5, 0.5, 30)
    w = np.full_like(k, 0.04)
    w[::2] = 0.20
    ajuste = bm.fit_ssvi(k, w, np.full(len(k), 0.04), np.array([0.04]), np.zeros(len(k)))
    assert not ajuste["aceptado"]
    assert ajuste["metodo"] == "ssvi_rechazado"


def test_integration_stays_inside_three_sigma_and_the_observed_wing():
    lo6, hi6 = bm.integration_strike_bounds(100.0, 0.40, 4 / 12, n_std=6)
    lo3, hi3 = bm.integration_strike_bounds(100.0, 0.40, 4 / 12, n_std=3)
    assert lo3 > lo6 and hi3 < hi6
    lo, hi = bm.integration_strike_bounds(100.0, 0.40, 4 / 12, n_std=6, k_min=-0.25, k_max=0.20)
    assert lo == pytest.approx(100.0 * np.exp(-0.25))
    assert hi == pytest.approx(100.0 * np.exp(0.20))


def test_mfiv_far_above_atm_falls_back_to_atm_variance():
    # META en la corrida real: MFIV SSVI ~0.22 contra ~0.05 de la cadena.
    fuera = bm.mfiv_vs_atm(0.2202, 0.050)
    assert not fuera["ok"] and fuera["motivo"] == "mfiv_fuera_de_banda"
    assert fuera["mfiv"] == pytest.approx(0.050)
    assert fuera["mfis"] == 0.0 and fuera["mfik"] == 3.0
    dentro = bm.mfiv_vs_atm(0.060, 0.050)
    assert dentro["ok"] and dentro["mfiv"] == pytest.approx(0.060)


def test_log_portfolio_return_renormalizes_missing_names():
    r = pd.Series({"A": np.log(1.10), "B": np.nan})
    w = pd.Series({"A": 0.25, "B": 0.75})
    assert bm.log_portfolio_return(r, w) == pytest.approx(np.log(1.10))
    assert np.isnan(bm.log_portfolio_return(pd.Series({"A": np.nan}), pd.Series({"A": 1.0})))
