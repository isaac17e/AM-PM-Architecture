"""Exportacion de portafolio y lectura de BL_INPUT_FILE. Sin red."""

import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

import pipeline_io

ROOT = Path(__file__).resolve().parents[1]


def _leer(path):
    texto = Path(path).read_text(encoding="utf-8")
    assert texto.endswith("\n")
    assert "\n  \"schema_version\": 1" in texto
    return json.loads(texto)


def test_export_writes_latest_and_timestamped_copy(tmp_path):
    pesos = pd.Series({"msft": 0.2, "aapl": 0.5, "spy": 1e-8, "qqq": 0.3})
    ruta = pipeline_io.export_portfolio(
        "minimum_variance",
        pesos,
        risk_profile=None,
        horizon_days=31,
        horizon_end=date(2026, 11, 5),
        params={"max_weight_per_asset": 0.35, "shrinkage_max": 0.4, "band": (0.0, 0.05)},
        metrics={"expected_return": 0.08, "volatility": float("nan"), "sharpe": 1.2},
        out_dir=tmp_path,
    )
    data = _leer(ruta)
    assert data["schema_version"] == 1
    assert data["source_repo"] == "AM-PM-Architecture"
    assert data["optimizer"] == "minimum_variance"
    assert data["risk_profile"] is None
    assert data["horizon_days"] == 31
    assert data["horizon_end"] == "2026-11-05"
    assert data["tickers"] == ["AAPL", "QQQ", "MSFT"]
    assert list(data["weights"]) == data["tickers"]
    assert "SPY" not in data["weights"]
    assert sum(int(round(v * 1_000_000)) for v in data["weights"].values()) == 1_000_000
    assert data["params"]["band"] == [0.0, 0.05]
    assert data["metrics"]["expected_return"] == pytest.approx(0.08)
    assert data["metrics"]["volatility"] is None
    assert data["metrics"]["sharpe"] == pytest.approx(1.2)
    assert data["run_ts"].endswith("-05:00")
    assert len(data["run_ts"]) == len("2026-10-05T16:40:12-05:00")
    sello = data["run_ts"][:19].replace("-", "").replace(":", "")
    copia = tmp_path / f"portfolio_minimum_variance_{sello}.json"
    assert copia.read_text(encoding="utf-8") == Path(ruta).read_text(encoding="utf-8")
    assert list(tmp_path.glob("*.tmp")) == []


def test_weights_round_to_six_decimals_and_sum_to_one(tmp_path):
    pipeline_io.export_portfolio(
        "quadratic_utility",
        {"A": 1 / 3, "B": 1 / 3, "C": 1 / 3},
        out_dir=tmp_path,
    )
    data = _leer(tmp_path / "portfolio_latest.json")
    assert sum(Decimal(f"{v:.6f}") for v in data["weights"].values()) == Decimal("1.000000")
    assert all(Decimal(f"{v:.6f}") == Decimal(str(v)) or abs(v - float(f"{v:.6f}")) < 1e-12
               for v in data["weights"].values())


def test_default_dir_and_env(monkeypatch, tmp_path):
    assert pipeline_io.DEFAULT_PORTFOLIO_DIR == "/workspace/pipeline/portfolio"
    monkeypatch.setenv("PORTFOLIO_OUT_DIR", str(tmp_path))
    ruta = pipeline_io.export_portfolio("black_litterman", {"X": 1.0}, out_dir=None)
    assert Path(ruta).parent == tmp_path
    data = _leer(ruta)
    assert data["weights"] == {"X": 1.0}
    assert data["risk_profile"] is None
    assert data["metrics"] == {"expected_return": None, "volatility": None}


def test_unwritable_directory_warns_and_returns_none(tmp_path, capsys):
    bloqueo = tmp_path / "no-es-directorio"
    bloqueo.write_text("x", encoding="utf-8")
    ruta = pipeline_io.export_portfolio(
        "black_litterman", {"A": 0.4, "B": 0.6}, out_dir=bloqueo / "portfolio")
    assert ruta is None
    assert "ADVERTENCIA" in capsys.readouterr().out


def test_write_error_warns(tmp_path, monkeypatch, capsys):
    def boom(path, text):
        raise OSError("read-only")

    monkeypatch.setattr(pipeline_io, "_atomic_write", boom)
    assert pipeline_io.export_portfolio(
        "quadratic_utility_seasonal", {"A": 1}, out_dir=tmp_path) is None
    assert "ADVERTENCIA" in capsys.readouterr().out


def test_atomic_replace(tmp_path, monkeypatch):
    real = os.replace
    vistos = []

    def spy(src, dst):
        vistos.append((src, dst))
        assert str(src).endswith(".tmp")
        assert Path(src).is_file()
        return real(src, dst)

    monkeypatch.setattr(pipeline_io.os, "replace", spy)
    pipeline_io.export_portfolio("minimum_variance_seasonal", [("A", 0.25), ("B", 0.75)], out_dir=tmp_path)
    assert len(vistos) == 2
    assert all(str(dst).endswith(".json") for _, dst in vistos)


