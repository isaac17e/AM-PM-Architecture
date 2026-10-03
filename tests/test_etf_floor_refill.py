"""E-1: piso de ETF alcanzable, reposiciones y factibilidad antes de quadprog.

Caso real (perfil conservador, oct-2026): banda 0.55 +/- 0.10 con
max_weight 0.12 y solo PDBC y MCHI en el optimizador. 2 x 12% = 24% < 45%
y quadprog fallaba con "constraints are inconsistent". MCHI ademas habia
vuelto por la reposicion de MFIS pese a fallar el filtro IV (ratio 1.31).
"""

import re
from pathlib import Path

import numpy as np
import pytest
import quadprog

import qu_metrics as qm

ROOT = Path(__file__).resolve().parents[1]
ETF = {"MCHI", "FXI", "XLU", "PDBC", "GLD", "SPY", "TLT", "SLV"}


# ------------------------------------------------------------------------------
# Restricciones con el mismo formato que quadratic_utility.py
# ------------------------------------------------------------------------------

def _restricciones(n, etf_idx, mw, etf_lo, etf_hi, regiones=(), region_cap=1.0):
    stock_idx = [i for i in range(n) if i not in set(etf_idx)]
    cols, b = [np.ones(n)], [1.0]
    for i in range(n):
        v = np.zeros(n); v[i] = 1
        cols.append(v); b.append(0.0)
    for i in range(n):
        v = np.zeros(n); v[i] = -1
        cols.append(v); b.append(-mw)
    v1 = np.zeros(n); v1[list(etf_idx)] = 1
    v2 = np.zeros(n); v2[list(etf_idx)] = -1
    v3 = np.zeros(n); v3[stock_idx] = 1
    v4 = np.zeros(n); v4[stock_idx] = -1
    cols += [v1, v2, v3, v4]
    b += [etf_lo, -etf_hi, 1 - etf_hi, -(1 - etf_lo)]
    for idx in regiones:
        v = np.zeros(n); v[list(idx)] = -1
        cols.append(v); b.append(-region_cap)
    return np.column_stack(cols), np.array(b)


def _quadprog(Amat, bvec, n):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(60, n))
    D = np.cov(X, rowvar=False) + np.eye(n) * 1e-6
    return quadprog.solve_qp(D, np.full(n, 0.01), Amat, bvec, 1)[0]


# ------------------------------------------------------------------------------
# Cuantos ETF hacen falta
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("piso, mw, esperado", [
    (0.45, 0.12, 4),   # conservador: ceil(3.75)
    (0.22, 0.18, 2),   # moderado
    (0.00, 0.30, 0),   # agresivo: 0.10 - 0.10
    (0.24, 0.12, 2),   # multiplo exacto, sin redondeo de mas
    (0.36, 0.12, 3),
])
def test_etfs_necesarios(piso, mw, esperado):
    assert qm.etfs_necesarios(piso, mw) == esperado


def test_etfs_necesarios_rechaza_max_weight_invalido():
    with pytest.raises(ValueError):
        qm.etfs_necesarios(0.45, 0.0)


def test_contar_etfs_sin_duplicados():
    assert qm.contar_etfs(["PDBC", "IBE.MC", "PDBC", "GLD"], ETF) == 2


# ------------------------------------------------------------------------------
# Reserva y completado del piso de ETF
# ------------------------------------------------------------------------------

def test_reserva_etf_toma_los_que_faltan_en_orden_de_ranking():
    ranking = ["AAPL", "TLT", "PDBC", "MSFT", "SPY", "GLD", "SLV"]
    seleccion = ["PDBC", "AAPL", "MSFT"]
    assert qm.reserva_etf(ranking, seleccion, ETF, 4) == ["TLT", "SPY", "GLD"]


def test_reserva_etf_vacia_si_la_seleccion_ya_alcanza():
    assert qm.reserva_etf(["TLT", "SPY"], ["PDBC", "GLD"], ETF, 2) == []


