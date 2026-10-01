import math

import numpy as np
import pytest
import quadprog

import portfolio_constraints as pq


def _base(**kw):
    cfg = dict(
        min_weight=0.0, max_weight=1.0,
        min_total=1.0, max_total=1.0,
        require_full_investment=False,
    )
    cfg.update(kw)
    n = cfg.pop("n")
    return pq.build_weight_constraints(n, **cfg)


def _slack(A, b, w):
    return A.T @ np.asarray(w, dtype=float) - b


# ------------------------------------------------------------------------------
# Delta ATM (M-3): el filtro delta_min = 0.30 no descartaba nada con K = S
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("vol", [0.10, 0.20, 0.35, 0.80])
@pytest.mark.parametrize("years", [30 / 365, 3 / 12, 1.0])
@pytest.mark.parametrize("rate", [0.0, 0.047])
def test_atm_call_delta_always_above_half(vol, years, rate):
    delta = pq.bs_call_delta(spot=100.0, strike=100.0, years=years, rate=rate, vol=vol)
    assert delta > 0.5
    assert delta >= 0.30          # el umbral antiguo (delta_min) nunca se activaba


def test_otm_call_delta_can_fall_below_old_threshold():
    delta = pq.bs_call_delta(spot=100.0, strike=160.0, years=30 / 365, rate=0.047, vol=0.20)
    assert delta < 0.30


def test_bs_call_delta_invalid_inputs_are_nan():
    assert math.isnan(pq.bs_call_delta(0, 100, 0.1, 0.02, 0.2))
    assert math.isnan(pq.bs_call_delta(100, 100, 0.0, 0.02, 0.2))


# ------------------------------------------------------------------------------
# Restricciones de peso (B-5)
# ------------------------------------------------------------------------------

def test_budget_is_equality_and_box_constraints_hold():
    cons = _base(n=3, min_weight=0.05, max_weight=0.60)
    assert cons["meq"] == 1
    assert cons["has_extra"] is False
    assert cons["Amat_base"].shape == (3, 1 + 6)
    w = np.array([0.20, 0.30, 0.50])
    slack = _slack(cons["Amat_full"], cons["bvec_full"], w)
    assert slack[0] == pytest.approx(0.0)
    assert np.all(slack[1:] >= -1e-12)


def test_total_weight_band_is_inequality_when_limits_differ():
    cons = _base(n=2, min_total=0.80, max_total=1.0, min_weight=0.0, max_weight=1.0)
    assert cons["meq"] == 0
    w = np.array([0.40, 0.45])                  # suma 0.85, dentro de [0.80, 1]
    slack = _slack(cons["Amat_full"], cons["bvec_full"], w)
    assert np.all(slack >= -1e-12)
    w_bajo = np.array([0.30, 0.30])             # suma 0.60, fuera
    assert _slack(cons["Amat_full"], cons["bvec_full"], w_bajo)[0] < 0


def test_etf_and_fx_columns_bind_on_invested_capital():
    cons = _base(
        n=3,
        is_etf=[0, 0, 1], use_etf_band=True, etf_min_weight=0.30, etf_max_weight=0.55,
        is_non_usd=[0, 1, 0], use_fx_cap=True, max_fx_exposure=0.35,
    )
    assert cons["has_extra"] is True
    assert cons["Amat_full"].shape[1] == cons["Amat_base"].shape[1] + 3
    dentro = np.array([0.40, 0.20, 0.40])      # ETF 40%, FX 20%
    assert np.all(_slack(cons["Amat_full"], cons["bvec_full"], dentro)[1:] >= -1e-12)
    etf_bajo = np.array([0.50, 0.30, 0.20])    # ETF 20% < 30%
    assert _slack(cons["Amat_full"], cons["bvec_full"], etf_bajo).min() < 0
    fx_alto = np.array([0.20, 0.40, 0.40])     # FX 40% > 35%
    assert _slack(cons["Amat_full"], cons["bvec_full"], fx_alto).min() < 0


def test_etf_band_skipped_when_subset_has_no_etf():
    cons = _base(n=2, is_etf=[0, 0], use_etf_band=True, etf_min_weight=0.30, etf_max_weight=0.55)
    assert cons["has_extra"] is False
    assert np.shares_memory(cons["Amat_base"], cons["Amat_full"]) or np.array_equal(
        cons["Amat_base"], cons["Amat_full"])


def _minvar(cov, cons, mu, target):
    n = cov.shape[0]
    D = 2 * cov + np.eye(n) * 1e-8
    A, b, meq = pq.with_return_target(cons, mu, target)
    sol = quadprog.solve_qp(D, np.zeros(n), A, b, meq)
    return sol[0]


def test_frontier_target_below_etf_band_is_infeasible():
    """Dos activos: el unico portafolio con retorno alto deja al ETF bajo el minimo."""
    mu = np.array([0.020, 0.001])               # accion, ETF
    cov = np.eye(2) * 1e-4
    dentro = _base(n=2, is_etf=[0, 1], use_etf_band=True, etf_min_weight=0.30, etf_max_weight=0.55)
    with pytest.raises(ValueError):
        _minvar(cov, dentro, mu, target=0.015)  # exigiria ~26% ETF

    sin_banda = _base(n=2)
    w = _minvar(cov, sin_banda, mu, target=0.015)
    assert w.sum() == pytest.approx(1.0, abs=1e-6)
    assert w[1] == pytest.approx((0.020 - 0.015) / (0.020 - 0.001), abs=1e-4)
    assert w[1] < 0.30                           # la frontera antigua violaba la banda


def test_frontier_feasible_target_respects_etf_band_and_fx_cap():
    mu = np.array([0.020, 0.004, 0.001])        # accion, FX, ETF
    cov = np.eye(3) * 1e-4
    cons = _base(
        n=3,
        is_etf=[0, 0, 1], use_etf_band=True, etf_min_weight=0.30, etf_max_weight=0.55,
        is_non_usd=[0, 1, 0], use_fx_cap=True, max_fx_exposure=0.35,
    )
    # 0.012 es alcanzable con ETF ~42% y sin usar el FX de retorno medio.
    w = _minvar(cov, cons, mu, target=0.012)
    assert w.sum() == pytest.approx(1.0, abs=1e-6)
    assert 0.30 - 1e-6 <= w[2] <= 0.55 + 1e-6
    assert w[1] <= 0.35 + 1e-6
    assert np.all(w >= -1e-8)

    with pytest.raises(ValueError):
        # Retorno solo alcanzable cargando el FX por encima del tope.
        _minvar(cov, cons, mu, target=0.016)


def test_relax_group_band_lowers_an_unreachable_etf_floor():
    # 2 ETFs x 12% no llegan al piso del 30%. El piso baja a 24% y la banda sigue.
    lo, hi, nota = pq.relax_group_band(2, 30, max_weight=0.12, min_share=0.30, max_share=0.55)
    assert lo == pytest.approx(0.24)
    assert hi == pytest.approx(0.55)
    assert "24.00%" in nota
    assert pq.relax_group_band(0, 10, 0.12, 0.30, 0.55)[2].startswith("sin activos")
    mismo = pq.relax_group_band(4, 20, 0.12, 0.30, 0.55)
    assert mismo[0] == pytest.approx(0.30) and mismo[1] == pytest.approx(0.55) and mismo[2] == ""
