"""Ajuste IV/tasa: la IV de Polygon viene invertida con su propio acarreo.

minimum_variance.py y quadratic_utility.py repreciaban esa IV a la tasa del
script. Con un acarreo distinto los precios no son los del mercado y la cadena
OTM (puts bajo S, calls encima) queda con un salto en el ATM que sesga MFIS.
Ahora se calibra el acarreo con los pares call/put de la cadena.
"""

import ast
import math
import re
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import norm

import polygon_client as pc
import qu_metrics as qm
import risk_estimators as rk

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ["minimum_variance.py", "quadratic_utility.py"]

S = 100.0
T = 31 / 365
RF = 0.047
STRIKES = np.arange(80.0, 121.0, 2.5)


def _smile(K):
    m = np.log(K / S)
    return 0.24 - 0.25 * m + 0.8 * m ** 2


def _mercado():
    """Precios con paridad a RF (q = 0) y la IV que publicaria un proveedor con acarreo 0."""
    sig = _smile(STRIKES)
    c = rk.bs_price(S, STRIKES, T, RF, sig, True)
    p = rk.bs_price(S, STRIKES, T, RF, sig, False)
    iv_c = rk.bs_implied_vol(c, S, STRIKES, T, 0.0, True)
    iv_p = rk.bs_implied_vol(p, S, STRIKES, T, 0.0, False)
    return sig, c, p, iv_c, iv_p


# ------------------------------------------------------------------------------
# risk_estimators
# ------------------------------------------------------------------------------

