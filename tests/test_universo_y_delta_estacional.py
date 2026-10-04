"""Sufijos internacionales en el universo y filtro de colchon OTM estacional.

El predicado de formato US (largo 1-5, sin digito inicial, sin ^/$) aplicado
a la lista ya mezclada tiraba SHOP.TO, ULVR.L, TTE.PA, los .DE/.MC y los
.T que empiezan por digito. Cada optimizador filtra solo domesticos y
concatena internacionales. El colchon estacional usa el horizonte
len(rebalance_months) y no la delta ATM de Polygon.
"""

import ast
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import market_data as md
import qu_metrics as qm

ROOT = Path(__file__).resolve().parents[1]

SCRIPTS = [
    "quadratic_utility_(seasonal_version).py",
    "minimum_variance.py",
    "minimum_variance_(seasonal_version).py",
    "black_litterman.py",
]

SUFIJOS_MONEDA = {
    ".TO": "CAD",
    ".DE": "EUR",
    ".PA": "EUR",
    ".MC": "EUR",
    ".L": "GBP",
    ".T": "JPY",
}

# Los que el filtro viejo de la lista mezclada eliminaba.
_CAEN_CON_FILTRO_VIEJO = (
    "SHOP.TO", "ENB.TO", "TRI.TO", "WCN.TO", "FNV.TO", "SAP.TO",
    "TTE.PA", "ULVR.L", "SIE.DE", "MUV2.DE", "ITX.MC", "BBVA.MC",
    "7203.T", "9984.T",
)

_VOLS = [
    0.14, 0.15, 0.16, 0.16, 0.17, 0.18, 0.18, 0.19,
    0.20, 0.21, 0.22, 0.22, 0.23, 0.24, 0.24, 0.25, 0.26, 0.26, 0.27, 0.28, 0.28, 0.29, 0.30,
    0.32, 0.33, 0.34, 0.35, 0.36, 0.38, 0.40, 0.42, 0.44, 0.46,
    0.48, 0.50, 0.52, 0.55, 0.58, 0.62, 0.66, 0.70, 0.75, 0.80, 0.85, 0.90,
]
_R = 0.047
_LOG_M = 0.08
_T_REF = 2 / 12


def _fuente(nombre):
    return (ROOT / nombre).read_text(encoding="utf-8")


def _literales(fuente):
    """Primera asignacion literal de cada nombre, a nivel de modulo."""
    out = {}
    for node in ast.parse(fuente).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        destino = node.targets[0]
        if not isinstance(destino, ast.Name) or destino.id in out:
            continue
        try:
            out[destino.id] = ast.literal_eval(node.value)
        except (ValueError, SyntaxError):
            continue
    return out


def _formato_us_viejo(tickers):
    import re
    return [
        t for t in tickers
        if not re.search(r"\^|\$", t) and 1 <= len(t) <= 5 and not re.match(r"^[0-9]", t) and t != ""
    ]


def _internacionales_del_script(fuente):
    vals = _literales(fuente)
    full = vals.get("international_tickers_full", vals.get("INTERNATIONAL_TICKERS"))
    assert full, "el script no declara la lista internacional"
    n = vals.get("n_top_int", vals.get("n_top_international", len(full)))
    return list(full[: int(n)])


def _descartados(years, umbral, ref_years=_T_REF):
    n = 0
    for vol in _VOLS:
        colchon = qm.delta_cushion(vol, years, _R, _LOG_M, ref_years=ref_years)
        if not qm.pasa_filtro_delta(colchon, umbral):
            n += 1
    return n


