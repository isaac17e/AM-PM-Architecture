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


def test_fit_ssvi_drops_deep_wings_that_dominate_the_error():
    theta = np.array([0.04])
    rho, eta, gamma = -0.40, 0.70, 0.40
    k_core = np.linspace(-0.45, 0.45, 16)
    w_core = bm.ssvi_total_variance(k_core, 0.04, rho, eta, gamma)
    k_wing = np.array([-5.0, -4.0, -3.0, 3.5, 4.5])
    w_wing = np.full(len(k_wing), 2.0)
    k = np.concatenate([k_core, k_wing])
    w = np.concatenate([w_core, w_wing])
    th = np.full(len(k), 0.04)
    sl = np.zeros(len(k))
    completo = bm.fit_ssvi(k, w, th, theta, sl, k_abs_max=None)
    ventana = bm.fit_ssvi(k, w, th, theta, sl, k_abs_max=0.5)
    assert not completo["aceptado"]
    assert ventana["aceptado"]
    assert ventana["n_strikes"] == len(k_core)
    assert ventana["k_min"] == pytest.approx(-0.45)
    assert ventana["k_max"] == pytest.approx(0.45)
    assert ventana["rmse_rel"] < completo["rmse_rel"]
    assert ventana["rho"] == pytest.approx(rho, abs=0.08)


def test_ssvi_weights_downweight_the_wing_and_keep_missing_oi():
    k = np.array([0.0, -5.0])
    w = np.array([0.04, 0.04])
    pesos = bm.ssvi_weights(k, w, open_interest=[100.0, np.nan])
    assert pesos[0] > pesos[1] * 10
    assert pesos[1] > 0


def test_ssvi_row_mask_drops_dead_quotes_and_known_zero_oi():
    mask = bm.ssvi_row_mask(precio=[1.0, 0.0, np.nan], open_interest=[10, np.nan, 0])
    assert list(mask) == [True, False, False]


def test_ssvi_surface_keeps_atm_when_the_smile_is_rejected():
    rechazado = bm.ssvi_surface_decision({"aceptado": False}, 0.28)
    assert rechazado["fuente"] == "atm" and not rechazado["usar_alas"]
    assert rechazado["sigma_atm_annual"] == pytest.approx(0.28)
    ok = bm.ssvi_surface_decision({"aceptado": True}, 0.22)
    assert ok["fuente"] == "ssvi" and ok["usar_alas"]
    historica = bm.ssvi_surface_decision({"aceptado": False}, np.nan)
    assert historica["fuente"] == "historica" and not np.isfinite(historica["sigma_atm_annual"])


def test_apply_vol_q_to_p_does_not_haircut_historical_vol():
    var_p = np.array([0.03, 0.3513 ** 2])
    mfiv = np.array([0.08, 0.4128 ** 2])
    out, n_clip = bm.apply_vol_q_to_p(var_p, mfiv, [True, False])
    assert out[1] == pytest.approx(mfiv[1])
    assert out[0] == pytest.approx(0.70 ** 2 * mfiv[0])
    assert n_clip == 1


def test_clip_negligible_weights_drops_solver_dust():
    out = bm.clip_negligible_weights(np.array([0.5, 0.5, 1e-6, 0.0]))
    assert out[2] == 0.0
    assert out.sum() == pytest.approx(1.0)
    assert out[0] == pytest.approx(0.5)


def test_fit_ssvi_rejects_a_surface_the_residual_cannot_explain():
    k = np.linspace(-0.5, 0.5, 30)
    w = np.full_like(k, 0.04)
    w[::2] = 0.20
    ajuste = bm.fit_ssvi(k, w, np.full(len(k), 0.04), np.array([0.04]), np.zeros(len(k)))
    assert not ajuste["aceptado"]
    assert ajuste["metodo"] == "ssvi_rechazado"


