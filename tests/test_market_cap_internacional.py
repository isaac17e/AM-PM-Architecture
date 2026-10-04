"""Orden de los internacionales por market cap en USD antes del top N.

La lista fija ponia primero los 15 .TO y n_top_international = 15 tomaba
solo Canada. Ahora se ordena por market cap convertido a USD con la moneda
del sufijo y los pares FX de los scripts.
"""

import json
import re
from pathlib import Path

import pytest

import market_data as md

ROOT = Path(__file__).resolve().parents[1]
SUFIJOS = {".TO": "CAD", ".DE": "EUR", ".PA": "EUR", ".MC": "EUR", ".L": "GBP", ".T": "JPY"}
FX_PARES = {
    "CAD": {"ticker": "CAD=X", "invert": True},
    "EUR": {"ticker": "EURUSD=X", "invert": False},
    "GBP": {"ticker": "GBPUSD=X", "invert": False},
    "JPY": {"ticker": "JPY=X", "invert": True},
}
FX = {"CAD": 0.70, "EUR": 1.10, "GBP": 1.30, "JPY": 0.0065}
# Cap en unidad mayor de la moneda local.
CAPS = {
    "RY.TO": 380e9,       # 266 B USD
    "SHOP.TO": 270e9,     # 189 B USD
    "SAP.TO": 12e9,       # 8.4 B USD
    "AZN.L": 185e9,       # 240.5 B USD
    "HSBC": 330e9,        # USD (ADR, sin sufijo)
    "7203.T": 34e12,      # 221 B USD
    "MC.PA": 190e9,       # 209 B USD
}


def _proveedores(caps=CAPS, fx=FX, llamadas=None):
    llamadas = [] if llamadas is None else llamadas

    def cap_provider(tickers):
        llamadas.append(("cap", tuple(tickers)))
        return {t: caps[t] for t in tickers if t in caps}

    def fx_provider(pares):
        llamadas.append(("fx", tuple(sorted(pares))))
        return {m: fx[m] for m in pares if m in fx}

    return cap_provider, fx_provider, llamadas


def _ordenar(tickers, n, **kw):
    cap, fx, _ = _proveedores()
    kw.setdefault("cap_provider", cap)
    kw.setdefault("fx_provider", fx)
    kw.setdefault("cache_path", None)
    kw.setdefault("sleep", lambda s: None)
    return md.ordenar_por_market_cap(tickers, n, SUFIJOS, FX_PARES, **kw)


def test_convierte_a_usd_con_la_moneda_del_sufijo():
    cap, fx, _ = _proveedores()
    res = md.market_caps_usd(list(CAPS), SUFIJOS, FX_PARES, cap_provider=cap, fx_provider=fx,
                             cache_path=None)
    assert res["moneda"]["RY.TO"] == "CAD"
    assert res["moneda"]["7203.T"] == "JPY"
    assert res["moneda"]["HSBC"] == "USD"
    assert res["usd"]["RY.TO"] == pytest.approx(380e9 * 0.70)
    assert res["usd"]["AZN.L"] == pytest.approx(185e9 * 1.30)
    assert res["usd"]["7203.T"] == pytest.approx(34e12 * 0.0065)
    assert res["usd"]["HSBC"] == pytest.approx(330e9)


def test_ordena_de_mayor_a_menor_y_toma_el_top():
    lista = ["RY.TO", "SHOP.TO", "SAP.TO", "AZN.L", "HSBC", "7203.T", "MC.PA"]
    res = _ordenar(lista, 4)
    assert res["seleccion"] == ["HSBC", "RY.TO", "AZN.L", "7203.T"]
    assert res["orden"][-1] == "SAP.TO"
    assert res["aviso"] is None
    tabla = res["tabla"]
    assert tabla["ticker"].tolist() == res["seleccion"]
    assert tabla["region"].tolist() == ["US", "Canada", "Europa", "Japon"]
    assert tabla["market_cap_usd"].is_monotonic_decreasing


def test_n_top_mayor_que_la_lista_devuelve_todo():
    assert len(_ordenar(["RY.TO", "HSBC"], 15)["seleccion"]) == 2


def test_sin_market_cap_van_al_final_en_su_orden():
    lista = ["X1.TO", "RY.TO", "X2.L", "SAP.TO", "X3.T", "HSBC"]
    res = _ordenar(lista, 6)
    assert res["orden"] == ["HSBC", "RY.TO", "SAP.TO", "X1.TO", "X2.L", "X3.T"]
    assert "X1.TO, X2.L, X3.T" in res["aviso"]


def test_sin_fx_de_una_moneda_esos_nombres_van_al_final():
    cap, fx, _ = _proveedores(fx={"CAD": 0.70, "EUR": 1.10, "GBP": 1.30})
    res = _ordenar(["7203.T", "RY.TO", "HSBC"], 3, cap_provider=cap, fx_provider=fx)
    assert res["orden"] == ["HSBC", "RY.TO", "7203.T"]


def test_si_yfinance_falla_por_completo_usa_el_orden_de_la_lista():
    def caido(_):
        raise ConnectionError("sin red")

    lista = ["RY.TO", "SHOP.TO", "AZN.L", "HSBC"]
    res = _ordenar(lista, 3, cap_provider=caido, fx_provider=caido)
    assert res["seleccion"] == ["RY.TO", "SHOP.TO", "AZN.L"]
    assert "orden actual de la lista" in res["aviso"]
    res_vacio = _ordenar(lista, 2, cap_provider=lambda t: {})
    assert res_vacio["seleccion"] == ["RY.TO", "SHOP.TO"]
    assert "ningun internacional" in res_vacio["aviso"]