# ------------------------------------------------------------------------------
# Universo: sufijos que el filtro US tiraba
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("nombre", SCRIPTS)
def test_script_conserva_sufijos_internacionales(nombre):
    fuente = _fuente(nombre)
    assert "combinar_tickers(" in fuente
    assert "1 <= len(t) <= 5" not in fuente
    intl = _internacionales_del_script(fuente)
    unidos = md.combinar_tickers(
        ["AAPL", "BRK-B", "^GSPC", "$VIX", "1234", "", "TOOLONG"], intl)
    for t in intl:
        assert t in unidos
    viejo = _formato_us_viejo(list(dict.fromkeys(
        ["AAPL", "BRK-B", "^GSPC"] + intl)))
    caidos = [t for t in _CAEN_CON_FILTRO_VIEJO if t in intl and t not in viejo]
    assert caidos, f"{nombre} no incluye ningun sufijo que el filtro viejo tiraba"
    for t in caidos:
        assert t in unidos
    for basura in ("^GSPC", "$VIX", "1234", "", "TOOLONG"):
        assert basura not in unidos


@pytest.mark.parametrize("nombre", SCRIPTS)
def test_script_mapea_sufijo_y_region(nombre):
    fuente = _fuente(nombre)
    vals = _literales(fuente)
    sufijos = vals["ticker_currency_by_suffix"]
    for suf, moneda in SUFIJOS_MONEDA.items():
        assert sufijos[suf] == moneda
    # .T listado antes que .TO no puede mandar Canada a JPY.
    invertido = {".T": "JPY", ".TO": "CAD", ".L": "GBP", ".DE": "EUR", ".PA": "EUR", ".MC": "EUR"}
    assert md.currency_from_suffix("SHOP.TO", invertido) == "CAD"
    assert md.currency_from_suffix("7203.T", invertido) == "JPY"
    override = vals.get("ticker_currency_override", {})
    assert "HSBC" not in override and "BP" not in override
    intl = _internacionales_del_script(fuente)
    for t in intl:
        region = md.region_de_ticker(t)
        moneda = md.currency_from_suffix(t, sufijos) or "USD"
        if region == "Canada":
            assert moneda == "CAD"
        elif region == "Japon":
            assert moneda == "JPY"
        elif region == "Europa":
            assert moneda in {"EUR", "GBP"}
        else:
            assert region == "US" and moneda == "USD"
    assert md.region_de_ticker("SHOP.TO") == "Canada"
    assert md.region_de_ticker("7203.T") == "Japon"
    assert md.region_de_ticker("HSBC") == "US"
    assert md.region_de_ticker("BP") == "US"


def test_reexport_de_qu_metrics_apunta_al_helper_compartido():
    assert qm.combinar_tickers is md.combinar_tickers
    assert qm.region_de_ticker is md.region_de_ticker
    assert qm.es_ticker_formato_us is md.es_ticker_formato_us


def test_convertir_serie_a_usd_alinea_el_fx():
    idx = pd.bdate_range("2024-01-02", periods=3)
    precios = pd.Series([100.0, 100.0, 110.0], index=idx)
    fx = pd.Series([1.20, 1.25], index=idx[:2])
    usd = md.convertir_serie_a_usd(precios, fx)
    assert usd.iloc[0] == pytest.approx(120.0)
    assert usd.iloc[1] == pytest.approx(125.0)
    # El tercer dia no tiene FX propio: arrastra el ultimo.
    assert usd.iloc[2] == pytest.approx(137.5)
    assert md.convertir_serie_a_usd(precios, None) is precios


def test_qu_estacional_usa_region_y_rotulo_de_colchon():
    fuente = _fuente("quadratic_utility_(seasonal_version).py")
    normal = _fuente("quadratic_utility.py")
    assert "qm.region_de_ticker" in fuente
    assert 'a.endswith(".TO")' not in fuente
    assert "Colchon delta OTM ponderado" in fuente
    assert "Colchon delta OTM ponderado" in normal
    assert "internacionales en el universo" in fuente
    for nombre in SCRIPTS:
        assert "internacionales en el universo" in _fuente(nombre)
        assert "en la optimizacion" in _fuente(nombre)
        assert "No hay piso de asignacion internacional" in _fuente(nombre)


