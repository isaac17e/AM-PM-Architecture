"""Horizonte configurable (BL_HORIZON_MONTHS / horizon_months) y modo previews (BL_MODE).

Sin red: black_litterman.py corre bajo AMPM_SMOKE=1 con yfinance falso y sin
clave de Polygon.
"""

import ast
import json
import math
import runpy
import sys
from datetime import date, datetime
from pathlib import Path

import plotly.graph_objects as go
import pytest

import pipeline_io
from test_script_smoke import _YahooFalso

ROOT = Path(__file__).resolve().parents[1]
UNIVERSO = ["AAPL", "MSFT", "SPY"]


# ----------------------------------------------------------------------------
# Resolucion del horizonte
# ----------------------------------------------------------------------------

def test_horizon_default_when_nothing_set():
    assert pipeline_io.resolve_horizon(2, None, env={}) == (2, "default")
    assert pipeline_io.resolve_horizon_months(2, None, env={}) == 2


def test_horizon_env_beats_default():
    assert pipeline_io.resolve_horizon(2, None, env={"BL_HORIZON_MONTHS": " 6 "}) == (6, "BL_HORIZON_MONTHS")


def test_horizon_blank_env_is_unset():
    assert pipeline_io.resolve_horizon(2, None, env={"BL_HORIZON_MONTHS": "  "}) == (2, "default")


def test_horizon_input_file_beats_env():
    entrada = {"tickers": ["AAPL"], "horizon_months": 9}
    assert pipeline_io.resolve_horizon(
        2, entrada, env={"BL_HORIZON_MONTHS": "3"}) == (9, "BL_INPUT_FILE")


def test_horizon_input_without_key_falls_back_to_env():
    entrada = {"tickers": ["AAPL"], "horizon_months": None}
    assert pipeline_io.resolve_horizon(
        2, entrada, env={"BL_HORIZON_MONTHS": "3"}) == (3, "BL_HORIZON_MONTHS")


@pytest.mark.parametrize("valor", [1, 2, 12, "1", "12", "+4", 5.0])
def test_horizon_accepts_integers_1_to_12(valor):
    assert pipeline_io.parse_horizon_months(valor, "x") == int(valor)


@pytest.mark.parametrize("valor", [0, 13, -1, 100, "0", "13", "abc", "2.5", "1e1", 2.5,
                                   True, False, None, [3], {"m": 3}, float("nan"),
                                   float("inf")])
def test_horizon_rejects_invalid_values(valor):
    with pytest.raises(pipeline_io.InvalidHorizonError) as exc:
        pipeline_io.parse_horizon_months(valor, "BL_HORIZON_MONTHS")
    assert "BL_HORIZON_MONTHS invalido" in str(exc.value)
    assert "entre 1 y 12" in str(exc.value)


def test_horizon_invalid_env_is_clear_error():
    with pytest.raises(ValueError, match="BL_HORIZON_MONTHS invalido: '24'"):
        pipeline_io.resolve_horizon(2, None, env={"BL_HORIZON_MONTHS": "24"})


def test_horizon_invalid_input_beats_valid_env():
    with pytest.raises(ValueError, match=r"horizon_months \(BL_INPUT_FILE\) invalido"):
        pipeline_io.resolve_horizon(
            2, {"horizon_months": 0}, env={"BL_HORIZON_MONTHS": "3"})


def _archivo(tmp_path, payload):
    ruta = tmp_path / "bl_input.json"
    ruta.write_text(json.dumps(payload), encoding="utf-8")
    return str(ruta)


def test_load_bl_input_returns_horizon_months(tmp_path):
    ruta = _archivo(tmp_path, {"tickers": ["aapl", "msft"], "horizon_months": 4})
    data = pipeline_io.load_bl_input(ruta)
    assert data["horizon_months"] == 4
    assert data["tickers"] == ["AAPL", "MSFT"]


