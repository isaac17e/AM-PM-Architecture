import numpy as np
import pandas as pd
import pytest

import market_data as md

SUFFIX_MAP = {".TO": "CAD", ".L": "GBP", ".T": "JPY", ".PA": "EUR", ".DE": "EUR", ".AS": "EUR"}


# ------------------------------------------------------------------------------
# 1. Moneda (A-2)
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("raw, esperado", [
    ("USD", "USD"), ("usd", "USD"), ("GBp", "GBP"), ("GBX", "GBP"), ("GBP", "GBP"),
    ("ZAc", "ZAR"), (" jpy ", "JPY"), (None, None), ("", None), ("nan", None), (float("nan"), None),
])
def test_normalize_currency(raw, esperado):
    assert md.normalize_currency(raw) == esperado


@pytest.mark.parametrize("raw, factor", [
    ("GBp", 0.01), ("GBX", 0.01), ("ZAc", 0.01), ("GBP", 1.0), ("USD", 1.0), (None, 1.0),
])
def test_price_scale_factor(raw, factor):
    assert md.price_scale_factor(raw) == factor


def test_currency_from_suffix():
    assert md.currency_from_suffix("RY.TO", SUFFIX_MAP) == "CAD"
    assert md.currency_from_suffix("AZN.L", SUFFIX_MAP) == "GBP"
    assert md.currency_from_suffix("AAPL", SUFFIX_MAP) is None
    assert md.currency_from_suffix("BRK-B", SUFFIX_MAP) is None


def test_resolve_currencies_provider_wins_over_override_hsbc_bp():
    """A-2: HSBC y BP son ADRs en USD; el override GBP antiguo debe generar conflicto."""
    tickers = ["HSBC", "BP", "AAPL"]
    overrides = {"HSBC": "GBP", "BP": "GBP"}
    provider = {"HSBC": "USD", "BP": "USD", "AAPL": "USD"}
    cur, conflictos = md.resolve_currencies(tickers, SUFFIX_MAP, overrides=overrides, provider=provider)
    assert cur == {"HSBC": "USD", "BP": "USD", "AAPL": "USD"}
    assert sorted(c["ticker"] for c in conflictos) == ["BP", "HSBC"]
    for c in conflictos:
        assert c["fuente"] == "override"
        assert c["manual"] == "GBP"
        assert c["proveedor"] == "USD"


def test_resolve_currencies_override_applies_without_provider():
    cur, conflictos = md.resolve_currencies(["HSBC"], SUFFIX_MAP, overrides={"HSBC": "gbp"}, provider={})
    assert cur == {"HSBC": "GBP"}
    assert conflictos == []


def test_resolve_currencies_suffix_and_default():
    cur, conflictos = md.resolve_currencies(["RY.TO", "7203.T", "MSFT"], SUFFIX_MAP)
    assert cur == {"RY.TO": "CAD", "7203.T": "JPY", "MSFT": "USD"}
    assert conflictos == []


def test_resolve_currencies_pence_normalized_no_conflict_with_suffix():
    cur, conflictos = md.resolve_currencies(["AZN.L"], SUFFIX_MAP, provider={"AZN.L": "GBp"})
    assert cur == {"AZN.L": "GBP"}
    assert conflictos == []


def test_resolve_currencies_suffix_conflict_reported():
    cur, conflictos = md.resolve_currencies(["ABC.L"], SUFFIX_MAP, provider={"ABC.L": "USD"})
    assert cur == {"ABC.L": "USD"}
    assert len(conflictos) == 1 and conflictos[0]["fuente"] == "sufijo"
    assert conflictos[0]["manual"] == "GBP" and conflictos[0]["proveedor"] == "USD"


def test_resolve_currencies_provider_nan_falls_back():
    cur, _ = md.resolve_currencies(["RY.TO"], SUFFIX_MAP, provider={"RY.TO": float("nan")})
    assert cur == {"RY.TO": "CAD"}


# ------------------------------------------------------------------------------
# 2. Alineacion multi-mercado con ffill acotado (M-1)
# ------------------------------------------------------------------------------

def _bdays(start, n):
    return pd.bdate_range(start, periods=n)


def _precios_dos_mercados():
    """SPY (calendario maestro, 20 dias) y un ticker de Tokio con un festivo local."""
    cal = _bdays("2024-01-01", 20)
    spy = pd.Series(np.linspace(100, 110, 20), index=cal)
    tokio_idx = cal.drop(cal[7])                  # festivo en Tokio el dia 8
    tokio = pd.Series(np.linspace(1000, 1050, 19), index=tokio_idx)
    prices = pd.concat({"SPY": spy, "7203.T": tokio}, axis=1)
    return prices, cal


