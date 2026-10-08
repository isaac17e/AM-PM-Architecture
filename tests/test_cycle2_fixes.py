"""Ciclo 2: RISK_FREE_RATE por env, delta_raw en el log y cola / presupuesto / cache del MFIS. Sin red."""

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import requests

import pipeline_io
import polygon_client as pc
import qu_metrics as qm
import risk_estimators as rk

ROOT = Path(__file__).resolve().parents[1]
OPTIMIZADORES = {
    "minimum_variance.py": ("risk_free_rate", "0.047"),
    "minimum_variance_(seasonal_version).py": ("risk_free_rate", "0.047"),
    "quadratic_utility.py": ("rf_rate", "0.047"),
    "quadratic_utility_(seasonal_version).py": ("rf_rate", "0.047"),
    "black_litterman.py": ("Rf", "0.046"),
}


# ------------------------------------------------------------------------------
# RISK_FREE_RATE
# ------------------------------------------------------------------------------

def test_risk_free_rate_sin_env_usa_el_default():
    assert pipeline_io.resolve_risk_free_rate(0.047, env={}) == 0.047
    assert pipeline_io.resolve_risk_free_rate(0.046, env={"RISK_FREE_RATE": "  "}) == 0.046


def test_risk_free_rate_env_sobreescribe(monkeypatch):
    monkeypatch.setenv("RISK_FREE_RATE", "0.052")
    assert pipeline_io.resolve_risk_free_rate(0.047) == pytest.approx(0.052)
    assert pipeline_io.resolve_risk_free_rate(0.047, env={"RISK_FREE_RATE": "0"}) == 0.0


@pytest.mark.parametrize("valor", ["abc", "5.2", "0.5", "-0.01", "nan", "inf"])
def test_risk_free_rate_invalida_lanza_error_claro(valor):
    with pytest.raises(ValueError, match="RISK_FREE_RATE"):
        pipeline_io.resolve_risk_free_rate(0.047, env={"RISK_FREE_RATE": valor})


@pytest.mark.parametrize("script", sorted(OPTIMIZADORES))
def test_optimizadores_leen_la_tasa_del_env_y_la_exportan(script):
    variable, default = OPTIMIZADORES[script]
    fuente = (ROOT / script).read_text(encoding="utf-8")
    assert f"{variable} = pipeline_io.resolve_risk_free_rate({default})" in fuente
    assert fuente.count("resolve_risk_free_rate(") == 1
    assert f'"risk_free_rate": {variable},' in fuente
    # El valor literal ya no se asigna en ningun otro lado.
    assert f"{variable} = {default}" not in fuente


# ------------------------------------------------------------------------------
# delta_raw en el log del shrinkage
# ------------------------------------------------------------------------------

def test_texto_delta_shrinkage_muestra_delta_raw_y_cota():
    texto = rk.texto_delta_shrinkage({"delta": 0.212, "delta_raw": 0.245, "delta_max": 0.9})
    assert texto == "delta shrinkage: 0.212 (delta_raw: 0.245, cota delta_max: 0.90)"
    recortado = rk.texto_delta_shrinkage({"delta": 0.9, "delta_raw": 1.3, "delta_max": 0.9})
    assert "delta_raw: 1.300" in recortado and "recortado a la cota" in recortado
    assert rk.texto_delta_shrinkage({"delta": 0.0}) == "delta shrinkage: 0.000"


def test_texto_delta_shrinkage_con_info_real():
    rng = np.random.default_rng(0)
    rets = pd.DataFrame(rng.normal(0, 0.01, size=(200, 4)), columns=list("ABCD"))
    _cov, info = rk.cov_ewma_shrunk(rets, halflife=60)
    texto = rk.texto_delta_shrinkage(info)
    assert f"delta shrinkage: {info['delta']:.3f}" in texto
    assert f"delta_raw: {info['delta_raw']:.3f}" in texto
    assert "cota delta_max" in texto


@pytest.mark.parametrize("script", sorted(OPTIMIZADORES))
def test_scripts_imprimen_delta_raw(script):
    fuente = (ROOT / script).read_text(encoding="utf-8")
    assert "rk.texto_delta_shrinkage(" in fuente
    assert "delta shrinkage: {cov_info" not in fuente


