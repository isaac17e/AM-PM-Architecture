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


def test_resolve_execution_months_none_follows_the_run_date():
    meses, aviso = md.resolve_execution_months(None, as_of="2026-10-01", n_months=1)
    assert meses == [10] and aviso is None
    meses, aviso = md.resolve_execution_months(None, as_of="2026-11-15", n_months=3)
    assert meses == [11, 12, 1] and aviso is None


def test_dedupe_share_classes_keeps_the_configured_class():
    kept, notas = md.dedupe_share_classes(
        ["GOOG", "AAPL", "GOOGL", "MSFT"], (("GOOGL", "GOOG"),))
    assert kept == ["AAPL", "GOOGL", "MSFT"]
    assert notas == [("GOOGL", ["GOOG"])]
    solo, vacias = md.dedupe_share_classes(["GOOG", "AAPL"], (("GOOGL", "GOOG"),))
    assert solo == ["GOOG", "AAPL"] and vacias == []


def test_resolve_execution_months_keeps_an_explicit_list_and_warns():
    meses, aviso = md.resolve_execution_months([9], as_of="2026-10-01")
    assert meses == [9]
    assert aviso and "10" in aviso and "9" in aviso
    meses, aviso = md.resolve_execution_months([10, 11], as_of="2026-10-01")
    assert meses == [10, 11] and aviso is None


def _cierres(n, nivel, tz=None):
    idx = pd.bdate_range("2024-01-02", periods=n, tz=tz)
    return pd.DataFrame({"date": idx, "close": np.linspace(nivel, nivel + 1, n)})


def test_frames_from_yf_download_reads_both_multiindex_orders():
    idx = pd.bdate_range("2024-01-02", periods=25, tz="America/New_York")
    por_campo = pd.DataFrame(
        np.column_stack([np.arange(25) + 10.0, np.arange(25) + 20.0]),
        index=idx,
        columns=pd.MultiIndex.from_product([["Close"], ["AAA", "BBB"]]),
    )
    frames = md.frames_from_yf_download(por_campo, ["AAA", "BBB", "CCC"])
    assert frames["CCC"] is None
    assert list(frames["AAA"].columns) == ["date", "close"]
    assert frames["AAA"]["date"].dt.tz is None
    assert frames["AAA"]["close"].iloc[0] == pytest.approx(10.0)
    assert frames["BBB"]["close"].iloc[-1] == pytest.approx(44.0)
    por_ticker = pd.DataFrame(
        np.column_stack([np.arange(25) + 3.0, np.arange(25) + 1.0]),
        index=idx,
        columns=pd.MultiIndex.from_product([["AAA"], ["Open", "Close"]]),
    )
    uno = md.frames_from_yf_download(por_ticker, ["AAA"])
    assert uno["AAA"]["close"].iloc[0] == pytest.approx(1.0)
    plano = pd.DataFrame({"Close": np.arange(25) + 7.0}, index=idx)
    solo = md.frames_from_yf_download(plano, ["MSFT"])
    assert solo["MSFT"]["close"].iloc[0] == pytest.approx(7.0)


def test_get_spot_history_downloads_the_batch_once_and_workers_only_read():
    from concurrent.futures import ThreadPoolExecutor

    llamadas = {"batch": 0, "single": 0}

    def batch(tickers, start, end):
        llamadas["batch"] += 1
        assert list(tickers) == ["AAA", "BBB", "CCC"]
        assert start == "2024-01-01" and end == "2024-06-01"
        return {t: _cierres(30, 10 + i) for i, t in enumerate(tickers)}

    def single(*_a, **_k):
        llamadas["single"] += 1
        raise AssertionError("yfinance no se llama desde un worker")

    out = md.get_spot_history(
        ["AAA", "BBB", "CCC"], "2024-01-01", "2024-06-01",
        providers=[{"name": "yfinance", "batch": batch, "single": single}],
    )
    assert llamadas["batch"] == 1 and llamadas["single"] == 0
    assert out["missing"] == [] and out["recovered"] == []

    def worker(ticker):
        serie = md.spot_series_for(out["series"], ticker)
        return float(serie["close"].iloc[0])

    with ThreadPoolExecutor(max_workers=3) as pool:
        leidos = list(pool.map(worker, ["AAA", "BBB", "CCC"]))
    assert leidos == pytest.approx([10.0, 11.0, 12.0])
    assert llamadas["single"] == 0


