"""Los scripts no se importan en el resto de la suite.

El bucle `rv, rs, rk = ...` de black_litterman pisaba el alias de
risk_estimators y solo petaba al llegar a Cornish-Fisher, que ningun test
ejecutaba. Aqui se rechaza esa clase de asignacion a nivel de modulo y se
corre black_litterman.py con datos falsos.
"""

import ast
import runpy
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    "black_litterman.py",
    "minimum_variance.py",
    "minimum_variance_(seasonal_version).py",
    "quadratic_utility.py",
    "quadratic_utility_(seasonal_version).py",
]


def _nombres(target):
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        nombres = []
        for elt in target.elts:
            nombres.extend(_nombres(elt))
        return nombres
    if isinstance(target, ast.Starred):
        return _nombres(target.value)
    return []


def _alias_importados(tree):
    nombres = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                nombres.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    nombres.add(alias.asname or alias.name)
    return nombres


def _asignaciones_de_modulo(body, encontrados):
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, ast.Assign):
            for target in node.targets:
                encontrados.extend(_nombres(target))
        elif isinstance(node, ast.AnnAssign):
            encontrados.extend(_nombres(node.target))
        elif isinstance(node, ast.AugAssign):
            encontrados.extend(_nombres(node.target))
        elif isinstance(node, ast.For):
            encontrados.extend(_nombres(node.target))
            _asignaciones_de_modulo(node.body, encontrados)
            _asignaciones_de_modulo(node.orelse, encontrados)
        elif isinstance(node, ast.If):
            _asignaciones_de_modulo(node.body, encontrados)
            _asignaciones_de_modulo(node.orelse, encontrados)
        elif isinstance(node, ast.While):
            _asignaciones_de_modulo(node.body, encontrados)
            _asignaciones_de_modulo(node.orelse, encontrados)
        elif isinstance(node, ast.With):
            _asignaciones_de_modulo(node.body, encontrados)
        elif isinstance(node, ast.Try):
            _asignaciones_de_modulo(node.body, encontrados)
            for handler in node.handlers:
                _asignaciones_de_modulo(handler.body, encontrados)
            _asignaciones_de_modulo(node.orelse, encontrados)
            _asignaciones_de_modulo(node.finalbody, encontrados)


def sombras_de_import(fuente):
    tree = ast.parse(fuente)
    alias = _alias_importados(tree)
    asignados = []
    _asignaciones_de_modulo(tree.body, asignados)
    return sorted({nombre for nombre in asignados if nombre in alias})


def test_function_local_rebind_is_not_a_module_shadow():
    fuente = "import risk_estimators as rk\n\ndef f():\n    rk = 1\n    return rk\n"
    assert sombras_de_import(fuente) == []


def test_module_level_loop_that_rebinds_an_import_is_flagged():
    fuente = "import risk_estimators as rk\nfor tk in []:\n    rv, rs, rk = (1, 2, 3)\n"
    assert sombras_de_import(fuente) == ["rk"]


@pytest.mark.parametrize("nombre", SCRIPTS)
def test_scripts_do_not_shadow_imported_names(nombre):
    fuente = (ROOT / nombre).read_text(encoding="utf-8")
    assert sombras_de_import(fuente) == []


class _YahooFalso:
    def __init__(self, ticker):
        self.ticker = ticker
        idx = pd.bdate_range("2023-06-01", periods=560, tz="UTC")
        rng = np.random.default_rng(abs(hash(ticker)) % (2 ** 32))
        px = 100.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, len(idx))))
        self._hist = pd.DataFrame(
            {"Open": px, "High": px, "Low": px, "Close": px, "Volume": 1_000_000},
            index=idx,
        )
        self._hist.index.name = "Date"

    def history(self, *args, **kwargs):
        return self._hist.copy()

    @property
    def fast_info(self):
        return {"lastPrice": 100.0, "marketCap": 1.0e12}

    @property
    def info(self):
        return {"regularMarketPrice": 100.0, "currentPrice": 100.0, "marketCap": 1.0e12}

    @property
    def history_metadata(self):
        return {"currency": "USD"}


def test_black_litterman_smoke_reaches_cornish_fisher(monkeypatch):
    monkeypatch.setenv("AMPM_SMOKE", "1")
    monkeypatch.setenv("POLYGON_API_KEY", "")
    monkeypatch.setattr("yfinance.Ticker", _YahooFalso)
    monkeypatch.setattr(go.Figure, "show", lambda self, *a, **k: None)
    runpy.run_path(str(ROOT / "black_litterman.py"), run_name="__main__")
