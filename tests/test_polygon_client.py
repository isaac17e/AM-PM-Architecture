import json
import os
from datetime import date, timedelta

import numpy as np
import pytest
import requests

import polygon_client as pc


class _RespuestaFalsa:
    def __init__(self, status, data=None, headers=None, text=""):
        self.status_code = status
        self._data = data
        self.headers = headers or {}
        self.text = text or (json.dumps(data) if data is not None else "")

    def json(self):
        if self._data is None:
            raise ValueError("sin json")
        return self._data


@pytest.fixture(autouse=True)
def entorno_aislado(monkeypatch, tmp_path):
    """Sin API key, cache en un directorio temporal, sin red y sin esperas."""
    monkeypatch.setattr(pc, "API_KEY", None)
    monkeypatch.setattr(pc, "CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(pc, "_aviso_api_key_emitido", False)
    monkeypatch.setattr(pc, "_aviso_403_emitido", False)
    monkeypatch.setattr(pc.time, "sleep", lambda s: None)

    def _sin_red(*a, **k):
        raise AssertionError("se intento una llamada HTTP real")
    monkeypatch.setattr(requests, "get", _sin_red)

    for k in ("http_calls", "cache_hits", "incompletas", "truncadas_max_pages"):
        pc.diag[k] = 0
    pc.diag["status_counts"].clear()
    pc.diag["sample_errors"].clear()
    tope_original = pc.CALLS_PER_MIN
    pc.set_rate_limit(None)
    yield
    pc.set_rate_limit(tope_original)


# ------------------------------------------------------------------------------
# Formato de tickers (M-14)
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("entrada,esperado", [
    ("BRK-B", "BRK.B"), ("BF-B", "BF.B"), ("AAPL", "AAPL"), (" spy ", "spy"),
    ("BRK.B", "BRK.B"), ("", ""),
])
def test_polygon_format_ticker(entrada, esperado):
    assert pc.polygon_format_ticker(entrada) == esperado


def test_polygon_format_ticker_none():
    assert pc.polygon_format_ticker(None) is None


# ------------------------------------------------------------------------------
# Limite de tasa (B-11)
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("valor,esperado", [
    (None, pc.DEFAULT_CALLS_PER_MIN), ("", pc.DEFAULT_CALLS_PER_MIN),
    ("abc", pc.DEFAULT_CALLS_PER_MIN), ("5", 5.0), ("12.5", 12.5), (7, 7.0),
    ("0", None), ("-3", None), ("none", None), ("unlimited", None), ("UNLIMITED ", None),
])
def test_parse_calls_per_min(valor, esperado):
    assert pc._parse_calls_per_min(valor) == esperado


def test_default_rate_limit_is_documented_constant():
    assert pc.DEFAULT_CALLS_PER_MIN == 1200.0


def test_default_cache_dir_lives_outside_the_repo():
    destino = pc.default_cache_dir()
    assert destino.endswith("/.cache/am-pm/polygon")
    repo = os.path.dirname(os.path.abspath(pc.__file__))
    assert not destino.startswith(repo)


def test_set_rate_limit_updates_limiter_and_estimate():
    assert pc.set_rate_limit(120) == 120.0
    assert pc.CALLS_PER_MIN == 120.0
    assert pc._limitador.intervalo == pytest.approx(0.5)
    assert pc.estimate_minutes(240) == pytest.approx(2.0)
    assert pc.set_rate_limit("unlimited") is None
    assert pc._limitador.intervalo == 0.0
    assert pc.estimate_minutes(240) is None


def test_limiter_spaces_calls(monkeypatch):
    reloj = {"t": 100.0}
    dormido = []
    monkeypatch.setattr(pc.time, "monotonic", lambda: reloj["t"])
    monkeypatch.setattr(pc.time, "sleep", lambda s: dormido.append(s))
    pc.set_rate_limit(60)                  # 1 llamada por segundo
    pc._limitador.proxima = 0.0
    pc._limitador.esperar()                # primera: sin espera
    pc._limitador.esperar()                # segunda: espera 1 s
    pc._limitador.esperar()                # tercera: espera 2 s (reloj congelado)
    assert dormido == pytest.approx([1.0, 2.0])


# ------------------------------------------------------------------------------
# Clasificacion de fallos (B-11)
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("status", [429, 500, 502, 503, 504, "red", "max_pages"])
def test_es_transitorio_true(status):
    assert pc.es_transitorio(status)


@pytest.mark.parametrize("status", ["sin_api_key", 401, 403, 404, 200, "json_invalido"])
def test_es_transitorio_false(status):
    assert not pc.es_transitorio(status)


def test_n_fallos_transitorios_excludes_missing_key():
    with pytest.warns(RuntimeWarning):
        pc.get_json("https://api.polygon.io/v3/x?limit=1")
    assert pc.diag["status_counts"] == {"sin_api_key": 1}
    assert pc.n_fallos_transitorios() == 0


# ------------------------------------------------------------------------------
# get_json: sin clave, cache, reintentos
# ------------------------------------------------------------------------------

def test_get_json_without_api_key_is_definitive_and_warns_once():
    with pytest.warns(RuntimeWarning, match="POLYGON_API_KEY"):
        data, status = pc.get_json("https://api.polygon.io/v3/a?limit=1")
    assert data is None and status == "sin_api_key"
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        data, status = pc.get_json("https://api.polygon.io/v3/b?limit=1")   # no vuelve a avisar
    assert status == "sin_api_key"
    assert pc.diag["http_calls"] == 0


def test_cache_never_stores_current_date_or_snapshot(monkeypatch):
    """La cache de disco no guarda la cadena de hoy ni un agregado con fecha de hoy."""
    monkeypatch.setattr(pc, "API_KEY", "K")
    monkeypatch.setattr(requests, "get", lambda url, timeout: _RespuestaFalsa(200, {"results": [{"c": 1}]}))
    hoy = date.today().isoformat()
    ayer = (date.today() - timedelta(days=2)).isoformat()

    snap = "https://api.polygon.io/v3/snapshot/options/AAPL?limit=250"
    data, status = pc.get_json(snap, permanente=True)
    assert status == 200 and data["results"]
    assert pc.cache_set(snap, {"results": [1]}) is False
    assert pc.cache_get(snap) is None

    aggs_hoy = f"https://api.polygon.io/v2/aggs/ticker/O:ABC/range/1/day/{ayer}/{hoy}"
    pc.get_json(aggs_hoy, permanente=True)
    assert pc.cache_set(aggs_hoy, {"results": []}) is False
    assert pc.cache_get(aggs_hoy) is None
    assert pc.cache_set(f"mfis_hist_v3|AAPL|{hoy}|dte=30", {"S": 1}) is False

    contratos_hoy = f"https://api.polygon.io/v3/reference/options/contracts?as_of={hoy}&limit=10"
    assert pc.cache_set(contratos_hoy, {"results": []}) is False

    viejo = f"https://api.polygon.io/v2/aggs/ticker/O:ABC/range/1/day/{ayer}/{ayer}"
    data, status = pc.get_json(viejo, permanente=True)
    assert status == 200 and pc.cache_get(viejo)["results"][0]["c"] == 1
    antes = pc.diag["http_calls"]
    otra, status = pc.get_json(viejo, permanente=True)
    assert status == 200 and otra["results"][0]["c"] == 1
    assert pc.diag["http_calls"] == antes
    assert pc.diag["cache_hits"] >= 1

    clave_ayer = f"mfis_hist_v3|AAPL|{ayer}|dte=30"
    assert pc.cache_set(clave_ayer, {"S": 2}) is True
    assert pc.cache_get(clave_ayer) == {"S": 2}


def test_get_json_serves_from_cache_without_key_or_network():
    url = "https://api.polygon.io/v3/reference/tickers/AAPL"
    pc.cache_set(url, {"results": {"name": "Apple"}})
    data, status = pc.get_json(url, permanente=True)
    assert status == 200 and data["results"]["name"] == "Apple"
    assert pc.diag["cache_hits"] == 1 and pc.diag["http_calls"] == 0


def test_get_json_strips_key_from_cache_key_and_sends_it(monkeypatch):
    secuencia = []

    def _get(url, timeout):
        secuencia.append(url)
        return _RespuestaFalsa(200, {"results": [1]})
    monkeypatch.setattr(requests, "get", _get)
    data, status = pc.get_json("https://api.polygon.io/v3/x?limit=1", api_key="K", permanente=True)
    assert status == 200 and data == {"results": [1]}
    assert secuencia == ["https://api.polygon.io/v3/x?limit=1&apiKey=K"]
    assert pc.cache_get("https://api.polygon.io/v3/x?limit=1") == {"results": [1]}
    assert pc.cache_get("https://api.polygon.io/v3/x?limit=1&apiKey=K") is None


def test_get_json_retries_on_429_respecting_retry_after(monkeypatch):
    esperas = []
    monkeypatch.setattr(pc.time, "sleep", lambda s: esperas.append(s))
    respuestas = iter([_RespuestaFalsa(429, headers={"retry-after": "3"}),
                       _RespuestaFalsa(503),
                       _RespuestaFalsa(200, {"results": []})])
    monkeypatch.setattr(requests, "get", lambda url, timeout: next(respuestas))
    data, status = pc.get_json("https://api.polygon.io/v3/x", api_key="K", backoff=1.0)
    assert status == 200 and data == {"results": []}
    assert esperas == pytest.approx([3.0, 2.0])         # Retry-After, luego backoff 1*2^1
    assert pc.diag["http_calls"] == 3
    assert pc.diag["status_counts"] == {"200": 1}        # los transitorios reintentados no se registran


def test_get_json_403_is_not_retried_and_names_the_plan(monkeypatch, capsys):
    llamadas = []

    def _get(url, timeout):
        llamadas.append(url)
        return _RespuestaFalsa(403, text="not entitled")
    monkeypatch.setattr(requests, "get", _get)
    url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/AAPL"
    data, status = pc.get_json(url, api_key="K")
    assert data is None and status == 403 and not pc.es_transitorio(403)
    assert len(llamadas) == 1
    aviso = capsys.readouterr().out
    assert "403" in aviso and "yfinance" in aviso and "opciones" in aviso
    data, status = pc.get_json(
        "https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/2024-01-01/2024-02-01",
        api_key="K")
    assert status == 403 and len(llamadas) == 2
    assert capsys.readouterr().out == ""


def test_get_json_non_transient_error_is_not_retried_nor_cached(monkeypatch):
    llamadas = []

    def _get(url, timeout):
        llamadas.append(url)
        return _RespuestaFalsa(404, text='{"status":"NOT_FOUND"}')
    monkeypatch.setattr(requests, "get", _get)
    data, status = pc.get_json("https://api.polygon.io/v3/nada", api_key="K", permanente=True)
    assert data is None and status == 404
    assert len(llamadas) == 1
    assert pc.cache_get("https://api.polygon.io/v3/nada") is None
    assert pc.diag["sample_errors"][0]["status"] == 404


def test_get_json_exhausts_retries_on_network_error(monkeypatch):
    def _get(url, timeout):
        raise requests.ConnectionError("caido")
    monkeypatch.setattr(requests, "get", _get)
    data, status = pc.get_json("https://api.polygon.io/v3/x", api_key="K", max_retries=3)
    assert data is None and status == "red"
    assert pc.diag["http_calls"] == 3
    assert pc.n_fallos_transitorios() == 1


# ------------------------------------------------------------------------------
# get_all: paginacion y completitud
# ------------------------------------------------------------------------------

def _paginas(monkeypatch, paginas):
    def _get_json(url, api_key=None, permanente=False, **kw):
        return paginas[url]
    monkeypatch.setattr(pc, "get_json", _get_json)


def test_get_all_follows_next_url(monkeypatch):
    _paginas(monkeypatch, {
        "u1": ({"results": [1, 2], "next_url": "u2"}, 200),
        "u2": ({"results": [3], "next_url": None}, 200),
    })
    res, completo, status = pc.get_all("u1")
    assert res == [1, 2, 3] and completo and status == 200


def test_get_all_marks_incomplete_when_a_page_fails(monkeypatch):
    _paginas(monkeypatch, {
        "u1": ({"results": [1, 2], "next_url": "u2"}, 200),
        "u2": (None, 429),
    })
    res, completo, status = pc.get_all("u1")
    assert not completo and status == 429 and res == [1, 2]
    assert pc.diag["incompletas"] == 1


def test_get_all_truncated_by_max_pages(monkeypatch):
    _paginas(monkeypatch, {"u": ({"results": [1], "next_url": "u"}, 200)})
    res, completo, status = pc.get_all("u", max_pages=3)
    assert not completo and status == "max_pages" and res == [1, 1, 1]
    assert pc.es_transitorio(status)


# ------------------------------------------------------------------------------
# fetch_otm_chain con respuesta grabada
# ------------------------------------------------------------------------------

def _contrato(tipo, strike, exp, iv):
    return {"details": {"contract_type": tipo, "strike_price": strike,
                        "expiration_date": exp.strftime("%Y-%m-%d")},
            "implied_volatility": iv}


def _snapshot_grabado():
    """Imita /v3/snapshot/options: dos vencimientos, uno solo con calls."""
    hoy = date.today()
    e25 = hoy + timedelta(days=25)
    e31 = hoy + timedelta(days=31)   # mas cercano a 30 pero sin puts OTM
    e60 = hoy + timedelta(days=60)
    calls = [_contrato("call", k, e25, 0.25) for k in (100, 105, 110, 95)]
    calls += [_contrato("call", k, e31, 0.24) for k in (100, 105)]
    calls += [_contrato("call", k, e60, 0.27) for k in (100, 110)]
    calls += [_contrato("call", 115, e25, None), _contrato("call", 120, e25, -0.1)]
    puts = [_contrato("put", k, e25, 0.30) for k in (95, 90, 85, 100)]
    puts += [_contrato("put", k, e60, 0.32) for k in (95, 90)]
    puts += [_contrato("put", 80, e25, 0.33), _contrato("put", 80, e25, 0.34)]  # duplicado
    return {"call": calls, "put": puts}


def test_fetch_otm_chain_prefers_expiry_at_or_beyond_target(monkeypatch):
    grabado = _snapshot_grabado()
    urls = []

    def _get_all(url, api_key=None, max_pages=40):
        urls.append(url)
        tipo = "call" if "contract_type=call" in url else "put"
        return grabado[tipo], True, 200
    monkeypatch.setattr(pc, "get_all", _get_all)

    S = 100.0
    calls, puts, info = pc.fetch_otm_chain("BRK.B", S, "2026-01-01", "2026-12-31",
                                           70.0, 140.0, target_dte=30)
    assert info["completo"] and info["status"] == 200
    # 25 esta mas cerca de 30, pero 60 cumple DTE >= objetivo. 31 no tiene puts.
    assert info["dte"] == 60
    assert info["expiracion"] == (date.today() + timedelta(days=60)).strftime("%Y-%m-%d")
    assert list(calls["strike"]) == [100, 110]
    assert sorted(puts["strike"]) == [90, 95]
    assert (calls["type"] == "call").all() and (puts["type"] == "put").all()
    assert len(urls) == 2 and "BRK.B" in urls[0]
    assert "strike_price.gte=70.00" in urls[0] and "strike_price.lte=140.00" in urls[0]


def test_fetch_otm_chain_falls_back_when_nothing_reaches_min_dte(monkeypatch):
    hoy = date.today()
    e15 = hoy + timedelta(days=15)
    grabado = {
        "call": [_contrato("call", 100, e15, 0.2), _contrato("call", 110, e15, 0.2)],
        "put": [_contrato("put", 90, e15, 0.2), _contrato("put", 80, e15, 0.2)],
    }
    monkeypatch.setattr(pc, "get_all", lambda url, api_key=None, max_pages=40: (
        grabado["call" if "contract_type=call" in url else "put"], True, 200))
    _calls, _puts, info = pc.fetch_otm_chain(
        "AAPL", 100.0, "2020-01-01", "2030-01-01", 50.0, 150.0, target_dte=30, min_dte=21)
    assert info["dte"] == 15


def test_expiry_rank_prefers_50_over_15_for_a_30_day_target():
    cols = pc.expiry_rank_columns([15, 50], target_dte=30, n_contracts=[10, 4], min_dte=21)
    # 15 queda por debajo del minimo y del objetivo; 50 cumple los dos.
    assert cols["_bajo_min"][0] == 1 and cols["_bajo_obj"][0] == 1
    assert cols["_bajo_min"][1] == 0 and cols["_bajo_obj"][1] == 0


@pytest.mark.parametrize("ticker, es_us", [
    ("AAPL", True),
    ("BRK-B", True),
    ("BRK.B", True),
    ("BF-B", True),
    ("NG.L", False),
    ("SU.TO", False),
    ("ASML.AS", False),
    ("NESN.SW", False),
    ("0700.HK", False),
    ("BHP.AX", False),
    ("VALE.SA", False),
    ("AMXL.MX", False),
    ("005930.KS", False),
    ("FOO.ZZ", False),
])
def test_is_us_ticker(ticker, es_us):
    assert pc.is_us_ticker(ticker) is es_us


def test_fetch_otm_chain_incomplete_download_returns_empty(monkeypatch):
    monkeypatch.setattr(pc, "get_all", lambda url, api_key=None, max_pages=40: ([], False, 429))
    calls, puts, info = pc.fetch_otm_chain("AAPL", 100.0, "2026-01-01", "2026-12-31",
                                           70.0, 140.0, target_dte=30)
    assert calls.empty and puts.empty
    assert not info["completo"] and info["status"] == 429 and pc.es_transitorio(info["status"])


def test_fetch_otm_chain_without_key_is_not_transient():
    with pytest.warns(RuntimeWarning):
        calls, puts, info = pc.fetch_otm_chain("AAPL", 100.0, "2026-01-01", "2026-12-31",
                                               70.0, 140.0, target_dte=30)
    assert calls.empty and puts.empty
    assert not info["completo"] and info["status"] == "sin_api_key"
    assert not pc.es_transitorio(info["status"])


@pytest.mark.parametrize("S", [None, np.nan, 0.0, -5.0])
def test_fetch_otm_chain_invalid_spot(S):
    calls, puts, info = pc.fetch_otm_chain("AAPL", S, "2026-01-01", "2026-12-31",
                                           70.0, 140.0, target_dte=30)
    assert calls.empty and puts.empty and info["completo"]
