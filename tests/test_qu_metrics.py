import math
import re
from datetime import date

import numpy as np
import pandas as pd
import pytest

import qu_metrics as qm


# ------------------------------------------------------------------------------
# M-5 correlacion promedio
# ------------------------------------------------------------------------------

def _corr_abc():
    # A-B 0.2, A-C 0.4, B-C 0.9. El metodo alfabetico (Var1 < Var2) dejaba a C en NaN.
    return pd.DataFrame(
        [[1.0, 0.2, 0.4],
         [0.2, 1.0, 0.9],
         [0.4, 0.9, 1.0]],
        index=["A", "B", "C"], columns=["A", "B", "C"],
    )


def test_average_abs_correlation_uses_full_row():
    avg = qm.average_abs_correlation(_corr_abc())
    assert avg["A"] == pytest.approx((0.2 + 0.4) / 2)
    assert avg["B"] == pytest.approx((0.2 + 0.9) / 2)
    assert avg["C"] == pytest.approx((0.4 + 0.9) / 2)
    assert avg.isna().sum() == 0


def test_average_abs_correlation_ignores_sign_and_order():
    corr = _corr_abc()
    corr.loc["A", "B"] = corr.loc["B", "A"] = -0.2
    directo = qm.average_abs_correlation(corr)
    reordenado = qm.average_abs_correlation(corr.loc[["C", "A", "B"], ["C", "A", "B"]])
    assert directo["A"] == pytest.approx((0.2 + 0.4) / 2)
    assert reordenado["C"] == pytest.approx(directo["C"])


def test_old_alphabetical_grouping_drops_last_ticker():
    """Documenta el sesgo que M-5 corrige: agrupar solo Var1 < Var2."""
    corr = _corr_abc()
    pares = corr.stack().reset_index()
    pares.columns = ["Var1", "Var2", "Freq"]
    pares = pares[pares["Var1"].astype(str) < pares["Var2"].astype(str)]
    por_var1 = pares.groupby("Var1")["Freq"].mean()
    assert "C" not in por_var1.index
    assert len(pares[pares["Var1"] == "A"]) == 2
    assert len(pares[pares["Var1"] == "B"]) == 1


# ------------------------------------------------------------------------------
# M-6 ventana de historia
# ------------------------------------------------------------------------------

def test_history_window_includes_current_year_through_last_full_month():
    years, start, end = qm.history_window(date(2026, 10, 1), 2014)
    assert years[0] == 2014 and years[-1] == 2026
    assert 2026 in years
    assert start == "2014-01-01"
    assert end == "2026-10-01"          # exclusivo: entra septiembre, no el octubre a medias


def test_history_window_january_stops_at_previous_year():
    years, _, end = qm.history_window(date(2026, 1, 15), 2016)
    assert years[-1] == 2025
    assert end == "2026-01-01"
    assert 2026 not in years


def test_history_window_rejects_start_after_sample():
    with pytest.raises(ValueError):
        qm.history_window(date(2013, 3, 1), 2014)


# ------------------------------------------------------------------------------
# M-7 anualizacion
# ------------------------------------------------------------------------------

def test_annualize_monthly_uses_twelve_not_horizon():
    # El atajo viejo hacia retorno_mensual * (12 / horizon_months). Con horizonte 2
    # eso es x6, no una anualizacion.
    out = qm.annualize_monthly(mu=0.01, sd=0.04)
    assert out["mu"] == pytest.approx(0.12)
    assert out["sd"] == pytest.approx(0.04 * np.sqrt(12))
    horizonte_2 = 0.01 * (12 / 2)
    assert horizonte_2 != pytest.approx(out["mu"])


# ------------------------------------------------------------------------------
# M-8 lambda
# ------------------------------------------------------------------------------

def test_lambda_monthly_from_annual_scales_by_twelve_and_is_opt_in():
    assert qm.lambda_monthly_from_annual(None) is None
    assert qm.lambda_monthly_from_annual(3) == pytest.approx(36)
    assert qm.lambda_monthly_from_annual(0.5, periods_per_year=12) == pytest.approx(6)
    with pytest.raises(ValueError):
        qm.lambda_monthly_from_annual(0)
    with pytest.raises(ValueError):
        qm.lambda_monthly_from_annual(-1)


