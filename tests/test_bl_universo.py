"""Black-Litterman: el universo es solo TICKERS, con internacionales si se ponen.

Antes el script concatenaba una lista internacional fija y tenia su propia
lista de ETFs con elegibilidad y tope. Ahora no hay listas paralelas: un
ticker de otra bolsa en TICKERS se descarga, se convierte a USD con la
moneda que reporta Yahoo (FX solo de las monedas presentes) y su market cap
entra a w_mkt en USD.
"""

import ast
import runpy
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

ROOT = Path(__file__).resolve().parents[1]
FUENTE = (ROOT / "black_litterman.py").read_text(encoding="utf-8")

# Moneda de cotizacion, market cap en esa moneda (fast_info) y nivel de precio.
_DATOS = {
    "AAPL": ("USD", 3.0e12, 200.0),
    "MSFT": ("USD", 3.1e12, 400.0),
    "AZN.L": ("GBp", 1.84e13, 11870.0),   # peniques, como fast_info real
    "7203.T": ("JPY", 3.4e13, 2850.0),
}
_FX = {"GBPUSD=X": 1.30, "JPY=X": 150.0}
_PEDIDOS = []


class _YahooMultimoneda:
    def __init__(self, ticker):
        self.ticker = ticker
        _PEDIDOS.append(ticker)
        idx = pd.bdate_range("2023-06-01", periods=560, tz="UTC")
        if ticker in _FX:
            px = np.full(len(idx), _FX[ticker])
        else:
            nivel = _DATOS.get(ticker, ("USD", 1e11, 100.0))[2]
            # crc32 y no hash(): hash() de un str cambia en cada proceso
            # (PYTHONHASHSEED) y volvia aleatorios los precios del test.
            rng = np.random.default_rng(zlib.crc32(ticker.encode()))
            px = nivel * np.exp(np.cumsum(rng.normal(0.0003, 0.012, len(idx))))
        self._hist = pd.DataFrame(
            {"Open": px, "High": px, "Low": px, "Close": px, "Volume": 1_000_000}, index=idx)
        self._hist.index.name = "Date"

    def history(self, *args, **kwargs):
        return self._hist.copy()

    @property
    def fast_info(self):
        cur, cap, nivel = _DATOS.get(self.ticker, ("USD", 1e11, 100.0))
        return {"lastPrice": nivel, "marketCap": cap, "currency": cur}

    @property
    def info(self):
        return {}

    @property
    def history_metadata(self):
        if self.ticker in _FX:
            return {"currency": "USD"}
        return {"currency": _DATOS.get(self.ticker, ("USD",))[0]}


def test_no_quedan_universos_fijos_ni_logica_de_etf():
    nombres = {n.targets[0].id for n in ast.parse(FUENTE).body
               if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
    for viejo in ("INTERNATIONAL_TICKERS", "ETF_TICKERS", "COMMODITY_TICKERS",
                  "INCLUIR_ETFS", "PESO_MAX_ETFS"):
        assert viejo not in nombres
        assert viejo not in FUENTE
    for viejo in ("activos_elegibles", "es_etf_banda", "usar_tope_etf", "combinar_tickers"):
        assert viejo not in FUENTE
    assert "FALLBACK_ETF_POR_TICKER = {}" in FUENTE


def test_bl_con_internacionales_en_tickers(monkeypatch):
    _PEDIDOS.clear()
    monkeypatch.setenv("AMPM_SMOKE", "1")
    monkeypatch.setenv("AMPM_SMOKE_TICKERS", "AAPL,MSFT,azn.l,7203.T,AAPL")
    monkeypatch.setenv("POLYGON_API_KEY", "")
    monkeypatch.setattr("yfinance.Ticker", _YahooMultimoneda)
    monkeypatch.setattr(go.Figure, "show", lambda self, *a, **k: None)
    g = runpy.run_path(str(ROOT / "black_litterman.py"), run_name="__main__")

    # Universo = TICKERS normalizado, sin duplicados ni listas agregadas.
    assert g["TICKERS"] == ["AAPL", "MSFT", "AZN.L", "7203.T"]
    assert g["_intl_universo"] == ["AZN.L", "7203.T"]
    assert set(g["tickers"]) == set(g["TICKERS"])

    # FX solo de las monedas presentes; precios en USD (peniques -> libras).
    assert set(g["fx_prices_diarios"]) == {"GBP", "JPY"}
    assert "CAD=X" not in _PEDIDOS and "EURUSD=X" not in _PEDIDOS
    assert g["ticker_currency"]["AZN.L"] == "GBP"
    assert g["ticker_currency"]["7203.T"] == "JPY"
    # Fecha a fecha, precio en USD / precio local = factor de conversion exacto.
    precios = g["precios_diarios"]
    for tk, factor in (("AZN.L", 0.01 * 1.30), ("7203.T", 1.0 / 150.0)):
        local = _YahooMultimoneda(tk)._hist["Close"]
        local.index = local.index.tz_localize(None).normalize()
        comun = precios.index.intersection(local.index)
        assert len(comun) > 100
        ratio = precios.loc[comun, tk] / local.loc[comun]
        assert ratio.min() == pytest.approx(factor, rel=1e-9)
        assert ratio.max() == pytest.approx(factor, rel=1e-9)

    # Market cap en USD: AZN.L 1.84e13 GBp -> 2.39e11 USD; 7203.T 3.4e13 JPY -> 2.27e11 USD.
    caps = g["market_caps_raw"]
    assert caps["AZN.L"] == pytest.approx(1.84e11 * 1.30)
    assert caps["7203.T"] == pytest.approx(3.4e13 / 150.0)
    assert caps["AAPL"] == pytest.approx(3.0e12)
    w_mkt = pd.Series(g["w_mkt"], index=g["tickers"])
    assert w_mkt["AAPL"] > 10 * w_mkt["AZN.L"]

    # Los pesos finales suman 1 y no hay tope ni exclusion de ETF.
    assert g["w_mvsk"].sum() == pytest.approx(1.0)
    assert (g["w_mvsk"] >= 0).all()


def test_tickers_internacionales_no_van_a_polygon():
    assert "if not pc.is_us_ticker(tk):" in FUENTE
    assert 'motivo_calibracion[tk] = "sin_opciones_us"' in FUENTE
