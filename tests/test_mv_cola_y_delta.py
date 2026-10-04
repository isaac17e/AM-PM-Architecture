"""minimum_variance (normal y estacional): fallback historico de cola y filtro delta OTM.

1. tail_risk_hist_fallback = True: los nombres sin opciones en EE. UU.
   (internacionales) pasan el filtro de cola con momentos historicos en vez
   de caer por falta de BKM.
2. Filtro delta con el diseno de QU: colchon = delta(K=S) - delta(K=S e^m),
   m = 0.08 sqrt(T / 2 meses), T = horizonte del script. Solo filtra.
"""

import ast
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import kurtosis, skew

import qu_metrics as qm
import risk_estimators as rk

ROOT = Path(__file__).resolve().parents[1]
MV = "minimum_variance.py"
MV_EST = "minimum_variance_(seasonal_version).py"
SCRIPTS = [MV, MV_EST]
_R = 0.047
_T_REF = 2 / 12

_VOLS = [
    0.14, 0.15, 0.16, 0.16, 0.17, 0.18, 0.18, 0.19,
    0.20, 0.21, 0.22, 0.22, 0.23, 0.24, 0.24, 0.25, 0.26, 0.26, 0.27, 0.28, 0.28, 0.29, 0.30,
    0.32, 0.33, 0.34, 0.35, 0.36, 0.38, 0.40, 0.42, 0.44, 0.46,
    0.48, 0.50, 0.52, 0.55, 0.58, 0.62, 0.66, 0.70, 0.75, 0.80, 0.85, 0.90,
]


def _fuente(nombre):
    return (ROOT / nombre).read_text(encoding="utf-8")


def _funcion(fuente, nombre):
    for node in ast.parse(fuente).body:
        if isinstance(node, ast.FunctionDef) and node.name == nombre:
            return ast.get_source_segment(fuente, node)
    raise AssertionError(f"{nombre} no esta en el script")


def _tramo(fuente, desde, hasta):
    i0 = fuente.index(desde)
    return fuente[i0:fuente.index(hasta, i0)]


# ------------------------------------------------------------------------------
# 1. Fallback historico del filtro de cola
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("nombre", SCRIPTS)
def test_fallback_historico_activo_por_defecto(nombre):
    assert re.search(r"^tail_risk_hist_fallback = True\b", _fuente(nombre), re.M)


def _bucle_de_cola(nombre, fallback):
    """Corre el bucle de cola del script con BKM vacio para los internacionales."""
    fuente = _fuente(nombre)
    rng = np.random.default_rng(7)
    idx = pd.date_range("2018-01-07", periods=420, freq="W")
    tickers = ["AAPL", "RY.TO", "7203.T", "AZN.L"]
    log_returns = pd.DataFrame(rng.normal(0.002, 0.025, (len(idx), len(tickers))), index=idx, columns=tickers)

    def bkm(ticker):
        if ticker == "AAPL":
            return dict(ok=True, mfiv=0.006, mfis=-0.4, mfik=4.0, dte=30, motivo=None)
        return dict(ok=False, mfiv=np.nan, mfis=np.nan, mfik=np.nan, dte=np.nan,
                    motivo="sin_opciones_en_polygon (no cotiza en EE. UU.)")

    ns = dict(
        np=np, pd=pd, math=math, rk=rk, skew=skew, kurtosis=kurtosis,
        selected_pre_seasonal=tickers, log_returns=log_returns,
        bkm_get_current_moments_cached=bkm, tail_risk_hist_fallback=fallback,
        annualization_factor=52, target_dte_iv=30, bkm_mfik_max=20.0,
        use_q_to_p_vol=True, vrp_ratio_bounds=(0.70, 1.00), vrp_fallback_ratio=0.90,
        tail_risk_filter_confidence=0.95, tail_risk_min_hist_weeks=26, seasonal_min_weeks=10,
        execution_months=[10],
    )
    ns["hv_min_obs_weeks"] = ns["tail_risk_min_hist_weeks"]
    if nombre == MV_EST:
        ns["log_returns_seasonal"] = log_returns.loc[log_returns.index.month.isin([10]), tickers]
    exec(_funcion(fuente, "momentos_cola_historicos"), ns)
    exec(_tramo(fuente, "tail_risk_rows = []\n", "n_con_tail = len(tail_risk_stats)"), ns)
    return ns["tail_risk_stats"]


@pytest.mark.parametrize("nombre", SCRIPTS)
def test_internacionales_pasan_la_cola_con_vol_historica(nombre):
    stats = _bucle_de_cola(nombre, fallback=True)
    fuente = dict(zip(stats["Symbol"], stats["Fuente"]))
    assert fuente["AAPL"] == "BKM"
    for t in ("RY.TO", "7203.T", "AZN.L"):
        assert fuente[t] == "Historico"
    assert stats["VaR_CF"].notna().all()


@pytest.mark.parametrize("nombre", SCRIPTS)
def test_sin_fallback_los_internacionales_se_descartaban(nombre):
    stats = _bucle_de_cola(nombre, fallback=False)
    assert stats["Symbol"].tolist() == ["AAPL"]