# ------------------------------------------------------------------------------
# MFIS: presupuesto por env, cola por relevancia, cache
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("valor,esperado", [
    (None, 60), ("", 60), ("90", 90.0), ("12.5", 12.5),
    ("0", None), ("unlimited", None), ("abc", 60), ("-5", 60),
])
def test_mfis_max_minutes_from_env(valor, esperado):
    env = {} if valor is None else {"MFIS_MAX_MINUTES": valor}
    assert qm.mfis_max_minutes_from_env(60, env=env) == esperado


def test_calls_per_min_alias_y_sin_tope(monkeypatch):
    monkeypatch.delenv("POLYGON_CALLS_PER_MINUTE", raising=False)
    monkeypatch.setenv("POLYGON_CALLS_PER_MIN", "1000")
    assert pc.calls_per_minute_from_env() == 1000.0
    monkeypatch.setenv("POLYGON_CALLS_PER_MIN", "unlimited")
    assert pc.calls_per_minute_from_env() is None


def test_orden_prioridad_mfis_por_market_cap_y_ranking():
    candidatos = ["XLU", "KO", "LLY", "BRK-B", "NG.L", "GLD", "T"]
    caps = {"LLY": 8.0e11, "KO": 2.9e11, "BRK.B": 1.0e12, "T": 1.9e11}
    orden = qm.orden_prioridad_mfis(candidatos, caps, ranking=["GLD", "XLU"])
    assert orden == ["BRK-B", "LLY", "KO", "T", "GLD", "XLU", "NG.L"]
    assert sorted(orden) == sorted(candidatos)
    assert qm.orden_prioridad_mfis(["B", "A", "B"]) == ["B", "A"]


def test_corte_de_presupuesto_deja_fuera_a_los_menos_relevantes():
    candidatos = [f"S{i}" for i in range(6)] + ["LLY"]
    caps = {t: 1e9 * (i + 1) for i, t in enumerate(candidatos[:-1])}
    caps["LLY"] = 8e11
    orden = qm.orden_prioridad_mfis(candidatos, caps)
    ranked = [{"ticker": t, "us": True, "mfis_ok": True, "n_pending": 10} for t in orden]
    plan = qm.plan_bkm_history_budget(
        ranked, contracts_per_date=26, calls_per_min=100, max_minutes=8.1, spent_calls=0)
    assert plan["procesar"] == ["LLY", "S5", "S4"]
    assert {o["ticker"] for o in plan["omitidos"]} == {"S3", "S2", "S1", "S0"}


@pytest.fixture
def polygon_aislado(monkeypatch, tmp_path):
    monkeypatch.setattr(pc, "API_KEY", "K")
    monkeypatch.setattr(pc, "CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(pc.time, "sleep", lambda s: None)
    for k in ("http_calls", "cache_hits"):
        pc.diag[k] = 0
    tope = pc.CALLS_PER_MIN
    pc.set_rate_limit(None)
    yield
    pc.set_rate_limit(tope)


class _Resp:
    status_code = 200
    headers = {}

    def __init__(self, data):
        self._data = data
        self.text = json.dumps(data)

    def json(self):
        return self._data


def test_cache_de_disco_evita_llamadas_en_la_reejecucion(monkeypatch, polygon_aislado):
    llamadas = []

    def _get(url, timeout):
        llamadas.append(url)
        return _Resp({"results": [{"t": 1_700_000_000_000, "c": 2.5}]})
    monkeypatch.setattr(requests, "get", _get)

    desde = (date.today() - timedelta(days=40)).isoformat()
    hasta = (date.today() - timedelta(days=10)).isoformat()
    primero = pc.fetch_option_aggs("O:LLY261120C00800000", desde, hasta)
    segundo = pc.fetch_option_aggs("O:LLY261120C00800000", desde, hasta)
    assert primero == segundo and primero[0][0]["c"] == 2.5
    assert len(llamadas) == 1
    assert pc.diag["cache_hits"] == 1

    # La entrada MFIS por ticker/fecha (clave v3) de un dia pasado se relee sin red.
    clave = f"mfis_hist_v3|LLY|{(date.today() - timedelta(days=14)).isoformat()}|dte=30"
    assert pc.cache_set(clave, {"S": 800.0, "dte": 30, "calls": [], "puts": []})
    assert pc.cache_get(clave)["S"] == 800.0
    assert len(llamadas) == 1
