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


def test_prune_order_drops_the_small_weight_not_the_capped_defensive():
    weights = {"XLP": 0.12, "GLD": 0.12, "MLPX": 0.04, "VZ": 0.11}
    mtr = {"XLP": 0.050, "GLD": 0.040, "MLPX": 0.008, "VZ": 0.030}
    assert pq.prune_order(weights, mtr, "max_mtr")[0] == "XLP"
    assert pq.prune_order(weights, mtr, "min_weight")[0] == "MLPX"
    assert pq.prune_order(weights, mtr, "min_weight_x_mtr")[0] == "MLPX"
    assert "XLP" not in pq.prune_order({"XLP": 0.0, "MLPX": 0.04}, None, "min_weight")


# ------------------------------------------------------------------------------
# Banda de beta del portafolio (palanca de perfil de QU y MV)
# ------------------------------------------------------------------------------

BETAS = np.array([0.30, 0.60, 0.90, 1.10, 1.40, 1.70])


def _minvar_banda(cons, cov):
    n = cov.shape[0]
    return quadprog.solve_qp(2 * cov + 1e-9 * np.eye(n), np.zeros(n),
                             cons["Amat_full"], cons["bvec_full"], cons["meq"])[0]


def test_beta_band_columns_son_homogeneas():
    cols, b = pq.beta_band_columns(BETAS, 0.6, 0.8)
    assert len(cols) == 2 and b == [0.0, 0.0]
    w = np.full(6, 1 / 6)                    # beta media 1.0: fuera del techo
    assert cols[0] @ w > 0 and cols[1] @ w < 0
    assert pq.beta_band_columns(BETAS, None, None) == ([], [])
    with pytest.raises(ValueError):
        pq.beta_band_columns(BETAS, 0.9, 0.8)
    with pytest.raises(ValueError):
        pq.beta_band_columns([1.0, np.nan], 0.5, 1.0)


@pytest.mark.parametrize("lo, hi", [(0.60, 0.80), (0.80, 0.95), (0.95, 1.30)])
def test_minima_varianza_respeta_la_banda_de_beta(lo, hi):
    vol = 0.02 + 0.03 * BETAS                # la vol sube con la beta
    cov = np.outer(vol, vol) * (0.3 + 0.7 * np.eye(6))
    libre = _minvar_banda(_base(n=6, max_weight=0.35), cov)
    cons = _base(n=6, max_weight=0.35, betas=BETAS, beta_lo=lo, beta_hi=hi)
    assert cons["has_extra"] is True
    w = _minvar_banda(cons, cov)
    beta_p = float(w @ BETAS)
    assert lo - 1e-6 <= beta_p <= hi + 1e-6
    if float(libre @ BETAS) < lo:
        # Sin banda la minima varianza queda bajo el piso: con banda se pega a el.
        assert beta_p == pytest.approx(lo, abs=1e-4)
    else:
        assert w == pytest.approx(libre, abs=1e-6)


def test_banda_de_beta_con_inversion_parcial_es_por_capital_invertido():
    cons = _base(n=6, min_total=0.5, max_total=1.0, max_weight=0.5, betas=BETAS, beta_lo=0.9, beta_hi=1.0)
    w = np.array([0.0, 0.0, 0.25, 0.25, 0.0, 0.0])      # 50% invertido con beta 1.0
    assert np.all(_slack(cons["Amat_full"], cons["bvec_full"], w) >= -1e-12)


def test_rango_de_beta_alcanzable():
    b_min, b_max = pq.beta_range_reachable(BETAS, 0.35)
    assert b_min == pytest.approx(0.35 * 0.30 + 0.35 * 0.60 + 0.30 * 0.90)
    assert b_max == pytest.approx(0.35 * 1.70 + 0.35 * 1.40 + 0.30 * 1.10)
    # Con piso por activo todos aportan; un tope 0 saca al activo del rango.
    b_min_piso, _ = pq.beta_range_reachable(BETAS, 0.35, min_weight=0.05)
    assert b_min_piso > b_min
    caps = np.array([0.0, 0.5, 0.5, 0.5, 0.5, 0.0])
    assert pq.beta_range_reachable(BETAS, caps) == pytest.approx((0.75, 1.25))
    assert all(math.isnan(x) for x in pq.beta_range_reachable(BETAS, 0.10))   # 6 x 10% < 100%