def test_load_bl_input_without_horizon_is_none(tmp_path):
    data = pipeline_io.load_bl_input(_archivo(tmp_path, {"tickers": ["AAPL", "MSFT"]}))
    assert data["horizon_months"] is None
    data = pipeline_io.load_bl_input(
        _archivo(tmp_path, {"tickers": ["AAPL", "MSFT"], "horizon_months": None}))
    assert data["horizon_months"] is None


@pytest.mark.parametrize("valor", [0, 13, "3", 2.5, True])
def test_load_bl_input_invalid_horizon_raises_not_warns(tmp_path, valor):
    ruta = _archivo(tmp_path, {"tickers": ["AAPL", "MSFT"], "horizon_months": valor})
    if valor == "3":
        # Un texto en el JSON se acepta igual que en la variable de entorno.
        assert pipeline_io.load_bl_input(ruta)["horizon_months"] == 3
        return
    with pytest.raises(pipeline_io.InvalidHorizonError):
        pipeline_io.load_bl_input(ruta)


def test_load_bl_input_invalid_horizon_not_masked_by_bad_tickers(tmp_path):
    ruta = _archivo(tmp_path, {"tickers": [], "horizon_months": 99})
    with pytest.raises(pipeline_io.InvalidHorizonError):
        pipeline_io.load_bl_input(ruta)


# ----------------------------------------------------------------------------
# Modo de ejecucion
# ----------------------------------------------------------------------------

def test_bl_mode_default_env_and_flag():
    assert pipeline_io.resolve_bl_mode(argv=[], env={}) == "full"
    assert pipeline_io.resolve_bl_mode(argv=[], env={"BL_MODE": ""}) == "full"
    assert pipeline_io.resolve_bl_mode(argv=[], env={"BL_MODE": " Previews "}) == "previews"
    assert pipeline_io.resolve_bl_mode(argv=["--previews"], env={}) == "previews"
    assert pipeline_io.resolve_bl_mode(argv=["--previews"], env={"BL_MODE": "full"}) == "previews"
    assert pipeline_io.resolve_bl_mode(
        argv=["--risk-profile", "moderado"], env={"BL_MODE": "full"}) == "full"


def test_bl_mode_rejects_unknown_value():
    with pytest.raises(ValueError, match="BL_MODE invalido: 'preview'"):
        pipeline_io.resolve_bl_mode(argv=[], env={"BL_MODE": "preview"})


# ----------------------------------------------------------------------------
# Forma del JSON de previews
# ----------------------------------------------------------------------------

def _payload(**extra):
    base = dict(
        as_of=date(2026, 1, 31), horizon_months=3, horizon_trading_days=63,
        risk_profile="agresivo", tau=0.10, delta_mkt=2.5, delta_mode="historical",
        tickers=["AAPL", "MSFT"], pi_eq=[0.02, 0.03], mu_historico=[0.05, float("nan")],
        vol_horizon=[0.11, 0.09], w_mkt=[0.6, 0.4],
        now=datetime(2026, 1, 31, 12, 0, 0, tzinfo=pipeline_io.BOGOTA),
    )
    base.update(extra)
    return pipeline_io.build_previews_payload(**base)