def test_get_spot_history_retries_the_missing_ticker_then_reports_the_rest():
    intentos = {"BBB": 0}
    esperas = []

    def batch(tickers, start, end):
        return {"AAA": _cierres(30, 10.0), "BBB": _cierres(5, 1.0), "CCC": None}

    def single(ticker, start, end):
        intentos[ticker] = intentos.get(ticker, 0) + 1
        if ticker == "BBB" and intentos[ticker] == 3:
            return _cierres(30, 8.0)
        return None

    out = md.get_spot_history(
        ["AAA", "BBB", "CCC"], "2024-01-01", "2024-06-01",
        providers=[{"name": "yfinance", "batch": batch, "single": single}],
        retries=3, backoff=0.5, sleep=esperas.append,
    )
    assert intentos["BBB"] == 3
    assert intentos["CCC"] == 3
    assert esperas == [0.5, 1.0, 0.5, 1.0]
    assert "BBB" in out["series"] and out["series"]["BBB"]["close"].iloc[0] == pytest.approx(8.0)
    assert out["recovered"] == ["BBB"]
    assert out["missing"] == ["CCC"]
    assert out["batch_calls"] == 1
    assert out["single_calls"] == 6


def test_get_spot_history_falls_through_to_the_next_provider():
    vistos = []

    def yf_batch(tickers, start, end):
        vistos.append(("yf-batch", list(tickers)))
        return {"AAA": _cierres(30, 1.0)}

    def yf_single(ticker, start, end):
        vistos.append(("yf-single", ticker))
        return None

    def fmp_batch(tickers, start, end):
        vistos.append(("fmp-batch", list(tickers)))
        return {"BBB": _cierres(30, 4.0)}

    def fmp_single(ticker, start, end):
        vistos.append(("fmp-single", ticker))
        return None

    out = md.get_spot_history(
        ["AAA", "BBB"], "2024-01-01", "2024-06-01",
        providers=[
            {"name": "yfinance", "batch": yf_batch, "single": yf_single},
            {"name": "fmp", "batch": fmp_batch, "single": fmp_single},
        ],
        retries=2, backoff=0.0, sleep=lambda _s: None,
    )
    assert out["missing"] == []
    assert out["recovered"] == ["BBB"]
    assert ("fmp-batch", ["BBB"]) in vistos
    assert ("fmp-single", "AAA") not in vistos
    assert out["batch_calls"] == 2


def test_yfinance_batch_is_one_unadjusted_download(monkeypatch):
    capturado = {}

    def download(tickers, **kwargs):
        capturado["tickers"] = list(tickers)
        capturado["kwargs"] = kwargs
        idx = pd.bdate_range("2024-01-02", periods=22)
        cols = pd.MultiIndex.from_product([["Close"], ["AAA", "BBB"]])
        return pd.DataFrame(
            np.column_stack([np.arange(22) + 10.0, np.arange(22) + 30.0]),
            index=idx, columns=cols,
        )

    monkeypatch.setattr(md.yf, "download", download)

    def _sin_ticker(*_a, **_k):
        raise AssertionError("el bloque no usa Ticker")

    monkeypatch.setattr(md.yf, "Ticker", _sin_ticker)
    frames = md.yfinance_spot_batch(["AAA", "BBB"], "2024-01-01", "2024-03-01")
    assert capturado["tickers"] == ["AAA", "BBB"]
    assert capturado["kwargs"]["auto_adjust"] is False
    assert capturado["kwargs"]["threads"] is False
    assert capturado["kwargs"]["group_by"] == "column"
    assert len(frames["AAA"]) == 22
    assert frames["BBB"]["close"].iloc[0] == pytest.approx(30.0)