def test_utility_terms_show_when_the_penalty_binds():
    # lambda mensual 0.5 y varianza mensual tipica: la penalizacion es mucho menor que mu'w.
    flojo = qm.utility_terms(expected_return=0.01, variance=0.04 ** 2 / 12, lambda_=0.5)
    assert flojo["risk_term"] < flojo["mu_term"] / 10
    # La conversion opt-in (lambda_annual=3 -> 36) invierte esa relacion.
    firme = qm.utility_terms(expected_return=0.01, variance=0.04 ** 2 / 12, lambda_=qm.lambda_monthly_from_annual(3))
    assert firme["risk_term"] > flojo["risk_term"] * 10
    assert firme["utility"] == pytest.approx(firme["mu_term"] - firme["risk_term"])


# ------------------------------------------------------------------------------
# M-9 colas del z-score
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("z, mode, decision, motivo", [
    (2.0, "upper", "descartar", "cola_superior"),
    (-2.0, "upper", "mantener", "dentro_de_banda"),
    (-2.0, "lower", "descartar", "cola_inferior"),
    (2.0, "lower", "mantener", "dentro_de_banda"),
    (2.0, "both", "descartar", "cola_superior"),
    (-2.0, "both", "descartar", "cola_inferior"),
    (0.5, "both", "mantener", "dentro_de_banda"),
    (np.nan, "upper", "mantener", "z_no_finito"),
])
def test_mfis_tail_decision(z, mode, decision, motivo):
    assert qm.mfis_tail_decision(z, threshold=1.75, mode=mode) == (decision, motivo)


def test_mfis_tail_default_upper_matches_old_inequality():
    """El default upper descarta solo z > umbral, que es lo que hacia el script."""
    for z in (-3, -1.75, 0, 1.75, 1.76, 4):
        decision, _ = qm.mfis_tail_decision(z, 1.75, mode="upper")
        assert decision == ("descartar" if z > 1.75 else "mantener")


def test_mfis_tail_rejects_unknown_mode():
    with pytest.raises(ValueError):
        qm.mfis_tail_decision(1.0, 1.75, mode="ambas")


# ------------------------------------------------------------------------------
# M-1 longitud minima, sin truncar a la serie mas corta
# ------------------------------------------------------------------------------

def test_columns_with_min_obs_keeps_long_history():
    idx = pd.bdate_range("2020-01-01", periods=30)
    corto = pd.Series(np.arange(10, dtype=float), index=idx[-10:])
    largo = pd.Series(np.arange(30, dtype=float), index=idx)
    frame = pd.concat({"CORTO": corto, "LARGO": largo}, axis=1, sort=True)
    # dropna global dejaria 10 filas. La regla nueva quita al corto y conserva las 30.
    assert len(frame.dropna()) == 10
    kept, dropped = qm.columns_with_min_obs(frame, min_obs=24)
    assert dropped == ["CORTO"]
    assert list(kept.columns) == ["LARGO"]
    assert len(kept) == 30


def test_covariance_min_history_uses_each_series_full_sample():
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2018-01-01", periods=80)
    a = pd.Series(rng.normal(0, 0.01, 80), index=idx)
    b = pd.Series(rng.normal(0, 0.02, 80), index=idx)
    # C solo existe los ultimos 10 dias: no entra, y no recorta a A ni a B.
    c = pd.Series(rng.normal(size=10), index=idx[-10:])
    frame = pd.concat({"A": a, "B": b, "C": c}, axis=1)
    cov, dropped = qm.covariance_min_history(frame, min_periods=24)
    assert dropped == ["C"]
    assert cov.loc["A", "A"] == pytest.approx(a.var())
    assert cov.loc["B", "B"] == pytest.approx(b.var())
    truncada = frame.dropna().cov()
    assert len(frame.dropna()) == 10
    assert cov.loc["A", "A"] != pytest.approx(truncada.loc["A", "A"])


def test_portfolio_returns_skipna_does_not_drop_the_month():
    idx = pd.to_datetime(["2024-01-31", "2024-02-29"])
    rets = pd.DataFrame({"A": [0.10, 0.20], "B": [0.00, np.nan]}, index=idx)
    w = pd.Series({"A": 0.25, "B": 0.75})
    out = qm.portfolio_returns_skipna(rets, w)
    assert out.loc[idx[0]] == pytest.approx(0.25 * 0.10 + 0.75 * 0.0)
    # Febrero solo tiene A: el peso se reescala, la fila no desaparece.
    assert out.loc[idx[1]] == pytest.approx(0.20)
    assert len(rets.dropna()) == 1


# ------------------------------------------------------------------------------
# M-10 cesta de dispersion
# ------------------------------------------------------------------------------

