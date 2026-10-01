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


def test_mfiv_annual_vol_uses_real_dte():
    mfiv = 0.0036
    vol = qm.mfiv_annual_vol(mfiv, dte=32)
    assert vol == pytest.approx(np.sqrt(mfiv * 365 / 32))
    assert vol != pytest.approx(np.sqrt(mfiv / (2 / 12)))
