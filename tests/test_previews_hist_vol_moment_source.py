"""Previews: `vol_hist_horizon` y `moment_source` por ticker. Sin red.

`vol_horizon` (sqrt(diag(Sigma_P)), implicita/ajustada a P) no cambia; junto a ella
va `vol_hist_horizon` (sqrt(diag(Sigma_hist)), historica pura al horizonte).
`moment_source` dice si MFIS/MFIK salieron de la sonrisa implicita propia ("iv") o
no ("hist") y por que.
"""

import json
import math
import re
from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

import bl_metrics as bm
import pipeline_io
from test_bl_horizonte_previews import UNIVERSO, _correr_previews
from test_bl_metrics import _cadena_ssvi

HOY = pd.Timestamp("2026-10-02")
SSVI_OK = {"usar_alas": True, "aceptado": True, "rmse_rel": 0.031, "gj_max": 1.2,
           "motivos": [], "motivo_fallback": ""}
BKM_IV = {"fuente_momentos": "ssvi", "motivo_fallback": "", "MFIS": -0.4, "MFIK": 4.1}


def _fuente(**kw):
    info = bm.moment_source_info(**kw)
    assert set(info) == {"source", "reason"}
    assert info["source"] in ("iv", "hist")
    assert isinstance(info["reason"], str) and info["reason"]
    return info


# ----------------------------------------------------------------------------
# moment_source: "iv" solo con momentos implicitos realmente usados
# ----------------------------------------------------------------------------

def test_iv_only_when_implied_moments_were_used():
    info = _fuente(surface=SSVI_OK, bkm=BKM_IV)
    assert info["source"] == "iv"
    assert info["reason"].startswith("implied_moments")
    assert "0.031" in info["reason"] and "0.20" in info["reason"]


def test_iv_requires_bkm_to_finish_on_the_smile():
    fallback = {"fuente_momentos": "fallback", "motivo_fallback": ""}
    assert _fuente(surface=SSVI_OK, bkm=fallback)["source"] == "hist"
    assert _fuente(surface=SSVI_OK, bkm=None)["source"] == "hist"


def test_iv_disabled_is_hist():
    info = _fuente(iv_enabled=False, bkm={"fuente_momentos": "fallback"})
    assert info["source"] == "hist"
    assert info["reason"].startswith("iv_disabled") and "USAR_IV_POLYGON" in info["reason"]


def test_ticker_without_us_options_is_hist():
    info = _fuente(is_us=False, bkm={"fuente_momentos": "fallback", "motivo_fallback": "sin_opciones_us"})
    assert info["source"] == "hist"
    assert info["reason"].startswith("no_options_data") and "sin_opciones_us" in info["reason"]


def test_no_options_data_when_chain_is_empty():
    err = bm.SSVICalibrationError("Cadena vacia", "chain_empty")
    info = _fuente(calib_error=err, bkm={"fuente_momentos": "fallback"})
    assert info["source"] == "hist" and info["reason"].startswith("no_options_data")


def test_chain_incomplete_is_reported_as_unavailable():
    err = bm.SSVICalibrationError("cadena incompleta (status 429)", "chain_incomplete")
    info = _fuente(calib_error=err, bkm={"fuente_momentos": "fallback"})
    assert info["reason"].startswith("options_chain_unavailable") and "429" in info["reason"]


def test_unknown_calibration_error_keeps_original_message():
    info = _fuente(calib_error=RuntimeError("boom"), bkm={"fuente_momentos": "fallback"})
    assert info["source"] == "hist" and info["reason"] == "calibration_error: boom"


def test_no_atm_vol_error_reports_fit_error_vs_threshold():
    err = bm.SSVICalibrationError("SSVI sin vol ATM", "no_atm_vol", rmse_rel=0.8123, gj_max=2.0)
    info = _fuente(calib_error=err, bkm={"fuente_momentos": "fallback"})
    assert info["reason"].startswith("ssvi_fit_rejected")
    assert "rmse_rel=0.812 > 0.20" in info["reason"]


def test_rejected_fit_reports_error_vs_threshold_and_keeps_atm():
    surf = {"usar_alas": False, "aceptado": False, "rmse_rel": 0.35, "gj_max": 1.0,
            "motivos": ["rmse_rel=0.350>0.20"], "motivo_fallback": "rmse_rel=0.350>0.20"}
    info = _fuente(surface=surf, bkm={"fuente_momentos": "fallback", "motivo_fallback": "rmse_rel=0.350>0.20"})
    assert info["source"] == "hist"
    assert info["reason"].startswith("ssvi_fit_rejected: rmse_rel=0.350 > 0.20 threshold")
    assert "wings not used" in info["reason"]