def test_reintenta_solo_los_que_faltan_con_espera():
    intentos, esperas = [], []

    def inestable(tickers):
        intentos.append(list(tickers))
        if len(intentos) == 1:
            raise TimeoutError("429")
        if len(intentos) == 2:
            return {t: CAPS[t] for t in tickers if t == "RY.TO"}
        return {t: CAPS[t] for t in tickers if t in CAPS}

    res = _ordenar(["RY.TO", "AZN.L", "NADA.L"], 3, cap_provider=inestable,
                   retries=4, backoff=1.0, sleep=esperas.append)
    assert intentos[0] == ["RY.TO", "AZN.L", "NADA.L"]
    assert intentos[2] == ["AZN.L", "NADA.L"]
    assert intentos[3] == ["NADA.L"]
    assert esperas == [1.0, 2.0, 4.0]
    assert res["orden"] == ["RY.TO", "AZN.L", "NADA.L"]


def test_cache_evita_repetir_llamadas_y_vence_con_el_ttl(tmp_path):
    ruta = str(tmp_path / "mc.json")
    cap, fx, llamadas = _proveedores()
    kw = dict(cap_provider=cap, fx_provider=fx, cache_path=ruta, sleep=lambda s: None)
    lista = ["RY.TO", "AZN.L", "HSBC"]
    r1 = md.market_caps_usd(lista, SUFIJOS, FX_PARES, now=1_000_000, **kw)
    assert r1["llamadas"] == 2
    guardado = json.loads(Path(ruta).read_text())
    assert set(guardado["cap"]) == set(lista)
    assert set(guardado["fx"]) == {"CAD", "GBP"}

    r2 = md.market_caps_usd(lista, SUFIJOS, FX_PARES, now=1_000_000 + 3600, **kw)
    assert r2["llamadas"] == 0
    assert r2["usd"] == r1["usd"]
    assert len(llamadas) == 2

    # FX vence a las 24 h, el cap a los 7 dias.
    r3 = md.market_caps_usd(lista, SUFIJOS, FX_PARES, now=1_000_000 + 25 * 3600, **kw)
    assert r3["llamadas"] == 1 and llamadas[-1][0] == "fx"
    r4 = md.market_caps_usd(lista, SUFIJOS, FX_PARES, now=1_000_000 + 8 * 24 * 3600, **kw)
    assert r4["llamadas"] == 2


def test_cache_corrupta_no_rompe(tmp_path):
    ruta = tmp_path / "mc.json"
    ruta.write_text("{no es json")
    res = _ordenar(["RY.TO", "HSBC"], 2, cache_path=str(ruta))
    assert res["seleccion"] == ["HSBC", "RY.TO"]


class _Ticker:
    def __init__(self, fast=None, info=None):
        self._fast, self._info = fast, info

    @property
    def fast_info(self):
        if self._fast is None:
            raise KeyError("sin fast_info")
        return self._fast

    @property
    def info(self):
        return self._info or {}


def test_fast_info_en_peniques_se_lleva_a_libras():
    # AZN.L real: fast_info 1.84e13 (GBp), info 1.84e11 (GBP).
    assert md._market_cap_yf(_Ticker({"marketCap": 1.84e13, "currency": "GBp"})) == pytest.approx(1.84e11)
    assert md._market_cap_yf(_Ticker({"marketCap": 3.8e11, "currency": "CAD"})) == pytest.approx(3.8e11)
    assert md._market_cap_yf(_Ticker(None, {"marketCap": 1.84e11, "currency": "GBp"})) == pytest.approx(1.84e11)
    assert md._market_cap_yf(_Ticker({"marketCap": None}, {})) is None


def test_tabla_imprime_cap_en_usd_y_region():
    texto = md.tabla_market_cap_texto(_ordenar(["RY.TO", "X.L", "HSBC"], 3))
    assert "HSBC" in texto and "330.0 B" in texto and "US" in texto
    assert "266.0 B" in texto and "Canada" in texto
    assert "sin dato" in texto


@pytest.mark.parametrize("nombre", [
    "minimum_variance.py",
    "minimum_variance_(seasonal_version).py",
    "quadratic_utility.py",
    "quadratic_utility_(seasonal_version).py",
])
def test_scripts_ordenan_por_market_cap_antes_del_top(nombre):
    fuente = (ROOT / nombre).read_text(encoding="utf-8")
    assert "md.ordenar_por_market_cap(international_tickers_full" in fuente
    assert 'international_tickers = _mc_intl["seleccion"]' in fuente
    assert "md.tabla_market_cap_texto(_mc_intl)" in fuente
    assert not re.search(r"international_tickers_full\[:", fuente)
    # Los pares FX y el mapa de sufijos existen antes de ordenar.
    i_orden = fuente.index("md.ordenar_por_market_cap(")
    assert fuente.index("fx_pairs = {") < i_orden
    assert fuente.index("ticker_currency_by_suffix = {") < i_orden
    # n_top_international / n_top_int no cambian.
    if nombre.startswith("minimum_variance"):
        assert re.search(r"^n_top_international = 15\b", fuente, re.M)
    else:
        assert re.search(r"^n_top_int = 50\b", fuente, re.M)