def test_align_fills_local_holiday_instead_of_dropping_row():
    prices, cal = _precios_dos_mercados()
    # Comportamiento antiguo: dropna global pierde el dia para todos.
    assert len(prices.dropna()) == 19
    aligned, info = md.align_prices_to_calendar(prices, cal, max_ffill=2, min_coverage=0.8)
    assert len(aligned) == 20
    assert info["n_rows_dropped"] == 0
    assert info["n_filled"]["7203.T"] == 1
    assert info["n_filled"]["SPY"] == 0
    # El festivo se cubre con el ultimo cierre disponible.
    assert aligned.loc[cal[7], "7203.T"] == aligned.loc[cal[6], "7203.T"]
    assert info["dropped_low_coverage"] == []


def test_align_long_gap_not_filled_beyond_limit():
    cal = _bdays("2024-01-01", 20)
    a = pd.Series(np.arange(20, dtype=float), index=cal)
    b = a.copy()
    b.iloc[5:10] = np.nan                         # laguna de 5 dias
    aligned, info = md.align_prices_to_calendar(pd.concat({"A": a, "B": b}, axis=1), cal,
                                                max_ffill=2, min_coverage=0.5)
    # Solo 2 dias se rellenan; los otros 3 se descartan como filas.
    assert info["n_filled"]["B"] == 2
    assert info["n_rows_dropped"] == 3
    assert len(aligned) == 17
    assert aligned.loc[cal[6], "B"] == b.iloc[4]


def test_align_zero_ffill_equivalent_to_dropna():
    prices, cal = _precios_dos_mercados()
    aligned, info = md.align_prices_to_calendar(prices, cal, max_ffill=0, min_coverage=0.5)
    assert len(aligned) == 19
    assert info["n_filled"].sum() == 0


def test_align_drops_low_coverage_ticker():
    cal = _bdays("2024-01-01", 20)
    a = pd.Series(np.arange(20, dtype=float), index=cal)
    corto = pd.Series(np.arange(5, dtype=float), index=cal[-5:])   # 25 % de cobertura
    aligned, info = md.align_prices_to_calendar(pd.concat({"A": a, "NUEVO": corto}, axis=1), cal,
                                                max_ffill=2, min_coverage=0.8)
    assert info["dropped_low_coverage"] == ["NUEVO"]
    assert list(aligned.columns) == ["A"]
    assert len(aligned) == 20
    assert info["coverage"]["NUEVO"] == pytest.approx(0.25)


def test_align_reindexes_to_calendar_and_keeps_offcalendar_level():
    cal = _bdays("2024-01-01", 10)
    # Tokio opera un dia en que EE. UU. cierra (feriado US el dia 5): el nivel
    # de ese cierre debe arrastrarse al siguiente dia del calendario.
    cal_us = cal.drop(cal[4])
    spy = pd.Series(np.arange(9, dtype=float), index=cal_us)
    tokio = pd.Series(np.arange(10, dtype=float) * 10, index=cal)
    aligned, info = md.align_prices_to_calendar(
        pd.concat({"SPY": spy, "T": tokio}, axis=1, sort=True), cal_us,
                                                max_ffill=2)
    assert list(aligned.index) == list(cal_us)
    assert aligned.loc[cal[5], "T"] == 50.0       # cierre propio del dia 6, no rellenado
    assert info["n_filled"].sum() == 0


def test_align_requires_datetime_index():
    with pytest.raises(TypeError):
        md.align_prices_to_calendar(pd.DataFrame({"A": [1.0, 2.0]}), pd.bdate_range("2024-01-01", periods=2))


# ------------------------------------------------------------------------------
# 3. Semana parcial (B-6)
# ------------------------------------------------------------------------------

def _semanal(last_daily):
    idx = pd.bdate_range("2024-01-01", last_daily)
    s = pd.Series(np.arange(len(idx), dtype=float), index=idx)
    return s.resample("W").last(), idx[-1]


def test_drop_partial_last_week_wednesday_dropped():
    semanal, ultimo = _semanal("2024-01-24")       # miercoles
    out, descartada = md.drop_partial_last_week(semanal, ultimo)
    assert descartada is True
    assert len(out) == len(semanal) - 1
    assert out.index[-1] == pd.Timestamp("2024-01-21")


def test_drop_partial_last_week_friday_kept():
    semanal, ultimo = _semanal("2024-01-26")       # viernes
    out, descartada = md.drop_partial_last_week(semanal, ultimo)
    assert descartada is False
    assert len(out) == len(semanal)


def test_drop_partial_last_week_thursday_before_holiday_friday():
    # Jueves con viernes festivo: conservador, se descarta (no hay forma de
    # distinguirlo de una semana en curso sin calendario de festivos).
    semanal, ultimo = _semanal("2024-01-25")
    _, descartada = md.drop_partial_last_week(semanal, ultimo)
    assert descartada is True


def test_drop_partial_last_week_empty_and_dataframe():
    vacio = pd.Series(dtype=float)
    out, descartada = md.drop_partial_last_week(vacio, pd.Timestamp("2024-01-24"))
    assert len(out) == 0 and descartada is False
    semanal, ultimo = _semanal("2024-01-24")
    df = semanal.to_frame("A")
    out_df, descartada = md.drop_partial_last_week(df, ultimo)
    assert descartada is True and isinstance(out_df, pd.DataFrame) and len(out_df) == len(df) - 1