def test_dispersion_weights_cap_weighted_spy_names_with_iv():
    assets = ["AAPL", "MSFT", "HSBC", "SPY", "XOM"]
    has_iv = {"AAPL", "MSFT", "XOM", "SPY"}          # HSBC sin IV; SPY es el indice, no un componente aqui
    components = {"AAPL", "MSFT", "XOM", "BRK-B"}
    caps = {"AAPL": 300.0, "MSFT": 100.0, "XOM": 100.0}
    w, info = qm.dispersion_weights(assets, has_iv, components, caps)
    assert info["mode"] == "cap"
    assert info["tickers"] == ["AAPL", "MSFT", "XOM"]
    assert w["HSBC"] == 0 and w["SPY"] == 0
    assert w["AAPL"] == pytest.approx(0.60)
    assert w["MSFT"] == pytest.approx(0.20)
    assert w.sum() == pytest.approx(1.0)


def test_dispersion_weights_equal_when_a_cap_is_missing():
    assets = ["AAPL", "MSFT"]
    w, info = qm.dispersion_weights(assets, {"AAPL", "MSFT"}, {"AAPL", "MSFT"}, caps={"AAPL": 10.0})
    assert info["mode"] == "equal"
    assert info["missing_caps"] == ["MSFT"]
    assert w["AAPL"] == pytest.approx(0.5) and w["MSFT"] == pytest.approx(0.5)


def test_dispersion_weights_insufficient_basket():
    w, info = qm.dispersion_weights(["AAPL", "EEM"], {"AAPL"}, {"AAPL"}, caps={"AAPL": 1.0})
    assert info["mode"] == "insuficiente"
    assert w.sum() == 0


# ------------------------------------------------------------------------------
# A-5 cadena historica: mismos limites, strike y DTE reales
# ------------------------------------------------------------------------------

def _contratos():
    # Spot 100 el 2024-06-03. Target 30 DTE, tolerancia 12.
    # Vencimiento 2024-07-05 -> 32 dias. Otro a 2024-08-16 -> 74 dias, fuera de banda.
    # Put 75: moneyness 0.75, dentro de 0.70-1.40 y fuera de la rejilla vieja 0.85-1.15.
    # Call 110.5 no es 100 * 1.10: hay que conservar el strike listado.
    filas = [
        ("O:P75", "put", 75.0, "2024-07-05"),    # moneyness 0.75: fuera de la rejilla vieja 0.85-1.15
        ("O:C1105", "call", 110.5, "2024-07-05"),
        ("O:C90", "call", 90.0, "2024-07-05"),     # call ITM, se descarta
        ("O:P90", "put", 90.0, "2024-07-05"),
        ("O:P110", "put", 110.0, "2024-07-05"),    # put ITM, se descarta
        ("O:C150", "call", 150.0, "2024-07-05"),   # moneyness 1.50, fuera de 1.40
        ("O:C100b", "call", 100.0, "2024-08-16"),  # DTE 74, fuera de tolerancia
        ("O:P100b", "put", 95.0, "2024-08-16"),
    ]
    return pd.DataFrame(filas, columns=["ticker", "contract_type", "strike_price", "expiration_date"])


def test_select_historical_otm_real_strikes_and_dte():
    elegido = qm.select_historical_otm(
        _contratos(), spot=100.0, as_of="2024-06-03", target_dte=30, dte_tol=12,
        moneyness_lo=0.70, moneyness_hi=1.40,
    )
    assert elegido["expiracion"] == "2024-07-05"
    assert elegido["dte"] == 32                      # real, no el target 30
    strikes_call = sorted(c["strike"] for c in elegido["calls"])
    strikes_put = sorted(p["strike"] for p in elegido["puts"])
    assert strikes_call == [110.5]
    assert 100 * 1.10 not in strikes_call
    assert strikes_put == [75.0, 90.0]
    assert all(k >= 100 for k in strikes_call)
    assert all(k < 100 for k in strikes_put)


def test_select_historical_otm_prefers_50_dte_over_15():
    filas = []
    for exp, dte_label in (("2024-06-18", "corto"), ("2024-07-23", "largo")):
        filas.append((f"C-{dte_label}", "call", 110.0, exp))
        filas.append((f"P-{dte_label}", "put", 90.0, exp))
    contratos = pd.DataFrame(filas, columns=["ticker", "contract_type", "strike_price", "expiration_date"])
    elegido = qm.select_historical_otm(
        contratos, spot=100.0, as_of="2024-06-03", target_dte=30, dte_tol=21,
        moneyness_lo=0.70, moneyness_hi=1.40, min_dte=21,
    )
    assert elegido["expiracion"] == "2024-07-23"
    assert elegido["dte"] == 50