def test_integration_three_sigma_is_wider_than_the_fit_window():
    # 40% anual, horizonte de 4 meses: +/-3 sigma pasa de |k|=0.5.
    ala = 3.0 * 0.40 * np.sqrt(4 / 12)
    lo, hi = bm.integration_strike_bounds(100.0, 0.40, 4 / 12, n_std=3)
    assert np.log(hi / 100.0) == pytest.approx(ala)
    assert np.log(lo / 100.0) == pytest.approx(-ala)
    assert ala > 0.5
    lo_fit, hi_fit = bm.integration_strike_bounds(
        100.0, 0.40, 4 / 12, n_std=3, k_min=-0.5, k_max=0.5)
    assert np.log(hi_fit / 100.0) == pytest.approx(0.5)
    assert hi_fit < hi


def test_ssvi_rho_at_the_bound_falls_back_to_atm():
    ajuste = {"aceptado": True, "rho": 0.999, "k_min": -0.50, "k_max": 0.33,
              "metodo": "ssvi_conjunto"}
    decision = bm.ssvi_surface_decision(ajuste, 0.30, n_put=8, n_call=4)
    assert decision["fuente"] == "atm" and not decision["usar_alas"]
    assert "rho_en_cota" in decision["motivos"]
    assert decision["sigma_atm_annual"] == pytest.approx(0.30)


def test_ssvi_one_sided_coverage_falls_back_to_atm():
    ajuste = {"aceptado": True, "rho": -0.40, "k_min": -0.50, "k_max": 0.02}
    decision = bm.ssvi_surface_decision(ajuste, 0.25, n_put=10, n_call=1)
    assert decision["fuente"] == "atm"
    assert "sin_ala_call" in decision["motivos"]
    assert "pocas_calls" in decision["motivos"]
    sana = bm.ssvi_surface_decision(
        {"aceptado": True, "rho": -0.40, "k_min": -0.45, "k_max": 0.40},
        0.25, n_put=8, n_call=8)
    assert sana["fuente"] == "ssvi" and sana["usar_alas"]


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


# ------------------------------------------------------------------------------
# Ventana de vencimientos, higiene, perdida por plazo y fallback de momentos
# ------------------------------------------------------------------------------

def test_seleccionar_vencimientos_corta_leaps_y_guarda_un_minimo():
    dias = np.array([10, 40, 120, 240, 400, 800])
    mask = bm.seleccionar_vencimientos(dias, max_dias=243, min_keep=3)
    assert list(mask) == [True, True, True, True, False, False]
    # Un solo vencimiento dentro del tope: se completan los dos mas cortos de afuera.
    corto = bm.seleccionar_vencimientos(np.array([10, 400, 800]), 243, min_keep=3)
    assert list(corto) == [True, True, True]
    # Ya hay suficientes dentro del tope: el LEAP no entra.
    ya = bm.seleccionar_vencimientos(np.array([10, 20, 400]), 243, min_keep=2)
    assert list(ya) == [True, True, False]


def test_ssvi_row_mask_drops_cheap_premiums_and_thin_oi():
    mask = bm.ssvi_row_mask(
        precio=[0.05, 0.10, 1.0, np.nan],
        open_interest=[100, 9, 10, np.nan],
        precio_min=0.10, oi_min=10)
    assert list(mask) == [False, False, True, True]


def test_ssvi_monotone_mask_drops_the_less_liquid_violator():
    calls = bm.ssvi_monotone_mask(
        [100, 105, 110, 115], [5.0, 6.0, 3.0, 2.5], ["call"] * 4, [100, 100, 100, 100])
    assert list(calls) == [True, False, True, True]
    puts = bm.ssvi_monotone_mask(
        [100, 105, 110, 115], [1.0, 0.5, 2.0, 3.0], ["put"] * 4)
    assert list(puts) == [True, False, True, True]
    # El print del medio es el iliquido: se tira ese, no el ala.
    medio = bm.ssvi_monotone_mask(
        [100, 105, 110], [10.0, 1.0, 9.0], ["call"] * 3, [100, 1, 100])
    assert list(medio) == [True, False, True]