def test_bl_no_manda_internacionales_a_polygon():
    fuente = _fuente("black_litterman.py")
    assert "sin_opciones_us" in fuente
    assert "pc.is_us_ticker" in fuente
    assert "md.region_de_ticker" in fuente


# ------------------------------------------------------------------------------
# Filtro delta estacional: colchon, horizonte y multiplicador
# ------------------------------------------------------------------------------

def test_defaults_estacionales_del_colchon():
    fuente = _fuente("quadratic_utility_(seasonal_version).py")
    assert 'delta_strike_mode = "otm"' in fuente
    assert 'delta_scale_mode = "relative"' in fuente
    assert "delta_min = 0.15" in fuente
    assert "Conservador 0.24, moderado 0.18, agresivo 0.15" in fuente
    assert "delta_otm_log_m = 0.08" in fuente
    assert "delta_otm_ref_months = 2" in fuente
    assert "evaluar_delta_candidato(" in fuente
    assert 'usar_delta_polygon=usa_polygon and delta_strike_mode != "otm"' in fuente
    # El horizonte del colchon es len(rebalance_months), no un tenor fijo.
    assert "T_horizon = horizon_months / 12" in fuente
    assert "horizon_months = len(rebalance_months)" in fuente


def test_moneyness_escala_con_uno_y_dos_meses_de_rebalanceo():
    un_mes = len([10]) / 12
    dos_meses = len([10, 11]) / 12
    m1 = qm.otm_log_moneyness(_LOG_M, un_mes, _T_REF)
    m2 = qm.otm_log_moneyness(_LOG_M, dos_meses, _T_REF)
    assert dos_meses == pytest.approx(2 / 12)
    assert un_mes == pytest.approx(1 / 12)
    assert m2 == pytest.approx(_LOG_M)
    assert m1 == pytest.approx(_LOG_M * math.sqrt(0.5))
    assert m1 < m2


def test_conteo_de_colchon_separa_umbrales_y_aguanta_el_horizonte():
    d15_1 = _descartados(1 / 12, 0.15)
    d18_1 = _descartados(1 / 12, 0.18)
    d24_1 = _descartados(1 / 12, 0.24)
    d15_2 = _descartados(2 / 12, 0.15)
    d18_2 = _descartados(2 / 12, 0.18)
    d24_2 = _descartados(2 / 12, 0.24)
    assert 0 < d15_1 < d18_1 < d24_1 < len(_VOLS)
    assert 0 < d15_2 < d18_2 < d24_2 < len(_VOLS)
    # sqrt(T) mantiene el corte parecido a 1 y a 2 meses.
    assert abs(d15_1 - d15_2) <= 2
    assert abs(d18_1 - d18_2) <= 2
    assert abs(d24_1 - d24_2) <= 2
    # Sin escalar, el 8% a 1 mes queda mas OTM y descarta menos.
    sin_escala_1 = _descartados(1 / 12, 0.15, ref_years=1 / 12)
    assert sin_escala_1 < d15_1


def test_multiplicador_relativo_recorta_a_la_banda():
    extremos = np.array([0.01, 0.20, 1.00, np.nan])
    mult = qm.scale_option_deltas(extremos, mode="relative", fixed_lo=0.75, fixed_hi=1.25)
    assert mult[0] == pytest.approx(0.75)
    assert mult[1] == pytest.approx(1.0)
    assert mult[2] == pytest.approx(1.25)
    assert mult[3] == pytest.approx(1.0)
    assert mult.min() >= 0.75 - 1e-12
    assert np.nanmax(mult) <= 1.25 + 1e-12


def test_sin_vol_se_conserva():
    fila = qm.evaluar_delta_candidato(
        float("nan"), 1 / 12, _R, mode="otm", log_m=_LOG_M, ref_years=_T_REF)
    assert fila["strike_mode"] == "sin_datos"
    assert math.isnan(fila["delta"])
    assert qm.pasa_filtro_delta(fila["delta"], 0.15)
    assert qm.pasa_filtro_delta(None, 0.15)