def test_summarize_yearly_mdd_reports_the_unfiltered_worst_year():
    serie = pd.Series([-0.10, -0.12, -0.08, -0.11, -0.09, -0.4423, -0.15, -0.07])
    out = qm.summarize_yearly_mdd(serie)
    assert out["peor"] == pytest.approx(-0.4423)
    assert out["mejor"] == pytest.approx(serie.max())
    assert out["conservador"] == pytest.approx(float(serie.quantile(0.10)))
    assert out["conservador"] < float(serie.quantile(0.90))
    assert out["n_iqr"] < out["n"]
    assert out["mediana"] > out["peor"]
    corto = qm.summarize_yearly_mdd(pd.Series([-0.40, -0.05]))
    assert corto["peor"] == pytest.approx(-0.40)
    assert corto["mejor"] == pytest.approx(-0.05)
    assert corto["conservador"] == pytest.approx(-0.40)


def test_select_historical_otm_empty_without_both_sides():
    solo_calls = _contratos()
    solo_calls = solo_calls[solo_calls["contract_type"] == "call"]
    elegido = qm.select_historical_otm(
        solo_calls, spot=100.0, as_of="2024-06-03", target_dte=30, dte_tol=12,
        moneyness_lo=0.70, moneyness_hi=1.40,
    )
    assert elegido["dte"] is None
    assert elegido["calls"] == [] and elegido["puts"] == []


def test_estimate_bkm_history_calls_counts_the_chain_not_the_seven_point_grid():
    # 10 tickers, 20 fechas pendientes, ~40 contratos con precio.
    nuevo = qm.estimate_bkm_history_calls(10, 20, contracts_per_date=40)
    rejilla_vieja = 2 * 10 + (1 + 7) * 20
    assert nuevo == 2 * 10 + (1 + 40) * 20
    assert nuevo > rejilla_vieja


def test_dispersion_cap_share_is_the_basket_over_known_spy_caps():
    assets = ["AAPL", "MSFT"]
    components = {"AAPL", "MSFT", "XOM", "BRK-B"}
    caps = {"AAPL": 100.0, "MSFT": 100.0, "XOM": 800.0}
    _, info = qm.dispersion_weights(assets, {"AAPL", "MSFT"}, components, caps)
    assert info["mode"] == "cap"
    assert info["n_caps_conocidas"] == 3
    assert info["cap_share"] == pytest.approx(200 / 1000)
    assert not qm.dispersion_usable(info, min_cap_share=0.40, min_known_caps=50)
    info["n_caps_conocidas"] = 80
    info["cap_share"] = 0.55
    assert qm.dispersion_usable(info)


def test_scale_option_deltas_direct_does_not_stretch_a_tight_range():
    delta = np.array([0.48, 0.51, 0.56, np.nan])
    directo = qm.scale_option_deltas(delta, mode="direct", delta_min=0.30)
    assert directo[:3] == pytest.approx([0.48, 0.51, 0.56])
    assert directo[3] == pytest.approx(1.0)
    estirado = qm.scale_option_deltas(delta, mode="minmax", delta_min=0.30)
    assert estirado[0] == pytest.approx(0.30)
    assert estirado[2] == pytest.approx(1.0)
    assert estirado[2] - estirado[0] == pytest.approx(0.70)
    fijo = qm.scale_option_deltas(np.array([0.45, 0.50, 0.55]), mode="fixed",
                                  delta_min=0.30, fixed_lo=0.45, fixed_hi=0.55)
    assert fijo[0] == pytest.approx(0.30)
    assert fijo[2] == pytest.approx(1.0)
    assert fijo[1] == pytest.approx(0.65)


def test_sector_implied_ready_rejects_two_names():
    assert not qm.sector_implied_ready(2, min_names=4)
    assert qm.sector_implied_ready(4, min_names=4)


def test_clip_implied_correlation_floors_at_zero():
    assert qm.clip_implied_correlation(-0.133) == 0.0
    assert qm.clip_implied_correlation(-0.080) == 0.0
    assert qm.clip_implied_correlation(0.25) == pytest.approx(0.25)
    assert qm.clip_implied_correlation(1.4) == pytest.approx(0.999)
    assert np.isnan(qm.clip_implied_correlation(np.nan))