def test_rejected_fit_by_arbitrage_bound_only():
    surf = {"usar_alas": False, "aceptado": False, "rmse_rel": 0.05, "gj_max": 5.5,
            "motivos": [], "motivo_fallback": "sonrisa rechazada"}
    info = _fuente(surface=surf, bkm={"fuente_momentos": "fallback"})
    assert info["reason"].startswith("ssvi_fit_rejected")
    assert "gj_max=5.500 > 4.0" in info["reason"] and "rmse_rel" not in info["reason"]


def test_degenerate_smile_is_not_called_a_fit_error():
    surf = {"usar_alas": False, "aceptado": True, "rmse_rel": 0.04, "gj_max": 1.0,
            "motivos": ["rho_en_cota", "sin_ala_put"], "motivo_fallback": "rho_en_cota, sin_ala_put"}
    info = _fuente(surface=surf, bkm={"fuente_momentos": "fallback"})
    assert info["reason"].startswith("ssvi_degenerate: rho_en_cota, sin_ala_put")


@pytest.mark.parametrize("motivo,prefijo", [
    ("mfiv_fuera_de_banda", "mfiv_out_of_band"),
    ("momentos_inadmisibles", "moments_inadmissible"),
    ("sin spot", "bkm_error: sin spot"),
])
def test_bkm_stage_failures(motivo, prefijo):
    bkm = {"fuente_momentos": "fallback", "motivo_fallback": motivo}
    info = _fuente(surface=SSVI_OK, bkm=bkm)
    assert info["source"] == "hist" and info["reason"].startswith(prefijo)


def test_applied_fallback_is_appended_to_reason():
    info = _fuente(iv_enabled=False, applied_fallback="neutro")
    assert info["source"] == "hist"
    assert info["reason"].endswith("| fallback applied: neutro")


# ----------------------------------------------------------------------------
# Causas reales: calibrar_superficie_ssvi sobre cadenas sinteticas
# ----------------------------------------------------------------------------

def _calibrar(cadena, **kw):
    return bm.calibrar_superficie_ssvi(
        cadena, tau_obj=2 / 12, hoy=HOY, precio_min=0.10, oi_min=10, **kw)


def _fuente_de_cadena(cadena, **kw):
    """Corre la calibracion real y clasifica el resultado igual que black_litterman.py."""
    try:
        surf, err = _calibrar(cadena, **kw), None
    except ValueError as e:
        surf, err = None, e
    bkm = ({"fuente_momentos": "ssvi", "motivo_fallback": ""}
           if surf is not None and surf["usar_alas"]
           else {"fuente_momentos": "fallback",
                 "motivo_fallback": (surf or {}).get("motivo_fallback") or str(err)})
    return bm.moment_source_info(calib_error=err, surface=surf, bkm=bkm), surf, err


def test_real_chain_accepted_smile_is_iv():
    cadena = _cadena_ssvi(HOY, -0.35, 0.50, 0.40, 0.32, (40, 90, 170))
    info, surf, _ = _fuente_de_cadena(cadena)
    assert surf["usar_alas"] and info["source"] == "iv"


def test_real_chain_with_one_expiry_has_fewer_than_2_usable_expiries():
    cadena = _cadena_ssvi(HOY, -0.35, 0.50, 0.40, 0.32, (60,))
    info, _, err = _fuente_de_cadena(cadena)
    assert isinstance(err, bm.SSVICalibrationError) and err.code == "fewer_than_2_expiries"
    assert info["source"] == "hist"
    assert info["reason"].startswith("fewer_than_2_usable_expiries")


def test_real_chain_with_expiries_below_minimum_dte():
    cadena = _cadena_ssvi(HOY, -0.35, 0.50, 0.40, 0.32, (2, 3))
    info, _, err = _fuente_de_cadena(cadena)
    assert err.code == "no_expiries_in_window"
    assert info["source"] == "hist"
    assert info["reason"].startswith("fewer_than_2_usable_expiries: 0 usable expiries")


def test_real_chain_without_valid_ivs_is_no_options_data():
    cadena = _cadena_ssvi(HOY, -0.35, 0.50, 0.40, 0.32, (40, 90, 170))
    cadena["iv"] = np.nan
    info, _, err = _fuente_de_cadena(cadena)
    assert err.code == "no_valid_ivs"
    assert info["source"] == "hist" and info["reason"].startswith("no_options_data")


def test_real_chain_with_noisy_smile_is_rejected_with_fit_error():
    cadena = _cadena_ssvi(HOY, -0.35, 0.50, 0.40, 0.32, (40, 90, 170))
    cadena["iv"] = cadena["iv"] * np.where(np.arange(len(cadena)) % 2 == 0, 0.4, 2.5)
    info, surf, _ = _fuente_de_cadena(cadena)
    assert not surf["aceptado"] and surf["rmse_rel"] > bm.SSVI_RMSE_REL_MAX
    assert info["source"] == "hist"
    esperado = f"rmse_rel={surf['rmse_rel']:.3f} > 0.20 threshold"
    assert esperado in info["reason"]