# ------------------------------------------------------------------------------
# 2. Filtro delta OTM
# ------------------------------------------------------------------------------

def _descartes(years, umbral):
    nombres = [f"N{i}" for i in range(len(_VOLS))]
    df = qm.filtro_delta_otm(nombres, {}, dict(zip(nombres, _VOLS)), years, _R, umbral,
                             log_m=0.08, ref_years=_T_REF)
    return int((~df["pasa"]).sum())


def test_conteos_por_umbral_conservador_moderado_agresivo():
    d15, d18, d24 = (_descartes(1 / 12, u) for u in (0.15, 0.18, 0.24))
    assert 0 < d15 < d18 < d24 < len(_VOLS)


@pytest.mark.parametrize("umbral", [0.15, 0.18, 0.24])
def test_conteo_estable_entre_horizontes(umbral):
    # sqrt(T / T_ref) mantiene el corte parecido a 1, 2 y 3 meses.
    d1, d2, d3 = (_descartes(m / 12, umbral) for m in (1, 2, 3))
    assert max(d1, d2, d3) - min(d1, d2, d3) <= 2


def test_horizonte_cambia_la_moneyness_efectiva():
    assert qm.otm_log_moneyness(0.08, 2 / 12, _T_REF) == pytest.approx(0.08)
    assert qm.otm_log_moneyness(0.08, 1 / 12, _T_REF) == pytest.approx(0.08 * math.sqrt(0.5))


def test_nombres_sin_vol_se_conservan_y_polygon_manda_sobre_historica():
    df = qm.filtro_delta_otm(
        ["AAPL", "TSLA", "RY.TO", "NUEVO"],
        iv_polygon={"AAPL": 0.22, "TSLA": 0.95, "RY.TO": np.nan},
        vol_hist={"AAPL": 0.90, "TSLA": 0.20, "RY.TO": 0.18},
        years=1 / 12, rate=_R, delta_min=0.15, log_m=0.08, ref_years=_T_REF,
    ).set_index("symbol")
    assert df.loc["AAPL", "strike_mode"] == "bs_otm_polygon_iv"
    assert df.loc["AAPL", "iv_used"] == pytest.approx(0.22)
    assert df.loc["AAPL", "pasa"]
    assert df.loc["TSLA", "strike_mode"] == "bs_otm_polygon_iv"
    assert not df.loc["TSLA", "pasa"]
    assert df.loc["RY.TO", "strike_mode"] == "bs_otm_hist"
    assert df.loc["RY.TO", "pasa"]
    assert df.loc["NUEVO", "strike_mode"] == "sin_datos"
    assert math.isnan(df.loc["NUEVO", "delta"])
    assert df.loc["NUEVO", "pasa"]
    assert df.loc["AAPL", "delta"] == pytest.approx(qm.delta_cushion(0.22, 1 / 12, _R, 0.08, ref_years=_T_REF))


@pytest.mark.parametrize("nombre", SCRIPTS)
def test_defaults_del_filtro_delta_en_mv(nombre):
    fuente = _fuente(nombre)
    assert re.search(r"^use_delta_filter = True\b", fuente, re.M)
    assert re.search(r"^delta_min = 0\.15\b", fuente, re.M)
    assert "Conservador 0.24, moderado 0.18, agresivo 0.15" in fuente
    assert re.search(r"^delta_otm_log_m = 0\.08\b", fuente, re.M)
    assert re.search(r"^delta_otm_ref_months = 2\b", fuente, re.M)
    # La tabla de griegas sigue con la delta real de la call ATM.
    assert re.search(r'^delta_strike_mode = "atm"', fuente, re.M)


@pytest.mark.parametrize("nombre", SCRIPTS)
def test_filtro_delta_va_antes_de_la_cola_y_solo_filtra(nombre):
    fuente = _fuente(nombre)
    i_iv = fuente.index("iv_cache = {t: get_atm_iv_safe(t) for t in selected_pre_seasonal}")
    i_delta = fuente.index("delta_df = qm.filtro_delta_otm(")
    i_cola = fuente.index("tail_risk_rows = []")
    assert i_iv < i_delta < i_cola
    assert "T_delta = horizon_months / 12" in fuente
    bloque = _tramo(fuente, "if use_delta_filter:", "tail_risk_rows = []")
    assert 'selected_pre_seasonal = delta_df.loc[delta_df["pasa"], "symbol"].tolist()' in bloque
    # Solo filtra: no hay escalado de retornos por delta.
    assert not re.search(r"(mu|retorno|return)\w*\s*\*=?\s*\w*delta", fuente, re.I)


def test_horizonte_estacional_son_los_meses_de_ejecucion():
    fuente = _fuente(MV_EST)
    assert "horizon_months = len(execution_months)" in fuente
    i_h = fuente.index("horizon_months = len(execution_months)")
    assert i_h < fuente.index("T_delta = horizon_months / 12")