def test_stitch_keeps_daily_block_and_monthly_for_the_short_name():
    assets = ["LARGO", "OTRO", "CORTO"]
    diaria = pd.DataFrame(
        [[0.20, 0.05], [0.05, 0.30]],
        index=["LARGO", "OTRO"], columns=["LARGO", "OTRO"])
    mensual = pd.DataFrame(
        [[0.40, 0.01, 0.01], [0.01, 0.40, 0.01], [0.01, 0.01, 0.40]],
        index=assets, columns=assets)
    out = qm.stitch_covariance(assets, diaria, ["LARGO", "OTRO"], mensual)
    assert out.loc["LARGO", "OTRO"] == pytest.approx(0.05)
    assert out.loc["LARGO", "LARGO"] == pytest.approx(0.20)
    assert out.loc["CORTO", "CORTO"] == pytest.approx(0.40)
    assert out.loc["CORTO", "LARGO"] == pytest.approx(0.01)


def test_align_daily_panel_uses_spy_and_drops_the_short_name_only():
    idx = pd.bdate_range("2024-01-02", periods=100)
    corta = idx[:40]
    wide = pd.DataFrame({
        "A": np.linspace(10, 20, len(idx)),
        "B": np.nan,
        "SPY": np.linspace(100, 110, len(idx)),
    }, index=idx)
    wide.loc[corta, "B"] = np.linspace(5, 6, len(corta))
    aligned, info = qm.align_daily_panel(wide, ["A", "B"], spy_col="SPY", min_coverage=0.80)
    assert info["calendar"] == "SPY"
    assert "A" in info["kept"] and "B" in info["dropped_low_coverage"]
    assert "SPY" not in aligned.columns


def test_mfiv_annual_vol_uses_real_dte():
    mfiv = 0.0036
    vol = qm.mfiv_annual_vol(mfiv, dte=32)
    assert vol == pytest.approx(np.sqrt(mfiv * 365 / 32))
    assert vol != pytest.approx(np.sqrt(mfiv / (2 / 12)))


