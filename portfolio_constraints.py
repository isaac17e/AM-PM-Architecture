# ==============================================================================
# PORTFOLIO_CONSTRAINTS - Restricciones de peso y delta ATM, compartidas
# ==============================================================================
# Extraido de minimum_variance.py y de su version estacional para poder
# probarlo sin ejecutar los scripts:
#
#   1. build_weight_constraints: cotas, inversion total, banda ETF y tope FX
#      en el formato de columnas de quadprog. El optimizador y la frontera
#      eficiente usan el mismo bloque (B-5); antes la frontera solo imponia
#      cotas y suma de pesos.
#   2. bs_call_delta: delta Black-Scholes de una call. Con strike ATM (K = S)
#      y r >= 0 la delta es N(d1) > 0.5, asi que el antiguo filtro
#      "delta >= delta_min" (delta_min = 0.30) no descartaba ningun activo
#      (M-3). Se elimino; esta funcion documenta por que.
# ==============================================================================

import math

import numpy as np
import pandas as pd
from scipy.stats import norm

__all__ = [
    "build_weight_constraints",
    "with_return_target",
    "bs_call_delta",
    "relax_group_band",
    "prune_order",
]


def build_weight_constraints(
    n,
    *,
    min_weight,
    max_weight,
    min_total,
    max_total,
    require_full_investment=False,
    is_etf=None,
    use_etf_band=False,
    etf_min_weight=0.0,
    etf_max_weight=1.0,
    is_non_usd=None,
    use_fx_cap=False,
    max_fx_exposure=1.0,
):
    """Restricciones (Amat, bvec, meq) de quadprog para n activos.

    quadprog impone C.T x >= b y trata las primeras `meq` como igualdades.
    Cada columna de Amat es una restriccion.

    Devuelve dict con base (cotas + inversion total), full (base + banda ETF
    + tope FX, como fraccion del capital invertido) y has_extra.
    """
    n = int(n)
    if n < 1:
        raise ValueError("n debe ser >= 1")

    if require_full_investment or math.isclose(float(min_total), float(max_total)):
        target_total = 1.0 if require_full_investment else float(min_total)
        A_eq = np.ones((n, 1))
        b_eq = np.array([target_total])
        meq = 1
    else:
        A_eq = np.column_stack([np.ones(n), -np.ones(n)])
        b_eq = np.array([float(min_total), -float(max_total)])
        meq = 0

    A_box = np.column_stack([np.eye(n), -np.eye(n)])
    b_box = np.concatenate([np.full(n, min_weight), np.full(n, -max_weight)])

    Amat_base = np.column_stack([A_eq, A_box])
    bvec_base = np.concatenate([b_eq, b_box])

    is_etf_vec = np.zeros(n) if is_etf is None else np.asarray(is_etf, dtype=float)
    is_fx_vec = np.zeros(n) if is_non_usd is None else np.asarray(is_non_usd, dtype=float)
    if is_etf_vec.shape != (n,) or is_fx_vec.shape != (n,):
        raise ValueError("is_etf e is_non_usd deben tener longitud n")

    extra_cols, extra_b = [], []
    if use_etf_band and is_etf_vec.sum() > 0:
        # sum(w_etf) >= etf_min * sum(w)  y  sum(w_etf) <= etf_max * sum(w)
        extra_cols += [is_etf_vec - etf_min_weight, etf_max_weight - is_etf_vec]
        extra_b += [0.0, 0.0]
    if use_fx_cap and is_fx_vec.sum() > 0:
        # sum(w_fx) <= max_fx * sum(w)
        extra_cols += [max_fx_exposure - is_fx_vec]
        extra_b += [0.0]

    Amat_full, bvec_full = Amat_base, bvec_base
    if extra_cols:
        Amat_full = np.column_stack([Amat_base] + extra_cols)
        bvec_full = np.concatenate([bvec_base, extra_b])
    return dict(
        Amat_base=Amat_base, bvec_base=bvec_base,
        Amat_full=Amat_full, bvec_full=bvec_full,
        meq=meq, has_extra=bool(extra_cols),
    )


