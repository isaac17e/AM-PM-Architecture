"""E-1 en quadratic_utility_(seasonal_version).py: piso de ETF alcanzable.

Caso real (perfil conservador, oct-2026): banda 0.55 +/- 0.10 con
max_weight 0.12. Llegaban solo FXI, GLD y MCHI (3 x 12% = 36% < 45%): el
filtro delta sacaba a PDBC y el MFIS (BKM) a XLU, y quadprog fallaba con
"constraints are inconsistent". Ahora se completa el piso con ETF que pasan
los filtros duros y, si aun asi no alcanza, se relaja la banda con aviso.
"""

import ast
import re
from pathlib import Path

import numpy as np
import pytest
import quadprog

import qu_metrics as qm

ROOT = Path(__file__).resolve().parents[1]
NOMBRE = "quadratic_utility_(seasonal_version).py"
FUENTE = (ROOT / NOMBRE).read_text(encoding="utf-8")
ETF = {"FXI", "GLD", "MCHI", "PDBC", "XLU", "TLT", "SLV", "IEF", "SPY"}


# ------------------------------------------------------------------------------
# Bloque de restricciones del script, ejecutado tal cual
# ------------------------------------------------------------------------------

def _bloque_restricciones():
    """Desde la banda de ETF hasta justo antes de quadprog.solve_qp."""
    i0 = FUENTE.index("etf_band_active = include_etfs_in_portfolio")
    i1 = FUENTE.index("try:\n    sol = quadprog.solve_qp(Dmat, dvec, Amat, bvec, meq)")
    return FUENTE[i0:i1]


def _correr_restricciones(assets, *, piso_relajable=True, mw=0.12, deseado=0.55, tol=0.10):
    n = len(assets)
    ns = dict(
        np=np, qm=qm, n=n, assets=list(assets),
        etf_commodity_assets=[i for i, a in enumerate(assets) if a in ETF],
        stock_assets=[i for i, a in enumerate(assets) if a not in ETF],
        excluded_etf_set=set(), canada_assets=[], europe_assets=[], japan_assets=[],
        include_etfs_in_portfolio=True, pct_etf_deseado=deseado, pct_etf_tolerancia=tol,
        max_weight=mw, max_region_weight=0.80,
        etf_band_relax_if_infeasible=piso_relajable,
    )
    exec(_bloque_restricciones(), ns)
    rng = np.random.default_rng(1)
    X = rng.normal(size=(80, n))
    D = np.cov(X, rowvar=False) + np.eye(n) * 1e-6
    w = quadprog.solve_qp(D, np.full(n, 0.01), ns["Amat"], ns["bvec"], ns["meq"])[0]
    return ns, w


ACCIONES = ["IBE.MC", "NEE", "PFE", "AEP", "DB1.DE", "COST", "KO", "PM",
            "ABBV", "GILD", "OR.PA", "WCN.TO", "SAP.TO"]


def test_parametros_del_piso_en_el_estacional():
    assert re.search(r"^etf_band_relax_if_infeasible = True\b", FUENTE, re.M)
    assert re.search(r"^etf_floor_reserve_factor = 3\b", FUENTE, re.M)
    assert "n_etf_needed = qm.etfs_necesarios(etf_band_floor_cfg, max_weight)" in FUENTE


def test_caso_conservador_tal_como_llegaba_es_infactible_para_quadprog():
    assets = ["FXI", "GLD", "MCHI"] + ACCIONES
    n = len(assets)
    # Restricciones viejas: misma banda, sin chequeo previo.
    etf_idx = [0, 1, 2]
    cols, b = [np.ones(n)], [1.0]
    for i in range(n):
        v = np.zeros(n); v[i] = 1; cols.append(v); b.append(0.0)
    for i in range(n):
        v = np.zeros(n); v[i] = -1; cols.append(v); b.append(-0.12)
    v = np.zeros(n); v[etf_idx] = 1; cols.append(v); b.append(0.45)
    A, bv = np.column_stack(cols), np.array(b)
    assert not qm.restricciones_factibles(A, bv, 1)
    with pytest.raises(ValueError, match="inconsistent"):
        quadprog.solve_qp(np.eye(n), np.zeros(n), A, bv, 1)


def test_con_el_cuarto_etf_el_conservador_resuelve_sin_relajar(capsys):
    assets = ["FXI", "GLD", "MCHI", "TLT"] + ACCIONES
    ns, w = _correr_restricciones(assets)
    assert not ns["etf_band_relaxed"]
    assert (ns["etf_lo"], ns["etf_hi"]) == pytest.approx((0.45, 0.65))
    etf = ns["etf_commodity_assets"]
    assert w[etf].sum() >= 0.45 - 1e-8
    assert w[etf].sum() <= 0.65 + 1e-8
    assert w.max() <= 0.12 + 1e-8
    assert "ADVERTENCIA" not in capsys.readouterr().out