def test_completar_etfs_agrega_solo_lo_necesario_y_en_orden():
    actuales = ["IBE.MC", "PDBC", "COST"]
    candidatos = ["AEP", "GLD", "TLT", "SPY"]
    assert qm.completar_etfs(actuales, candidatos, ETF, 3) == ["GLD", "TLT"]
    assert qm.completar_etfs(actuales, candidatos, ETF, 1) == []


def test_completar_etfs_devuelve_lo_que_haya_si_no_alcanza():
    assert qm.completar_etfs(["PDBC"], ["GLD", "COST"], ETF, 4) == ["GLD"]


# ------------------------------------------------------------------------------
# Reposiciones: los descartados por IV no vuelven
# ------------------------------------------------------------------------------

ORDEN_VOL_RECIENTE = ["IBE.MC", "MCHI", "FXI", "NEE", "MUV2.DE", "ENB.TO", "PFE",
                      "TRP.TO", "AEP", "DB1.DE", "XLU", "HSBC", "ABBV", "COST", "NG.L",
                      "OR.PA", "WCN.TO", "GILD", "BATS.L", "PM", "PDBC", "SAP.TO",
                      "KO", "GLD"]
DESCARTADOS_IV = {"MCHI", "FXI", "NEE", "PFE", "XLU", "HSBC"}


def test_reposicion_bkm_no_trae_de_vuelta_a_mchi():
    actuales = [t for t in ORDEN_VOL_RECIENTE[:22] if t not in DESCARTADOS_IV]
    pool = qm.candidatos_reposicion(ORDEN_VOL_RECIENTE, actuales, descartados=DESCARTADOS_IV)
    assert "MCHI" not in pool
    assert not (set(pool) & DESCARTADOS_IV)
    assert pool == ["KO", "GLD"]
    # Antes: recent_vol_ratio_stats sin los actuales -> MCHI primero.
    viejo = [t for t in ORDEN_VOL_RECIENTE if t not in actuales]
    assert viejo[0] == "MCHI"


def test_reposicion_aplica_el_filtro_iv_a_quien_nunca_paso_por_el():
    ratios = {"KO": 1.40, "GLD": 0.86}

    def rechaza(t):
        return t in ratios and ratios[t] > 1.15

    pool = qm.candidatos_reposicion(["KO", "GLD", "AEP"], [], rechaza=rechaza)
    assert pool == ["GLD", "AEP"]


def test_siguiente_reposicion_prioriza_etf_cuando_faltan():
    pool = ["KO", "AEP", "GLD", "TLT"]
    assert qm.siguiente_reposicion(pool, set()) == "KO"
    assert qm.siguiente_reposicion(pool, set(), ETF, priorizar_etf=True) == "GLD"
    assert qm.siguiente_reposicion(pool, {"GLD"}, ETF, solo_etf=True) == "TLT"
    assert qm.siguiente_reposicion(pool, {"GLD", "TLT"}, ETF, solo_etf=True) is None
    assert qm.siguiente_reposicion(pool, set(pool)) is None


def test_siguiente_reposicion_sin_etf_coincide_con_el_indice_secuencial():
    pool = ["A", "B", "C"]
    usados, salida = set(), []
    for _ in range(4):
        t = qm.siguiente_reposicion(pool, usados)
        if t is None:
            break
        usados.add(t)
        salida.append(t)
    assert salida == pool


# ------------------------------------------------------------------------------
# Factibilidad antes de quadprog
# ------------------------------------------------------------------------------

def test_caso_conservador_es_infactible_y_quadprog_lo_confirma():
    n = 16
    Amat, bvec = _restricciones(n, [0, 1], 0.12, 0.45, 0.65)
    assert not qm.restricciones_factibles(Amat, bvec, 1)
    with pytest.raises(ValueError, match="inconsistent"):
        _quadprog(Amat, bvec, n)