def test_bs_price_matches_closed_form_and_parity():
    K, sig = 105.0, 0.3
    d1 = (math.log(S / K) + (RF + sig ** 2 / 2) * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    call = S * norm.cdf(d1) - K * math.exp(-RF * T) * norm.cdf(d2)
    assert rk.bs_price(S, K, T, RF, sig, True) == pytest.approx(call, rel=1e-12)
    put = rk.bs_price(S, K, T, RF, sig, False)
    assert call - put == pytest.approx(S - K * math.exp(-RF * T), abs=1e-10)
    assert np.isnan(rk.bs_price(S, K, 0.0, RF, sig, True))


def test_bs_implied_vol_round_trip_and_out_of_bounds():
    sig = _smile(STRIKES)
    for is_call in (True, False):
        precio = rk.bs_price(S, STRIKES, T, RF, sig, is_call)
        assert np.allclose(rk.bs_implied_vol(precio, S, STRIKES, T, RF, is_call), sig, atol=1e-8)
    # bajo el intrinseco descontado no hay vol
    assert np.isnan(rk.bs_implied_vol(1.0, S, 80.0, T, RF, True))


def test_provider_carry_splits_call_and_put_iv():
    _sig, _c, _p, iv_c, iv_p = _mercado()
    atm = np.argmin(np.abs(STRIKES - S))
    # mismo precio de mercado, IV distinta segun el lado: el salto que sesgaba MFIS
    assert iv_c[atm] - iv_p[atm] > 0.02


def test_calibrate_iv_carry_recovers_market_prices():
    sig, c, p, iv_c, iv_p = _mercado()
    aj = rk.calibrate_iv_carry(S, T, RF, STRIKES, iv_c, iv_p)
    # una put ITM vale menos que su intrinseco con acarreo 0: sin IV, no cuenta
    con_iv = np.isfinite(iv_c) & np.isfinite(iv_p)
    assert not con_iv.all()
    assert aj["ok"] and aj["n_pairs"] == int(np.sum(con_iv & (np.abs(np.log(STRIKES / S)) <= 0.10)))
    assert aj["carry"] == pytest.approx(0.0, abs=1e-5)
    assert aj["iv_gap_before"] > 0.02 and aj["iv_gap_after"] < 1e-5
    k, ivc, ivp = STRIKES[con_iv], iv_c[con_iv], iv_p[con_iv]
    assert np.allclose(rk.bs_price(S, k, T, aj["carry"], ivc, True), c[con_iv], atol=1e-6)
    assert np.allclose(rk.bs_price(S, k, T, aj["carry"], ivp, False), p[con_iv], atol=1e-6)
    assert np.allclose(rk.iv_at_rate(ivc, S, k, T, aj["carry"], RF, True), sig[con_iv], atol=1e-5)


def test_calibrate_iv_carry_is_neutral_when_provider_uses_script_rate():
    sig = _smile(STRIKES)
    aj = rk.calibrate_iv_carry(S, T, RF, STRIKES, sig, sig)
    assert aj["ok"] and aj["carry"] == pytest.approx(RF, abs=1e-5)
    assert np.allclose(rk.iv_at_rate(sig, S, STRIKES, T, aj["carry"], RF, False), sig, atol=1e-5)


@pytest.mark.parametrize("strikes, iv_c, iv_p", [
    ([], [], []),
    ([100.0], [np.nan], [0.2]),
    ([150.0, 60.0], [0.3, 0.3], [0.3, 0.3]),      # fuera de la banda de +/-10%
])
def test_calibrate_iv_carry_without_pairs_keeps_script_rate(strikes, iv_c, iv_p):
    aj = rk.calibrate_iv_carry(S, T, RF, strikes, iv_c, iv_p)
    assert not aj["ok"] and aj["carry"] == RF and aj["n_pairs"] == 0


def test_calibrate_iv_carry_at_bound_keeps_script_rate():
    _sig, _c, _p, iv_c, iv_p = _mercado()
    aj = rk.calibrate_iv_carry(S, T, RF, STRIKES, iv_c, iv_p, bounds=(0.03, 0.06))
    assert not aj["ok"] and aj["carry"] == RF and aj["n_pairs"] > 0


# ------------------------------------------------------------------------------
# polygon_client: pares del vencimiento elegido
# ------------------------------------------------------------------------------

def _contrato(tipo, strike, exp, iv):
    return {"details": {"contract_type": tipo, "strike_price": strike,
                        "expiration_date": exp.strftime("%Y-%m-%d")},
            "implied_volatility": iv}


def test_fetch_otm_chain_returns_call_put_pairs_of_chosen_expiry(monkeypatch):
    hoy = date.today()
    e25, e60 = hoy + timedelta(days=25), hoy + timedelta(days=60)
    grabado = {
        "call": [_contrato("call", k, e60, 0.30) for k in (95, 100, 110)]
                + [_contrato("call", k, e25, 0.20) for k in (100, 105)],
        "put": [_contrato("put", k, e60, 0.26) for k in (90, 95, 100)]
               + [_contrato("put", 95, e60, 0.99)]                        # duplicado
               + [_contrato("put", k, e25, 0.20) for k in (95, 100)],
    }
    monkeypatch.setattr(pc, "get_all", lambda url, api_key=None, max_pages=40: (
        grabado["call" if "contract_type=call" in url else "put"], True, 200))
    calls, puts, info = pc.fetch_otm_chain("AAPL", 100.0, "2026-01-01", "2030-01-01",
                                           70.0, 140.0, target_dte=30)
    assert info["dte"] == 60
    pares = info["pares"]
    assert list(pares.columns) == ["strike", "iv_call", "iv_put"]
    assert list(pares["strike"]) == [95, 100]
    assert list(pares["iv_call"]) == [0.30, 0.30] and list(pares["iv_put"]) == [0.26, 0.26]
    # la cadena OTM no cambia
    assert list(calls["strike"]) == [100, 110] and sorted(puts["strike"]) == [90, 95]


def test_fetch_otm_chain_empty_paths_carry_empty_pairs(monkeypatch):
    monkeypatch.setattr(pc, "get_all", lambda url, api_key=None, max_pages=40: ([], False, 429))
    _c, _p, info = pc.fetch_otm_chain("AAPL", 100.0, "2026-01-01", "2030-01-01", 70.0, 140.0, 30)
    assert not info["completo"] and info["pares"].empty


# ------------------------------------------------------------------------------
# qu_metrics: resumen de consola
# ------------------------------------------------------------------------------

def test_resumen_ajuste_iv_counts_only_queried_chains():
    momentos = [
        {"carry": -0.002, "carry_ok": True, "iv_gap_antes": 0.052, "iv_gap_despues": 0.012},
        {"carry": 0.013, "carry_ok": True, "iv_gap_antes": 0.036, "iv_gap_despues": 0.008},
        {"carry": RF, "carry_ok": False, "iv_gap_antes": np.nan, "iv_gap_despues": np.nan},
        {"ok": False, "motivo": "sin_opciones_us"},
    ]
    r = qm.resumen_ajuste_iv(momentos)
    assert r["n"] == 3 and r["n_ok"] == 2
    assert r["carry_mediana"] == pytest.approx(0.0055)
    assert r["brecha_antes"] == pytest.approx(0.044) and r["brecha_despues"] == pytest.approx(0.010)
    texto = qm.texto_ajuste_iv(r, RF)
    assert "2 de 3 cadenas calibradas" in texto and "4.4 -> 1.0 puntos" in texto


def test_texto_ajuste_iv_without_pairs():
    assert "sin cadenas" in qm.texto_ajuste_iv(qm.resumen_ajuste_iv([]), RF)
    r = qm.resumen_ajuste_iv([{"carry": RF, "carry_ok": False}])
    assert "0 de 1" in qm.texto_ajuste_iv(r, RF)


# ------------------------------------------------------------------------------
# Scripts normales: la IV se reprecia con el acarreo calibrado
# ------------------------------------------------------------------------------

def _fuente(nombre):
    return (ROOT / nombre).read_text(encoding="utf-8")


def _funcion(fuente, nombre):
    for node in ast.parse(fuente).body:
        if isinstance(node, ast.FunctionDef) and node.name == nombre:
            return ast.get_source_segment(fuente, node)
    raise AssertionError(f"{nombre} no esta en el script")


@pytest.mark.parametrize("nombre", SCRIPTS)
def test_chain_to_prices_uses_calibrated_carry(nombre):
    import pandas as pd
    fuente = _fuente(nombre)
    ns = {"math": math, "norm": norm, "np": np}
    exec(_funcion(fuente, "bs_price"), ns)
    exec(_funcion(fuente, "bkm_iv_chain_to_prices"), ns)
    chain = pd.DataFrame({"strike": [95.0, 105.0], "iv": [0.25, 0.25], "type": ["put", "call"]})
    con_tasa = ns["bkm_iv_chain_to_prices"](S, RF, T, chain)
    con_acarreo = ns["bkm_iv_chain_to_prices"](S, RF, T, chain, carry=0.0)
    esperado = rk.bs_price(S, chain["strike"].values, T, 0.0, 0.25, chain["type"].values == "call")
    assert np.allclose(con_acarreo["price"].values, esperado, rtol=1e-10)
    assert np.allclose(con_tasa["price"].values,
                       rk.bs_price(S, chain["strike"].values, T, RF, 0.25,
                                   chain["type"].values == "call"), rtol=1e-10)


@pytest.mark.parametrize("nombre", SCRIPTS)
def test_current_moments_calibrate_before_pricing(nombre):
    cuerpo = _funcion(_fuente(nombre), "bkm_get_current_moments")
    i_cal = cuerpo.index("rk.calibrate_iv_carry(")
    precios = re.findall(r'bkm_iv_chain_to_prices\([^)]*carry=ajuste\["carry"\]\)', cuerpo)
    assert len(precios) == 2
    assert i_cal < cuerpo.index("bkm_iv_chain_to_prices(")
    assert 'info_cadena.get("pares")' in cuerpo


@pytest.mark.parametrize("nombre, funcion", [
    ("minimum_variance.py", "get_polygon_option_snapshot"),
    ("quadratic_utility.py", "polygon_get_atm_option"),
])
def test_atm_snapshot_fetches_both_sides_and_adjusts_iv(nombre, funcion):
    cuerpo = _funcion(_fuente(nombre), funcion)
    assert "contract_type=call" not in cuerpo and "contract_type={contract_type}" not in cuerpo
    assert "pc.pares_call_put(" in cuerpo
    assert "rk.calibrate_iv_carry(" in cuerpo and "rk.iv_at_rate(" in cuerpo
    assert "iv_api=" in cuerpo
