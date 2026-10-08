"""Horizonte del portafolio en Quadratic Utility: QP y VaR Cornish-Fisher.

horizon_months es la unica fuente del plazo. El QP ve mu x h y Sigma x h, y el
VaR CF se calcula al horizonte. Los pesos no dependen de h.
"""

import math
import re
from pathlib import Path

import numpy as np
import pytest
import quadprog

import qu_metrics as qm
import risk_estimators as rk

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ["quadratic_utility.py", "quadratic_utility_(seasonal_version).py"]

MU_M = np.array([0.012, 0.008, 0.015, 0.004, 0.010])
_VOL_A = np.array([0.28, 0.18, 0.35, 0.12, 0.22])
_R = np.array([
    [1.0, 0.3, 0.5, 0.1, 0.2],
    [0.3, 1.0, 0.2, 0.0, 0.4],
    [0.5, 0.2, 1.0, 0.1, 0.3],
    [0.1, 0.0, 0.1, 1.0, 0.1],
    [0.2, 0.4, 0.3, 0.1, 1.0],
])
COV_M = np.outer(_VOL_A, _VOL_A) * _R / 12


def _restricciones(n, max_weight):
    cols, b = [np.ones(n)], [1.0]
    for i in range(n):
        v = np.zeros(n); v[i] = 1
        cols.append(v); b.append(0.0)
    for i in range(n):
        v = np.zeros(n); v[i] = -1
        cols.append(v); b.append(-max_weight)
    return np.column_stack(cols), np.array(b)


def _pesos(h, lam, max_weight=0.30):
    mu_qp, cov_qp = qm.qp_inputs_at_horizon(MU_M, COV_M, h)
    n = len(MU_M)
    Amat, bvec = _restricciones(n, max_weight)
    sol = quadprog.solve_qp(cov_qp + np.eye(n) * 1e-8 * h, mu_qp / lam, Amat, bvec, 1)
    w = np.maximum(sol[0], 0)
    return w / w.sum()


@pytest.mark.parametrize("h", [1, 2])
def test_qp_inputs_escalan_media_y_covarianza_por_h(h):
    mu_h, cov_h = qm.qp_inputs_at_horizon(MU_M, COV_M, h)
    np.testing.assert_allclose(mu_h, MU_M * h)
    np.testing.assert_allclose(cov_h, COV_M * h)
    assert cov_h.shape == COV_M.shape


def test_qp_inputs_h1_es_identidad():
    mu_1, cov_1 = qm.qp_inputs_at_horizon(MU_M, COV_M, 1)
    np.testing.assert_array_equal(mu_1, MU_M)
    np.testing.assert_array_equal(cov_1, COV_M)


@pytest.mark.parametrize("lam", [0.5, 1.5, 3.0, 6.0, 50.0])
@pytest.mark.parametrize("max_weight", [0.22, 0.30, 1.0])
def test_pesos_del_qp_no_dependen_del_horizonte(lam, max_weight):
    w1 = _pesos(1, lam, max_weight)
    w2 = _pesos(2, lam, max_weight)
    np.testing.assert_allclose(w1, w2, atol=1e-7)
    assert w2.max() <= max_weight + 1e-7


def test_utilidad_y_penalizacion_relativa_escalan_igual():
    w = _pesos(1, 1.5)
    mu_2, cov_2 = qm.qp_inputs_at_horizon(MU_M, COV_M, 2)
    t1 = qm.utility_terms(w @ MU_M, w @ COV_M @ w, 1.5)
    t2 = qm.utility_terms(w @ mu_2, w @ cov_2 @ w, 1.5)
    assert t2["utility"] == pytest.approx(2 * t1["utility"])
    assert t2["risk_term"] / t2["mu_term"] == pytest.approx(t1["risk_term"] / t1["mu_term"])


def test_cf_h1_es_el_var_mensual_de_antes():
    antes = rk.var_cvar_cornish_fisher(0.01, 0.05, -0.4, 1.2, confidence=0.95)
    ahora = qm.cornish_fisher_at_horizon(0.01, 0.05, -0.4, 1.2, 1, confidence=0.95)
    assert ahora["var"] == pytest.approx(antes["var"])
    assert ahora["cvar"] == pytest.approx(antes["cvar"])
    assert ahora["horizon_months"] == 1


def test_cf_h2_usa_scale_moments():
    out = qm.cornish_fisher_at_horizon(0.01, 0.05, -0.4, 1.2, 2, confidence=0.95)
    ref = rk.var_cvar_cornish_fisher(0.02, 0.05 * math.sqrt(2), -0.4 / math.sqrt(2), 0.6,
                                     confidence=0.95)
    assert out["mu_h"] == pytest.approx(0.02)
    assert out["sd_h"] == pytest.approx(0.05 * math.sqrt(2))
    assert out["skew_h"] == pytest.approx(-0.4 / math.sqrt(2))
    assert out["exkurt_h"] == pytest.approx(0.6)
    assert out["var"] == pytest.approx(ref["var"])
    assert out["cvar"] == pytest.approx(ref["cvar"])


def test_cf_gaussiano_escala_con_raiz_de_h():
    v1 = qm.cornish_fisher_at_horizon(0.0, 0.05, 0.0, 0.0, 1)["var"]
    v2 = qm.cornish_fisher_at_horizon(0.0, 0.05, 0.0, 0.0, 2)["var"]
    assert v2 == pytest.approx(v1 * math.sqrt(2))


def test_cf_sin_momentos_da_nan():
    out = qm.cornish_fisher_at_horizon(0.01, 0.05, np.nan, np.nan, 2)
    assert np.isnan(out["var"]) and np.isnan(out["cvar"])


@pytest.mark.parametrize("script", SCRIPTS)
def test_scripts_usan_el_horizonte_en_qp_y_cf(script):
    fuente = (ROOT / script).read_text(encoding="utf-8")
    assert "mu_qp, cov_qp = qm.qp_inputs_at_horizon(mu_final, cov_mat, horizon_months)" in fuente
    assert "dvec = mu_qp / lambda_" in fuente
    assert "Dmat = cov_qp + np.eye(n) * qp_nugget" in fuente
    assert "dv = mu_qp / lambda_val" in fuente
    assert "qm.cornish_fisher_at_horizon(" in fuente
    assert "rk.var_cvar_cornish_fisher(" not in fuente
    assert fuente.count("horizonte {horizon_months}m): {var_cf") == 2
    i_qp = fuente.index("mu_qp, cov_qp = qm.qp_inputs_at_horizon(")
    assert i_qp < fuente.index("sol = quadprog.solve_qp(Dmat, dvec, Amat, bvec, meq)")


@pytest.mark.parametrize("script", SCRIPTS)
def test_json_del_portafolio_sale_de_la_misma_variable(script):
    fuente = (ROOT / script).read_text(encoding="utf-8")
    assert re.search(r'"horizon_months": horizon_months,', fuente)
    assert "horizon_days=_h_days" in fuente and "horizon_end=_h_end" in fuente
    if "seasonal" in script:
        assert "horizon_months = len(rebalance_months)" in fuente
        assert "pipeline_io.horizon_from_month_list(as_of_date, rebalance_months)" in fuente
    else:
        assert "pipeline_io.horizon_from_months(as_of_date, horizon_months)" in fuente