def test_relax_beta_band_solo_mueve_lo_inalcanzable():
    lo, hi, nota = pq.relax_beta_band(BETAS, 0.60, 0.80, max_weight=0.35)
    assert (lo, hi, nota) == (0.60, 0.80, "")
    defensivo = np.array([0.20, 0.30, 0.40, 0.50])
    lo, hi, nota = pq.relax_beta_band(defensivo, 0.60, 0.80, max_weight=0.35)
    b_max = 0.35 * 0.50 + 0.35 * 0.40 + 0.30 * 0.30
    assert lo == pytest.approx(b_max) and hi == 0.80
    assert "piso de beta" in nota
    ofensivo = np.array([1.2, 1.4, 1.6, 1.8])
    lo, hi, nota = pq.relax_beta_band(ofensivo, 0.60, 0.80, max_weight=0.35)
    assert lo == 0.60 and hi == pytest.approx(0.35 * 1.2 + 0.35 * 1.4 + 0.30 * 1.6)
    assert "techo de beta" in nota


def test_cobertura_de_beta_agrega_solo_lo_que_falta():
    betas = {"A": 0.5, "B": 0.6, "C": 0.7, "D": 0.8, "E": 1.5, "F": 1.4, "G": 0.3, "H": 1.6}
    pool = ["A", "B", "C", "D"]                      # max alcanzable con 30%: 0.72
    ranking = ["G", "E", "A", "F", "H"]
    extra = pq.beta_coverage_additions(pool, ranking, betas, 0.95, 1.30, max_weight=0.30, max_add=5)
    assert extra == ["E", "F", "H"]                  # orden del ranking, solo beta >= 1.30
    nuevo = [betas[t] for t in pool + extra]
    assert pq.beta_range_reachable(nuevo, 0.30)[1] >= 1.30
    # Una banda ya cubierta no agrega nada; max_add corta.
    assert pq.beta_coverage_additions(pool + extra, ranking, betas, 0.65, 0.8, max_weight=0.30, max_add=5) == []
    assert pq.beta_coverage_additions(pool, ranking, betas, 0.95, 1.30, max_weight=0.30, max_add=1) == ["E"]
    # Piso inalcanzable por arriba: suma nombres de beta baja.
    alto = {"X": 1.2, "Y": 1.3, "Z": 1.4, "W": 1.5, "L": 0.4}
    assert pq.beta_coverage_additions(["X", "Y", "Z", "W"], ["L"], alto, 0.60, 0.80,
                                      max_weight=0.30, max_add=3) == ["L"]


def test_banda_sin_techo():
    cols, b = pq.beta_band_columns(BETAS, 0.95, None)
    assert len(cols) == 1 and b == [0.0]
    assert pq.beta_band_text(0.95, None) == ">= 0.95"
    assert pq.beta_band_text(0.60, 0.80) == "0.60-0.80"
    assert pq.beta_band_text(None, None) == "sin banda"
    lo, hi, nota = pq.relax_beta_band(np.array([0.3, 0.5, 0.7, 0.9]), 0.95, None, max_weight=0.35)
    assert hi is None and lo == pytest.approx(0.35 * 0.9 + 0.35 * 0.7 + 0.30 * 0.5)
    assert "piso de beta" in nota
    # Sin techo, el pool debe superar el piso con holgura (BETA_COVERAGE_MARGIN).
    betas = {"A": 0.9, "B": 0.95, "C": 1.0, "D": 0.8, "E": 1.6, "F": 0.2, "G": 1.5, "H": 1.7}
    extra = pq.beta_coverage_additions(["A", "B", "C", "D"], ["F", "E", "G", "H"], betas, 0.95, None,
                                       max_weight=0.30, max_add=5)
    assert extra == ["E", "G"]                       # solo beta >= piso + margen; F (0.2) nunca entra
    nuevo = [betas[t] for t in ["A", "B", "C", "D"] + extra]
    assert pq.beta_range_reachable(nuevo, 0.30)[1] >= 0.95 + pq.BETA_COVERAGE_MARGIN