def with_return_target(cons, expected_returns, target):
    """Anade el retorno objetivo como desigualdad mu'w >= target (B-5).

    No incrementa meq: solo la inversion total (si la hay) sigue siendo
    igualdad. Devuelve (Amat, bvec, meq) listos para quadprog.solve_qp.
    """
    mu = np.asarray(expected_returns, dtype=float)
    if mu.shape != (cons["Amat_full"].shape[0],):
        raise ValueError("expected_returns debe tener un valor por activo")
    Amat = np.column_stack([cons["Amat_full"], mu])
    bvec = np.concatenate([cons["bvec_full"], [float(target)]])
    return Amat, bvec, cons["meq"]


def relax_group_band(n_group, n_other, max_weight, min_share, max_share, total=1.0):
    """Baja el piso de un grupo al maximo alcanzable con el tope por activo.

    Con 2 ETFs y tope 12%, un piso del 30% es imposible (2*12%=24%) y quadprog
    cae en silencio a un problema sin banda. Aqui el piso pasa a ser
    n_grupo * max_weight y la banda sigue activa. Si el complemento no puede
    cubrir `total - techo`, se sube el techo. Sin activos del grupo la banda
    no tiene efecto: min y max vuelven en 0.

    Devuelve (min_usado, max_usado, nota). nota es "" si no hubo que mover nada.
    """
    notas = []
    n_group = int(n_group)
    n_other = int(n_other)
    max_weight = float(max_weight)
    min_share = float(min_share)
    max_share = float(max_share)
    total = float(total)
    if n_group <= 0 or max_weight <= 0:
        return 0.0, 0.0, "sin activos del grupo: banda desactivada"
    cap_group = n_group * max_weight
    if cap_group + 1e-12 < min_share:
        notas.append(
            f"piso {min_share:.2%} inalcanzable con {n_group} activos "
            f"x {max_weight:.2%} = {cap_group:.2%}; se baja el piso a {cap_group:.2%}"
        )
        min_share = cap_group
    cap_other = max(n_other, 0) * max_weight
    necesario = max(0.0, total - cap_other)
    if max_share + 1e-12 < necesario:
        notas.append(
            f"techo {max_share:.2%} deja al resto (max {cap_other:.2%}) corto "
            f"de {total:.2%}; se sube el techo a {necesario:.2%}"
        )
        max_share = necesario
    if min_share > max_share + 1e-12:
        notas.append(
            f"piso {min_share:.2%} supera el techo {max_share:.2%}; se igualan en {max_share:.2%}"
        )
        min_share = max_share
    return float(min_share), float(max_share), "; ".join(notas)


def bs_call_delta(spot, strike, years, rate, vol):
    """Delta de una call europea, N(d1). NaN si algun insumo no es positivo."""
    if min(spot, strike, years, vol) <= 0:
        return float("nan")
    d1 = (math.log(spot / strike) + (rate + vol ** 2 / 2.0) * years) / (vol * math.sqrt(years))
    return float(norm.cdf(d1))


def prune_order(weights, contributions=None, rule="min_weight"):
    """Orden en el que intentar sacar activos del portafolio de cola.

    `min_weight` saca primero el peso mas chico. Un activo en la cota del
    12% aporta mucho riesgo marginal solo por el peso, y la regla vieja
    `max_mtr` lo poda antes que un nombre chico y concentrado.
    `min_weight_x_mtr` ordena por peso * contribucion, de menor a mayor.
    `max_mtr` es la regla anterior: mayor contribucion marginal primero.
    """
    w = pd.Series(weights, dtype=float)
    active = w[w > 0]
    if rule == "max_mtr":
        c = pd.Series(contributions, dtype=float).reindex(active.index)
        return list(c.sort_values(ascending=False).index)
    if rule == "min_weight_x_mtr":
        c = pd.Series(contributions, dtype=float).reindex(active.index)
        return list((active * c).sort_values(ascending=True).index)
    if rule == "min_weight":
        return list(active.sort_values(ascending=True).index)
    raise ValueError(f"regla de poda desconocida: {rule}")