def test_yfinance_single_uses_history_when_download_is_empty(monkeypatch):
    llamadas = []

    def download(*_a, **_k):
        llamadas.append("download")
        return pd.DataFrame()

    class _Ticker:
        def __init__(self, ticker):
            llamadas.append(ticker)

        def history(self, **_k):
            llamadas.append("history")
            idx = pd.bdate_range("2024-01-02", periods=21)
            return pd.DataFrame({"Close": np.arange(21) + 5.0}, index=idx)

    monkeypatch.setattr(md.yf, "download", download)
    monkeypatch.setattr(md.yf, "Ticker", _Ticker)
    frame = md.yfinance_spot_single("CCC", "2024-01-01", "2024-03-01")
    assert llamadas == ["download", "CCC", "history"]
    assert frame["close"].iloc[0] == pytest.approx(5.0)


def test_single_retries_do_not_overlap():
    import threading
    import time

    en_vuelo = {"n": 0, "max": 0}
    guarda = threading.Lock()

    def batch(_tickers, _start, _end):
        return {}

    def single(_ticker, _start, _end):
        with guarda:
            en_vuelo["n"] += 1
            en_vuelo["max"] = max(en_vuelo["max"], en_vuelo["n"])
        time.sleep(0.05)
        with guarda:
            en_vuelo["n"] -= 1
        return None

    def correr():
        md.get_spot_history(
            ["ZZZ"], "2024-01-01", "2024-02-01",
            providers=[{"name": "t", "batch": batch, "single": single}],
            retries=1, sleep=lambda _s: None,
        )

    hilos = [threading.Thread(target=correr) for _ in range(4)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert en_vuelo["max"] == 1


# ------------------------------------------------------------------------------
# 5. Factores Fama-French: https + timeout + reintentos + cache local (sin red)
# ------------------------------------------------------------------------------

def _zip_ff(n_meses=36, desplazo=0.0):
    import io
    import zipfile
    filas = []
    for i in range(n_meses):
        anio, mes = 2020 + i // 12, i % 12 + 1
        filas.append(f"{anio}{mes:02d},{1.0 + i * 0.1 + desplazo:8.2f},{-0.5:8.2f},{0.3:8.2f},{0.02:8.2f}")
    texto = ("This file was created by CMPT_ME_BEME_RETS using the 202509 CRSP database.\r\n\r\n"
             ",Mkt-RF,SMB,HML,RF\r\n" + "\r\n".join(filas) + "\r\n\r\n"
             " Annual Factors: January-December \r\n,Mkt-RF,SMB,HML,RF\r\n2020,   10.00,    1.00,    2.00,    0.50\r\n")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("F-F_Research_Data_Factors.CSV", texto)
    return buf.getvalue()


class _Resp:
    def __init__(self, content=b"", status=200):
        self.content = content
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")


class _GetterFalso:
    """Devuelve las respuestas (o lanza las excepciones) en orden; registra las llamadas."""

    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []

    def __call__(self, url, timeout=None):
        self.llamadas.append((url, timeout))
        r = self.respuestas.pop(0) if len(self.respuestas) > 1 else self.respuestas[0]
        if isinstance(r, Exception):
            raise r
        return r


def _ff(tmp_path, getter, **kw):
    pausas = []
    out = md.fetch_fama_french(cache_dir=str(tmp_path), getter=getter, sleep=pausas.append, **kw)
    return out, pausas


def test_parse_fama_french_zip_devuelve_la_tabla_mensual_en_porcentaje():
    tabla = md.parse_fama_french_zip(_zip_ff())
    assert list(tabla.columns) == ["Mkt-RF", "SMB", "HML", "RF"]
    assert len(tabla) == 36 and str(tabla.index[0]) == "2020-01"
    assert tabla["Mkt-RF"].iloc[0] == pytest.approx(1.0)
    recorte = md.parse_fama_french_zip(_zip_ff(), start="2021-01-01", end="2021-12-31")
    assert len(recorte) == 12


def test_ff_descarga_ok_usa_https_timeout_y_guarda_cache(tmp_path):
    getter = _GetterFalso(_Resp(_zip_ff()))
    out, pausas = _ff(tmp_path, getter)
    assert out["status"] == "downloaded" and out["age_days"] == 0.0 and len(out["data"]) == 36
    assert getter.llamadas == [(md.FF_URL.format(dataset="F-F_Research_Data_Factors"), 30)]
    assert getter.llamadas[0][0].startswith("https://")
    assert pausas == []
    assert (tmp_path / "F-F_Research_Data_Factors_CSV.zip").read_bytes() == _zip_ff()


def test_ff_reintenta_con_backoff_y_luego_baja(tmp_path):
    getter = _GetterFalso(TimeoutError("timed out"), _Resp(status=503), _Resp(_zip_ff()))
    out, pausas = _ff(tmp_path, getter, retries=3, backoff=2.0)
    assert out["status"] == "downloaded"
    assert len(getter.llamadas) == 3
    assert pausas == [2.0, 4.0]


def test_ff_si_falla_usa_la_cache_con_su_edad(tmp_path, capsys):
    import os
    ruta = tmp_path / "F-F_Research_Data_Factors_CSV.zip"
    ruta.write_bytes(_zip_ff())
    hace_10_dias = os.path.getmtime(ruta) + 10 * 86400
    getter = _GetterFalso(TimeoutError("timed out"))
    pausas = []
    out = md.fetch_fama_french(cache_dir=str(tmp_path), getter=getter, sleep=pausas.append,
                               retries=2, now=lambda: hace_10_dias)
    assert out["status"] == "cache"
    assert out["age_days"] == pytest.approx(10.0)
    assert len(out["data"]) == 36 and "timed out" in out["error"]
    assert len(getter.llamadas) == 2 and pausas == [2.0]
    assert "hace 10 dias" in capsys.readouterr().out


def test_ff_sin_red_ni_cache_es_failed_con_aviso_fuerte(tmp_path, capsys):
    out, _ = _ff(tmp_path, _GetterFalso(ConnectionError("sin red")), retries=2)
    assert out["status"] == "failed" and out["data"] is None and out["age_days"] is None
    assert "sin red" in out["error"]
    assert "ADVERTENCIA FUERTE" in capsys.readouterr().out


def test_ff_cache_corrupta_cuenta_como_failed_y_un_zip_invalido_no_pisa_la_cache(tmp_path):
    ruta = tmp_path / "F-F_Research_Data_Factors_CSV.zip"
    ruta.write_bytes(_zip_ff())
    # Respuesta 200 pero basura: no se parsea, no sobreescribe la copia buena.
    out, _ = _ff(tmp_path, _GetterFalso(_Resp(b"<html>mantenimiento</html>")), retries=1)
    assert out["status"] == "cache"
    assert ruta.read_bytes() == _zip_ff()
    ruta.write_bytes(b"corrupto")
    out, _ = _ff(tmp_path, _GetterFalso(_Resp(b"<html></html>")), retries=1)
    assert out["status"] == "failed"


def test_ff_cache_dir_por_defecto_esta_ignorada_por_git(monkeypatch):
    monkeypatch.delenv("AMPM_FF_CACHE_DIR", raising=False)
    ruta = md.default_ff_cache_dir()
    assert ruta.endswith("/.cache/fama_french")
    monkeypatch.setenv("AMPM_FF_CACHE_DIR", "/tmp/otra")
    assert md.default_ff_cache_dir() == "/tmp/otra"
    gitignore = (__import__("pathlib").Path(md.__file__).parent / ".gitignore").read_text()
    assert ".cache/fama_french/" in gitignore.splitlines()
