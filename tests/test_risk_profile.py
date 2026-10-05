"""Selector de perfil sin red: CLI, env y presets contra los literales vivos."""

import ast
from pathlib import Path

import pytest

import pipeline_io

ROOT = Path(__file__).resolve().parents[1]


def test_resolve_default_si_no_hay_env_ni_cli(monkeypatch):
    monkeypatch.delenv("RISK_PROFILE", raising=False)
    assert pipeline_io.resolve_risk_profile("agresivo", argv=[]) == "agresivo"


def test_resolve_env_y_cli(monkeypatch):
    monkeypatch.setenv("RISK_PROFILE", " Moderado ")
    assert pipeline_io.resolve_risk_profile("agresivo", argv=[]) == "moderado"
    assert pipeline_io.resolve_risk_profile(
        "agresivo", argv=["--risk-profile", "CONSERVADOR"]) == "conservador"
    assert pipeline_io.resolve_risk_profile(
        "agresivo", argv=["--risk-profile=agresivo"]) == "agresivo"


def test_resolve_rechaza_un_nombre_desconocido():
    with pytest.raises(ValueError, match="conservador"):
        pipeline_io.resolve_risk_profile("agresivo", argv=["--risk-profile", "crecimiento"])
    with pytest.raises(ValueError, match="necesita un valor"):
        pipeline_io.resolve_risk_profile("agresivo", argv=["--risk-profile"])


def _presets(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "RISK_PRESETS":
                return ast.literal_eval(node.value)
    raise AssertionError(f"sin RISK_PRESETS en {path.name}")


def _literales(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id in out:
            continue
        try:
            out[target.id] = ast.literal_eval(node.value)
        except (ValueError, TypeError, SyntaxError):
            continue
    return out


@pytest.mark.parametrize("nombre", [
    "minimum_variance.py",
    "minimum_variance_(seasonal_version).py",
    "quadratic_utility.py",
    "quadratic_utility_(seasonal_version).py",
])
def test_preset_agresivo_no_cambia_los_literales(nombre):
    path = ROOT / nombre
    presets = _presets(path)
    assert set(presets) == {"conservador", "moderado", "agresivo"}
    claves = set(presets["agresivo"])
    assert set(presets["moderado"]) == claves
    assert set(presets["conservador"]) == claves
    literales = _literales(path)
    for clave, valor in presets["agresivo"].items():
        assert literales[clave] == valor
    fuente = path.read_text(encoding="utf-8")
    assert "pipeline_io.resolve_risk_profile" in fuente
    assert "risk_profile=RISK_PROFILE" in fuente


def test_presets_de_mv_y_qu_coinciden_con_la_auditoria():
    mv = _presets(ROOT / "minimum_variance.py")
    mv_s = _presets(ROOT / "minimum_variance_(seasonal_version).py")
    qu = _presets(ROOT / "quadratic_utility.py")
    qu_s = _presets(ROOT / "quadratic_utility_(seasonal_version).py")

    assert mv["moderado"]["delta_min"] == 0.18
    assert mv["conservador"]["max_weight_per_asset"] == 0.12
    assert mv["moderado"]["max_assets_in_portfolio"] == 10
    assert mv["agresivo"]["etf_max_weight"] == 0.05
    assert "seasonal_min_weeks" not in mv["agresivo"]
    assert mv_s["conservador"]["seasonal_min_weeks"] == 20
    assert mv_s["moderado"]["seasonal_min_weeks"] == 15
    assert mv_s["agresivo"]["seasonal_min_weeks"] == 10

    assert qu["conservador"]["lambda_"] == 6.0
    assert qu["moderado"]["lambda_"] == 3.0
    assert qu["agresivo"]["lambda_"] == 1.5
    assert qu["moderado"]["volatility_percentile"] == 0.65
    assert qu["moderado"]["pct_etf_deseado"] == 0.30
    assert qu_s["moderado"]["volatility_percentile"] == 0.60
    assert qu_s["moderado"]["pct_etf_deseado"] == 0.40
    assert qu_s["moderado"]["pct_etf_tolerancia"] == 0.05
    assert qu_s["conservador"]["seasonal_min_weeks"] == 40


def test_black_litterman_acepta_el_override_y_exporta_el_perfil():
    fuente = (ROOT / "black_litterman.py").read_text(encoding="utf-8")
    assert 'pipeline_io.resolve_risk_profile("agresivo")' in fuente
    assert "risk_profile=PERFIL_RIESGO" in fuente