def test_fit_ssvi_normaliza_por_vencimiento_y_no_sigue_al_leap():
    rho, eta, gamma = -0.40, 0.55, 0.45
    k = np.linspace(-0.35, 0.35, 15)
    th_s, th_l = 0.02, 0.45
    w_s = bm.ssvi_total_variance(k, th_s, rho, eta, gamma)
    w_l = bm.ssvi_total_variance(k, th_l, 0.85, eta, gamma)
    k_all = np.concatenate([k, k])
    w_all = np.concatenate([w_s, w_l])
    th_row = np.concatenate([np.full(len(k), th_s), np.full(len(k), th_l)])
    sl = np.concatenate([np.zeros(len(k)), np.ones(len(k))])
    theta = np.array([th_s, th_l])
    crudo = bm.fit_ssvi(
        k_all, w_all, th_row, theta, sl, normalizar_vencimiento=False)
    norm = bm.fit_ssvi(
        k_all, w_all, th_row, theta, sl, normalizar_vencimiento=True)
    assert crudo["rho"] > 0.4
    assert norm["rho"] < crudo["rho"]
    assert abs(norm["rho"] - rho) < abs(crudo["rho"] - rho)


def test_momentos_fallback_historico_sector_y_neutro():
    hist = bm.momentos_fallback("historico", skew_hist=-0.40, kurt_hist=3.80)
    assert hist["fuente"] == "historico"
    assert hist["mfis"] == pytest.approx(-0.40)
    assert hist["mfik"] == pytest.approx(3.80)
    neutro = bm.momentos_fallback("neutro", skew_hist=-0.40, kurt_hist=3.80)
    assert neutro["fuente"] == "neutro"
    assert neutro["mfis"] == 0.0 and neutro["mfik"] == 3.0
    sector = bm.momentos_fallback(
        "sector", -0.20, 3.20, skew_sector=-0.55, kurt_sector=4.10)
    assert sector["fuente"] == "sector" and sector["mfis"] == pytest.approx(-0.55)
    sin_etf = bm.momentos_fallback("sector", -0.20, 3.20, skew_sector=np.nan, kurt_sector=np.nan)
    assert sin_etf["fuente"] == "historico"
    # Curtosis por debajo de 1 + skew^2 no es un par posible: ultimo recurso, neutro.
    roto = bm.momentos_fallback("historico", skew_hist=2.0, kurt_hist=3.0)
    assert roto["fuente"] == "neutro"
    with pytest.raises(ValueError):
        bm.momentos_fallback("otro", 0.0, 3.0)


def test_elegir_spot_momentos_usa_el_cierre_del_dia_o_la_cadena():
    mismo = bm.elegir_spot_momentos(100.0, "2026-10-02", "2026-10-02", spot_cadena=103.8)
    assert mismo["fuente"] == "cierre" and mismo["spot"] == pytest.approx(100.0)
    # La barra de hoy no esta (yfinance end-exclusivo, o el diario todavia no cerro).
    cadena = bm.elegir_spot_momentos(96.2, "2026-10-01", "2026-10-02", spot_cadena=100.0)
    assert cadena["fuente"] == "cadena" and cadena["spot"] == pytest.approx(100.0)
    previo = bm.elegir_spot_momentos(96.2, "2026-10-01", "2026-10-02", spot_cadena=np.nan)
    assert previo["fuente"] == "cierre_previo" and previo["spot"] == pytest.approx(96.2)


def _precios_con_paridad(f, k, t, r=0.02):
    """Call y put con la misma constante, para que call - put = e^{-rT}(F-K)."""
    disc = np.exp(-r * t)
    call = disc * np.maximum(f - k, 0.0) + 2.0
    put = disc * np.maximum(k - f, 0.0) + 2.0
    return call, put


def _cadena_ssvi(hoy, rho, eta, gamma, vol, dias_list, rho_por_dias=None, k_span=0.30):
    filas = []
    r = 0.02
    for dias in dias_list:
        t = dias / 365.0
        theta = vol ** 2 * t
        f = 100.0 * np.exp(r * t)
        rho_d = rho if rho_por_dias is None else rho_por_dias.get(dias, rho)
        for k in np.linspace(-k_span, k_span, 9):
            strike = float(f * np.exp(k))
            w = float(bm.ssvi_total_variance([k], theta, rho_d, eta, gamma)[0])
            iv = float(np.sqrt(max(w, 1e-12) / t))
            px_call, px_put = _precios_con_paridad(f, strike, t, r)
            base = dict(strike=strike, expiracion=hoy + pd.Timedelta(days=int(dias)),
                        iv=iv, oi=500.0, spot=100.0)
            filas.append({**base, "tipo": "call", "precio": float(px_call)})
            filas.append({**base, "tipo": "put", "precio": float(px_put)})
    return pd.DataFrame(filas)