def test_previews_payload_shape():
    p = _payload(iv_horizon={"AAPL": 0.12}, iv_source={"AAPL": "ssvi"},
                 universe_requested=["AAPL", "MSFT", "ZZZ"])
    assert set(p) == {
        "schema_version", "kind", "source_repo", "generated_at", "as_of", "horizon_months",
        "horizon_days", "horizon_end", "horizon_trading_days", "risk_profile", "tau",
        "delta_mkt", "delta_mkt_mode", "units", "universe", "universe_requested",
        "universe_excluded", "tickers"}
    assert p["schema_version"] == 1 and p["kind"] == "bl_previews"
    assert p["as_of"] == "2026-01-31"
    assert p["generated_at"] == "2026-01-31T12:00:00-05:00"
    assert p["horizon_months"] == 3
    assert p["horizon_days"] == 89 and p["horizon_end"] == "2026-04-30"
    assert p["horizon_trading_days"] == 63
    assert p["risk_profile"] == "agresivo" and p["tau"] == 0.10 and p["delta_mkt"] == 2.5
    assert p["universe"] == ["AAPL", "MSFT"]
    assert p["universe_excluded"] == ["ZZZ"]
    assert "3 month(s)" in p["units"]["returns"] and "not annualized" in p["units"]["returns"]
    assert list(p["tickers"]) == ["AAPL", "MSFT"]
    aapl = p["tickers"]["AAPL"]
    assert set(aapl) == {"pi_eq", "mu_historico", "diff", "vol_horizon", "vol_hist_horizon",
                         "iv_horizon", "iv_source", "w_mkt", "moment_source"}
    assert aapl["diff"] == pytest.approx(0.05 - 0.02)
    assert aapl["iv_horizon"] == 0.12 and aapl["iv_source"] == "ssvi"
    assert aapl["w_mkt"] == 0.6 and aapl["vol_horizon"] == 0.11
    msft = p["tickers"]["MSFT"]
    assert msft["iv_horizon"] is None and msft["iv_source"] is None
    assert msft["mu_historico"] is None and msft["diff"] is None
    json.dumps(p, allow_nan=False)


def test_previews_payload_rejects_misaligned_columns():
    with pytest.raises(ValueError, match="w_mkt tiene 1 valores y hay 2 tickers"):
        _payload(w_mkt=[1.0])


def test_write_previews_default_dir_and_name(monkeypatch, tmp_path):
    monkeypatch.setenv("PORTFOLIO_OUT_DIR", str(tmp_path / "pf"))
    monkeypatch.delenv("BL_PREVIEWS_OUT", raising=False)
    ahora = datetime(2026, 1, 31, 12, 0, 5, tzinfo=pipeline_io.BOGOTA)
    ruta = pipeline_io.write_previews(_payload(), now=ahora)
    assert ruta == str(tmp_path / "pf" / "previews_20260131T120005.json")
    assert json.loads(Path(ruta).read_text(encoding="utf-8"))["kind"] == "bl_previews"
    assert not list((tmp_path / "pf").glob("*.tmp"))


def test_write_previews_env_dir_and_file(monkeypatch, tmp_path):
    ahora = datetime(2026, 1, 31, 12, 0, 5, tzinfo=pipeline_io.BOGOTA)
    monkeypatch.setenv("BL_PREVIEWS_OUT", str(tmp_path / "salida"))
    ruta = pipeline_io.write_previews(_payload(), now=ahora)
    assert ruta == str(tmp_path / "salida" / "previews_20260131T120005.json")

    destino = tmp_path / "otro" / "mi.json"
    monkeypatch.setenv("BL_PREVIEWS_OUT", str(destino))
    assert pipeline_io.write_previews(_payload(), now=ahora) == str(destino)
    assert destino.is_file()


# ----------------------------------------------------------------------------
# black_litterman.py de punta a punta (sin red)
# ----------------------------------------------------------------------------

def _entorno(monkeypatch, tmp_path, entrada=None):
    monkeypatch.setenv("AMPM_SMOKE", "1")
    monkeypatch.setenv("POLYGON_API_KEY", "")
    monkeypatch.setenv("PORTFOLIO_OUT_DIR", str(tmp_path / "portfolio"))
    monkeypatch.setattr("yfinance.Ticker", _YahooFalso)
    monkeypatch.setattr(go.Figure, "show", lambda self, *a, **k: None)
    payload = {"schema_version": 1, "tickers": UNIVERSO}
    payload.update(entrada or {})
    archivo = tmp_path / "bl_input.json"
    archivo.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("BL_INPUT_FILE", str(archivo))


def _correr(monkeypatch, tmp_path, entrada=None):
    _entorno(monkeypatch, tmp_path, entrada)
    g = runpy.run_path(str(ROOT / "black_litterman.py"), run_name="__main__")
    latest = json.loads((tmp_path / "portfolio" / "portfolio_latest.json").read_text(encoding="utf-8"))
    return g, latest