def test_con_cuatro_etf_el_conservador_es_factible():
    n = 16
    Amat, bvec = _restricciones(n, [0, 1, 2, 3], 0.12, 0.45, 0.65)
    assert qm.restricciones_factibles(Amat, bvec, 1)
    w = _quadprog(Amat, bvec, n)
    assert w[:4].sum() >= 0.45 - 1e-8
    assert w.max() <= 0.12 + 1e-8


def test_factibilidad_considera_el_tope_regional():
    # 10 activos, 6 en una region con tope 0.30: el resto (4 x 0.15) no llena.
    n = 10
    Amat, bvec = _restricciones(n, [0], 0.15, 0.0, 1.0, regiones=[range(4, 10)], region_cap=0.30)
    assert not qm.restricciones_factibles(Amat, bvec, 1)
    Amat2, bvec2 = _restricciones(n, [0], 0.15, 0.0, 1.0, regiones=[range(4, 10)], region_cap=0.50)
    assert qm.restricciones_factibles(Amat2, bvec2, 1)


def test_diagnostico_explica_el_piso_de_etf():
    razones = qm.diagnostico_banda_etf(2, 14, 0.12, 0.45, 0.65)
    assert len(razones) == 1
    assert "piso de ETF 45%" in razones[0]
    assert "2 ETF" in razones[0] and "24%" in razones[0]
    assert "al menos 4 ETF" in razones[0]


def test_diagnostico_vacio_si_los_conteos_alcanzan():
    assert qm.diagnostico_banda_etf(4, 12, 0.12, 0.45, 0.65) == []


def test_relajar_banda_lleva_el_piso_a_lo_alcanzable_y_queda_factible():
    lo, hi = qm.relajar_banda_etf(2, 14, 0.12, 0.45, 0.65)
    assert lo == pytest.approx(0.24)
    assert hi == pytest.approx(0.65)
    Amat, bvec = _restricciones(16, [0, 1], 0.12, lo, hi)
    assert qm.restricciones_factibles(Amat, bvec, 1)
    w = _quadprog(Amat, bvec, 16)
    assert w[:2].sum() == pytest.approx(0.24, abs=1e-6)


def test_relajar_banda_no_toca_una_banda_alcanzable():
    assert qm.relajar_banda_etf(4, 12, 0.12, 0.45, 0.65) == (0.45, 0.65)


def test_relajar_banda_sube_el_techo_si_faltan_acciones():
    lo, hi = qm.relajar_banda_etf(10, 3, 0.12, 0.10, 0.50)
    assert lo == pytest.approx(0.10)
    assert hi == pytest.approx(1 - 3 * 0.12)


# ------------------------------------------------------------------------------
# Cableado en quadratic_utility.py (version normal)
# ------------------------------------------------------------------------------

FUENTE = (ROOT / "quadratic_utility.py").read_text(encoding="utf-8")


def test_script_delta_min_agresivo_es_015():
    assert re.search(r"^delta_min = 0\.15\b", FUENTE, re.M)
    assert "Conservador 0.24, moderado 0.18, agresivo 0.15" in FUENTE


def test_script_reposiciones_excluyen_descartados_por_iv():
    assert FUENTE.count("descartados=iv_descartados, rechaza=rechaza_iv_vs_reciente") >= 4
    assert "reponer_pool_bkm = qm.candidatos_reposicion(" in FUENTE
    assert "reponer_iv_pool = qm.candidatos_reposicion(" in FUENTE


def test_script_chequea_factibilidad_antes_de_quadprog():
    i_chk = FUENTE.index("qm.restricciones_factibles(Amat, bvec, meq)")
    i_qp = FUENTE.index("sol = quadprog.solve_qp(Dmat, dvec, Amat, bvec, meq)")
    assert i_chk < i_qp
    assert re.search(r"^etf_band_relax_if_infeasible = True\b", FUENTE, re.M)