def test_calibrar_superficie_ignora_leaps_y_quotes_rotos():
    hoy = pd.Timestamp("2026-10-02")
    rho, eta, gamma = -0.35, 0.50, 0.40
    cadena = _cadena_ssvi(
        hoy, rho, eta, gamma, vol=0.32,
        dias_list=(40, 90, 170, 700),
        rho_por_dias={700: 0.95})
    # Basura en el vencimiento de 90 dias: centavos, OI fino y un call que no es monotono.
    exp90 = hoy + pd.Timedelta(days=90)
    f90 = 100.0 * np.exp(0.02 * 90 / 365.0)
    cadena = pd.concat([
        cadena,
        pd.DataFrame([
            dict(strike=f90 * np.exp(-0.05), expiracion=exp90, tipo="put",
                 iv=3.5, precio=0.03, oi=400.0, spot=100.0),
            dict(strike=f90 * np.exp(0.05), expiracion=exp90, tipo="call",
                 iv=3.5, precio=1.50, oi=2.0, spot=100.0),
            dict(strike=f90 * np.exp(0.12), expiracion=exp90, tipo="call",
                 iv=3.5, precio=80.0, oi=12.0, spot=100.0),
        ]),
    ], ignore_index=True)
    sup = bm.calibrar_superficie_ssvi(
        cadena, tau_obj=4 / 12, hoy=hoy, max_dias=243, min_vencimientos=3,
        precio_min=0.10, oi_min=10)
    assert sup["usar_alas"] and sup["fuente"] == "ssvi"
    assert sup["n_vencimientos"] == 3
    assert sup["n_vencimientos_cadena"] == 4
    assert sup["dias_max"] <= 243
    assert sup["rho"] == pytest.approx(rho, abs=0.08)
    assert sup["n_drop_precio"] >= 1
    assert sup["n_drop_oi"] >= 1
    assert sup["n_drop_monotonia"] >= 1
    assert sup["spot_cadena"] == pytest.approx(100.0)


def test_tope_k_ssvi_es_el_minimo_entre_el_absoluto_y_tres_sigma():
    # 7 dias, 30% anual: 3 sigma * sqrt(T) ~ 0.12, por debajo del tope 0.5.
    t = 7 / 365.0
    corto = bm.tope_k_ssvi(0.30, t, k_abs_max=0.5, k_sd_max=3.0)
    assert corto == pytest.approx(3.0 * 0.30 * np.sqrt(t))
    assert corto < 0.5
    # Un plazo largo choca con el tope absoluto.
    largo = bm.tope_k_ssvi(0.30, 200 / 365.0, k_abs_max=0.5, k_sd_max=3.0)
    assert largo == pytest.approx(0.5)
    assert bm.tope_k_ssvi(0.30, t, k_abs_max=0.5, k_sd_max=None) == pytest.approx(0.5)