def test_default_horizon_is_unchanged(monkeypatch, tmp_path):
    g, latest = _correr(monkeypatch, tmp_path)
    assert g["MESES_HORIZONTE"] == 2
    assert g["horizonte_dias"] == 42
    assert g["factor_anualizacion"] == 9
    assert g["MAX_DIAS_VENCIMIENTO"] == 122
    assert g["BOOTSTRAP_BLOQUE"] == 21
    assert g["tau_horizonte"] == pytest.approx(2 / 12)
    assert g["_fuente_horizonte"] == "default"
    assert latest["params"]["meses_horizonte"] == 2
    esperado, fin = pipeline_io.horizon_from_months(date.today(), 2)
    assert latest["horizon_days"] == esperado and latest["horizon_end"] == fin


@pytest.mark.parametrize("meses", [1, 6, 12])
def test_env_horizon_propagates_to_every_derived_quantity(monkeypatch, tmp_path, meses):
    monkeypatch.setenv("BL_HORIZON_MONTHS", str(meses))
    g, latest = _correr(monkeypatch, tmp_path)
    assert g["MESES_HORIZONTE"] == meses
    assert g["_fuente_horizonte"] == "BL_HORIZON_MONTHS"
    assert g["horizonte_dias"] == meses * 21
    assert g["factor_anualizacion"] == round(52 * (meses / 12))
    assert g["MAX_DIAS_VENCIMIENTO"] == int(round(2.0 * (meses / 12.0) * 365.0))
    assert g["BOOTSTRAP_BLOQUE"] == max(21, (meses * 21) // 4)
    assert g["tau_horizonte"] == pytest.approx(meses / 12)
    assert g["H_VENTANA"] == meses * 21
    assert g["Rf_h"] == pytest.approx(g["Rf"] * meses / 12)
    assert g["etiqueta_horizonte"] == f"{meses} mes(es)"
    esperado, fin = pipeline_io.horizon_from_months(date.today(), meses)
    assert latest["horizon_days"] == esperado
    assert latest["horizon_end"] == fin
    assert latest["params"]["meses_horizonte"] == meses
    assert latest["metrics"]["expected_return"] is not None


def test_input_file_horizon_beats_env(monkeypatch, tmp_path):
    monkeypatch.setenv("BL_HORIZON_MONTHS", "3")
    g, latest = _correr(monkeypatch, tmp_path, {"horizon_months": 4})
    assert g["MESES_HORIZONTE"] == 4
    assert g["_fuente_horizonte"] == "BL_INPUT_FILE"
    assert g["horizonte_dias"] == 84
    assert latest["params"]["meses_horizonte"] == 4


def test_invalid_horizon_aborts_run_with_clear_error(monkeypatch, tmp_path):
    monkeypatch.setenv("BL_HORIZON_MONTHS", "13")
    _entorno(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="BL_HORIZON_MONTHS invalido: '13'"):
        runpy.run_path(str(ROOT / "black_litterman.py"), run_name="__main__")


def test_horizon_is_resolved_before_any_use():
    """Ninguna sentencia de modulo puede leer MESES_HORIZONTE antes de resolverlo."""
    tree = ast.parse((ROOT / "black_litterman.py").read_text(encoding="utf-8"))

    def nombres(nodo, ctx):
        return {n.id for n in ast.walk(nodo) if isinstance(n, ast.Name) and isinstance(n.ctx, ctx)}

    resuelto = False
    for nodo in tree.body:
        if isinstance(nodo, (ast.FunctionDef, ast.ClassDef)):
            continue
        if not resuelto:
            assert "MESES_HORIZONTE" not in nombres(nodo, ast.Load), (
                f"linea {nodo.lineno} usa MESES_HORIZONTE antes de resolverlo")
        if "MESES_HORIZONTE" in nombres(nodo, ast.Store):
            resuelto = True
    assert resuelto


def _correr_previews(monkeypatch, tmp_path, capsys, entrada=None, argv=None):
    _entorno(monkeypatch, tmp_path, entrada)
    salida = tmp_path / "previews"
    monkeypatch.setenv("BL_PREVIEWS_OUT", str(salida))
    if argv is None:
        monkeypatch.setenv("BL_MODE", "previews")
    else:
        monkeypatch.setattr(sys, "argv", ["black_litterman.py", *argv])
    capsys.readouterr()
    with pytest.raises(SystemExit) as salida_exit:
        runpy.run_path(str(ROOT / "black_litterman.py"), run_name="__main__")
    assert salida_exit.value.code == 0
    texto = capsys.readouterr().out
    archivos = list(salida.glob("previews_*.json"))
    assert len(archivos) == 1
    return json.loads(archivos[0].read_text(encoding="utf-8")), texto


def _verificar_previews(p, meses):
    assert p["kind"] == "bl_previews" and p["schema_version"] == 1
    assert p["horizon_months"] == meses
    assert p["horizon_trading_days"] == meses * 21
    esperado, fin = pipeline_io.horizon_from_months(date.fromisoformat(p["as_of"]), meses)
    assert p["horizon_days"] == esperado and p["horizon_end"] == fin
    assert p["as_of"] == date.today().isoformat()
    assert p["risk_profile"] == "agresivo"
    assert p["tau"] == 0.10
    assert math.isfinite(p["delta_mkt"])
    assert p["universe"] == UNIVERSO
    assert list(p["tickers"]) == UNIVERSO
    assert f"{meses} month(s)" in p["units"]["returns"]
    for fila in p["tickers"].values():
        assert fila["diff"] == pytest.approx(fila["mu_historico"] - fila["pi_eq"])
        assert fila["vol_horizon"] > 0
        assert fila["iv_horizon"] is None and fila["iv_source"] is None
    assert sum(f["w_mkt"] for f in p["tickers"].values()) == pytest.approx(1.0)


def test_previews_mode_via_env_stops_before_views_and_portfolio(monkeypatch, tmp_path, capsys):
    p, texto = _correr_previews(monkeypatch, tmp_path, capsys)
    _verificar_previews(p, 2)
    assert "REFERENCIA PARA FORMULAR VIEWS" in texto
    assert "MODO PREVIEWS" in texto
    assert "BLOQUE 6B" not in texto and "BLOQUE 7:" not in texto
    assert not (tmp_path / "portfolio").exists()


def test_previews_mode_via_cli_flag_with_horizon(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("BL_HORIZON_MONTHS", "6")
    p, _ = _correr_previews(monkeypatch, tmp_path, capsys, argv=["--previews"])
    _verificar_previews(p, 6)
    assert not (tmp_path / "portfolio").exists()


def test_previews_returns_are_expressed_at_configured_horizon(monkeypatch, tmp_path, capsys):
    p3, _ = _correr_previews(monkeypatch, tmp_path, capsys, {"horizon_months": 3})
    (tmp_path / "b").mkdir()
    p6, _ = _correr_previews(monkeypatch, tmp_path / "b", capsys, {"horizon_months": 6})
    for tk in UNIVERSO:
        # Mismas semanas de historia: mu escala con round(52 * m / 12) = 13 y 26.
        assert p6["tickers"][tk]["mu_historico"] == pytest.approx(
            2.0 * p3["tickers"][tk]["mu_historico"], rel=1e-9, abs=1e-12)
    assert p3["horizon_months"] == 3 and p6["horizon_months"] == 6


def test_full_mode_unchanged_when_bl_mode_full(monkeypatch, tmp_path):
    monkeypatch.setenv("BL_MODE", "full")
    g, latest = _correr(monkeypatch, tmp_path)
    assert g["MODO_EJECUCION"] == "full"
    assert latest["optimizer"] == "black_litterman"