def test_sin_cuarto_etf_la_banda_se_relaja_y_quadprog_resuelve(capsys):
    assets = ["FXI", "GLD", "MCHI"] + ACCIONES
    ns, w = _correr_restricciones(assets)
    salida = capsys.readouterr().out
    assert ns["etf_band_relaxed"]
    assert ns["etf_lo"] == pytest.approx(0.36)
    assert w[ns["etf_commodity_assets"]].sum() == pytest.approx(0.36, abs=1e-6)
    assert "piso de ETF 45% inalcanzable: 3 ETF x max_weight 0.12 = 36%" in salida
    assert "al menos 4 ETF" in salida
    assert "FXI, GLD, MCHI" in salida
    assert "45%-65% -> 36%-65%" in salida


def test_sin_relajar_falla_con_mensaje_claro_y_no_con_quadprog():
    assets = ["FXI", "GLD", "MCHI"] + ACCIONES
    with pytest.raises(RuntimeError, match=r"infactibles \(piso de ETF 45% inalcanzable") as exc:
        _correr_restricciones(assets, piso_relajable=False)
    assert "activa etf_band_relax_if_infeasible" in str(exc.value)


def test_banda_que_ya_cumplia_no_cambia(capsys):
    # Perfil agresivo por defecto: 0.10 +/- 0.10 con max_weight 0.30.
    assets = ["GLD"] + ACCIONES
    ns, w = _correr_restricciones(assets, mw=0.30, deseado=0.10, tol=0.10)
    assert not ns["etf_band_relaxed"]
    assert (ns["etf_lo"], ns["etf_hi"]) == pytest.approx((0.0, 0.20))
    assert "ADVERTENCIA" not in capsys.readouterr().out
    assert qm.etfs_necesarios(0.0, 0.30) == 0


# ------------------------------------------------------------------------------
# Flujo de seleccion: reserva, filtro estacional y reposicion de MFIS
# ------------------------------------------------------------------------------

def test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados():
    """Mismo orden de helpers que el script estacional."""
    n_needed = qm.etfs_necesarios(0.45, 0.12)
    assert n_needed == 4
    # Pre-filtro QUBO: 4 ETF; PDBC cae por delta.
    ranking = ["IBE.MC", "FXI", "GLD", "AEP", "PDBC", "MCHI", "XLU", "COST", "TLT", "KO", "SLV", "IEF"]
    pre = ["IBE.MC", "FXI", "GLD", "AEP", "PDBC", "MCHI", "XLU", "COST", "KO"]
    reserva = qm.reserva_etf(ranking, pre, ETF, 3 * n_needed)
    assert reserva == ["TLT", "SLV", "IEF"]
    falla_delta = {"PDBC", "SLV"}
    reserva = [t for t in reserva if t not in falla_delta]
    post_delta = [t for t in pre if t not in falla_delta]

    # Filtro estacional: queda todo el post-delta (5 ETF con XLU).
    orden_estacional = ["IBE.MC", "XLU", "FXI", "GLD", "AEP", "MCHI", "COST", "KO"]
    orden_etf = orden_estacional + reserva
    keep = list(orden_estacional)
    assert qm.contar_etfs(keep, ETF) == 4
    assert qm.completar_etfs(keep, qm.candidatos_reposicion(orden_etf, keep), ETF, n_needed) == []

    # BKM saca a XLU: la reposicion trae un ETF de la reserva, no una accion.
    pool = qm.candidatos_reposicion(orden_estacional, keep)
    pool_etf = qm.candidatos_reposicion(orden_etf, keep)
    full_set = [t for t in keep if t != "XLU"]
    usados = set()
    reemplazo = None
    if qm.contar_etfs(full_set, ETF) < n_needed:
        reemplazo = qm.siguiente_reposicion(pool_etf, usados | set(full_set), ETF, solo_etf=True)
    assert reemplazo == "TLT"
    full_set.append(reemplazo)
    assert qm.contar_etfs(full_set, ETF) == n_needed
    assert not {"PDBC", "SLV", "XLU"} & set(full_set)
    assert pool == []


def test_script_estacional_cablea_reserva_rellenos_y_reposicion():
    assert "return selected, list(df_candidates[\"symbol\"])" in FUENTE
    assert "etf_reserva = qm.reserva_etf(prefilter_ranking + _orden_eleg" in FUENTE
    # La reserva pasa por Polygon y por el mismo filtro delta.
    assert "_delta_universo = list(dict.fromkeys(ticker_candidates + etf_reserva))" in FUENTE
    assert "qm.pasa_filtro_delta(d, delta_min)), \"symbol\"].tolist()" in FUENTE
    assert "etf_piso_agregados = qm.completar_etfs(seasonal_keep, pool_etf_piso" in FUENTE
    assert "reponer_pool_bkm_etf = qm.candidatos_reposicion(orden_reposicion_etf" in FUENTE
    assert "reponer_pool_bkm_etf, ocupados_bkm, etf_group_set, solo_etf=True)" in FUENTE
    i_chk = FUENTE.index("qm.restricciones_factibles(Amat, bvec, meq)")
    i_qp = FUENTE.index("sol = quadprog.solve_qp(Dmat, dvec, Amat, bvec, meq)")
    assert i_chk < i_qp
    # Sin duplicar los helpers: el script no redefine los de qu_metrics.
    definidas = {n.name for n in ast.parse(FUENTE).body if isinstance(n, ast.FunctionDef)}
    assert not definidas & {"etfs_necesarios", "reserva_etf", "completar_etfs",
                            "restricciones_factibles", "relajar_banda_etf"}