def test_threshold_in_reason_follows_the_configured_limit():
    cadena = _cadena_ssvi(HOY, -0.35, 0.50, 0.40, 0.32, (40, 90, 170))
    surf = _calibrar(cadena, rmse_rel_max=1e-12)
    assert not surf["aceptado"]
    info = bm.moment_source_info(
        surface=surf, bkm={"fuente_momentos": "fallback"}, rmse_rel_max=1e-12)
    assert re.search(r"rmse_rel=0\.\d{3} > 0\.00 threshold", info["reason"])


def test_calibration_errors_are_still_value_errors_with_original_messages():
    cadena = _cadena_ssvi(HOY, -0.35, 0.50, 0.40, 0.32, (60,))
    with pytest.raises(ValueError, match="Menos de 2 vencimientos utilizables"):
        _calibrar(cadena)
    assert bm.SSVI_RMSE_REL_MAX == 0.20


# ----------------------------------------------------------------------------
# JSON de previews
# ----------------------------------------------------------------------------

def _payload(**extra):
    base = dict(
        as_of=date(2026, 1, 31), horizon_months=3, horizon_trading_days=63,
        risk_profile="agresivo", tau=0.10, delta_mkt=2.5, delta_mode="historical",
        tickers=["AAPL", "MSFT"], pi_eq=[0.02, 0.03], mu_historico=[0.05, 0.04],
        vol_horizon=[0.11, 0.09], w_mkt=[0.6, 0.4],
        now=datetime(2026, 1, 31, 12, 0, 0, tzinfo=pipeline_io.BOGOTA),
    )
    base.update(extra)
    return pipeline_io.build_previews_payload(**base)


def test_payload_carries_both_vols_and_moment_source():
    fuente = {
        "AAPL": {"source": "iv", "reason": "implied_moments: BKM on accepted SSVI smile"},
        "MSFT": {"source": "hist", "reason": "ssvi_fit_rejected: rmse_rel=0.350 > 0.20 threshold"},
    }
    p = _payload(vol_hist_horizon=[0.13, float("nan")], moment_source=fuente)
    aapl, msft = p["tickers"]["AAPL"], p["tickers"]["MSFT"]
    assert aapl["vol_horizon"] == 0.11 and aapl["vol_hist_horizon"] == 0.13
    assert msft["vol_horizon"] == 0.09 and msft["vol_hist_horizon"] is None
    assert aapl["moment_source"] == fuente["AAPL"]
    assert msft["moment_source"] == fuente["MSFT"]
    assert "sqrt(diag(Sigma_hist))" in p["units"]["vol_hist_horizon"]
    assert "sqrt(diag(Sigma_P))" in p["units"]["vol_horizon"]
    assert "moment_source" in p["units"]
    json.dumps(p, allow_nan=False)


def test_payload_new_fields_default_to_null():
    p = _payload()
    for fila in p["tickers"].values():
        assert fila["vol_hist_horizon"] is None and fila["moment_source"] is None


def test_payload_rejects_misaligned_vol_hist_and_bad_source():
    with pytest.raises(ValueError, match="vol_hist_horizon tiene 1 valores y hay 2 tickers"):
        _payload(vol_hist_horizon=[0.1])
    with pytest.raises(ValueError, match="moment_source.source invalido"):
        _payload(moment_source={"AAPL": {"source": "sector", "reason": "x"}})


# ----------------------------------------------------------------------------
# black_litterman.py de punta a punta (smoke, sin red)
# ----------------------------------------------------------------------------

def test_script_previews_emit_vol_hist_and_moment_source(monkeypatch, tmp_path, capsys):
    p, _ = _correr_previews(monkeypatch, tmp_path, capsys)
    for tk in UNIVERSO:
        fila = p["tickers"][tk]
        assert fila["vol_hist_horizon"] > 0 and math.isfinite(fila["vol_hist_horizon"])
        assert fila["vol_horizon"] > 0
        ms = fila["moment_source"]
        assert set(ms) == {"source", "reason"}
        assert ms["source"] == "hist"
        assert ms["reason"].startswith("iv_disabled")
        assert ms["reason"].endswith("fallback applied: historico")


def test_script_vol_hist_scales_with_the_configured_horizon(monkeypatch, tmp_path, capsys):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    p3, _ = _correr_previews(monkeypatch, tmp_path / "a", capsys, {"horizon_months": 3})
    p6, _ = _correr_previews(monkeypatch, tmp_path / "b", capsys, {"horizon_months": 6})
    for tk in UNIVERSO:
        ratio = p6["tickers"][tk]["vol_hist_horizon"] / p3["tickers"][tk]["vol_hist_horizon"]
        assert ratio == pytest.approx(math.sqrt(26 / 13), rel=1e-6)