def test_horizon_from_months():
    days, end = pipeline_io.horizon_from_months(date(2026, 10, 5), 2)
    assert (days, end) == (61, "2026-12-05")
    days, end = pipeline_io.horizon_from_months(date(2026, 1, 31), 1)
    assert (days, end) == (28, "2026-02-28")


def test_horizon_from_execution_months():
    assert pipeline_io.horizon_from_month_list(date(2026, 10, 5), [10]) == (31, "2026-10-31")
    assert pipeline_io.horizon_from_month_list(date(2026, 10, 5), [11, 12, 1]) == (92, "2027-01-31")
    assert pipeline_io.horizon_from_month_list(date(2026, 12, 15), [11, 12, 1]) == (92, "2027-01-31")
    assert pipeline_io.horizon_from_month_list(date(2026, 2, 1), [10]) == (31, "2026-10-31")
    assert pipeline_io.horizon_from_month_list(date(2024, 2, 10), [2]) == (29, "2024-02-29")


def _escribir(tmp_path, payload, nombre="bl.json"):
    path = tmp_path / nombre
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_bl_input_views_shape(tmp_path):
    ruta = _escribir(tmp_path, {
        "schema_version": 1,
        "tickers": ["dell", "META", "dell"],
        "source": "manager",
        "views": [
            {"name": "View_1", "p": {"DELL": 1, "META": -1}, "q": 0.15},
            {"p": {"AAPL": 1.0}, "q": 0.04},
        ],
    })
    data = pipeline_io.load_bl_input(ruta)
    assert data["tickers"] == ["DELL", "META"]
    assert data["source"] == "manager"
    assert data["views"] == [
        {"name": "View_1", "p": {"DELL": 1.0, "META": -1.0}, "q": 0.15},
        {"name": "View_2", "p": {"AAPL": 1.0}, "q": 0.04},
    ]


def test_bl_input_universe_uses_only_tickers(tmp_path):
    ruta = _escribir(tmp_path, {
        "schema_version": 1,
        "source_repo": "US-Asset-Allocation",
        "source": "Corp_FR_Optimization",
        "tickers": ["AAPL", "MSFT"],
        "details": [{"ticker": "AAPL", "rank": 1, "name": "Apple", "sector": "Tech", "score": 1.2}],
    })
    data = pipeline_io.load_bl_input(ruta)
    assert data["tickers"] == ["AAPL", "MSFT"]
    assert data["views"] is None
    assert data["source"] == "Corp_FR_Optimization"


def test_bl_input_invalid_or_missing(tmp_path, capsys):
    assert pipeline_io.load_bl_input(None) is None
    assert pipeline_io.load_bl_input("  ") is None
    assert capsys.readouterr().out == ""

    faltante = pipeline_io.load_bl_input(str(tmp_path / "no.json"))
    assert faltante is None
    assert "ADVERTENCIA" in capsys.readouterr().out

    malo = _escribir(tmp_path, {"schema_version": 1, "tickers": ["AAPL"], "views": [{"p": {}, "q": 1}]})
    assert pipeline_io.load_bl_input(malo) is None
    assert "invalido" in capsys.readouterr().out

    version = _escribir(tmp_path, {"schema_version": 2, "tickers": ["AAPL"]}, "v2.json")
    assert pipeline_io.load_bl_input(version) is None


def test_select_views_keeps_defaults_only_when_complete():
    defecto = [
        {"name": "View_1", "p": {"DELL": 1.0, "META": -1.0}, "q": 0.15},
        {"name": "View_2", "p": {"GS": 1.0, "REGN": -1.0}, "q": 0.10},
        {"name": "View_3", "p": {"EBAY": 1.0, "ARES": -1.0}, "q": 0.08},
    ]
    kept, skipped = pipeline_io.select_views(defecto, ["dell", "META", "GS"])
    assert [v["name"] for v in kept] == ["View_1"]
    assert kept[0]["p"] == {"dell": 1.0, "META": -1.0}
    assert [s["name"] for s in skipped] == ["View_2", "View_3"]
    assert skipped[0]["missing"] == ["REGN"]


def test_empty_views_list_is_explicit(tmp_path):
    ruta = _escribir(tmp_path, {"tickers": ["AAPL", "MSFT"], "views": []})
    data = pipeline_io.load_bl_input(ruta)
    assert data["views"] == []


def test_scripts_call_export_with_spec_names():
    esperado = {
        "black_litterman.py": "black_litterman",
        "minimum_variance.py": "minimum_variance",
        "minimum_variance_(seasonal_version).py": "minimum_variance_seasonal",
        "quadratic_utility.py": "quadratic_utility",
        "quadratic_utility_(seasonal_version).py": "quadratic_utility_seasonal",
    }
    for nombre, optimizer in esperado.items():
        fuente = (ROOT / nombre).read_text(encoding="utf-8")
        assert "import pipeline_io" in fuente
        assert "pipeline_io.export_portfolio(" in fuente
        assert f'"{optimizer}"' in fuente
    bl = (ROOT / "black_litterman.py").read_text(encoding="utf-8")
    assert "BL_INPUT_FILE" in bl
    assert '"DELL": 1.0, "META": -1.0' in bl
    assert '"q": 0.15' in bl