def _barra(dia, precio):
    ms = int(pd.Timestamp(dia).value // 10**6)
    return {"t": ms, "c": precio}


def test_range_fetch_matches_per_date_close():
    """Un rango por contrato, recortado a ±5 dias, da el mismo cierre que la consulta de esa fecha."""
    barras = [_barra(f"2024-01-{d:02d}", 10.0 + d) for d in range(1, 32)]
    # 16 de enero cae a 6 dias del 10: la consulta de un solo dia (±5) no la trae.
    barras.append(_barra("2024-01-16", 99.0))
    fechas = [pd.Timestamp("2024-01-10"), pd.Timestamp("2024-01-20")]
    needed = [("O:AAA", f) for f in fechas] + [("O:BBB", fechas[0])]
    rangos = qm.contract_agg_ranges(needed, window_days=5)
    assert set(rangos) == {"O:AAA", "O:BBB"}
    assert rangos["O:AAA"] == ("2024-01-05", "2024-01-25")
    assert rangos["O:BBB"] == ("2024-01-05", "2024-01-15")
    # 2 contratos, no 3 consultas (AAA en dos fechas + BBB).
    assert len(rangos) == 2
    assert len(rangos) < len(needed)

    for fecha in fechas:
        ventana = []
        for barra in barras:
            dia = pd.to_datetime(barra["t"], unit="ms").normalize()
            if abs((dia - fecha).days) <= 5:
                ventana.append(barra)
        assert qm.close_near_from_bars(barras, fecha, 5) == qm.close_near_from_bars(ventana, fecha, 5)
    # El 10 de enero tiene barra propia (precio 20). La del 16 no la pisa.
    assert qm.close_near_from_bars(barras, "2024-01-10", 5) == pytest.approx(20.0)
    # Sin barra el 12: la mas cercana dentro de ±5, no la de fuera.
    solo = [_barra("2024-01-14", 1.0), _barra("2024-01-18", 9.0)]
    assert qm.close_near_from_bars(solo, "2024-01-12", 5) == pytest.approx(1.0)


def test_plan_bkm_history_budget_keeps_a_ranked_prefix():
    ranked = [
        {"ticker": "AAA", "us": True, "mfis_ok": True, "n_pending": 10},
        {"ticker": "BBB.L", "us": False, "mfis_ok": False, "n_pending": 10},
        {"ticker": "CCC", "us": True, "mfis_ok": False, "n_pending": 10, "motivo": "mfis_inadmisible"},
        {"ticker": "DDD", "us": True, "mfis_ok": True, "n_pending": 0},
        {"ticker": "EEE", "us": True, "mfis_ok": True, "n_pending": 10},
        {"ticker": "FFF", "us": True, "mfis_ok": True, "n_pending": 10},
    ]
    # 1 + 26 = 27 por fecha. 2 min * 300/min = 600 llamadas.
    # AAA 270, DDD 0, EEE 270, FFF no cabe (810).
    plan = qm.plan_bkm_history_budget(
        ranked, contracts_per_date=26, calls_per_min=300, max_minutes=2, spent_calls=0)
    assert plan["procesar"] == ["AAA", "DDD", "EEE"]
    assert [o["ticker"] for o in plan["omitidos"]] == ["FFF"]
    assert plan["omitidos"][0]["motivo"] == "historia_no_procesada_presupuesto"
    assert plan["n_us_mfis"] == 4
    fuera = {f["ticker"]: f["motivo"] for f in plan["fuera_de_historia"]}
    assert fuera["BBB.L"] == "sin_opciones_us"
    assert fuera["CCC"] == "mfis_inadmisible"
    assert "BBB.L" not in plan["procesar"] and "CCC" not in plan["procesar"]

    # Con todo en cache el presupuesto chico igual procesa a los elegibles.
    en_cache = [
        {"ticker": "AAA", "us": True, "mfis_ok": True, "n_pending": 0},
        {"ticker": "EEE", "us": True, "mfis_ok": True, "n_pending": 0},
    ]
    plan_cache = qm.plan_bkm_history_budget(
        en_cache, contracts_per_date=26, calls_per_min=5, max_minutes=1, spent_calls=0)
    assert plan_cache["procesar"] == ["AAA", "EEE"]
    assert plan_cache["omitidos"] == []
    assert plan_cache["llamadas"] == 0

    # No es todo o nada: el que cabe entra, aunque el total no quepa.
    justo = [
        {"ticker": "AAA", "us": True, "mfis_ok": True, "n_pending": 1},
        {"ticker": "EEE", "us": True, "mfis_ok": True, "n_pending": 10},
    ]
    # 81 llamadas: AAA (27) entra entero y sobran 54, que calientan 2 fechas de EEE.
    plan_justo = qm.plan_bkm_history_budget(
        justo, contracts_per_date=26, calls_per_min=81, max_minutes=1, spent_calls=0)
    assert plan_justo["procesar"] == ["AAA"]
    assert plan_justo["omitidos"][0]["ticker"] == "EEE"
    assert plan_justo["calentar"]["ticker"] == "EEE"
    assert plan_justo["calentar"]["n_fechas"] == 2


def test_constrained_frontier_passes_through_the_optimum():
    import quadprog

    cov = np.array([[0.04, 0.01, 0.00],
                    [0.01, 0.09, 0.00],
                    [0.00, 0.00, 0.02]])
    mu = np.array([0.01, 0.03, 0.015])
    lambda_ref = 2.5

    def solve(lam):
        n = 3
        g = cov + np.eye(n) * 1e-8
        a = mu / float(lam)
        c = np.column_stack([np.ones(n), np.eye(n)])
        b = np.array([1.0, 0.0, 0.0, 0.0])
        return quadprog.solve_qp(g, a, c, b, meq=1)[0]

    w_opt = solve(lambda_ref)
    curva = qm.frontier_curve(solve, cov, mu, qm.frontier_lambda_grid(lambda_ref), lambda_utility=lambda_ref)
    fila = curva.iloc[(curva["lambda_"] - lambda_ref).abs().argmin()]
    assert fila["lambda_"] == pytest.approx(lambda_ref)
    assert fila["risk"] == pytest.approx(float(np.sqrt(w_opt @ cov @ w_opt)))
    assert fila["ret"] == pytest.approx(float(w_opt @ mu))


def test_shrink_mu_to_prior_weights_by_history_length():
    hist = pd.Series({"LARGO": 0.020, "CORTO": 0.030, "SIN_FF": 0.015})
    prior = pd.Series({"LARGO": 0.010, "CORTO": 0.008})
    n = pd.Series({"LARGO": 140, "CORTO": 35, "SIN_FF": 60})
    mu, w = qm.shrink_mu_to_prior(hist, prior, n, k=140)
    assert w["LARGO"] == pytest.approx(0.5)
    assert mu["LARGO"] == pytest.approx(0.015)
    assert w["CORTO"] == pytest.approx(35 / 175)
    assert mu["CORTO"] == pytest.approx(0.2 * 0.030 + 0.8 * 0.008)
    # Sin prior el activo conserva su media historica.
    assert w["SIN_FF"] == 1.0 and mu["SIN_FF"] == pytest.approx(0.015)
    # k = 0 desactiva el encogimiento.
    mu0, _ = qm.shrink_mu_to_prior(hist, prior, n, k=0)
    assert np.allclose(mu0.values, hist.values)
    with pytest.raises(ValueError):
        qm.shrink_mu_to_prior(hist, prior, n, k=-1)


def test_lambda_scores_use_the_reference_lambda_and_mu_final():
    mu_final = np.array([0.02, 0.01])
    cov = np.array([[0.04, 0.0], [0.0, 0.01]])
    w_agresivo = np.array([1.0, 0.0])
    w_conservador = np.array([0.2, 0.8])
    scored = qm.score_candidate_portfolios(
        [(0.1, w_agresivo), (10.0, w_conservador)],
        mu_final, cov, lambda_ref=10.0)
    # Al lambda 0.1 la utilidad del agresivo seria mayor. Al lambda de
    # referencia 10 gana el conservador, y el retorno es w'mu_final.
    mejor = scored.loc[scored["utilidad"].idxmax(), "lambda_"]
    assert mejor == pytest.approx(10.0)
    agresivo = scored.loc[np.isclose(scored["lambda_"], 0.1)].iloc[0]
    assert agresivo["ret"] == pytest.approx(0.02)
    assert agresivo["utilidad"] == pytest.approx(0.02 - 5.0 * 0.04)
    assert 0.8 in qm.comparison_lambdas(0.8)
    # pen_ret usa el lambda de su propia fila, no el de referencia.
    assert agresivo["pen_ret"] == pytest.approx((0.1 / 2 * 0.04) / 0.02)
    conservador = scored.loc[np.isclose(scored["lambda_"], 10.0)].iloc[0]
    var_c = 0.2 ** 2 * 0.04 + 0.8 ** 2 * 0.01
    assert conservador["pen_ret"] == pytest.approx((10.0 / 2 * var_c) / (0.2 * 0.02 + 0.8 * 0.01))


def test_pen_ret_is_nan_when_return_is_not_positive():
    scored = qm.score_candidate_portfolios(
        [(1.5, np.array([1.0]))], np.array([-0.01]), np.array([[0.04]]), lambda_ref=1.5)
    assert np.isnan(scored.iloc[0]["pen_ret"])


# ------------------------------------------------------------------------------
# Universo: el formato US no se aplica a internacionales
# ------------------------------------------------------------------------------

_INTERNACIONALES = [
    "RY.TO", "SHOP.TO", "ENB.TO", "SU.TO", "SIE.DE", "MUV2.DE", "ULVR.L",
    "NG.L", "TTE.PA", "MC.PA", "ITX.MC", "BBVA.MC", "7203.T", "9984.T",
    "HSBC", "BP",
]


def _formato_us_viejo(tickers):
    return [
        t for t in tickers
        if not re.search(r"\^|\$", t) and 1 <= len(t) <= 5 and not re.match(r"^[0-9]", t) and t != ""
    ]


def test_combinar_tickers_conserva_sufijos_que_el_filtro_us_tiraba():
    domesticos = ["AAPL", "BRK-B", "MSFT", "^GSPC", "$VIX", "1234", "", "TOOLONG"]
    unidos = qm.combinar_tickers(domesticos, _INTERNACIONALES)
    viejo = _formato_us_viejo(list(dict.fromkeys(domesticos + _INTERNACIONALES)))
    for t in ("SHOP.TO", "ENB.TO", "SIE.DE", "MUV2.DE", "ULVR.L", "TTE.PA",
              "ITX.MC", "BBVA.MC", "7203.T", "9984.T"):
        assert t in unidos
        assert t not in viejo
    # MC.PA cabe en 5 caracteres: el filtro viejo ya lo dejaba pasar.
    assert "MC.PA" in unidos and "MC.PA" in viejo
    for t in ("AAPL", "BRK-B", "SU.TO", "NG.L", "HSBC", "BP"):
        assert t in unidos
    for t in ("^GSPC", "$VIX", "1234", "", "TOOLONG"):
        assert t not in unidos
    # SU.TO (largo 5) y NG.L (largo 4) ya pasaban el filtro viejo.
    assert "SU.TO" in viejo and "NG.L" in viejo


def test_region_de_ticker_separa_canada_de_japon_y_deja_adrs_en_us():
    assert qm.region_de_ticker("SHOP.TO") == "Canada"
    assert qm.region_de_ticker("ENB.TO") == "Canada"
    assert qm.region_de_ticker("SU.TO") == "Canada"
    assert qm.region_de_ticker("7203.T") == "Japon"
    assert qm.region_de_ticker("9984.T") == "Japon"
    assert qm.region_de_ticker("SIE.DE") == "Europa"
    assert qm.region_de_ticker("ULVR.L") == "Europa"
    assert qm.region_de_ticker("NG.L") == "Europa"
    assert qm.region_de_ticker("TTE.PA") == "Europa"
    assert qm.region_de_ticker("ITX.MC") == "Europa"
    assert qm.region_de_ticker("HSBC") == "US"
    assert qm.region_de_ticker("BP") == "US"
    assert qm.region_de_ticker("BRK.B") == "US"


# ------------------------------------------------------------------------------
# Filtro delta: colchon OTM, no la delta ATM
# ------------------------------------------------------------------------------

# Pool sintetico de 45 vols anuales. Sin POLYGON_API_KEY: Black-Scholes,
# no cadenas reales. Mezcla defensiva / mega-cap / growth / high-beta.
_VOLS_POOL_45 = [
    0.14, 0.15, 0.16, 0.16, 0.17, 0.18, 0.18, 0.19,
    0.20, 0.21, 0.22, 0.22, 0.23, 0.24, 0.24, 0.25, 0.26, 0.26, 0.27, 0.28, 0.28, 0.29, 0.30,
    0.32, 0.33, 0.34, 0.35, 0.36, 0.38, 0.40, 0.42, 0.44, 0.46,
    0.48, 0.50, 0.52, 0.55, 0.58, 0.62, 0.66, 0.70, 0.75, 0.80, 0.85, 0.90,
]
_T_REF = 2 / 12
_R = 0.047
_LOG_M = 0.08


def _cojines(years=_T_REF):
    return [
        qm.delta_cushion(v, years, _R, _LOG_M, ref_years=_T_REF)
        for v in _VOLS_POOL_45
    ]


def test_delta_atm_no_separa_los_umbrales_de_perfil():
    atm = [qm.bs_call_delta_from_vol(v, _T_REF, _R, 0.0) for v in _VOLS_POOL_45]
    assert min(atm) > 0.50
    assert max(atm) - min(atm) < 0.06
    # 0.30 y 0.42 no tiran a nadie. 0.55 solo roza el borde inferior.
    assert sum(d < 0.30 for d in atm) == 0
    assert sum(d < 0.42 for d in atm) == 0
    assert sum(d < 0.55 for d in atm) <= 5


def test_colchon_baja_con_la_vol_y_separa_perfiles():
    bajo = qm.delta_cushion(0.18, _T_REF, _R, _LOG_M, ref_years=_T_REF)
    alto = qm.delta_cushion(0.70, _T_REF, _R, _LOG_M, ref_years=_T_REF)
    assert bajo > alto
    cojines = _cojines()
    drop_agr = sum(c < 0.12 for c in cojines)
    drop_mod = sum(c < 0.18 for c in cojines)
    drop_con = sum(c < 0.24 for c in cojines)
    assert (drop_agr, drop_mod, drop_con) == (6, 14, 22)
    assert drop_agr < drop_mod < drop_con
    # El mismo umbral, a 4 meses, sigue separando parecido porque la
    # moneyness escala con sqrt(T).
    cojines_4m = _cojines(years=4 / 12)
    drop_agr_4 = sum(c < 0.12 for c in cojines_4m)
    drop_con_4 = sum(c < 0.24 for c in cojines_4m)
    assert drop_agr_4 == drop_agr
    assert abs(drop_con_4 - drop_con) <= 1


def test_delta_cushion_sin_vol_es_nan():
    assert math.isnan(qm.delta_cushion(0.0, _T_REF, _R, _LOG_M))
    assert math.isnan(qm.delta_cushion(float("nan"), _T_REF, _R, _LOG_M))
    assert math.isnan(qm.bs_call_delta_from_vol(-0.2, 0.2, 0.04))


def test_scale_relative_no_reescala_lambda():
    # Colchon tipico: la mediana queda en 1. NaN (sin opciones, como SU.TO
    # si no hay vol) no recorta mu.
    delta = np.array([0.12, 0.20, 0.28, 0.36, 0.44, np.nan])
    mult = qm.scale_option_deltas(delta, mode="relative", fixed_lo=0.75, fixed_hi=1.25)
    assert mult[2] == pytest.approx(1.0)  # mediana de los finitos
    assert mult[5] == pytest.approx(1.0)
    assert mult.min() >= 0.75 - 1e-12
    assert mult.max() <= 1.25 + 1e-12
    # direct sobre ATM ~0.5 si seria un recorte uniforme. relative no.
    assert mult[2] > 0.9