def test_delta_de_polygon_no_salta_el_modo_otm():
    # ATM ~0.50 pasaria delta_min 0.15. La vol alta no: el colchon cae.
    vol = 0.90
    years = 1 / 12
    fila = qm.evaluar_delta_candidato(
        vol, years, _R, mode="otm", log_m=_LOG_M, ref_years=_T_REF,
        usar_delta_polygon=True, polygon_delta=0.51, polygon_iv=vol,
    )
    esperado = qm.delta_cushion(vol, years, _R, _LOG_M, ref_years=_T_REF)
    assert fila["strike_mode"] == "bs_otm_polygon_iv"
    assert fila["delta"] == pytest.approx(esperado)
    assert fila["delta"] < 0.15
    assert not qm.pasa_filtro_delta(fila["delta"], 0.15)
    assert qm.pasa_filtro_delta(0.51, 0.15)
    # Sin IV de Polygon se usa la historica, no la delta ATM.
    fila_hist = qm.evaluar_delta_candidato(
        0.20, years, _R, mode="otm", log_m=_LOG_M, ref_years=_T_REF,
        usar_delta_polygon=True, polygon_delta=0.48, polygon_iv=float("nan"),
    )
    assert fila_hist["strike_mode"] == "bs_otm_hist"
    assert fila_hist["iv_used"] == pytest.approx(0.20)
    assert abs(fila_hist["delta"] - 0.48) > 0.05
    # Fuera de otm el atajo de Polygon se conserva.
    fila_rf = qm.evaluar_delta_candidato(
        0.20, years, _R, mode="rf", usar_delta_polygon=True, polygon_delta=0.48, polygon_iv=0.22,
    )
    assert fila_rf["strike_mode"] == "polygon_real"
    assert fila_rf["delta"] == pytest.approx(0.48)


def test_conteo_del_filtro_estacional_sobre_universo_sintetico():
    """Misma regla que el script: colchon, horizonte y descarte."""
    nombres = [f"N{i}" for i in range(len(_VOLS))]
    # Dos sin vol y uno de vol alta con delta ATM de Polygon. El resto, historica.
    vols = list(_VOLS)
    vols[0] = float("nan")
    vols[1] = float("nan")
    vols[2] = 0.90

    def corrida(rebalance_months):
        years = len(rebalance_months) / 12
        filas = []
        for i, vol in enumerate(vols):
            es_poly = i == 2
            fila = qm.evaluar_delta_candidato(
                vol, years, _R, mode="otm", log_m=_LOG_M, ref_years=_T_REF,
                usar_delta_polygon=es_poly,
                polygon_delta=0.52 if es_poly else None,
                polygon_iv=0.90 if es_poly else None,
            )
            fila["symbol"] = nombres[i]
            filas.append(fila)
        quedan = [f["symbol"] for f in filas if qm.pasa_filtro_delta(f["delta"], 0.15)]
        fuera = [f for f in filas if not qm.pasa_filtro_delta(f["delta"], 0.15)]
        return quedan, fuera, filas

    quedan_1, fuera_1, filas_1 = corrida([10])
    _quedan_2, fuera_2, _filas_2 = corrida([10, 11])
    assert "N0" in quedan_1 and "N1" in quedan_1
    assert filas_1[0]["strike_mode"] == "sin_datos"
    assert filas_1[2]["strike_mode"] == "bs_otm_polygon_iv"
    assert filas_1[2]["delta"] < 0.15
    assert "N2" in [f["symbol"] for f in fuera_1]
    assert len(fuera_1) > 0
    assert abs(len(fuera_1) - len(fuera_2)) <= 2
    assert len(quedan_1) + len(fuera_1) == len(vols)
    # El modo rf con la misma delta de Polygon no habria descartado a N2.
    assert qm.pasa_filtro_delta(0.52, 0.15)
