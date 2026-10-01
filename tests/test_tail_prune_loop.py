"""Bucle de poda de cola de los scripts de minima varianza.

`prune_order` recibia `w_iter` completo, asi que con `min_weight` elegia un
nombre ya pegado al piso de 0.1%; el print lo buscaba en `active` (que excluye
el piso) y el script moria con KeyError ('UNP', 'TXN'). Ademas, los activos por
debajo de `prune_below_weight` se recortan en bloque si el resto es factible.
Aqui se extrae el `while` real de cada script y se corre con dobles.
"""

import ast
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import portfolio_constraints as pq

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ["minimum_variance.py", "minimum_variance_(seasonal_version).py"]

PISO = 0.001
PESOS = {
    "XLP": 0.12, "GLD": 0.12, "VZ": 0.11, "PPH": 0.10,
    "AAA": 0.05, "BBB": 0.03, "CCC": 0.02,
    "UNP": PISO, "TXN": PISO, "KO": PISO,
}
EN_EL_PISO = {"UNP", "TXN", "KO"}


def _bucle_de_poda(nombre):
    fuente = (ROOT / nombre).read_text(encoding="utf-8")
    for node in ast.parse(fuente).body:
        if isinstance(node, ast.While) and "prune_order" in ast.get_source_segment(fuente, node):
            return ast.get_source_segment(fuente, node)
    raise AssertionError(f"no se encontro el bucle de poda en {nombre}")


def _correr(nombre, regla="min_weight", *, pesos=PESOS, max_assets=4,
            prune_below=0.01, max_weight=1.0):
    ordenes, mensajes = [], []
    tickers = list(pesos)

    def run_minvar_qp(subset):
        return pd.Series({t: pesos[t] for t in subset})

    def compute_marginal_cvar_contrib(subset, w_vec, cm_sub):
        return pd.Series(w_vec * (cm_sub @ w_vec), index=subset)

    class _Espia:
        def __getattr__(self, attr):
            return getattr(pq, attr)

        @staticmethod
        def prune_order(weights, contributions=None, rule="min_weight"):
            orden = pq.prune_order(weights, contributions, rule)
            ordenes.append(orden)
            return orden

    ns = {
        "math": math, "np": np, "pd": pd, "pq": _Espia(),
        "cov_mat": pd.DataFrame(np.eye(len(tickers)), index=tickers, columns=tickers),
        "current_tickers": tickers, "iteration": 0,
        "w_last_valid": None, "tickers_last_valid": None,
        "max_assets_in_portfolio": max_assets, "tail_prune_rule": regla,
        "prune_below_weight": prune_below,
        "max_weight_per_asset": max_weight, "min_total_weight": 1.0,
        "run_minvar_qp": run_minvar_qp,
        "compute_marginal_cvar_contrib": compute_marginal_cvar_contrib,
        "constraints_feasible": lambda remaining: len(remaining) > 0,
        "print": lambda *a, **k: mensajes.append(" ".join(map(str, a))),
    }
    exec(_bucle_de_poda(nombre), ns)
    return ns, ordenes, mensajes


@pytest.mark.parametrize("nombre", SCRIPTS)
@pytest.mark.parametrize("regla", ["min_weight", "max_mtr", "min_weight_x_mtr"])
@pytest.mark.parametrize("prune_below", [0.0, 0.01])
def test_prune_loop_survives_floor_weights(nombre, regla, prune_below):
    ns, ordenes, _ = _correr(nombre, regla, prune_below=prune_below)
    for orden in ordenes:
        assert not EN_EL_PISO & set(orden)
    activos = ns["w_last_valid"][ns["w_last_valid"] > PISO]
    assert len(activos) <= 4


@pytest.mark.parametrize("nombre", SCRIPTS)
def test_min_weight_keeps_capped_defensives(nombre):
    ns, ordenes, _ = _correr(nombre, "min_weight")
    assert len(ordenes) == 3                    # solo AAA/BBB/CCC, nada del piso
    assert set(ns["w_last_valid"].index) == {"XLP", "GLD", "VZ", "PPH"}


@pytest.mark.parametrize("nombre", SCRIPTS)
def test_names_below_threshold_are_cut_in_one_step(nombre):
    pesos = dict(PESOS, DDD=0.005)
    ns, ordenes, mensajes = _correr(nombre, pesos=pesos, max_assets=15)
    assert ordenes == []                        # n_active ya cabe: solo el recorte en bloque
    assert ns["iteration"] == 2
    assert any("Recortando 4 activos" in m for m in mensajes)
    assert (ns["w_last_valid"] >= 0.01).all()
    assert not (EN_EL_PISO | {"DDD"}) & set(ns["w_last_valid"].index)


@pytest.mark.parametrize("nombre", SCRIPTS)
def test_block_cut_is_skipped_when_it_leaves_too_few_names(nombre):
    # 7 activos * 12% < 100%: el recorte en bloque haria el QP infactible.
    ns, ordenes, mensajes = _correr(nombre, max_weight=0.12)
    assert any("no se recortan en bloque" in m for m in mensajes)
    assert not any("Recortando" in m for m in mensajes)
    for orden in ordenes:
        assert not EN_EL_PISO & set(orden)