def test_ventana_k_sd_excluye_el_ala_vieja_que_rechazaba_la_sonrisa():
    """Un put profundo en el vencimiento de 7 dias (k~-0.46, IV rota).

    Con solo el tope |k|<=0.5 entra al ajuste y la perdida de ese plazo
    rechaza la superficie. Con 3 sigma * sqrt(T) queda fuera y la sonrisa
    calibra.
    """
    hoy = pd.Timestamp("2026-10-02")
    rho, eta, gamma, vol = -0.30, 0.50, 0.40, 0.30
    # k_span por dentro de 3 sigma aun en el plazo de 30 dias, para que el
    # unico punto que saque la ventana sea el ala vieja.
    cadena = _cadena_ssvi(
        hoy, rho, eta, gamma, vol, dias_list=(30, 90, 180), k_span=0.20)
    r = 0.02
    dias = 7
    t = dias / 365.0
    theta = vol ** 2 * t
    f = 100.0 * np.exp(r * t)
    exp = hoy + pd.Timedelta(days=dias)
    filas = []
    for k in (-0.08, -0.04, 0.0, 0.04, 0.08):
        strike = float(f * np.exp(k))
        w = float(bm.ssvi_total_variance([k], theta, rho, eta, gamma)[0])
        iv = float(np.sqrt(max(w, 1e-12) / t))
        px_call, px_put = _precios_con_paridad(f, strike, t, r)
        base = dict(strike=strike, expiracion=exp, iv=iv, oi=500.0, spot=100.0)
        filas.append({**base, "tipo": "call", "precio": float(px_call)})
        filas.append({**base, "tipo": "put", "precio": float(px_put)})
    # El ala: dentro de |k|<=0.5, precio por encima del piso, OI liquido.
    k_ala = -0.46
    filas.append(dict(
        strike=float(f * np.exp(k_ala)), expiracion=exp, tipo="put",
        iv=1.85, precio=0.50, oi=200.0, spot=100.0))
    cadena = pd.concat([cadena, pd.DataFrame(filas)], ignore_index=True)
    comun = dict(tau_obj=4 / 12, hoy=hoy, max_dias=243, min_vencimientos=3,
                 k_abs_max=0.5, precio_min=0.10, oi_min=10)
    sin_ventana = bm.calibrar_superficie_ssvi(cadena, k_sd_max=None, **comun)
    con_ventana = bm.calibrar_superficie_ssvi(cadena, k_sd_max=3.0, **comun)
    assert not sin_ventana["aceptado"]
    assert sin_ventana["rmse_rel"] > 0.20
    assert sin_ventana["n_drop_k_sd"] == 0
    assert sin_ventana["k_min"] == pytest.approx(k_ala, abs=0.02)
    assert con_ventana["aceptado"] and con_ventana["usar_alas"]
    assert con_ventana["rmse_rel"] <= 0.20
    assert con_ventana["n_drop_k_sd"] == 1
    assert con_ventana["k_min"] > -0.40
    assert con_ventana["rho"] == pytest.approx(rho, abs=0.12)


# ------------------------------------------------------------------------------
# lambda3 / lambda4 desde gamma (Taylor CRRA)
# ------------------------------------------------------------------------------

def test_crra_taylor_lambdas_match_profile_ladder():
    assert bm.crra_taylor_lambdas(6.0) == pytest.approx((21.0, 56.0))
    assert bm.crra_taylor_lambdas(3.0) == pytest.approx((6.0, 10.0))
    assert bm.crra_taylor_lambdas(1.5) == pytest.approx((1.875, 2.1875))
    with pytest.raises(ValueError):
        bm.crra_taylor_lambdas(0.0)


def test_crra_taylor_terms_are_the_crra_expansion():
    # Con l3/3 y l4/4 los coeficientes quedan g(g+1)/6 y g(g+1)(g+2)/24, los de
    # la serie de u(1 + r) = (1 + r)^(1 - g) / (1 - g) alrededor de r = 0.
    g = 4.0
    l3, l4 = bm.crra_taylor_lambdas(g)
    assert l3 / 3.0 == pytest.approx(g * (g + 1) / 6.0)
    assert l4 / 4.0 == pytest.approx(g * (g + 1) * (g + 2) / 24.0)
    # Chequeo numerico: lo que separa la CRRA de su Taylor a 4.o orden es el
    # termino de 5.o orden, g(g+1)(g+2)(g+3)/120 r^5.
    r = 0.03
    u = lambda x: (1.0 + x) ** (1.0 - g) / (1.0 - g)
    taylor = u(0.0) + r - (g / 2.0) * r ** 2 + (l3 / 3.0) * r ** 3 - (l4 / 4.0) * r ** 4
    quinto = g * (g + 1) * (g + 2) * (g + 3) / 120.0 * r ** 5
    assert u(r) - taylor == pytest.approx(quinto, rel=0.15)
