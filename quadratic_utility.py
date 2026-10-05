# ==============================================================================
# Script: Optimizacion de portafolio - Utilidad Cuadratica
# ==============================================================================

import warnings
warnings.filterwarnings("ignore")

import time
import math
import re
import itertools
import io
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

import yfinance as yf
import pandas_datareader.data as pdr
import statsmodels.api as sm
from scipy.stats import norm
import quadprog

import plotly.express as px
import plotly.graph_objects as go

import risk_estimators as rk
import polygon_client as pc
import market_data as md
import qu_metrics as qm
import pipeline_io

# ==============================================================================
# PARAMETROS CONFIGURABLES
# ==============================================================================

# ------------------------------------------------------------------------------
# API KEY - Polygon.io
# ------------------------------------------------------------------------------
import os
from dotenv import load_dotenv
load_dotenv()
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY")

if not POLYGON_API_KEY:
    print("ADVERTENCIA: No hay POLYGON_API_KEY configurada. Todas las consultas de opciones")
    print("             fallaran y cada activo caera a fallback historico (sin BKM real).")

polygon_dte_tol = 21
polygon_dte_min = 21
atm_strike_band = 0.10

# ------------------------------------------------------------------------------
# UNIVERSO DE ACTIVOS
# ------------------------------------------------------------------------------

n_top_nasdaq = 90
n_top_sp500 = 90
n_top_int = 50

# ------------------------------------------------------------------------------
# FECHA DE REFERENCIA Y HORIZONTE
# ------------------------------------------------------------------------------
as_of_date = date.today()
horizon_months = 2

# ------------------------------------------------------------------------------
# PARAMETROS GENERALES
# ------------------------------------------------------------------------------
history_start_year = 2014
target_years, history_start, history_end = qm.history_window(as_of_date, history_start_year)
mdd_start_year = history_start_year
rf_rate = 0.047
seed = 123
max_weight = 0.30
n_sim = 5000

# ------------------------------------------------------------------------------
# VENTANA DE ENTRENAMIENTO
# ------------------------------------------------------------------------------
lookback_months = None

# ------------------------------------------------------------------------------
# AVERSION AL RIESGO Y PONDERADORES DE SELECCION
# ------------------------------------------------------------------------------
lambda_ = 1.5
lambda_annual = None
# El puntaje de seleccion no premia la vol baja: esa preferencia vive solo en
# lambda. Sharpe mide eficiencia (retorno por unidad de riesgo), no nivel de vol.
weight_sharpe = 0.70
weight_decorr = 0.30

# ------------------------------------------------------------------------------
# RETORNO ESPERADO: MEDIA HISTORICA ENCOGIDA HACIA FAMA-FRENCH
# ------------------------------------------------------------------------------
# mu_i = w_i * media_historica_i + (1 - w_i) * retorno_FF3_i, w_i = n_i / (n_i + k).
# k = meses de historia que pesan igual que el modelo (140 -> 50/50 con ~12 anios;
# 36 meses -> ~20% historica). El mismo mu se usa en la seleccion y en el QP.
# 0 desactiva el encogimiento (solo media historica).
mu_shrink_k = 140

# ------------------------------------------------------------------------------
# TAMANO DE LOS FILTROS DE CANDIDATOS
# ------------------------------------------------------------------------------
n_pre_filter = 45
n_filter_candidates = 30

# ------------------------------------------------------------------------------
# SELECCION CONJUNTA QUBO/ISING
# ------------------------------------------------------------------------------
qubo_exact_threshold = 2e6
qubo_sa_iterations = 20000

# ------------------------------------------------------------------------------
# PERCENTILES DE VOLATILIDAD Y CORRELACION
# ------------------------------------------------------------------------------
volatility_percentile = 0.85
correlation_percentile = 0.85

# ------------------------------------------------------------------------------
# FILTRO DE VOLATILIDAD RECIENTE
# ------------------------------------------------------------------------------
recent_vol_window_min_weeks = 13
recent_vol_window_max_weeks = 18
recent_vol_ratio_max = 1.80
recent_vol_min_survivors = 14

# ------------------------------------------------------------------------------
# TENOR MAXIMO DE OPCIONES
# ------------------------------------------------------------------------------
options_dte_cap_days = 90

# ------------------------------------------------------------------------------
# FILTRO DE IV vs VOLATILIDAD RECIENTE
# ------------------------------------------------------------------------------
iv_vs_realized_ratio_max = 1.80
iv_min_survivors = 10

# ------------------------------------------------------------------------------
# PARAMETROS BKM
# ------------------------------------------------------------------------------
bkm_moneyness_lo = 0.70
bkm_moneyness_hi = 1.40
bkm_hist_contracts_estimate = 26
bkm_min_options_per_side = 3
bkm_mfik_max = 20.0
bkm_mfik_max_hard = 80.0
bkm_lookback_months = 12
bkm_hist_sample_freq = "2W"
bkm_hist_anchor = "2020-01-05"
bkm_hist_min_valid = 8
bkm_hist_max_minutes = 60
bkm_max_workers = 12
bkm_z_threshold = 2.00
bkm_tail_mode = "upper"
bkm_min_survivors = 12
cornish_fisher_confidence = 0.95

# ------------------------------------------------------------------------------
# COVARIANZA HISTORICA: DIARIA + EWMA + SHRINKAGE LEDOIT-WOLF
# ------------------------------------------------------------------------------
use_daily_cov = True
cov_halflife_days = 120
use_lw_shrinkage = True

# ------------------------------------------------------------------------------
# CORRECCION Q -> P (PRIMAS DE RIESGO)
# ------------------------------------------------------------------------------
use_q_to_p_vol = True
vrp_ratio_bounds = (0.70, 1.00)
vrp_fallback_ratio = 0.90
use_q_to_p_correlation = True
dispersion_min_cap_share = 0.40
dispersion_min_known_caps = 50
crp_ratio_bounds = (0.60, 1.00)
crp_fallback_ratio = 0.85

# ------------------------------------------------------------------------------
# PANEL DE ESCENARIOS PARA MOMENTOS DEL PORTAFOLIO
# ------------------------------------------------------------------------------
panel_min_obs = 24

# ------------------------------------------------------------------------------
# RETORNO ESPERADO VIA SVIX (MARTIN-WAGNER) - EXPERIMENTAL
# ------------------------------------------------------------------------------
use_svix_expected_return = False
svix_blend = 0.50

# ------------------------------------------------------------------------------
# ORDEN DE CORRELACION
# ------------------------------------------------------------------------------
correlation_order = 0

# ------------------------------------------------------------------------------
# OBSERVACIONES MINIMAS E IDEALES
# ------------------------------------------------------------------------------
min_observations = 24
ideal_observations = 60

# ------------------------------------------------------------------------------
# FILTRO DELTA
# ------------------------------------------------------------------------------
use_delta_filter = True
# Conservador 0.24, moderado 0.18, agresivo 0.15.
delta_min = 0.15
sector_implied_min_names = 4
delta_strike_mode = "otm"
delta_otm_log_m = 0.08
delta_otm_ref_months = 2
iv_outlier_multiplier = 6.0

# ------------------------------------------------------------------------------
# LIMITE DE PESO POR REGION
# ------------------------------------------------------------------------------
max_region_weight = 0.80

# ------------------------------------------------------------------------------
# PARTICIPACION DE ETFs EN EL PORTAFOLIO FINAL
# ------------------------------------------------------------------------------
pct_etf_deseado = 0.10
pct_etf_tolerancia = 0.1
etf_floor_reserve_factor = 3
etf_band_relax_if_infeasible = True

# ------------------------------------------------------------------------------
# ETFs EN EL PORTAFOLIO RESULTANTE
# ------------------------------------------------------------------------------
include_etfs_in_portfolio = True

# ==============================================================================
# VALIDACION DE PARAMETROS
# ==============================================================================
if not (1 <= horizon_months <= 24):
    raise ValueError("Error: horizon_months debe estar entre 1 y 24")
if not (0 <= pct_etf_deseado <= 1):
    raise ValueError("Error: pct_etf_deseado debe estar entre 0 y 1 (ej. 0.30 = 30%)")
if not (math.isfinite(mu_shrink_k) and mu_shrink_k >= 0):
    raise ValueError("Error: mu_shrink_k debe ser finito y >= 0")
if not (0 <= pct_etf_tolerancia <= 0.5):
    raise ValueError("Error: pct_etf_tolerancia debe estar entre 0 y 0.5")
if not (isinstance(etf_floor_reserve_factor, int) and etf_floor_reserve_factor >= 1):
    raise ValueError("Error: etf_floor_reserve_factor debe ser un entero >= 1")
if delta_strike_mode not in ("atm", "mu", "rf", "otm"):
    raise ValueError("Error: delta_strike_mode debe ser atm, mu, rf u otm")
if not (math.isfinite(delta_min) and delta_min >= 0):
    raise ValueError("Error: delta_min debe ser finito y >= 0")
if delta_strike_mode == "otm" and not (math.isfinite(delta_otm_log_m) and delta_otm_log_m > 0):
    raise ValueError("Error: delta_otm_log_m debe ser finito y > 0")
if delta_strike_mode == "otm" and not (delta_otm_ref_months > 0):
    raise ValueError("Error: delta_otm_ref_months debe ser > 0")

horizon_desc = f"{horizon_months} mes(es) desde {as_of_date.isoformat()}"

print("\n" + "=" * 60)
print(f"FECHA DE REFERENCIA (as_of_date): {as_of_date.isoformat()} | HORIZONTE DE INVERSION: {horizon_months} mes(es)")
lb_txt = f" (ultimos {lookback_months} meses)" if lookback_months is not None else " (sin restriccion de ventana)"
print("ENTRENAMIENTO: todo el historico mensual disponible" + lb_txt)
print("=" * 60 + "\n")

rf_rate_monthly = rf_rate / 12
returns_per_year = 12
periodo_label = "mensual"
if lambda_annual is not None:
    lambda_ = qm.lambda_monthly_from_annual(lambda_annual, periods_per_year=returns_per_year)
    print(f"lambda_annual={lambda_annual:g} -> lambda mensual={lambda_:g} "
          f"(x{returns_per_year}; ver M-8 en qu_metrics)")


# ==============================================================================
# FUNCION AUXILIAR: Web scraping seguro
# ==============================================================================
def safe_scrape_table(url, fallback=None, headers=None):
    try:
        headers = headers or {"User-Agent": "Mozilla/5.0 (compatible; PortfolioBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        tables = pd.read_html(io.StringIO(resp.text))
        if not tables:
            return fallback
        return tables[0]
    except Exception as e:
        print(f"Error al obtener datos de {url}: {e}")
        return fallback


def _parse_market_cap(x):
    m = re.match(r"^\$?\s*([0-9]*\.?[0-9]+)\s*([TBMK]?)$", str(x).strip().upper())
    if not m:
        return np.nan
    val, suf = m.groups()
    return float(val) * {"T": 1e12, "B": 1e9, "M": 1e6, "K": 1e3, "": 1.0}[suf]


def clean_symbol_table(tbl):
    tbl = tbl.copy()
    tbl.columns = [str(c).strip().lower().replace(" ", "_") for c in tbl.columns]
    symbol_col = "symbol" if "symbol" in tbl.columns else tbl.columns[1]
    tbl = tbl.rename(columns={symbol_col: "symbol"})
    tbl = tbl[
        tbl["symbol"].notna()
        & ~tbl["symbol"].astype(str).str.contains(r"\^|\$", regex=True)
        & (tbl["symbol"].astype(str).str.len() >= 1)
        & (tbl["symbol"].astype(str).str.len() <= 5)
        & ~tbl["symbol"].astype(str).str.match(r"^[0-9]")
    ].copy()
    tbl["symbol"] = tbl["symbol"].astype(str).str.upper().str.replace(".", "-", regex=False)
    if "market_cap" in tbl.columns:
        cap_num = tbl["market_cap"].apply(_parse_market_cap)
        if cap_num.notna().any():
            tbl = tbl.assign(_cap_num=cap_num).sort_values(
                "_cap_num", ascending=False, kind="stable"
            ).drop(columns="_cap_num")
    return tbl.reset_index(drop=True)


# ==============================================================================
# FUNCIONES AUXILIARES: Polygon.io
# ==============================================================================
def is_us_ticker(ticker):
    return pc.is_us_ticker(ticker)


def polygon_format_ticker(ticker):
    return pc.polygon_format_ticker(ticker)


def polygon_get_atm_option(ticker, target_dte, dte_tol=21, api_key=None, contract_type="call"):
    api_key = api_key or POLYGON_API_KEY
    vacio = dict(iv=np.nan, delta=np.nan, gamma=np.nan, vega=np.nan, theta=np.nan,
                 dte=np.nan, strike=np.nan, ok=False)
    if not is_us_ticker(ticker):
        return vacio

    hoy = date.today()
    fecha_min = (hoy + timedelta(days=max(target_dte - dte_tol, 1))).strftime("%Y-%m-%d")
    fecha_max = (hoy + timedelta(days=target_dte + dte_tol)).strftime("%Y-%m-%d")

    S = get_spot_safe_bkm(ticker)
    filtro_strike = ""
    if np.isfinite(S) and S > 0:
        filtro_strike = (f"strike_price.gte={S * (1 - atm_strike_band):.4f}&"
                         f"strike_price.lte={S * (1 + atm_strike_band):.4f}&")

    url_chain = (
        f"https://api.polygon.io/v3/snapshot/options/{polygon_format_ticker(ticker)}?"
        f"contract_type={contract_type}&{filtro_strike}"
        f"expiration_date.gte={fecha_min}&expiration_date.lte={fecha_max}&"
        f"limit=250"
    )

    try:
        results, completo, _ = pc.get_all(url_chain, api_key=api_key)
        if not completo or not results:
            return vacio
        df = pd.json_normalize(results)
        if df.empty:
            return vacio

        df["dte"] = (pd.to_datetime(df["details.expiration_date"]) - pd.Timestamp(hoy)).dt.days
        df = df[df.get("implied_volatility").notna() & (df.get("implied_volatility") > 0) &
                 df.get("greeks.delta").notna()].copy()
        if df.empty:
            return vacio

        rango = pc.expiry_rank_columns(df["dte"], target_dte, np.ones(len(df)), polygon_dte_min)
        df = df.assign(**rango)
        df["_delta"] = (df["greeks.delta"] - 0.50).abs()
        df = df.sort_values(pc.EXPIRY_SORT_COLS + ["_delta"])
        c1 = df.iloc[0]

        return dict(
            iv=c1.get("implied_volatility", np.nan),
            delta=c1.get("greeks.delta", np.nan),
            gamma=c1.get("greeks.gamma", np.nan),
            vega=c1.get("greeks.vega", np.nan),
            theta=c1.get("greeks.theta", np.nan),
            dte=c1.get("dte", np.nan),
            strike=c1.get("details.strike_price", np.nan),
            ok=True,
        )
    except Exception:
        return vacio


# ==============================================================================
# FUNCIONES AUXILIARES: Black-Scholes y contratos historicos (Polygon)
# ==============================================================================
def bs_price(S, K, T_yrs, r, sigma, tipo="call"):
    if T_yrs <= 0 or sigma <= 0:
        return np.nan
    d1 = (math.log(S / K) + (r + sigma ** 2 / 2) * T_yrs) / (sigma * math.sqrt(T_yrs))
    d2 = d1 - sigma * math.sqrt(T_yrs)
    if tipo == "call":
        return S * norm.cdf(d1) - K * math.exp(-r * T_yrs) * norm.cdf(d2)
    else:
        return K * math.exp(-r * T_yrs) * norm.cdf(-d2) - S * norm.cdf(-d1)


def polygon_contracts_asof(ticker, strike_lo, strike_hi, exp_min, exp_max, as_of, api_key=None):
    """Calls y puts vigentes en `as_of` dentro de la ventana de strike y vencimiento.

    Una sola consulta paginada por fecha en lugar de una por punto de la rejilla.
    Devuelve (df, definitivo); definitivo es False si fallo por limite o red.
    """
    url_ref = (
        f"https://api.polygon.io/v3/reference/options/contracts?"
        f"underlying_ticker={polygon_format_ticker(ticker)}&"
        f"strike_price.gte={strike_lo:.4f}&strike_price.lte={strike_hi:.4f}&"
        f"expiration_date.gte={exp_min}&expiration_date.lte={exp_max}&"
        f"as_of={as_of}&limit=1000"
    )
    results, completo, status = pc.get_all(url_ref, api_key=api_key or POLYGON_API_KEY, permanente=True)
    if not completo:
        return pd.DataFrame(), not pc.es_transitorio(status)
    if not results:
        return pd.DataFrame(), True
    return pd.json_normalize(results), True


def polygon_contract_close_near(contract_ticker, target_date, window_days=5, api_key=None):
    """Cierre diario del contrato mas cercano a target_date. Devuelve (precio, definitivo)."""
    if not str(contract_ticker).startswith("O:"):
        return np.nan, True
    target_d = pd.Timestamp(target_date)
    from_d = (target_d - timedelta(days=window_days)).strftime("%Y-%m-%d")
    to_d = (target_d + timedelta(days=window_days)).strftime("%Y-%m-%d")
    barras, definitivo = pc.fetch_option_aggs(
        contract_ticker, from_d, to_d, api_key=api_key or POLYGON_API_KEY)
    if not barras:
        return np.nan, definitivo
    return qm.close_near_from_bars(barras, target_d, window_days), definitivo


def get_spot_safe_bkm(ticker):
    try:
        fi = yf.Ticker(ticker).fast_info
        px = fi.get("lastPrice") if hasattr(fi, "get") else None
        if px is None:
            px = getattr(fi, "last_price", None)
        if px is None:
            info = yf.Ticker(ticker).info
            px = info.get("regularMarketPrice") or info.get("currentPrice")
        return float(px) if px is not None else np.nan
    except Exception:
        return np.nan


# ==============================================================================
# FUNCIONES BKM (Bakshi, Kapadia y Madan, 2003)
# ==============================================================================
def bkm_iv_chain_to_prices(S, r, T, chain_df):
    if chain_df is None or chain_df.empty:
        return chain_df
    chain_df = chain_df.copy()
    chain_df["price"] = [
        bs_price(S, k, T, r, iv, tipo)
        for k, iv, tipo in zip(chain_df["strike"], chain_df["iv"], chain_df["type"])
    ]
    chain_df = chain_df[chain_df["price"].notna() & (chain_df["price"] > 0)]
    return chain_df


def bkm_compute_moments(S, r, T, calls_df, puts_df):
    vacio = dict(mfiv=np.nan, mfis=np.nan, mfik=np.nan, mu=np.nan, ok=False, motivo="pocas_opciones_otm")
    if calls_df is None or puts_df is None or len(calls_df) < bkm_min_options_per_side \
            or len(puts_df) < bkm_min_options_per_side or T <= 0 or S <= 0:
        return vacio

    calls_df = calls_df.sort_values("strike")
    puts_df = puts_df.sort_values("strike")
    Kc, Cc = calls_df["strike"].values.astype(float), calls_df["price"].values.astype(float)
    Kp, Pp = puts_df["strike"].values.astype(float), puts_df["price"].values.astype(float)

    fC_V = (2 * (1 - np.log(Kc / S))) / Kc ** 2 * Cc
    fP_V = (2 * (1 + np.log(S / Kp))) / Kp ** 2 * Pp
    fC_W = (6 * np.log(Kc / S) - 3 * np.log(Kc / S) ** 2) / Kc ** 2 * Cc
    fP_W = (6 * np.log(S / Kp) + 3 * np.log(S / Kp) ** 2) / Kp ** 2 * Pp
    fC_X = (12 * np.log(Kc / S) ** 2 - 4 * np.log(Kc / S) ** 3) / Kc ** 2 * Cc
    fP_X = (12 * np.log(S / Kp) ** 2 + 4 * np.log(S / Kp) ** 3) / Kp ** 2 * Pp

    try:
        V = rk.trapezoid(fC_V, Kc) + rk.trapezoid(fP_V, Kp)
        W = rk.trapezoid(fC_W, Kc) - rk.trapezoid(fP_W, Kp)
        X = rk.trapezoid(fC_X, Kc) + rk.trapezoid(fP_X, Kp)
    except Exception as exc:
        vacio["motivo"] = f"integracion_fallida ({type(exc).__name__})"
        return vacio

    erT = math.exp(r * T)
    mu = erT - 1 - erT / 2 * V - erT / 6 * W - erT / 24 * X
    mfiv = erT * V - mu ** 2
    if not np.isfinite(mfiv) or mfiv <= 0:
        vacio["motivo"] = "mfiv_no_positiva"
        return vacio

    mfis = (erT * W - 3 * mu * erT * V + 2 * mu ** 3) / mfiv ** 1.5
    mfik = (erT * X - 4 * mu * erT * W + 6 * erT * mu ** 2 * V - 3 * mu ** 4) / mfiv ** 2

    motivo = None
    n_otm = len(calls_df) + len(puts_df)
    dte_chain = float(T) * rk.DAYS_PER_YEAR
    cap_mfik = rk.mfik_cap_tenor(
        n_otm, dte_chain, ref_dte=float(target_dte_polygon),
        base=bkm_mfik_max, hard=bkm_mfik_max_hard)
    if not rk.higher_moments_admissible(mfis, mfik, cap_mfik):
        motivo = (f"momentos_inadmisibles (MFIS={mfis:.2f}, MFIK={mfik:.2f}, "
                  f"tope={cap_mfik:.1f} a {dte_chain:.0f}d vs ref {target_dte_polygon}d "
                  f"con {n_otm} strikes OTM; MFIV se conserva)")
        mfis, mfik = np.nan, np.nan

    return dict(mfiv=mfiv, mfis=float(mfis), mfik=float(mfik), mu=mu, ok=True, motivo=motivo)


def bkm_fetch_otm_chain(ticker, target_dte, dte_tol, S, moneyness_lo, moneyness_hi, api_key=None):
    """Cadena OTM paginada de un unico vencimiento (el mas cercano a target_dte)."""
    hoy = date.today()
    fecha_min = (hoy + timedelta(days=max(target_dte - dte_tol, 1))).strftime("%Y-%m-%d")
    fecha_max = (hoy + timedelta(days=target_dte + dte_tol)).strftime("%Y-%m-%d")
    return pc.fetch_otm_chain(
        polygon_format_ticker(ticker), S, fecha_min, fecha_max, S * moneyness_lo, S * moneyness_hi,
        target_dte, api_key=api_key or POLYGON_API_KEY, strike_fmt="{:.4f}",
        min_dte=polygon_dte_min)

def bkm_get_current_moments(ticker, target_dte, dte_tol, rf):
    vacio = dict(mfiv=np.nan, mfis=np.nan, mfik=np.nan, mu=np.nan, ok=False,
                 spot=np.nan, dte=np.nan, motivo="sin_spot")
    if not is_us_ticker(ticker):
        vacio.update(motivo="sin_opciones_us", transitorio=False)
        return vacio
    S = get_spot_safe_bkm(ticker)
    if pd.isna(S) or S <= 0:
        return vacio
    calls_df, puts_df, info_cadena = bkm_fetch_otm_chain(ticker, target_dte, dte_tol, S,
                                                         bkm_moneyness_lo, bkm_moneyness_hi)
    if not info_cadena["completo"]:
        vacio.update(spot=S, motivo=f"cadena_incompleta ({info_cadena['status']})",
                     transitorio=pc.es_transitorio(info_cadena["status"]))
        return vacio
    dte = info_cadena.get("dte")
    if dte is None or not np.isfinite(dte) or dte <= 0:
        if calls_df is None or len(calls_df) == 0:
            vacio.update(spot=S, motivo="sin_cadena_en_ventana_dte", transitorio=False)
            return vacio
        dte = target_dte
    T = rk.to_years(dte=float(dte))
    calls_df = bkm_iv_chain_to_prices(S, rf, T, calls_df)
    puts_df = bkm_iv_chain_to_prices(S, rf, T, puts_df)
    mom = bkm_compute_moments(S, rf, T, calls_df, puts_df)
    mom["spot"] = S
    mom["dte"] = int(dte)
    mom["expiracion"] = info_cadena["expiracion"]
    mom["transitorio"] = False
    return mom


def bkm_clave_historia(ticker, fecha, target_dte, dte_tol, moneyness_lo, moneyness_hi,
                       min_dte=21):
    """Cache v3: vencimiento >= min_dte y >= objetivo, spot sin ajustar, DTE real."""
    return (f"mfis_hist_v3|{ticker}|{pd.Timestamp(fecha):%Y-%m-%d}|dte={target_dte}|tol={dte_tol}"
            f"|min={int(min_dte)}|m={float(moneyness_lo):.2f}-{float(moneyness_hi):.2f}|spot=unadj")


def bkm_seleccion_fecha(ticker, spot_series, fecha_i, target_dte, dte_tol, moneyness_lo, moneyness_hi,
                       min_dte=21):
    """Contratos OTM de una fecha, sin precios. Devuelve (seleccion, definitivo).

    seleccion trae S, dte y las listas calls/puts de {strike, ticker}. El spot
    es el cierre sin ajustar. Los precios se piden despues, un rango por contrato.
    """
    spot_row = spot_series[spot_series["date"] <= fecha_i].sort_values("date", ascending=False)
    if spot_row.empty:
        return None, True
    S_i = float(spot_row.iloc[0]["close"])
    exp_target = fecha_i + timedelta(days=int(target_dte))
    exp_min = (exp_target - timedelta(days=int(dte_tol))).strftime("%Y-%m-%d")
    exp_max = (exp_target + timedelta(days=int(dte_tol))).strftime("%Y-%m-%d")

    df_ct, definitivo = polygon_contracts_asof(
        ticker, S_i * moneyness_lo, S_i * moneyness_hi,
        exp_min, exp_max, fecha_i.strftime("%Y-%m-%d"))
    vacio = {"S": S_i, "dte": None, "calls": [], "puts": []}
    if df_ct.empty:
        return vacio, definitivo
    elegido = qm.select_historical_otm(
        df_ct, S_i, fecha_i, target_dte, dte_tol, moneyness_lo, moneyness_hi, min_dte=min_dte)
    return {
        "S": S_i,
        "dte": elegido["dte"],
        "calls": list(elegido["calls"]),
        "puts": list(elegido["puts"]),
    }, definitivo


def bkm_precios_en_rango(needed, window_days=5):
    """Un agregado por contrato para todas las fechas en `needed`.

    needed es (ticker_opcion, fecha). Devuelve (precios, ok_por_contrato)
    con precios[(contrato, YYYY-MM-DD)] = cierre ±window_days.
    """
    rangos = qm.contract_agg_ranges(needed, window_days=window_days)
    barras = {}
    ok = {}
    for contrato, (desde, hasta) in rangos.items():
        series, definitivo = pc.fetch_option_aggs(contrato, desde, hasta, api_key=POLYGON_API_KEY)
        barras[contrato] = series
        ok[contrato] = definitivo
    precios = {}
    for contrato, fecha in needed:
        iso = pd.Timestamp(fecha).strftime("%Y-%m-%d")
        precios[(contrato, iso)] = qm.close_near_from_bars(barras.get(contrato), fecha, window_days)
    return precios, ok


def _datos_con_precios(seleccion, fecha_i, precios, ok_contrato, definitivo):
    """Arma {S, dte, calls:[[K, px]], puts} recortando el rango ya descargado."""
    datos = {"S": seleccion["S"], "dte": seleccion["dte"], "calls": [], "puts": []}
    if seleccion["dte"] is None:
        return datos, definitivo
    if (len(seleccion["calls"]) < bkm_min_options_per_side
            or len(seleccion["puts"]) < bkm_min_options_per_side):
        return datos, definitivo
    iso = pd.Timestamp(fecha_i).strftime("%Y-%m-%d")
    for lado in ("calls", "puts"):
        for contrato in seleccion[lado]:
            ticker_op = contrato["ticker"]
            definitivo = definitivo and ok_contrato.get(ticker_op, True)
            px = precios.get((ticker_op, iso), np.nan)
            if pd.isna(px) or px <= 0:
                continue
            datos[lado].append([float(contrato["strike"]), float(px)])
    return datos, definitivo


def bkm_reconstruct_mfis_history(ticker, spot_series, sample_dates, target_dte, dte_tol,
                                 moneyness_lo, moneyness_hi, rf, min_validos=None,
                                 max_fechas_nuevas=None):
    """MFIS historico. Cada contrato OTM se descarga una vez para todo el tramo.

    La cache (clave v3) sigue siendo por fecha y solo guarda dias anteriores
    a hoy. max_fechas_nuevas limita cuantas fechas sin cache se bajan (para
    dejar la cache tibia cuando el presupuesto no alcanza al ticker entero).
    """
    if not is_us_ticker(ticker):
        return np.full(len(sample_dates), np.nan)
    n_fechas = len(sample_dates)
    slots = []
    faltan = []
    for i, fecha_i in enumerate(sample_dates):
        fecha_i = pd.Timestamp(fecha_i)
        clave = bkm_clave_historia(
            ticker, fecha_i, target_dte, dte_tol, moneyness_lo, moneyness_hi, polygon_dte_min)
        datos = pc.cache_get(clave)
        if datos is not None:
            slots.append(("cache", datos, clave, fecha_i, True))
        else:
            slots.append(("miss", None, clave, fecha_i, True))
            faltan.append(i)

    if max_fechas_nuevas is not None:
        permitidas = set(faltan[:int(max_fechas_nuevas)])
    else:
        permitidas = set(faltan)

    if spot_series is not None and permitidas:
        necesarias = []
        selecciones = {}
        for i in permitidas:
            _tipo, _datos, clave, fecha_i, _ok = slots[i]
            seleccion, definitivo = bkm_seleccion_fecha(
                ticker, spot_series, fecha_i, target_dte, dte_tol, moneyness_lo, moneyness_hi,
                min_dte=polygon_dte_min)
            if seleccion is None:
                slots[i] = ("vacio", None, clave, fecha_i, True)
                continue
            selecciones[i] = (seleccion, definitivo, clave, fecha_i)
            if seleccion["dte"] is None:
                continue
            if (len(seleccion["calls"]) < bkm_min_options_per_side
                    or len(seleccion["puts"]) < bkm_min_options_per_side):
                continue
            for lado in ("calls", "puts"):
                for contrato in seleccion[lado]:
                    necesarias.append((contrato["ticker"], fecha_i))
        precios, ok_contrato = bkm_precios_en_rango(necesarias) if necesarias else ({}, {})
        for i, (seleccion, definitivo, clave, fecha_i) in selecciones.items():
            datos, definitivo = _datos_con_precios(
                seleccion, fecha_i, precios, ok_contrato, definitivo)
            slots[i] = ("nuevo", datos, clave, fecha_i, definitivo)

    mfis_hist = [np.nan] * n_fechas
    validos = 0
    for i in range(n_fechas):
        if min_validos is not None and validos + (n_fechas - i) < min_validos:
            break
        tipo, datos, clave, _, definitivo = slots[i]
        if tipo == "miss" or datos is None:
            continue
        if tipo == "nuevo" and definitivo:
            pc.cache_set(clave, datos)
        dte_i = datos.get("dte")
        if dte_i is None or not np.isfinite(dte_i) or dte_i <= 0:
            continue
        calls_df = pd.DataFrame(datos["calls"], columns=["strike", "price"])
        puts_df = pd.DataFrame(datos["puts"], columns=["strike", "price"])
        mom = bkm_compute_moments(datos["S"], rf, rk.to_years(dte=float(dte_i)), calls_df, puts_df)
        if mom["ok"] and np.isfinite(mom["mfis"]):
            mfis_hist[i] = rk.scale_bkm_moments(
                mom["mfiv"], mom["mfis"], mom["mfik"], float(dte_i), float(target_dte))["mfis"]
            validos += 1
    return np.array(mfis_hist)



sector_keywords = {
    "XLK": ["SEMICONDUCTOR", "COMPUTER", "SOFTWARE", "ELECTRONIC COMPONENTS", "COMPUTER PROGRAMMING", "COMPUTER PERIPHERAL"],
    "XLV": ["PHARMACEUTICAL", "BIOLOGICAL", "MEDICAL", "HOSPITAL", "HEALTH", "SURGICAL", "DRUG"],
    "XLF": ["BANK", "INSURANCE", "INVESTMENT OFFICE", "FINANCE", "SECURITY BROKER", "SAVINGS INSTITUTION"],
    "XLE": ["PETROLEUM", "CRUDE", "NATURAL GAS", "DRILLING", "OIL"],
    "XLY": ["RETAIL", "APPAREL", "HOTEL", "RESTAURANT", "AUTOMOTIVE", "MOTOR VEHICLE", "DEPARTMENT STORE"],
    "XLP": ["FOOD", "BEVERAGE", "TOBACCO", "HOUSEHOLD", "GROCERY", "SOAP"],
    "XLI": ["MACHINERY", "AEROSPACE", "INDUSTRIAL", "TRANSPORTATION", "CONSTRUCTION", "DEFENSE", "RAILROAD", "AIR TRANSPORT"],
    "XLB": ["CHEMICAL", "MINING", "METAL", "PAPER", "STEEL"],
    "XLU": ["ELECTRIC", "UTILITY", "GAS AND ELECTRIC", "WATER SUPPLY"],
    "XLRE": ["REAL ESTATE", "REIT", "LESSORS OF REAL PROPERTY"],
    "XLC": ["TELEPHONE", "TELECOMMUNICATIONS", "BROADCASTING", "CABLE", "MOTION PICTURE", "PUBLISHING", "ADVERTISING", "INTERNET", "RADIOTELEPHONE"],
}


def polygon_get_sic_description(ticker, api_key=None):
    if not is_us_ticker(ticker):
        return None
    api_key = api_key or POLYGON_API_KEY
    url_ref = f"https://api.polygon.io/v3/reference/tickers/{polygon_format_ticker(ticker)}"
    try:
        data, _ = pc.get_json(url_ref, api_key=api_key, permanente=True)
        if data is None:
            return None
        results = data.get("results")
        if not results or not results.get("sic_description"):
            return None
        return results["sic_description"].upper()
    except Exception:
        return None


def polygon_get_sector_etf(ticker):
    sic = polygon_get_sic_description(ticker)
    if sic is None:
        return None
    for etf, keywords in sector_keywords.items():
        if any(kw in sic for kw in keywords):
            return etf
    return None


# ==============================================================================
# OBTENER TICKERS: S&P 500 (top N por market cap real, stockanalysis.com)
# ==============================================================================
print("Obteniendo tickers del S&P 500...")
sp500_tbl = safe_scrape_table("https://stockanalysis.com/list/sp-500-stocks/")

if sp500_tbl is None:
    print("Reintentando con slickcharts.com como fuente alterna...")
    sp500_tbl = safe_scrape_table("https://www.slickcharts.com/sp500")

sp500_caps = {}
if sp500_tbl is not None:
    sp500_tbl_clean = clean_symbol_table(sp500_tbl)
    sp500_components = set(sp500_tbl_clean["symbol"].astype(str).str.upper())
    if "market_cap" in sp500_tbl_clean.columns:
        for sym, cap in zip(sp500_tbl_clean["symbol"], sp500_tbl_clean["market_cap"]):
            cap_num = _parse_market_cap(cap)
            if pd.notna(cap_num) and cap_num > 0:
                sp500_caps[str(sym).upper()] = float(cap_num)
    sp500_tickers = sp500_tbl_clean["symbol"].iloc[: min(n_top_sp500, len(sp500_tbl_clean))].unique().tolist()
    print(f"S&P 500: {n_top_sp500} tickers objetivo, {len(sp500_tickers)} unicos obtenidos "
          f"(ordenados por market cap real, stockanalysis.com); "
          f"constituyentes conocidos {len(sp500_components)}, con cap {len(sp500_caps)}")
else:
    sp500_tickers = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "BRK-B", "LLY", "AVGO",
                      "TSLA", "JPM", "UNH", "V", "XOM", "MA", "JNJ", "PG", "COST", "HD"]
    sp500_components = set(sp500_tickers)
    print("ADVERTENCIA: Scraping fallo en ambas fuentes - usando fallback S&P 500 (20 tickers hardcodeados, sin caps)")

# ==============================================================================
# OBTENER TICKERS: NASDAQ
# ==============================================================================
print("\nObteniendo tickers del NASDAQ...")
nasdaq_tbl = safe_scrape_table("https://stockanalysis.com/list/nasdaq-stocks/")

if nasdaq_tbl is not None:
    nasdaq_tbl_clean = clean_symbol_table(nasdaq_tbl)
    nasdaq_tickers = nasdaq_tbl_clean["symbol"].iloc[: min(n_top_nasdaq, len(nasdaq_tbl_clean))].unique().tolist()
    print(f"NASDAQ: {n_top_nasdaq} tickers objetivo, {len(nasdaq_tickers)} unicos obtenidos")

    shortage_nasdaq = n_top_nasdaq - len(nasdaq_tickers)
    if shortage_nasdaq > 0 and len(nasdaq_tbl_clean) > n_top_nasdaq:
        additional_needed = min(shortage_nasdaq * 2, len(nasdaq_tbl_clean) - n_top_nasdaq)
        additional_nasdaq = (
            nasdaq_tbl_clean["symbol"]
            .iloc[n_top_nasdaq: n_top_nasdaq + additional_needed]
            .unique().tolist()
        )
        additional_nasdaq_unique = [t for t in additional_nasdaq if t not in nasdaq_tickers]
        if additional_nasdaq_unique:
            to_add = additional_nasdaq_unique[: shortage_nasdaq]
            nasdaq_tickers = nasdaq_tickers + to_add
else:
    nasdaq_tbl_clean = None
    nasdaq_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
                       "AVGO", "ASML", "COST", "NFLX", "AMD", "PEP", "ADBE", "CSCO"]
    print("Usando NASDAQ fallback")

# ==============================================================================
# ETFs
# ==============================================================================
etf_core = ["SPY", "QQQ", "VOO", "VTI", "VYM", "IWM", "GLD", "SLV", "USO", "PDBC", "HYG", "VNQ"]

etf_sectoriales = ["XLK", "XLV", "XLF", "XLE", "XLY", "XLP", "XLI", "XLB", "XLU", "XLRE", "XLC", "VOX"]

etf_subsectoriales = [
    "SMH", "SOXX", "IGV", "CIBR", "HACK", "SKYY", "BOTZ", "ROBO", "BUG",
    "XBI", "IBB", "PPH", "IHI", "IHF", "ARKG",
    "KBE", "KRE", "KIE", "IAI", "FINX",
    "XOP", "AMLP", "MLPX", "OIH", "ICLN", "TAN", "FAN",
    "XRT", "XHB", "ITB", "PEJ", "ONLN", "CARZ",
    "MOO",
    "ITA", "PPA", "IYT", "PAVE",
    "GDX", "GDXJ", "LIT", "SLX", "COPX",
    "REM",
    "ARKW", "ARKF",
]

etf_geograficos = [
    "VWO", "EEM",
    "EFA", "VGK", "EZU",
    "AAXJ", "EWJ",
    "MCHI", "FXI", "INDA",
    "ILF", "EWZ",
    "VXUS", "ACWX", "VT",
]

etf_tickers = list(dict.fromkeys(etf_core + etf_sectoriales + etf_subsectoriales + etf_geograficos))

# ==============================================================================
# COMMODITIES
# ==============================================================================
commodity_tickers = ["SLV", "UNG"]

# ==============================================================================
# TICKERS INTERNACIONALES
# ==============================================================================
international_tickers_full = [
    "RY.TO", "SHOP.TO", "TD.TO", "BN.TO", "ENB.TO", "TRI.TO", "BNS.TO",
    "CP.TO", "CNQ.TO", "AEM.TO", "SU.TO", "TRP.TO", "WCN.TO", "FNV.TO",
    "SAP.TO", "SIE.DE", "DTE.DE", "ALV.DE", "MBG.DE", "IFX.DE", "BMW.DE",
    "DB1.DE", "DHL.DE", "DBK.DE", "MUV2.DE", "AZN.L", "HSBC", "ULVR.L",
    "BP", "GSK.L", "RIO.L", "BATS.L", "GLEN.L", "DGE.L", "NG.L", "MC.PA",
    "TTE.PA", "SAN.PA", "OR.PA", "SU.PA", "AI.PA", "BNP.PA", "RMS.PA",
    "CS.PA", "SAF.PA", "CAP.PA", "ITX.MC", "IBE.MC", "BBVA.MC", "SAN.MC",
    "7203.T", "6758.T", "6861.T", "8306.T", "9984.T", "6367.T", "6098.T",
    "4063.T", "7974.T", "9432.T", "6501.T", "7267.T", "8316.T", "4568.T",
    "6902.T", "4502.T", "8031.T",
]

# ==============================================================================
# MAPEO DE MONEDA POR SUFIJO DE TICKER + PARES FX (para conversion a USD)
# ==============================================================================

fx_pairs = {
    "CAD": {"ticker": "CAD=X", "invert": True},
    "EUR": {"ticker": "EURUSD=X", "invert": False},
    "GBP": {"ticker": "GBPUSD=X", "invert": False},
    "JPY": {"ticker": "JPY=X", "invert": True},
}
ticker_currency_by_suffix = {
    ".TO": "CAD",
    ".DE": "EUR",
    ".PA": "EUR",
    ".MC": "EUR",
    ".L": "GBP",
    ".T": "JPY",
}
ticker_currency_override = {}
provider_currency = {}
ticker_currency = {}


def get_currency_for_ticker(ticker):
    if ticker in ticker_currency:
        return ticker_currency[ticker]
    manual = ticker_currency_override.get(ticker)
    if manual is not None:
        return md.normalize_currency(manual)
    for suf, cur in ticker_currency_by_suffix.items():
        if ticker.endswith(suf):
            return cur
    return "USD"


_mc_intl = md.ordenar_por_market_cap(international_tickers_full, n_top_int,
                                     ticker_currency_by_suffix, fx_pairs)
international_tickers = _mc_intl["seleccion"]
print(f"\nInternacionales: top {len(international_tickers)} de {len(international_tickers_full)} "
      "por market cap (USD):")
print(md.tabla_market_cap_texto(_mc_intl))
if _mc_intl["aviso"]:
    print(f"ADVERTENCIA: market cap internacional: {_mc_intl['aviso']}")

# ==============================================================================
# COMBINAR Y LIMPIAR
# ==============================================================================
print("\nCombinando y limpiando tickers...")

sp500_tickers_clean = list(dict.fromkeys(t.upper() for t in sp500_tickers))
nasdaq_tickers_clean = list(dict.fromkeys(t.upper() for t in nasdaq_tickers))
etf_tickers_clean = list(dict.fromkeys(t.upper() for t in etf_tickers))
commodity_tickers_clean = list(dict.fromkeys(t.upper() for t in commodity_tickers))
international_tickers_clean = list(dict.fromkeys(t.upper() for t in international_tickers))

tickers_domesticos = list(dict.fromkeys(
    sp500_tickers_clean + nasdaq_tickers_clean + etf_tickers_clean + commodity_tickers_clean
))
all_tickers = qm.combinar_tickers(tickers_domesticos, international_tickers_clean)

all_tickers = list(dict.fromkeys(all_tickers))
_intl_set = set(international_tickers_clean)
_n_intl_universo = sum(1 for t in all_tickers if t in _intl_set)
print(f"Total tickers FINAL (unicos): {len(all_tickers)} | "
      f"internacionales en el universo: {_n_intl_universo} de {len(international_tickers_clean)}")


# ==============================================================================
# DESCARGA DE PRECIOS (helper generico yfinance)
# ==============================================================================
def download_fx_prices(start, end, period="1mo"):
    fx_prices = {}
    for cur, info in fx_pairs.items():
        try:
            hist = yf.Ticker(info["ticker"]).history(start=start, end=end, interval=period, auto_adjust=True)
            if hist is None or hist.empty:
                continue
            s = hist["Close"].copy()
            s.index = pd.to_datetime(s.index).tz_localize(None)
            if info["invert"]:
                s = 1 / s
            fx_prices[cur] = s.sort_index()
        except Exception:
            pass
    return fx_prices


def download_period_returns(tickers, start, end, period="1mo", fx_prices=None):
    all_rows = []
    n = len(tickers)
    n_convertidos = 0
    for i, tk in enumerate(tickers, start=1):
        try:
            yf_tk = yf.Ticker(tk)
            hist = yf_tk.history(start=start, end=end, interval=period, auto_adjust=True)
            if hist is None or hist.empty:
                print(f"   {tk}: sin cotizacion en Yahoo; se excluye")
                continue
            hist = hist[["Close"]].rename(columns={"Close": "adjusted"})
            hist.index = pd.to_datetime(hist.index).tz_localize(None)

            meta = getattr(yf_tk, "history_metadata", None) or {}
            cur_prov = meta.get("currency")
            if cur_prov:
                provider_currency[tk] = cur_prov
            hist["adjusted"] = hist["adjusted"] * md.price_scale_factor(cur_prov)
            cur_map, conflictos = md.resolve_currencies(
                [tk], ticker_currency_by_suffix,
                overrides=ticker_currency_override,
                provider={tk: cur_prov} if cur_prov else {},
            )
            ticker_currency[tk] = cur_map[tk]
            for c in conflictos:
                print(f"   ADVERTENCIA moneda {c['ticker']}: {c['fuente']} {c['manual']} "
                      f"contradice al proveedor {c['proveedor']}; se usa {c['proveedor']}")
            cur = ticker_currency[tk]
            if cur != "USD" and fx_prices is not None and cur in fx_prices:
                fx_aligned = fx_prices[cur].reindex(
                    fx_prices[cur].index.union(hist.index)
                ).sort_index().ffill().reindex(hist.index)
                hist["adjusted"] = hist["adjusted"] * fx_aligned
                n_convertidos += 1

            hist["return"] = hist["adjusted"].pct_change()
            hist = hist.dropna(subset=["return"])
            hist["symbol"] = tk
            hist = hist.reset_index().rename(columns={"Date": "date", "index": "date"})
            hist["date"] = pd.to_datetime(hist["date"]).dt.tz_localize(None)
            all_rows.append(hist[["symbol", "date", "return", "adjusted"]])
        except Exception:
            pass
        if i % 25 == 0 or i == n:
            print(f"   Descargados {i}/{n} tickers...")
    if n_convertidos > 0:
        print(f"   OK Tickers convertidos a USD en esta descarga: {n_convertidos}")
    if not all_rows:
        return pd.DataFrame(columns=["symbol", "date", "return", "adjusted"])
    return pd.concat(all_rows, ignore_index=True)


start_date = history_start
end_date = history_end

print("Descargando pares FX (mensual) para conversion a USD...")
fx_prices_monthly = download_fx_prices(start_date, end_date, period="1mo")
print(f"   OK Pares FX mensuales disponibles: {', '.join(fx_prices_monthly.keys()) if fx_prices_monthly else '(ninguno)'}")

print("Descargando datos de precios MENSUALES...")
df_prices_monthly = download_period_returns(all_tickers, start_date, end_date, period="1mo",
                                             fx_prices=fx_prices_monthly)
df_prices_monthly = df_prices_monthly.rename(columns={"return": "monthly_return"})

df_prices = df_prices_monthly.copy()
df_prices["year"] = df_prices["date"].dt.year
df_prices = df_prices[df_prices["year"].isin(target_years)]
if lookback_months is not None:
    cutoff_date = df_prices["date"].max() - relativedelta(months=lookback_months - 1)
    df_prices = df_prices[df_prices["date"] >= cutoff_date]
df_prices = df_prices[["symbol", "date", "monthly_return"]]

print(f"Meses disponibles en entrenamiento: {df_prices['date'].nunique()}")
print(f"Tickers con al menos 1 observacion: {df_prices['symbol'].nunique()}")

# ==============================================================================
# BENCHMARK (SPY)
# ==============================================================================
print("Procesando benchmark (SPY)...")
benchmark_prices = download_period_returns(["SPY"], start_date, end_date, period="1mo",
                                            fx_prices=fx_prices_monthly)
benchmark_prices = benchmark_prices.rename(columns={"return": "benchmark_return"})[["date", "benchmark_return"]]
if lookback_months is not None:
    cutoff_date = benchmark_prices["date"].max() - relativedelta(months=lookback_months - 1)
    benchmark_prices = benchmark_prices[benchmark_prices["date"] >= cutoff_date]

# ==============================================================================
# RETORNOS DIARIOS RECIENTES PARA FILTRO DE VOLATILIDAD RECIENTE
# ==============================================================================
recent_vol_window_weeks = int(min(max(round(horizon_months * 4), recent_vol_window_min_weeks),
                                   recent_vol_window_max_weeks))
print(f"Descargando retornos DIARIOS recientes para filtro de volatilidad reciente "
      f"(ventana={recent_vol_window_weeks} semanas, ancladas a {as_of_date.isoformat()})...")

recent_vol_start = (pd.Timestamp(as_of_date) - timedelta(weeks=recent_vol_window_weeks)).strftime("%Y-%m-%d")
recent_vol_end = (pd.Timestamp(as_of_date) + timedelta(days=1)).strftime("%Y-%m-%d")

fx_prices_daily = download_fx_prices(recent_vol_start, recent_vol_end, period="1d")

df_daily_recent = download_period_returns(all_tickers, recent_vol_start, recent_vol_end, period="1d",
                                           fx_prices=fx_prices_daily)
df_daily_recent = df_daily_recent.rename(columns={"return": "daily_return"})

recent_vol_min_obs = max(int(recent_vol_window_weeks * 5 * 0.6), 10)

recent_vol_stats = (
    df_daily_recent.groupby("symbol")["daily_return"]
    .agg(recent_vol_sd="std", recent_vol_n_obs="count")
    .reset_index()
)
recent_vol_stats["recent_vol_annual"] = recent_vol_stats["recent_vol_sd"] * math.sqrt(252)
recent_vol_stats = recent_vol_stats[
    (recent_vol_stats["recent_vol_n_obs"] >= recent_vol_min_obs)
    & (recent_vol_stats["recent_vol_sd"] > 0)
    & recent_vol_stats["recent_vol_sd"].notna()
].sort_values("recent_vol_sd").reset_index(drop=True)

print(f"Tickers con volatilidad reciente calculable: {len(recent_vol_stats)}")

# ==============================================================================
# ESTADISTICAS DESCRIPTIVAS
# ==============================================================================
rf_rate_period = rf_rate_monthly

summary_stats = (
    df_prices.groupby("symbol")["monthly_return"]
    .agg(mean_return="mean", sd_return="std", n_obs="count")
    .reset_index()
)
summary_stats = summary_stats[(summary_stats["n_obs"] >= min_observations) & (summary_stats["sd_return"] > 0)].copy()
summary_stats["sharpe_ratio"] = (summary_stats["mean_return"] - rf_rate_monthly) / summary_stats["sd_return"]
summary_stats["data_quality_penalty"] = (summary_stats["n_obs"] / ideal_observations).clip(upper=1.0)

if len(summary_stats) > 0:
    tickers_total = len(summary_stats)
    obs_median = summary_stats["n_obs"].median()
    pct_ideal = (summary_stats["n_obs"] >= ideal_observations).mean() * 100
    pct_acceptable = (summary_stats["n_obs"] >= min_observations).mean() * 100
    print(f"Tickers totales: {tickers_total} | Obs mediana: {obs_median:.0f} | "
          f"Ideal: {pct_ideal:.1f}% | Minimo: {pct_acceptable:.1f}%")

    fig = px.histogram(summary_stats, x="n_obs", nbins=20, color_discrete_sequence=["steelblue"],
                       opacity=0.7, labels={"n_obs": "Numero de Observaciones"})
    fig.add_vline(x=ideal_observations, line_dash="dash", line_color="darkgreen", line_width=1.5)
    fig.add_vline(x=min_observations, line_dash="dash", line_color="orange", line_width=1.5)
    fig.update_traces(marker_line_color="white", marker_line_width=1)
    fig.update_layout(title="Distribucion de Observaciones por Ticker", yaxis_title="Frecuencia",
                      template="plotly_white", bargap=0.02)
    fig.show()
else:
    raise RuntimeError("No hay tickers con datos suficientes. Ajusta los parametros.")

# ==============================================================================
# CORRELACIONES
# ==============================================================================
returns_wide = df_prices.pivot_table(index="date", columns="symbol", values="monthly_return")
cor_matrix_full = returns_wide.corr(min_periods=1)

avg_cor_by_ticker = (
    qm.average_abs_correlation(cor_matrix_full).rename("avg_cor").rename_axis("symbol").reset_index()
)

# ==============================================================================
# FAMA-FRENCH
# ==============================================================================
print("Descargando datos Fama-French...")
try:
    ff_raw = pdr.DataReader("F-F_Research_Data_Factors", "famafrench",
                             start=history_start, end=history_end)[0]
    ff_raw = ff_raw.copy()
    ff_raw.index = ff_raw.index.to_timestamp()
    ff_raw = ff_raw.rename(columns={"Mkt-RF": "Mkt-RF", "SMB": "SMB", "HML": "HML"})
    ff_raw = ff_raw[ff_raw.index.year.isin(target_years)]
    if lookback_months is not None:
        cutoff_date = ff_raw.index.max() - relativedelta(months=lookback_months - 1)
        ff_raw = ff_raw[ff_raw.index >= cutoff_date]
    ff_raw = ff_raw / 100.0
    ff_data = ff_raw[["Mkt-RF", "SMB", "HML", "RF"]]
except Exception as e:
    print(f"Error con Fama-French ({e}). Continuando sin ellos.")
    ff_data = None

# ==============================================================================
# BETAS FF3
# ==============================================================================
if ff_data is not None:
    ff_data_m = ff_data.copy()
    ff_data_m.index = ff_data_m.index.to_period("M")
    ff_data_m.index.name = "period"
    ff_data_m_reset = ff_data_m.reset_index()

    df_prices_m = df_prices.copy()
    df_prices_m["period"] = df_prices_m["date"].dt.to_period("M")
    df_prices_m = df_prices_m[df_prices_m["period"].isin(ff_data_m_reset["period"])]

    rows = []
    if len(df_prices_m) > 0:
        for sym, g in df_prices_m.groupby("symbol"):
            if len(g) < 3:
                continue
            merged = g.merge(ff_data_m_reset, on="period", how="inner")
            if len(merged) < 3:
                continue
            try:
                merged["excess_return"] = merged["monthly_return"] - merged["RF"]
                X = sm.add_constant(merged[["Mkt-RF", "SMB", "HML"]])
                y = merged["excess_return"]
                mat = np.asarray(X, dtype=float)
                yy = np.asarray(y, dtype=float)
                filas_ok = np.isfinite(mat).all(axis=1) & np.isfinite(yy)
                if int(filas_ok.sum()) < mat.shape[1] or np.linalg.matrix_rank(mat[filas_ok]) < mat.shape[1]:
                    rows.append(dict(symbol=sym, beta_mkt=np.nan, beta_smb=np.nan, beta_hml=np.nan))
                    continue
                model = sm.OLS(y, X, missing="drop").fit()
                rows.append(dict(symbol=sym, beta_mkt=model.params.get("Mkt-RF", np.nan),
                                  beta_smb=model.params.get("SMB", np.nan),
                                  beta_hml=model.params.get("HML", np.nan)))
            except Exception:
                rows.append(dict(symbol=sym, beta_mkt=np.nan, beta_smb=np.nan, beta_hml=np.nan))

    ff_stats = pd.DataFrame(rows, columns=["symbol", "beta_mkt", "beta_smb", "beta_hml"])
    if len(ff_stats) > 0:
        market_premium = ff_data["Mkt-RF"].mean()
        smb_premium = ff_data["SMB"].mean()
        hml_premium = ff_data["HML"].mean()
        ff_stats["ff_expected_return"] = (rf_rate_period
                                           + ff_stats["beta_mkt"] * market_premium
                                           + ff_stats["beta_smb"] * smb_premium
                                           + ff_stats["beta_hml"] * hml_premium)
        print(f"Betas calculados para {len(ff_stats)} activos")
    else:
        ff_stats = pd.DataFrame(columns=["symbol", "beta_mkt", "beta_smb", "beta_hml", "ff_expected_return"])
else:
    ff_stats = pd.DataFrame(columns=["symbol", "beta_mkt", "beta_smb", "beta_hml", "ff_expected_return"])

# ==============================================================================
# COMBINAR METRICAS
# ==============================================================================
combined_stats = summary_stats.merge(avg_cor_by_ticker, on="symbol", how="left")
combined_stats = combined_stats.merge(
    ff_stats[["symbol", "beta_mkt", "beta_smb", "beta_hml", "ff_expected_return"]], on="symbol", how="left"
)
combined_stats["avg_cor"] = combined_stats["avg_cor"].fillna(combined_stats["avg_cor"].median())
# Retorno esperado unico del script (seleccion y QP): media historica encogida
# hacia FF3 segun la historia de cada activo. Sin FF3 queda la media historica.
_mu_adj, _w_hist = qm.shrink_mu_to_prior(
    combined_stats["mean_return"], combined_stats["ff_expected_return"],
    combined_stats["n_obs"], mu_shrink_k)
combined_stats["adjusted_return"] = _mu_adj
combined_stats["mu_weight_hist"] = _w_hist
combined_stats["ff_expected_return"] = combined_stats["ff_expected_return"].fillna(combined_stats["mean_return"])
_con_ff = combined_stats["mu_weight_hist"] < 1.0
print(f"Retorno esperado (k={mu_shrink_k:g}): {int(_con_ff.sum())} de {len(combined_stats)} activos encogidos hacia FF3"
      + (f" | peso de la historica {combined_stats.loc[_con_ff, 'mu_weight_hist'].min():.2f}-"
         f"{combined_stats.loc[_con_ff, 'mu_weight_hist'].max():.2f}" if _con_ff.any() else " (sin FF3: solo media historica)"))
_disp_hist = combined_stats["mean_return"].std() * 12
_disp_adj = combined_stats["adjusted_return"].std() * 12
print(f"   Dispersion de mu entre activos (anual): historica {_disp_hist * 100:.1f}% -> encogida {_disp_adj * 100:.1f}%")
combined_stats["sharpe_ratio_adjusted"] = (
    (combined_stats["adjusted_return"] - rf_rate_period) / combined_stats["sd_return"]
)
combined_stats["is_etf_commodity"] = combined_stats["symbol"].isin(etf_tickers + commodity_tickers)

if combined_stats is None or len(combined_stats) == 0:
    raise RuntimeError("combined_stats no se creo correctamente")
print(f"combined_stats creado: {len(combined_stats)} activos")


# ==============================================================================
# SELECCION CONJUNTA VIA QUBO/ISING
# ==============================================================================
def qubo_energy(idx_sel, h, J):
    idx_sel = list(idx_sel)
    if len(idx_sel) < 2:
        return -np.sum(h[idx_sel])
    sub_J = J[np.ix_(idx_sel, idx_sel)]
    return -np.sum(h[idx_sel]) + np.sum(np.triu(sub_J, k=1))


def select_candidates_qubo(symbols, h_dict, cor_matrix, n_select, weight_decorr_):
    n_pool = len(symbols)
    if n_select >= n_pool:
        return symbols

    J = weight_decorr_ * cor_matrix.loc[symbols, symbols].abs().values
    np.fill_diagonal(J, 0)
    h = np.array([h_dict[s] for s in symbols])

    n_combos = math.comb(n_pool, n_select)
    print(f"   QUBO: pool={n_pool}, seleccionar={n_select}, combinaciones={n_combos:.3e}")

    if n_combos <= qubo_exact_threshold:
        print("   Combinaciones dentro del umbral - resolviendo por fuerza bruta (optimo exacto)")
        best_energy = np.inf
        best_combo = None
        combos = itertools.combinations(range(n_pool), n_select)
        count = 0
        for combo in combos:
            e = qubo_energy(combo, h, J)
            if e < best_energy:
                best_energy = e
                best_combo = combo
            count += 1
            if count % 5000 == 0:
                print(f"      ... {count}/{n_combos:.0f} combinaciones evaluadas")
        print(f"   Optimo exacto - energia={best_energy:.4f}")
        return [symbols[i] for i in best_combo]

    print(f"   Combinaciones exceden el umbral - resolviendo via Simulated Annealing ({qubo_sa_iterations} iteraciones)")
    rng = np.random.default_rng(seed)
    idx_current = list(rng.choice(n_pool, n_select, replace=False))
    e_current = qubo_energy(idx_current, h, J)
    best_idx = idx_current.copy()
    best_energy = e_current
    e_inicial = e_current

    temp_init = max(abs(e_current), 1e-6)
    temp_final = temp_init * 1e-4

    idx_set = set(idx_current)
    for it in range(1, qubo_sa_iterations + 1):
        temp = temp_init * (temp_final / temp_init) ** (it / qubo_sa_iterations)
        out_pos = idx_current[rng.integers(0, len(idx_current))]
        remaining = [x for x in range(n_pool) if x not in idx_set]
        in_pos = remaining[rng.integers(0, len(remaining))]
        idx_prop = [x for x in idx_current if x != out_pos] + [in_pos]
        e_prop = qubo_energy(idx_prop, h, J)
        delta_e = e_prop - e_current

        if delta_e < 0 or rng.random() < np.exp(-delta_e / temp):
            idx_current = idx_prop
            idx_set = set(idx_current)
            e_current = e_prop
            if e_current < best_energy:
                best_energy = e_current
                best_idx = idx_current.copy()

    print(f"   SA completado - energia inicial={e_inicial:.4f} | mejor energia={best_energy:.4f}")
    return [symbols[i] for i in best_idx]


def select_optimal_candidates(df, n_candidates):
    df_filtered = df[(df["n_obs"] >= min_observations) & (df["sd_return"] > 0)
                      & df["sharpe_ratio_adjusted"].notna() & np.isfinite(df["sharpe_ratio_adjusted"])].copy()

    sd_threshold = df_filtered["sd_return"].quantile(volatility_percentile)
    cor_threshold = df_filtered["avg_cor"].quantile(correlation_percentile)

    if correlation_order == 1:
        df_candidates = df_filtered[(df_filtered["sd_return"] <= sd_threshold) & (df_filtered["avg_cor"] >= cor_threshold)]
    else:
        df_candidates = df_filtered[(df_filtered["sd_return"] <= sd_threshold) & (df_filtered["avg_cor"] <= cor_threshold)]

    if len(df_candidates) < n_candidates * 0.5:
        sd_threshold = df_filtered["sd_return"].quantile(0.75)
        cor_threshold = df_filtered["avg_cor"].quantile(0.80)
        if correlation_order == 1:
            df_candidates = df_filtered[(df_filtered["sd_return"] <= sd_threshold) & (df_filtered["avg_cor"] >= cor_threshold)]
        else:
            df_candidates = df_filtered[(df_filtered["sd_return"] <= sd_threshold) & (df_filtered["avg_cor"] <= cor_threshold)]

    df_candidates = df_candidates.copy()
    sr = df_candidates["sharpe_ratio_adjusted"]
    sharpe_norm = (sr - sr.min()) / (sr.max() - sr.min())
    df_candidates["sharpe_norm"] = sharpe_norm.fillna(0.5)
    df_candidates["h_score"] = (
        weight_sharpe * df_candidates["sharpe_norm"] * df_candidates["data_quality_penalty"]
    )
    df_candidates = df_candidates.sort_values("h_score", ascending=False)

    n_to_select = min(n_candidates, len(df_candidates))

    h_vec = dict(zip(df_candidates["symbol"], df_candidates["h_score"]))
    selected = select_candidates_qubo(
        symbols=list(df_candidates["symbol"]),
        h_dict=h_vec,
        cor_matrix=cor_matrix_full,
        n_select=n_to_select,
        weight_decorr_=weight_decorr,
    )

    print("\nTop 10 activos seleccionados (via QUBO):")
    top10 = (df_candidates[df_candidates["symbol"].isin(selected)]
             .sort_values("h_score", ascending=False)
             .head(10)[["symbol", "sharpe_ratio_adjusted", "sd_return", "avg_cor", "n_obs", "h_score"]])
    print(top10.to_string(index=False))
    return selected, list(df_candidates["symbol"])


ticker_candidates, prefilter_ranking = select_optimal_candidates(combined_stats, n_pre_filter)
print(f"\nPool pre-filtro: {len(ticker_candidates)} candidatos\n")

# ==============================================================================
# PISO DE ETF: CUANTOS HACEN FALTA Y RESERVA DESDE EL PRE-FILTRO
# ==============================================================================
etf_group_set = set(etf_tickers + commodity_tickers)
etf_band_floor_cfg = max(0.0, pct_etf_deseado - pct_etf_tolerancia) if include_etfs_in_portfolio else 0.0
n_etf_needed = qm.etfs_necesarios(etf_band_floor_cfg, max_weight)
n_etf_prefilter = qm.contar_etfs(ticker_candidates, etf_group_set)
etf_reserva = []
if n_etf_needed > 0:
    _eleg = combined_stats[(combined_stats["n_obs"] >= min_observations) & (combined_stats["sd_return"] > 0)
                           & combined_stats["sharpe_ratio_adjusted"].notna()
                           & np.isfinite(combined_stats["sharpe_ratio_adjusted"])].copy()
    _sr = _eleg["sharpe_ratio_adjusted"]
    _h_eleg = weight_sharpe * ((_sr - _sr.min()) / (_sr.max() - _sr.min())).fillna(0.5)
    if "data_quality_penalty" in _eleg.columns:
        _h_eleg = _h_eleg * _eleg["data_quality_penalty"]
    _orden_eleg = _eleg.assign(_h=_h_eleg).sort_values("_h", ascending=False)["symbol"].tolist()
    etf_reserva = qm.reserva_etf(prefilter_ranking + _orden_eleg, ticker_candidates, etf_group_set,
                                 etf_floor_reserve_factor * n_etf_needed)
    print(f"Piso de ETF: {etf_band_floor_cfg * 100:.0f}% con max_weight {max_weight:.2f} -> "
          f"{n_etf_needed} ETF necesarios | en el pre-filtro: {n_etf_prefilter} | "
          f"reserva: {len(etf_reserva)}{' (' + ', '.join(etf_reserva) + ')' if etf_reserva else ''}\n")

# ==============================================================================
# TENOR DE OPCIONES OBJETIVO (Polygon) - tope universal
# ==============================================================================
target_dte_polygon = min(max(round(horizon_months * 30), 15), options_dte_cap_days)
print(f"Tenor de opciones objetivo (Polygon): {target_dte_polygon} dias "
      f"(horizonte={horizon_months}m, tope universal={options_dte_cap_days}d)\n")

# ==============================================================================
# DATOS DE MERCADO VIA POLYGON (IV, GRIEGAS, SECTOR)
# ==============================================================================
print("Consultando datos de mercado (Polygon) para tickers estadounidenses...")

us_candidates = [t for t in ticker_candidates if is_us_ticker(t)]
intl_candidates = [t for t in ticker_candidates if not is_us_ticker(t)]

print(f"  Tickers US: {len(us_candidates)} | Tickers internacionales (sin cobertura Polygon): {len(intl_candidates)}")

polygon_market_list = {}
for i, tk in enumerate(us_candidates, start=1):
    opt_tk = polygon_get_atm_option(tk, target_dte_polygon, polygon_dte_tol)
    polygon_market_list[tk] = {"symbol": tk, **opt_tk}
    if i % 10 == 0 or i == len(us_candidates):
        print(f"   Polygon IV: {i}/{len(us_candidates)}")

polygon_market_df = pd.DataFrame(list(polygon_market_list.values()))
if "ok" not in polygon_market_df.columns:
    polygon_market_df["ok"] = False

n_polygon_ok = polygon_market_df["ok"].fillna(False).sum()
print(f"  Datos de opciones obtenidos: {n_polygon_ok} de {len(us_candidates)} tickers US")

us_reserva = [t for t in etf_reserva if is_us_ticker(t) and t not in polygon_market_list]
if us_reserva:
    for tk in us_reserva:
        polygon_market_list[tk] = {"symbol": tk, **polygon_get_atm_option(tk, target_dte_polygon, polygon_dte_tol)}
    polygon_market_df = pd.DataFrame(list(polygon_market_list.values()))
    if "ok" not in polygon_market_df.columns:
        polygon_market_df["ok"] = False
    n_res_ok = int(polygon_market_df.loc[polygon_market_df["symbol"].isin(us_reserva), "ok"].fillna(False).sum())
    print(f"  Reserva de ETF: opciones de {n_res_ok} de {len(us_reserva)} (no cuentan en el pool)")

stock_us_candidates = [t for t in us_candidates if t not in (etf_tickers + commodity_tickers)]
print(f"  Clasificando sector de {len(stock_us_candidates)} acciones US (Polygon SIC)...")

sector_map = {}
for i, tk in enumerate(stock_us_candidates, start=1):
    sector_map[tk] = polygon_get_sector_etf(tk)
    if i % 10 == 0 or i == len(stock_us_candidates):
        print(f"   Sector: {i}/{len(stock_us_candidates)}")

n_sector_ok = sum(1 for v in sector_map.values() if v is not None)
print(f"  Sector identificado (Polygon SIC, US): {n_sector_ok} de {len(stock_us_candidates)} acciones")

international_sector_etf_map = {
    "RY.TO": "XLF", "SHOP.TO": "XLK", "TD.TO": "XLF", "BN.TO": "XLF",
    "ENB.TO": "XLE", "TRI.TO": "XLI", "BNS.TO": "XLF", "CP.TO": "XLI",
    "CNQ.TO": "XLE", "AEM.TO": "XLB", "SU.TO": "XLE", "TRP.TO": "XLE",
    "WCN.TO": "XLI", "FNV.TO": "XLB", "SAP.TO": "XLP",
    "SIE.DE": "XLI", "DTE.DE": "VOX", "ALV.DE": "XLF", "MBG.DE": "XLY",
    "IFX.DE": "XLK", "BMW.DE": "XLY", "DB1.DE": "XLF", "DHL.DE": "XLI",
    "DBK.DE": "XLF", "MUV2.DE": "XLF",
    "AZN.L": "XLV", "HSBC": "XLF", "ULVR.L": "XLP", "BP": "XLE",
    "GSK.L": "XLV", "RIO.L": "XLB", "BATS.L": "XLP", "GLEN.L": "XLB",
    "DGE.L": "XLP", "NG.L": "XLU",
    "MC.PA": "XLY", "TTE.PA": "XLE", "SAN.PA": "XLV", "OR.PA": "XLP",
    "SU.PA": "XLI", "AI.PA": "XLB", "BNP.PA": "XLF", "RMS.PA": "XLY",
    "CS.PA": "XLF", "SAF.PA": "XLI", "CAP.PA": "XLK",
    "ITX.MC": "XLY", "IBE.MC": "XLU", "BBVA.MC": "XLF", "SAN.MC": "XLF",
    "7203.T": "XLY", "6758.T": "XLY", "6861.T": "XLK", "8306.T": "XLF",
    "9984.T": "VOX", "6367.T": "XLI", "6098.T": "XLI", "4063.T": "XLB",
    "7974.T": "VOX", "9432.T": "VOX", "6501.T": "XLI", "7267.T": "XLY",
    "8316.T": "XLF", "4568.T": "XLV", "6902.T": "XLY", "4502.T": "XLV",
    "8031.T": "XLI",
}

stock_intl_candidates = [t for t in intl_candidates if t not in (etf_tickers + commodity_tickers)]
for tk in stock_intl_candidates:
    sector_map[tk] = international_sector_etf_map.get(tk)

n_sector_intl_ok = sum(1 for t in stock_intl_candidates if sector_map.get(t) is not None)
print(f"  Sector identificado (mapeo manual, internacionales): {n_sector_intl_ok} de {len(stock_intl_candidates)} acciones")

print("  Diagnostico de llamadas a Polygon:")
pc.print_diagnostics("     ")

# ==============================================================================
# FILTRO DELTA
# ==============================================================================
if use_delta_filter:
    print(f"\nAplicando filtro Delta (delta_min={delta_min:.2f}, modo={delta_strike_mode}, "
          f"T={horizon_months / 12:.3f} anios)...")
    if delta_strike_mode == "otm":
        print("   Metrica: colchon = delta(K=S) - delta(K OTM). Alto si la vol es baja.")
        print("   IV: Polygon si hay cadena US; si no, vol historica (internacionales incluidos).")
    else:
        print("   Fuente: delta real de mercado (Polygon) para US, formula BS con vol historica para el resto")

    T_horizon = horizon_months / 12

    _delta_universo = list(dict.fromkeys(ticker_candidates + etf_reserva))
    mu_for_delta = (
        df_prices[df_prices["symbol"].isin(_delta_universo)]
        .groupby("symbol")["monthly_return"].mean().rename("mu_monthly").reset_index()
    )
    hist_vol_for_delta = (
        df_prices[df_prices["symbol"].isin(_delta_universo)]
        .groupby("symbol")["monthly_return"].std().mul(math.sqrt(12)).rename("vol_hist").reset_index()
    )

    delta_rows = []
    poly_ok_set = set(polygon_market_df.loc[polygon_market_df["ok"] == True, "symbol"]) if "ok" in polygon_market_df.columns else set()

    m_otm = qm.otm_log_moneyness(delta_otm_log_m, T_horizon, delta_otm_ref_months / 12.0)
    if delta_strike_mode == "otm":
        print(f"   Log-moneyness OTM efectiva: {m_otm:.4f} "
              f"(base {delta_otm_log_m:.4f} a {delta_otm_ref_months:g} meses)")

    for ticker in _delta_universo:
        usa_polygon = ticker in poly_ok_set
        fila_poly = None
        if usa_polygon:
            fila_poly = polygon_market_df[polygon_market_df["symbol"] == ticker].iloc[0]

        mu_i_series = mu_for_delta.loc[mu_for_delta["symbol"] == ticker, "mu_monthly"]
        mu_i = mu_i_series.iloc[0] if len(mu_i_series) and not pd.isna(mu_i_series.iloc[0]) else 0.0

        iv_series = hist_vol_for_delta.loc[hist_vol_for_delta["symbol"] == ticker, "vol_hist"]
        iv_hist = iv_series.iloc[0] if len(iv_series) else np.nan

        fila_delta = qm.evaluar_delta_candidato(
            iv_hist, T_horizon, rf_rate,
            mode=delta_strike_mode,
            log_m=delta_otm_log_m,
            ref_years=delta_otm_ref_months / 12.0,
            mu_sobre_horizonte=float(mu_i) * horizon_months,
            usar_delta_polygon=usa_polygon and delta_strike_mode != "otm",
            polygon_delta=None if fila_poly is None else fila_poly["delta"],
            polygon_iv=None if fila_poly is None else fila_poly["iv"],
        )
        delta_rows.append(dict(symbol=ticker, **fila_delta))

    delta_df = pd.DataFrame(delta_rows)
    delta_named = dict(zip(delta_df["symbol"], delta_df["delta"]))
    _es_reserva = delta_df["symbol"].isin(set(etf_reserva) - set(ticker_candidates))
    delta_df_reserva = delta_df[_es_reserva].copy()
    delta_df = delta_df[~_es_reserva].copy()
    etf_reserva = delta_df_reserva.loc[
        delta_df_reserva["delta"].isna() | (delta_df_reserva["delta"] >= delta_min), "symbol"].tolist()
    if len(delta_df_reserva):
        print(f"  Reserva de ETF tras filtro Delta: {len(etf_reserva)} de {len(delta_df_reserva)}")

    n_delta_ok = delta_df["delta"].notna().sum()
    n_delta_na = delta_df["delta"].isna().sum()
    n_below = ((delta_df["delta"].notna()) & (delta_df["delta"] < delta_min)).sum()
    n_pass = ((delta_df["delta"].notna()) & (delta_df["delta"] >= delta_min)).sum()
    n_real = (delta_df["strike_mode"] == "polygon_real").sum()

    n_bs = int(delta_df["strike_mode"].astype(str).str.startswith(f"bs_{delta_strike_mode}").sum())
    print(f"  Deltas de mercado real (Polygon): {n_real} | Deltas via formula BS "
          f"(modo '{delta_strike_mode}'): {n_bs}")
    print(f"  Deltas calculados: {n_delta_ok} | Sin datos (se conservan): {n_delta_na}")
    print(f"  Descartados (delta < {delta_min:.2f}): {n_below}")
    print(f"  Superan el filtro (delta >= {delta_min:.2f}): {n_pass}")

    discarded_delta = delta_df[(delta_df["delta"].notna()) & (delta_df["delta"] < delta_min)].sort_values("delta")
    if len(discarded_delta) > 0:
        disp = discarded_delta.copy()
        disp["Delta"] = disp["delta"].map(lambda x: f"{x:.3f}")
        disp["IV_anual"] = disp["iv_used"].map(lambda x: f"{x * 100:.1f}%")
        print("\nActivos descartados por Delta insuficiente:")
        print(disp[["symbol", "Delta", "IV_anual", "strike_mode"]]
              .rename(columns={"symbol": "Symbol", "strike_mode": "Fuente"}).to_string(index=False))

    tickers_pass_delta = delta_df[(delta_df["delta"].isna()) | (delta_df["delta"] >= delta_min)]["symbol"].tolist()
    ticker_candidates = tickers_pass_delta
    print(f"\nTras filtro Delta: {len(ticker_candidates)} tickers disponibles para los siguientes filtros\n")
else:
    print("Filtro Delta desactivado\n")
    delta_named = {t: np.nan for t in ticker_candidates}

# ==============================================================================
# FILTRO DE VOLATILIDAD RECIENTE
# ==============================================================================
print(f"Aplicando filtro de volatilidad reciente (ventana={recent_vol_window_weeks} semanas, "
      f"ratio max={recent_vol_ratio_max:.2f}x)...")

def tabla_ratio_vol_reciente(tickers):
    """Vol. reciente / vol. general anual de `tickers`, en orden ascendente de ratio."""
    tabla = (
        recent_vol_stats[recent_vol_stats["symbol"].isin(tickers)]
        .merge(combined_stats[["symbol", "sharpe_ratio_adjusted", "sd_return", "n_obs"]], on="symbol", how="left")
    )
    tabla = tabla[tabla["sd_return"].notna() & (tabla["sd_return"] > 0)].copy()
    tabla["general_vol_anual"] = tabla["sd_return"] * math.sqrt(12)
    tabla["recent_vol_ratio"] = tabla["recent_vol_annual"] / tabla["general_vol_anual"]
    return tabla.sort_values("recent_vol_ratio")


recent_vol_ratio_stats = tabla_ratio_vol_reciente(ticker_candidates)
reserva_ratio_stats = tabla_ratio_vol_reciente([t for t in etf_reserva if t not in set(ticker_candidates)])

n_pool_post_delta = len(ticker_candidates)
n_con_recent_vol = len(recent_vol_ratio_stats)
print(f"Candidatos previos (post-Delta): {n_pool_post_delta} | Con ratio de vol. reciente calculable: {n_con_recent_vol}")

recent_vol_pass = recent_vol_ratio_stats[recent_vol_ratio_stats["recent_vol_ratio"] <= recent_vol_ratio_max]

n_descartados = n_con_recent_vol - len(recent_vol_pass)
print(f"Descartados por umbral (ratio > {recent_vol_ratio_max:.2f}x): {n_descartados} | "
      f"Superan el filtro: {len(recent_vol_pass)}")

if len(recent_vol_pass) < recent_vol_min_survivors:
    print(f"Advertencia: solo {len(recent_vol_pass)} tickers superan el umbral - relajando hasta "
          f"el piso minimo ({recent_vol_min_survivors})")
    recent_vol_pass = recent_vol_ratio_stats.head(min(recent_vol_min_survivors, n_con_recent_vol))

if len(recent_vol_pass) > n_filter_candidates:
    print(f"Pool post-umbral ({len(recent_vol_pass)}) supera el techo n_filter_candidates "
          f"({n_filter_candidates}) - recortando por ratio ascendente")
    recent_vol_pass = recent_vol_pass.sort_values("recent_vol_ratio").head(n_filter_candidates)

recent_vol_candidates = recent_vol_pass.copy()

disp = recent_vol_candidates.copy()
disp["Vol_Reciente_Anual"] = disp["recent_vol_annual"].map(lambda x: f"{x * 100:.2f}%")
disp["Vol_General_Anual"] = disp["general_vol_anual"].map(lambda x: f"{x * 100:.2f}%")
disp["Ratio"] = disp["recent_vol_ratio"].map(lambda x: f"{x:.2f}x")
disp["Sharpe"] = disp["sharpe_ratio_adjusted"].map(lambda x: f"{x:.3f}")
print(disp.rename(columns={"symbol": "Symbol", "n_obs": "Obs_Mensuales"})
      [["Symbol", "Vol_Reciente_Anual", "Vol_General_Anual", "Ratio", "Sharpe", "Obs_Mensuales"]]
      .to_string(index=False))

ticker_candidates = recent_vol_candidates["symbol"].tolist()
print(f"\nConjunto tras filtro de volatilidad reciente: {len(ticker_candidates)} tickers\n")

# ==============================================================================
# FILTRO DE IV vs VOLATILIDAD RECIENTE (flujo de opciones, forward-looking)
# ==============================================================================
print(f"Aplicando filtro de IV vs volatilidad reciente (DTE={target_dte_polygon}d, "
      f"ratio max={iv_vs_realized_ratio_max:.2f}x)...")

recent_vol_lookup = dict(zip(recent_vol_stats["symbol"], recent_vol_stats["recent_vol_annual"]))
poly_iv_lookup = polygon_market_df.set_index("symbol")["iv"].to_dict() if len(polygon_market_df) else {}
poly_ok_lookup = polygon_market_df.set_index("symbol")["ok"].to_dict() if len(polygon_market_df) else {}

def fila_iv_vs_reciente(tk):
    iv_tk = poly_iv_lookup.get(tk, np.nan)
    ok_tk = bool(poly_ok_lookup.get(tk, False))
    rv_tk = recent_vol_lookup.get(tk, np.nan)
    if not ok_tk or pd.isna(iv_tk) or pd.isna(rv_tk) or rv_tk <= 0:
        return dict(symbol=tk, iv=iv_tk, recent_vol=rv_tk, iv_ratio=np.nan, evaluable=False)
    return dict(symbol=tk, iv=iv_tk, recent_vol=rv_tk, iv_ratio=iv_tk / rv_tk, evaluable=True)


def rechaza_iv_vs_reciente(tk):
    """Mismo criterio del filtro: evaluable y ratio IV / vol. reciente sobre el maximo."""
    fila = fila_iv_vs_reciente(tk)
    return bool(fila["evaluable"] and fila["iv_ratio"] > iv_vs_realized_ratio_max)


iv_flow_rows = [fila_iv_vs_reciente(tk) for tk in ticker_candidates]
iv_flow_df = pd.DataFrame(iv_flow_rows)
n_evaluables = int(iv_flow_df["evaluable"].sum()) if len(iv_flow_df) else 0
print(f"  Candidatos con IV de mercado evaluable: {n_evaluables} de {len(ticker_candidates)}")

iv_flow_discard = iv_flow_df[iv_flow_df["evaluable"] & (iv_flow_df["iv_ratio"] > iv_vs_realized_ratio_max)] \
    if len(iv_flow_df) else pd.DataFrame(columns=["symbol", "iv", "recent_vol", "iv_ratio"])

iv_flow_keep = [t for t in ticker_candidates if t not in set(iv_flow_discard["symbol"])]

print(f"  Descartados por IV anomala respecto a vol. reciente (ratio > {iv_vs_realized_ratio_max:.2f}x): "
      f"{len(iv_flow_discard)}")

if len(iv_flow_discard) > 0:
    disp2 = iv_flow_discard.copy()
    disp2["IV"] = disp2["iv"].map(lambda x: f"{x * 100:.1f}%")
    disp2["Vol_Reciente"] = disp2["recent_vol"].map(lambda x: f"{x * 100:.1f}%")
    disp2["Ratio"] = disp2["iv_ratio"].map(lambda x: f"{x:.2f}x")
    print(disp2.rename(columns={"symbol": "Symbol"})[["Symbol", "IV", "Vol_Reciente", "Ratio"]].to_string(index=False))

iv_descartados = set(iv_flow_discard["symbol"]) if len(iv_flow_discard) else set()
orden_reposicion = recent_vol_ratio_stats.sort_values("recent_vol_ratio")["symbol"].tolist()
orden_reposicion_etf = orden_reposicion + reserva_ratio_stats["symbol"].tolist()

etf_piso_agregados = []
n_etf_iv = qm.contar_etfs(iv_flow_keep, etf_group_set)
if n_etf_needed > n_etf_iv:
    pool_etf_piso = qm.candidatos_reposicion(
        orden_reposicion_etf, iv_flow_keep, descartados=iv_descartados, rechaza=rechaza_iv_vs_reciente)
    etf_piso_agregados = qm.completar_etfs(iv_flow_keep, pool_etf_piso, etf_group_set, n_etf_needed)
    print(f"  Piso de ETF: {n_etf_iv} ETF tras filtro de IV, se necesitan {n_etf_needed} "
          f"(piso {etf_band_floor_cfg * 100:.0f}% / max_weight {max_weight:.2f})")
    if etf_piso_agregados:
        print(f"  Agregando {len(etf_piso_agregados)} ETF que superan los filtros duros: "
              f"{', '.join(etf_piso_agregados)}")
        iv_flow_keep = iv_flow_keep + etf_piso_agregados
    if n_etf_iv + len(etf_piso_agregados) < n_etf_needed:
        print(f"  ADVERTENCIA: no quedan mas ETF que superen los filtros duros "
              f"({n_etf_iv + len(etf_piso_agregados)} de {n_etf_needed}); se revisa antes de optimizar")

if len(iv_flow_keep) < iv_min_survivors:
    reponer_iv_pool = qm.candidatos_reposicion(
        orden_reposicion, iv_flow_keep, descartados=iv_descartados, rechaza=rechaza_iv_vs_reciente)
    faltan = iv_min_survivors - len(iv_flow_keep)
    repuestos = reponer_iv_pool[:faltan]
    if repuestos:
        print(f"  Advertencia: solo {len(iv_flow_keep)} tickers tras filtro de IV - reponiendo con "
              f"{len(repuestos)} desde el pool de vol. reciente (sin los descartados por IV)")
        iv_flow_keep = iv_flow_keep + repuestos

ticker_candidates = list(dict.fromkeys(iv_flow_keep))
print(f"\nConjunto tras filtro de IV vs volatilidad reciente: {len(ticker_candidates)} tickers\n")

# ==============================================================================
# FILTRO MFIS (BKM) - cobertura anomala vs especulacion
# ==============================================================================
print(f"\nAplicando filtro MFIS (Bakshi-Kapadia-Madan) (z_threshold={bkm_z_threshold:.2f}, "
      f"lookback={bkm_lookback_months} meses)...")

hoy_ts = pd.Timestamp(as_of_date)
sample_dates_bkm = pd.date_range(start=bkm_hist_anchor, end=hoy_ts - timedelta(days=7), freq=bkm_hist_sample_freq)
sample_dates_bkm = sample_dates_bkm[sample_dates_bkm >= hoy_ts - relativedelta(months=bkm_lookback_months)]
print(f"   Fechas de muestreo historico: {len(sample_dates_bkm)} (freq={bkm_hist_sample_freq}, "
      f"ancladas a {bkm_hist_anchor})")

reponer_pool_bkm = qm.candidatos_reposicion(
    orden_reposicion, ticker_candidates, descartados=iv_descartados, rechaza=rechaza_iv_vs_reciente)
reponer_pool_bkm_etf = qm.candidatos_reposicion(
    orden_reposicion_etf, ticker_candidates, descartados=iv_descartados, rechaza=rechaza_iv_vs_reciente)

bkm_current_moments = {}
bkm_spot_series = {}
_bkm_presupuesto = {"usadas": 0.0}


def bkm_fechas_pendientes(ticker):
    """Fechas de muestreo cuyos datos aun no estan en la cache de disco (clave v3)."""
    return sum(
        1 for f in sample_dates_bkm
        if pc.cache_get(bkm_clave_historia(
            ticker, f, target_dte_polygon, polygon_dte_tol, bkm_moneyness_lo, bkm_moneyness_hi,
            polygon_dte_min)) is None
    )


def _ventana_spot_bkm():
    """Lookback del MFIS mas un mes de colchon. `end` es exclusivo para yfinance."""
    start_sk = (hoy_ts - relativedelta(months=bkm_lookback_months + 1)).strftime("%Y-%m-%d")
    end_sk = hoy_ts.strftime("%Y-%m-%d")
    return start_sk, end_sk


def _precargar_spots_bkm(tickers):
    """Una descarga para todos los tickers que aun necesitan historia.

    Los hilos solo leen `bkm_spot_series`. Lo que el bloque no trae se
    reintenta en serie dentro de get_spot_history, antes del pool.
    """
    faltan = []
    for ticker in tickers:
        if ticker in bkm_spot_series:
            continue
        if bkm_fechas_pendientes(ticker) <= 0:
            continue
        faltan.append(ticker)
    if not faltan:
        return
    start_sk, end_sk = _ventana_spot_bkm()
    print(f"   Precios spot sin ajustar de {len(faltan)} ticker(s), una descarga "
          f"({start_sk} a {end_sk})...")
    paquete = md.get_spot_history(faltan, start_sk, end_sk)
    bkm_spot_series.update(paquete["series"])
    for ticker in paquete["missing"]:
        bkm_spot_series[ticker] = None
    if paquete["recovered"]:
        print(f"   Recuperados en reintento secuencial ({len(paquete['recovered'])}): "
              f"{', '.join(paquete['recovered'])}")
    print(f"   Sin precio historico tras reintentos: {len(paquete['missing'])}")
    if paquete["missing"]:
        print("   Tickers sin spot: " + ", ".join(paquete["missing"]))


def _spot_series_bkm(ticker):
    """Cierre sin ajustar ya descargado. No llama a yfinance."""
    return md.spot_series_for(bkm_spot_series, ticker)


def _fila_bkm(ticker, mom, decision, motivo, z=np.nan):
    mom = mom or {}
    return dict(symbol=ticker, decision=decision, motivo=motivo, z=z, dte=mom.get("dte", np.nan))


def _momento_actual_bkm(ticker):
    bkm_current_moments[ticker] = bkm_get_current_moments(
        ticker, target_dte_polygon, polygon_dte_tol, rf_rate)


def _asegurar_momentos_actuales(tickers):
    """Cadena de hoy solo para tickers de EE. UU. que aun no se consultaron.

    El snapshot no se cachea. Cuesta 2 llamadas (call y put) y se descuenta
    del mismo presupuesto que la historia.
    """
    nuevos_us = [t for t in tickers if is_us_ticker(t) and t not in bkm_current_moments]
    for t in tickers:
        if not is_us_ticker(t) and t not in bkm_current_moments:
            bkm_current_moments[t] = dict(
                mfiv=np.nan, mfis=np.nan, mfik=np.nan, mu=np.nan, ok=False,
                spot=np.nan, dte=np.nan, motivo="sin_opciones_us", transitorio=False)
    if not nuevos_us:
        return
    print(f"   Momento BKM actual de {len(nuevos_us)} ticker(s) de EE. UU. "
          f"({bkm_max_workers} en paralelo)...")
    with ThreadPoolExecutor(max_workers=bkm_max_workers) as executor:
        list(executor.map(_momento_actual_bkm, nuevos_us))
    _bkm_presupuesto["usadas"] += 2 * len(nuevos_us)


def _rank_bkm(ticker):
    mom = bkm_current_moments.get(ticker) or {}
    us = is_us_ticker(ticker)
    mfis_ok = us and bool(mom.get("ok")) and np.isfinite(mom.get("mfis", np.nan))
    return {
        "ticker": ticker,
        "us": us,
        "mfis_ok": mfis_ok,
        "n_pending": bkm_fechas_pendientes(ticker) if mfis_ok else 0,
        "motivo": None if mfis_ok else (mom.get("motivo") or "sin_mfis_actual"),
    }


def evaluar_historia_bkm(ticker, max_fechas_nuevas=None, solo_cache=False):
    mom_actual = bkm_current_moments[ticker]

    def _fila(decision, motivo, z=np.nan):
        return _fila_bkm(ticker, mom_actual, decision, motivo, z)

    spot_series_tk = None
    if bkm_fechas_pendientes(ticker) > 0:
        spot_series_tk = _spot_series_bkm(ticker)
        if spot_series_tk is None and not solo_cache:
            return _fila("mantener", "sin_precio_historico")

    hist_mfis = bkm_reconstruct_mfis_history(
        ticker, spot_series_tk, sample_dates_bkm, target_dte_polygon, polygon_dte_tol,
        bkm_moneyness_lo, bkm_moneyness_hi, rf_rate,
        min_validos=None if solo_cache else bkm_hist_min_valid,
        max_fechas_nuevas=max_fechas_nuevas,
    )
    if solo_cache:
        return _fila("no_procesado", "historia_no_procesada_presupuesto")

    hist_mfis_validos = hist_mfis[~np.isnan(hist_mfis)]
    if len(hist_mfis_validos) < bkm_hist_min_valid:
        return _fila("mantener", "muestra_insuficiente")

    media_hist = np.mean(hist_mfis_validos)
    sd_hist = np.std(hist_mfis_validos, ddof=1)
    if sd_hist <= 0 or np.isnan(sd_hist):
        return _fila("mantener", "sd_hist_invalida")

    dte_now = mom_actual.get("dte", np.nan)
    mfis_now = rk.scale_bkm_moments(
        mom_actual["mfiv"], mom_actual["mfis"],
        mom_actual["mfik"] if np.isfinite(mom_actual.get("mfik", np.nan)) else 3.0,
        float(dte_now), float(target_dte_polygon))["mfis"]
    z = (mfis_now - media_hist) / sd_hist
    decision, motivo = qm.mfis_tail_decision(z, bkm_z_threshold, bkm_tail_mode)
    return _fila(decision, motivo, z)


def _plan_ronda_bkm(tickers):
    ranked = [_rank_bkm(t) for t in tickers]
    plan = qm.plan_bkm_history_budget(
        ranked,
        contracts_per_date=bkm_hist_contracts_estimate,
        calls_per_min=pc.CALLS_PER_MIN,
        max_minutes=bkm_hist_max_minutes,
        spent_calls=_bkm_presupuesto["usadas"],
    )
    _bkm_presupuesto["usadas"] += plan["llamadas"]
    return plan


print(f"   Cola MFIS: {bkm_tail_mode} | umbral |z|={bkm_z_threshold:.2f} "
      f"(upper=demanda de calls, lower=demanda de puts)")
print(f"   Cache historica clave v3 en {pc.CACHE_DIR}")
print(f"   Presupuesto: {bkm_hist_max_minutes:g} min"
      + (f" a {pc.CALLS_PER_MIN:g} llamadas/min" if pc.CALLS_PER_MIN else " (sin tope de llamadas)")
      + f" | ~{bkm_hist_contracts_estimate} contratos/fecha | {bkm_max_workers} hilos")

full_set = list(ticker_candidates)
resultados_log = []
i_reponer = 0
usados_reponer_bkm = set()
por_evaluar = list(ticker_candidates)
ronda_bkm = 1
t0_bkm = time.perf_counter()

while por_evaluar:
    print(f"   [Ronda {ronda_bkm}] {len(por_evaluar)} activo(s) en el orden de candidatos...")
    _asegurar_momentos_actuales(por_evaluar)
    plan = _plan_ronda_bkm(por_evaluar)
    n_pend = sum(_rank_bkm(t)["n_pending"] for t in plan["procesar"])
    print(f"      EE. UU. con MFIS finito: {plan['n_us_mfis']} | "
          f"historia completa: {len(plan['procesar'])} | "
          f"sin presupuesto: {len(plan['omitidos'])} | "
          f"fechas pendientes de los que entran: {n_pend} | "
          f"llamadas de historia de esta ronda: ~{plan['llamadas']}")

    for info in plan["fuera_de_historia"]:
        resultados_log.append(_fila_bkm(
            info["ticker"], bkm_current_moments.get(info["ticker"]), "mantener", info["motivo"]))
    calentar = plan.get("calentar") or {}
    for info in plan["omitidos"]:
        if info["ticker"] == calentar.get("ticker"):
            continue
        resultados_log.append(_fila_bkm(
            info["ticker"], bkm_current_moments.get(info["ticker"]),
            "no_procesado", info["motivo"]))

    resultados = []
    a_precargar = list(plan["procesar"])
    if calentar:
        a_precargar.append(calentar["ticker"])
    _precargar_spots_bkm(a_precargar)
    if plan["procesar"]:
        with ThreadPoolExecutor(max_workers=bkm_max_workers) as executor:
            for k, r in enumerate(executor.map(evaluar_historia_bkm, plan["procesar"]), start=1):
                resultados.append(r)
                if k % 10 == 0 or k == len(plan["procesar"]):
                    print(f"      ... {k}/{len(plan['procesar'])}")
    if calentar:
        print(f"      Cache tibia: {calentar['n_fechas']} fecha(s) de {calentar['ticker']} "
              f"(no alcanza para el z-score; queda como no procesado)")
        resultados.append(evaluar_historia_bkm(
            calentar["ticker"], max_fechas_nuevas=calentar["n_fechas"], solo_cache=True))

    resultados_log.extend(resultados)
    descartados = [r for r in resultados if r["decision"] == "descartar"]
    if not descartados:
        break

    reemplazos_nuevos = []
    for d in descartados:
        print(f"   Descartado por MFIS anomalo: {d['symbol']} (z={d['z']:.2f})")
        full_set = [s for s in full_set if s != d["symbol"]]

        actuales_bkm = full_set + reemplazos_nuevos
        ocupados_bkm = usados_reponer_bkm | set(actuales_bkm)
        reemplazo = None
        if qm.contar_etfs(actuales_bkm, etf_group_set) < n_etf_needed:
            reemplazo = qm.siguiente_reposicion(
                reponer_pool_bkm_etf, ocupados_bkm, etf_group_set, solo_etf=True)
            if reemplazo is not None:
                print(f"   Reponiendo con: {reemplazo} (ETF para el piso de la banda)")
        if reemplazo is None and len(actuales_bkm) < bkm_min_survivors:
            reemplazo = qm.siguiente_reposicion(reponer_pool_bkm, ocupados_bkm)
            if reemplazo is not None:
                print(f"   Reponiendo con: {reemplazo} (pool de vol. reciente validado)")
        if reemplazo is not None:
            usados_reponer_bkm.add(reemplazo)
            i_reponer = len(usados_reponer_bkm)
            reemplazos_nuevos.append(reemplazo)

    if not reemplazos_nuevos:
        break
    full_set = list(dict.fromkeys(full_set + reemplazos_nuevos))
    por_evaluar = list(dict.fromkeys(reemplazos_nuevos))
    ronda_bkm += 1

_elapsed_bkm = time.perf_counter() - t0_bkm
bkm_log_df = pd.DataFrame(resultados_log)
n_descartados_bkm = (bkm_log_df["decision"] == "descartar").sum() if len(bkm_log_df) else 0
n_sin_presupuesto = (bkm_log_df["decision"] == "no_procesado").sum() if len(bkm_log_df) else 0
n_con_z = int(np.isfinite(pd.to_numeric(bkm_log_df["z"], errors="coerce")).sum()) if len(bkm_log_df) else 0
print(f"\n   Procesados con z-score: {n_con_z} | No procesados por presupuesto: {n_sin_presupuesto} | "
      f"Descartados por MFIS: {n_descartados_bkm} | Repuestos: {i_reponer} | "
      f"Tiempo real: {_elapsed_bkm:.1f} s | clave v3")
if len(bkm_log_df):
    print("\n   COBERTURA BKM POR TICKER (A-1)")
    conteo = bkm_log_df["motivo"].fillna("(sin motivo)").value_counts()
    for motivo, n in conteo.items():
        print(f"      {n:4d}  {motivo}")
    cols_bkm = [c for c in ("symbol", "decision", "motivo", "dte", "z") if c in bkm_log_df.columns]
    print(bkm_log_df[cols_bkm].to_string(index=False))

if len(full_set) < bkm_min_survivors:
    print(f"   Advertencia: solo {len(full_set)} tickers tras filtro BKM "
          f"(piso deseado: {bkm_min_survivors}) - pool de reposicion agotado")

ticker_candidates = full_set
print(f"\nConjunto FINAL tras filtro BKM (MFIS): {len(ticker_candidates)} tickers\n")

for tk in ticker_candidates:
    if tk not in bkm_current_moments or not bkm_current_moments[tk]["ok"]:
        bkm_current_moments[tk] = bkm_get_current_moments(tk, target_dte_polygon, polygon_dte_tol, rf_rate)

# ==============================================================================
# CONSTRUCCION DE MATRIZ DE RETORNOS
# ==============================================================================
df_wide = (
    df_prices[df_prices["symbol"].isin(ticker_candidates)]
    .pivot_table(index="date", columns="symbol", values="monthly_return")
    .sort_index()
)
df_wide, dropped_short = qm.columns_with_min_obs(df_wide, min_observations)
if dropped_short:
    print(f"   Activos fuera del panel por menos de {min_observations} meses: {', '.join(map(str, dropped_short))}")

dates = df_wide.index
ticker_candidates = list(df_wide.columns)
df_xts = df_wide.copy()
n_por_ticker = df_xts.notna().sum()
print(f"Matriz de retornos: {df_xts.shape[0]} fechas x {df_xts.shape[1]} activos | "
      f"historia por ticker {int(n_por_ticker.min()) if len(n_por_ticker) else 0}-"
      f"{int(n_por_ticker.max()) if len(n_por_ticker) else 0} meses | "
      f"interseccion {len(df_xts.dropna())} meses (no se usa para la media)")

# ==============================================================================
# MEDIA
# ==============================================================================
assets = ticker_candidates
# El mismo mu de la seleccion (historica encogida hacia FF3). Un activo fuera de
# combined_stats cae a su media historica del panel.
mu_hist_panel = df_xts[assets].mean()
mu = (combined_stats.set_index("symbol")["adjusted_return"].reindex(assets)
      .fillna(mu_hist_panel)).values
mu = np.where(np.isfinite(mu), mu, 0.0)
n_assets = len(assets)
_w_sel = combined_stats.set_index("symbol")["mu_weight_hist"].reindex(assets)
print(f"   mu del optimizador: historica encogida hacia FF3 (k={mu_shrink_k:g}) | "
      f"peso medio de la historica en los finalistas: {_w_sel.mean():.2f}")

# ==============================================================================
# MATRIZ DE COVARIANZA: SHRINKAGE IMPLIED (BKM) + HISTORICA
# ==============================================================================
iv_rank_low = 0.20
iv_rank_high = 0.80
alpha_min = 0.20
alpha_max = 0.80
iv_cap_multiplier = iv_outlier_multiplier

print("\nEstimando covarianza robusta: Shrinkage MFIV (BKM) + Historica...")
print(f"   Tenor objetivo: {target_dte_polygon} dias (consistente con horizonte de inversion, "
      f"tope universal={options_dte_cap_days}d) | Cap IV: {iv_cap_multiplier:.1f}x vol historica")
print("   La vol anual de MFIV usa el DTE real del vencimiento elegido, no target_dte/365. "
      "T_bkm queda solo para el camino SVIX.")

T_bkm = target_dte_polygon / 365

iv_assets_implied = {a: np.nan for a in assets}
for a in assets:
    mom_a = bkm_current_moments.get(a)
    if mom_a is not None and mom_a.get("ok") and mom_a.get("mfiv", np.nan) > 0:
        vol_hist_a = df_prices.loc[df_prices["symbol"] == a, "monthly_return"].std() * math.sqrt(12)
        vol_mfiv_annual_a = qm.mfiv_annual_vol(mom_a["mfiv"], mom_a.get("dte", target_dte_polygon))
        iv_cap_a = vol_hist_a * iv_cap_multiplier
        if np.isfinite(iv_cap_a) and vol_mfiv_annual_a <= iv_cap_a:
            iv_assets_implied[a] = vol_mfiv_annual_a

n_iv_ok = sum(1 for v in iv_assets_implied.values() if not pd.isna(v))
n_iv_na = len(assets) - n_iv_ok
print(f"   MFIV (BKM) validas: {n_iv_ok} | Sin datos (fallback historico): {n_iv_na}")

sd_hist_annual = df_xts[assets].std().values * math.sqrt(12)
iv_final = np.array([iv_assets_implied[a] if not pd.isna(iv_assets_implied[a]) else sd_hist_annual[i]
                      for i, a in enumerate(assets)])

# ==============================================================================
# CORRECCION Q -> P: LA MFIV INCLUYE LA PRIMA DE RIESGO DE VARIANZA
# ==============================================================================
iv_final_q = iv_final.copy()
if use_q_to_p_vol:
    iv_final, vrp_ratio = rk.q_to_p_vol(
        iv_final_q, sd_hist_annual,
        ratio_bounds=vrp_ratio_bounds, fallback_ratio=vrp_fallback_ratio)
    print("   CORRECCION Q -> P (prima de riesgo de varianza):")
    print(f"      ratio sigma_P/sigma_Q: min={vrp_ratio.min():.3f} | "
          f"mediana={np.median(vrp_ratio):.3f} | max={vrp_ratio.max():.3f}")
    print(f"      vol media: Q={np.nanmean(iv_final_q) * 100:.1f}% -> "
          f"P={np.nanmean(iv_final) * 100:.1f}%")
else:
    print("   ADVERTENCIA use_q_to_p_vol=False - se optimiza con vol bajo medida Q")

iv_final_dict = dict(zip(assets, iv_final))

print(f"   IV final - Min: {iv_final.min() * 100:.1f}% | Mediana: {np.median(iv_final) * 100:.1f}% | "
      f"Max: {iv_final.max() * 100:.1f}%")

mom_spy = bkm_get_current_moments("SPY", target_dte_polygon, polygon_dte_tol, rf_rate)
if mom_spy["ok"] and mom_spy["mfiv"] > 0:
    iv_spy_implied = qm.mfiv_annual_vol(mom_spy["mfiv"], mom_spy.get("dte", target_dte_polygon))
else:
    print("   Sin MFIV de mercado para SPY - usando vol historica mensual")
    iv_spy_implied = benchmark_prices["benchmark_return"].std() * math.sqrt(12)


def get_iv_rank(ticker, iv_current):
    try:
        hist_ret = df_prices.loc[df_prices["symbol"] == ticker, "monthly_return"].values
        if len(hist_ret) < 12:
            return 0.5
        n_roll = 3
        vol_history = []
        for i in range(n_roll - 1, len(hist_ret)):
            window = hist_ret[i - n_roll + 1: i + 1]
            vol_history.append(np.std(window, ddof=1) * math.sqrt(12))
        vol_history = np.array(vol_history)
        vol_history = vol_history[np.isfinite(vol_history) & (vol_history > 0)]
        if len(vol_history) < 6:
            return 0.5
        return float(np.mean(vol_history <= iv_current))
    except Exception:
        return 0.5


print("   Calculando IV Percentile Rank...")
iv_ranks = {t: get_iv_rank(t, iv_final_dict[t]) for t in assets}

has_iv_real = np.array([not pd.isna(iv_assets_implied[a]) for a in assets])

alpha_per_asset = np.zeros(n_assets)
for i, t in enumerate(assets):
    rank = iv_ranks[t]
    if not has_iv_real[i]:
        alpha_per_asset[i] = alpha_min
        continue
    if iv_rank_low <= rank <= iv_rank_high:
        center_dist = 1 - 2 * abs(rank - 0.5)
        alpha_per_asset[i] = alpha_min + (alpha_max - alpha_min) * center_dist
    else:
        alpha_per_asset[i] = alpha_min

alpha_global = np.nanmean(alpha_per_asset)
alpha_global = max(alpha_min, min(alpha_max, alpha_global))

n_alpha_full = int((alpha_per_asset > alpha_min).sum())
n_alpha_min = int((alpha_per_asset <= alpha_min).sum())
print(f"   IV Rank - Min: {min(iv_ranks.values()):.2f} | Mediana: {np.median(list(iv_ranks.values())):.2f} | "
      f"Max: {max(iv_ranks.values()):.2f}")
print(f"   Alpha por activo - Pleno (>{alpha_min:.2f}): {n_alpha_full} | Minimo ({alpha_min:.2f}): "
      f"{n_alpha_min} (sin MFIV real o MFIV extrema)")
print(f"   Alpha shrinkage global (promedio): {alpha_global:.3f} ({alpha_global * 100:.0f}% implied / "
      f"{(1 - alpha_global) * 100:.0f}% historica)")

# ==============================================================================
# COVARIANZA HISTORICA ANUALIZADA
# ==============================================================================
Sigma_hist = None
cov_label = "mensual por pares"
df_daily_for_mdd = None
if use_daily_cov:
    print("\n   Descargando retornos DIARIOS de los finalistas para la covarianza...")
    try:
        fx_prices_daily = download_fx_prices(start_date, end_date, period="1d")
        nombres_diarios = list(dict.fromkeys(list(assets) + ["SPY"]))
        df_daily = download_period_returns(nombres_diarios, start_date, end_date,
                                           period="1d", fx_prices=fx_prices_daily)
        df_daily_for_mdd = df_daily
        price_wide = (df_daily.pivot_table(index="date", columns="symbol", values="adjusted")
                      .sort_index())
        aligned_px, align_info = qm.align_daily_panel(
            price_wide, assets, spy_col="SPY", max_ffill=2, min_coverage=0.80)
        print(f"   Alineacion diaria (ffill<=2, calendario={align_info['calendar']}): "
              f"{align_info['n_rows']} dias, rellenos={int(align_info['n_filled'].sum())}, "
              f"baja cobertura={align_info['dropped_low_coverage'] or 'ninguno'}")
        daily_names = list(align_info["kept"])
        if len(aligned_px) >= 2 and aligned_px.shape[1] >= 2:
            daily_wide = aligned_px.pct_change().iloc[1:].dropna(how="any")
        else:
            daily_wide = aligned_px.iloc[0:0]
        print(f"   Retornos diarios alineados: {daily_wide.shape[0]} dias x {daily_wide.shape[1]} activos")

        if daily_wide.shape[1] >= 2 and len(daily_wide) >= 120:
            Sigma_daily_df, cov_info = rk.cov_ewma_shrunk(
                daily_wide, halflife=cov_halflife_days, scale=252.0,
                shrink=use_lw_shrinkage)
            if set(daily_names) == set(assets):
                Sigma_hist = np.asarray(
                    Sigma_daily_df.reindex(index=assets, columns=assets), dtype=float)
                cov_label = "diaria EWMA+LW"
                print("   COVARIANZA (EWMA + Ledoit-Wolf, base diaria, calendario SPY):")
            else:
                Sigma_pair, _ = qm.covariance_min_history(df_xts[assets], min_observations)
                mensual = pd.DataFrame(
                    np.asarray(rk.nearest_psd(Sigma_pair, eps_rel=1e-8), dtype=float) * returns_per_year,
                    index=list(assets), columns=list(assets))
                cosida = qm.stitch_covariance(assets, Sigma_daily_df, daily_names, mensual)
                Sigma_hist = np.asarray(rk.nearest_psd(cosida, eps_rel=1e-8), dtype=float)
                cov_label = ("mixta: diaria EWMA+LW en la submatriz larga, "
                             "mensual por pares en el resto")
                print("   COVARIANZA MIXTA: la historia corta no descarta el EWMA diario.")
                print(f"      fuera de la diaria: {align_info['dropped_low_coverage']}")
            vol_daily_based = np.sqrt(np.clip(np.diag(np.asarray(Sigma_daily_df, dtype=float)), 0, None))
            en_diaria = [a for a in assets if a in daily_names]
            vol_monthly_based = df_xts[en_diaria].std().values * math.sqrt(12)
            print(f"      obs diarias: {cov_info['n_obs']} | t_eff (Kish): {cov_info['t_eff']:.1f} "
                  f"| delta shrinkage: {cov_info['delta']:.3f}")
            print(f"      vol anual media (nombres con diaria): mensual={vol_monthly_based.mean() * 100:.1f}% -> "
                  f"diaria+EWMA={vol_daily_based.mean() * 100:.1f}%")
        else:
            print(f"   ADVERTENCIA Cobertura diaria insuficiente "
                  f"({daily_wide.shape[1]}/{len(assets)} activos, {len(daily_wide)} dias)")
    except Exception as e:
        print(f"   ADVERTENCIA Fallo la descarga diaria ({e})")

if Sigma_hist is None:
    Sigma_pair, _ = qm.covariance_min_history(df_xts[assets], min_observations)
    Sigma_hist = np.asarray(rk.nearest_psd(Sigma_pair, eps_rel=1e-8), dtype=float) * returns_per_year
    cov_label = "mensual por pares"
    print("   COVARIANZA: muestral mensual por pares, anualizada (fallback; cada serie usa su historia)")

# ==============================================================================
# CORRELACION IMPLICITA GLOBAL VIA DISPERSION DE SPY
# ==============================================================================
has_iv_disp = {a for a, v in iv_assets_implied.items() if v is not None and np.isfinite(v)}
w_disp_s, disp_info = qm.dispersion_weights(assets, has_iv_disp, sp500_components, sp500_caps)
w_disp = w_disp_s.to_numpy(dtype=float)
print(f"   Cesta de dispersion (M-10): {disp_info['mode']} | {disp_info['n']} componentes de SPY con MFIV")
if disp_info["mode"] == "equal":
    print("   Falta capitalizacion para "
          + ", ".join(map(str, disp_info["missing_caps"][:8]))
          + ": la cesta queda equiponderada.")
elif disp_info["mode"] == "insuficiente":
    print("   Cesta con menos de 2 nombres: se usara la correlacion realizada.")
elif disp_info["n"] < n_assets:
    print(f"   Quedan fuera ETFs, internacionales y nombres sin MFIV "
          f"({n_assets - disp_info['n']} de {n_assets}).")
_cap_share = disp_info.get("cap_share", float("nan"))
_txt_share = f"{_cap_share:.1%}" if np.isfinite(_cap_share) else "n/d"
print(f"   Cobertura de la cesta: cap_share={_txt_share} de la cap conocida | "
      f"n_caps={disp_info.get('n_caps_conocidas', 0)}")
cesta_ok = qm.dispersion_usable(disp_info, dispersion_min_cap_share, dispersion_min_known_caps)
if not cesta_ok:
    print(f"   Cobertura bajo el minimo ({dispersion_min_cap_share:.0%} y "
          f"{dispersion_min_known_caps} caps): se usa la correlacion realizada.")
sigma_i = iv_final
sigma_i_q = iv_final_q

var_spy_impl = iv_spy_implied ** 2
weighted_var_i = np.sum(w_disp ** 2 * sigma_i_q ** 2)
sigma_total_sq = (np.sum(w_disp * sigma_i_q)) ** 2

d_hist = np.sqrt(np.clip(np.diag(Sigma_hist), 1e-300, None))
R_hist_full = Sigma_hist / np.outer(d_hist, d_hist)
np.fill_diagonal(R_hist_full, 1.0)

tril_idx = np.tril_indices(n_assets, k=-1)
rho_realized_avg = float(np.nanmean(R_hist_full[tril_idx]))

if cesta_ok and sigma_total_sq > weighted_var_i and sigma_total_sq > 0:
    rho_implied_q = (var_spy_impl - weighted_var_i) / (sigma_total_sq - weighted_var_i)
    rho_implied_q = max(-0.999, min(0.999, rho_implied_q))
    print(f"   Correlacion promedio implicita Q (dispersion SPY): {rho_implied_q:.4f}")

    if use_q_to_p_correlation:
        rho_implied_avg, crp_ratio = rk.q_to_p_correlation(
            rho_implied_q, rho_realized_avg,
            ratio_bounds=crp_ratio_bounds, fallback_ratio=crp_fallback_ratio)
        print(f"   Correlacion realizada ({cov_label}):        {rho_realized_avg:.4f}")
        rho_bruto = rho_implied_avg
        rho_implied_avg = qm.clip_implied_correlation(rho_implied_avg)
        print(f"   Correlacion promedio P (post-correccion):   {rho_implied_avg:.4f} "
              f"(ratio={crp_ratio:.3f})")
        if rho_implied_avg != rho_bruto:
            print(f"   Correlacion P recortada a >= 0 (venia de {rho_bruto:.4f})")
    else:
        rho_implied_avg = qm.clip_implied_correlation(rho_implied_q)
        print("   ADVERTENCIA use_q_to_p_correlation=False - correlacion bajo medida Q, piso 0")
else:
    rho_implied_avg = qm.clip_implied_correlation(rho_realized_avg)
    print(f"   Correlacion promedio (fallback a la realizada, piso 0): {rho_implied_avg:.4f}")

rho_hist_avg_ref = np.nanmean(np.abs(R_hist_full[tril_idx]))

# ==============================================================================
# CORRELACION IMPLICITA SECTORIAL (ETFs SECTORIALES SPDR + VOX), VIA MFIV (BKM)
# ==============================================================================
print("   Calculando correlacion implicita por sector (MFIV de ETFs sectoriales)...")

rho_sector_lookup = {etf: np.nan for etf in etf_sectoriales}
sector_etf_iv = {etf: np.nan for etf in etf_sectoriales}
for etf in etf_sectoriales:
    mom_etf = bkm_get_current_moments(etf, target_dte_polygon, polygon_dte_tol, rf_rate)
    if mom_etf["ok"] and mom_etf["mfiv"] > 0:
        sector_etf_iv[etf] = qm.mfiv_annual_vol(mom_etf["mfiv"], mom_etf.get("dte", target_dte_polygon))

for etf in etf_sectoriales:
    stocks_sector = [t for t in assets if sector_map.get(t) == etf]
    if pd.isna(sector_etf_iv.get(etf)):
        continue
    if not qm.sector_implied_ready(len(stocks_sector), sector_implied_min_names):
        print(f"      {etf:<5}: {len(stocks_sector)} acciones, bajo el minimo "
              f"{sector_implied_min_names}; se usa la correlacion global")
        continue

    idxs = [assets.index(s) for s in stocks_sector]
    sigma_sector = iv_final_q[idxs]
    var_etf_impl = sector_etf_iv[etf] ** 2
    w_disp_sector = np.repeat(1 / len(stocks_sector), len(stocks_sector))
    weighted_var_s = np.sum(w_disp_sector ** 2 * sigma_sector ** 2)
    sigma_total_s = (np.sum(w_disp_sector * sigma_sector)) ** 2

    if sigma_total_s > weighted_var_s and sigma_total_s > 0:
        rho_sec_q = (var_etf_impl - weighted_var_s) / (sigma_total_s - weighted_var_s)
        rho_sec_q = max(-0.999, min(0.999, rho_sec_q))

        sub = R_hist_full[np.ix_(idxs, idxs)]
        m = len(idxs)
        rho_sec_realized = float(np.nanmean(sub[np.tril_indices(m, k=-1)]))
        if use_q_to_p_correlation:
            rho_sec, _ = rk.q_to_p_correlation(
                rho_sec_q, rho_sec_realized,
                ratio_bounds=crp_ratio_bounds, fallback_ratio=crp_fallback_ratio)
        else:
            rho_sec = rho_sec_q

        rho_sec_bruto = rho_sec
        rho_sec = qm.clip_implied_correlation(rho_sec)
        rho_sector_lookup[etf] = rho_sec
        _recorte = "" if rho_sec == rho_sec_bruto else f", recortada desde {rho_sec_bruto:.4f}"
        print(f"      {etf:<5}: rho Q = {rho_sec_q:.4f} -> rho P = {rho_sec:.4f} "
              f"(realizada {rho_sec_realized:.4f}, {len(stocks_sector)} acciones{_recorte})")

n_sectores_ok = sum(1 for v in rho_sector_lookup.values() if not pd.isna(v))
print(f"   Correlacion sectorial calculada para {n_sectores_ok} de {len(etf_sectoriales)} sectores")

R_implied = np.eye(n_assets)
for i in range(n_assets):
    for j in range(n_assets):
        if i == j:
            continue
        rho_hist_ij = R_hist_full[i, j]
        if pd.isna(rho_hist_ij) or not np.isfinite(rho_hist_ij):
            rho_hist_ij = rho_implied_avg

        sector_i = sector_map.get(assets[i])
        sector_j = sector_map.get(assets[j])

        if sector_i is not None and sector_j is not None and sector_i == sector_j and not pd.isna(rho_sector_lookup.get(sector_i)):
            rho_ancla = rho_sector_lookup[sector_i]
        else:
            rho_ancla = rho_implied_avg

        scale_factor = (rho_hist_ij / rho_hist_avg_ref) if rho_hist_avg_ref > 0 else 1.0
        rho_ij_impl = max(-0.999, min(0.999, rho_ancla * scale_factor))
        R_implied[i, j] = rho_ij_impl

R_implied = (R_implied + R_implied.T) / 2
np.fill_diagonal(R_implied, 1.0)
eig_vals_R, eig_vecs_R = np.linalg.eigh(R_implied)
if np.any(eig_vals_R < 0):
    eig_vals_R = np.maximum(eig_vals_R, 1e-8)
    R_implied = eig_vecs_R @ np.diag(eig_vals_R) @ eig_vecs_R.T
    D_norm = np.diag(1 / np.sqrt(np.diag(R_implied)))
    R_implied = D_norm @ R_implied @ D_norm
    np.fill_diagonal(R_implied, 1.0)

D_implied = np.diag(sigma_i)
Sigma_impl = D_implied @ R_implied @ D_implied

Sigma_blend = np.zeros((n_assets, n_assets))
for i in range(n_assets):
    for j in range(n_assets):
        a_ij = (alpha_per_asset[i] + alpha_per_asset[j]) / 2
        Sigma_blend[i, j] = a_ij * Sigma_impl[i, j] + (1 - a_ij) * Sigma_hist[i, j]

cov_mat = Sigma_blend / 12

vol_impl_pct = np.sqrt(np.diag(Sigma_impl)) * 100
vol_hist_pct = np.sqrt(np.diag(Sigma_hist)) * 100
vol_blend_pct = np.sqrt(np.diag(Sigma_blend)) * 100

print("\n   Volatilidades anualizadas (promedio):")
print(f"      Implied (MFIV): {vol_impl_pct.mean():.1f}%")
print(f"      Historica:      {vol_hist_pct.mean():.1f}%")
print(f"      Blend:          {vol_blend_pct.mean():.1f}% (a_global={alpha_global:.2f})")

eig_vals = np.linalg.eigvalsh(cov_mat)
print(f"   Eigenvalue minimo (Sigma blend): {eig_vals.min():.6f}")
if not np.all(eig_vals >= -1e-8):
    print("   Sigma blend no es PSD - proyectando al cono PSD...")
    cov_mat = np.asarray(rk.nearest_psd(cov_mat, eps_rel=1e-8))

if np.any(~np.isfinite(cov_mat)):
    print("   Limpiando valores no finitos en cov_mat...")
    cov_mat = np.nan_to_num(cov_mat, nan=0.0, posinf=0.0, neginf=0.0)

print(f"   cov_mat blend construida: {cov_mat.shape[0]} x {cov_mat.shape[1]} activos")
print(f"   Rango MFIV anualizada (post-cap): {vol_impl_pct.min():.1f}% - {vol_impl_pct.max():.1f}%")
tril_R = R_implied[np.tril_indices(n_assets, k=-1)]
print(f"   Rango correlaciones implicitas (off-diagonal R_implied): {tril_R.min():.3f} - {tril_R.max():.3f}")

# ==============================================================================
# OPTIMIZACION CUADRATICA (quadprog)
# ==============================================================================
print(f"\nEjecutando optimizacion cuadratica (quadprog) con lambda={lambda_:.2f}...")

etf_commodity_assets = [i for i, a in enumerate(assets) if a in (etf_tickers + commodity_tickers)]
stock_assets = [i for i, a in enumerate(assets) if a not in (etf_tickers + commodity_tickers)]

etf_excluded_from_portfolio = set(etf_tickers) - set(commodity_tickers)
excluded_etf_assets = [] if include_etfs_in_portfolio else [
    i for i, a in enumerate(assets) if a in etf_excluded_from_portfolio]
excluded_etf_set = set(excluded_etf_assets)
if not include_etfs_in_portfolio:
    n_eligible = n_assets - len(excluded_etf_assets)
    print("   include_etfs_in_portfolio = False: el portafolio resultante solo tendra acciones y commodities")
    print(f"   ETFs con peso fijado en 0 ({len(excluded_etf_assets)}): "
          f"{', '.join(assets[i] for i in excluded_etf_assets) if excluded_etf_assets else 'ninguno'}")
    print(f"   Activos elegibles para el portafolio: {n_eligible} de {n_assets}")
    if n_eligible * max_weight < 1 - 1e-9:
        raise RuntimeError(
            f"Error: con include_etfs_in_portfolio = False quedan {n_eligible} acciones/commodities "
            f"elegibles y max_weight = {max_weight:.2f} no alcanza el 100% del portafolio.\n"
            "   Amplia el pool de candidatos (n_pre_filter, n_filter_candidates) o sube max_weight."
        )

canada_assets = [i for i, a in enumerate(assets) if qm.region_de_ticker(a) == "Canada"]
europe_assets = [i for i, a in enumerate(assets) if qm.region_de_ticker(a) == "Europa"]
japan_assets = [i for i, a in enumerate(assets) if qm.region_de_ticker(a) == "Japon"]

geo_union = set(canada_assets) | set(europe_assets) | set(japan_assets)
print(f"   Grupos geograficos - CA: {len(canada_assets)} | EU: {len(europe_assets)} | "
      f"JP: {len(japan_assets)} | US/ETF: {n_assets - len(geo_union)}")

n = n_assets
Dmat = cov_mat + np.eye(n) * 1e-8

# ==============================================================================
# RETORNO ESPERADO EN EL VECTOR dvec
# ==============================================================================
# El colchon delta ya no multiplica a mu: premiaba la vol baja otra vez, fuera
# de lambda. La aversion al riesgo del QP queda solo en lambda * w'Sigma w.
delta_aligned = np.array([delta_named.get(a, np.nan) for a in assets])

mfis_aligned = np.array([bkm_current_moments.get(a, {}).get("mfis", np.nan) for a in assets])
mfik_aligned = np.array([bkm_current_moments.get(a, {}).get("mfik", np.nan) for a in assets])
mfis_aligned = np.where(np.isnan(mfis_aligned), 0.0, mfis_aligned)
mfik_aligned = np.where(np.isnan(mfik_aligned), 3.0, mfik_aligned)

mu_final = mu.copy()

# ==============================================================================
# RETORNO ESPERADO VIA SVIX (MARTIN-WAGNER) - EXPERIMENTAL, APAGADO
# ==============================================================================
if use_svix_expected_return:
    print("\n   AVISO use_svix_expected_return=True: la formula de Martin-Wagner")
    print("   implementada en risk_estimators.py NO ha sido verificada contra el")
    print("   paper ni validada empiricamente. No usar para asignar capital sin")
    print("   contrastarla primero.")
    svix2_assets = np.array([
        bkm_current_moments.get(a, {}).get("mfiv", np.nan) for a in assets])
    mom_spy_svix = bkm_current_moments.get("SPY") or mom_spy
    svix2_mkt = mom_spy_svix.get("mfiv", np.nan) if mom_spy_svix else np.nan

    if np.isfinite(svix2_mkt) and np.isfinite(svix2_assets).sum() >= 2:
        periodos_por_T = (T_bkm * 12.0)
        exc_annual, mw_info = rk.martin_wagner_excess_return(svix2_assets, svix2_mkt)
        mu_svix = rf_rate / 12.0 + exc_annual / max(periodos_por_T, 1e-6)
        mask_mw = np.isfinite(mu_svix)
        mu_final = np.where(
            mask_mw,
            svix_blend * mu_svix + (1 - svix_blend) * mu,
            mu)
        print(f"   SVIX aplicado a {int(mask_mw.sum())}/{n_assets} activos "
              f"(blend={svix_blend:.2f}) | {mw_info['warning']}")
    else:
        print("   Sin SVIX de mercado suficiente - se mantiene mu historico")

dvec = mu_final / lambda_

print("   Delta: solo filtro de elegibilidad, no multiplica a mu")
print("   Penalizacion de cola sobre mu: ELIMINADA (MFIS/MFIK son momentos Q sin calibrar)")

etf_band_active = include_etfs_in_portfolio and len(etf_commodity_assets) > 0 and len(stock_assets) > 0
etf_lo = max(0, pct_etf_deseado - pct_etf_tolerancia)
etf_hi = min(1, pct_etf_deseado + pct_etf_tolerancia)
etf_band_relaxed = False
if include_etfs_in_portfolio and not etf_band_active and etf_lo > 0:
    print(f"   ADVERTENCIA: banda de ETF {etf_lo * 100:.0f}%-{etf_hi * 100:.0f}% sin aplicar: "
          f"{len(etf_commodity_assets)} ETF y {len(stock_assets)} acciones en el optimizador")
geo_groups = {"Canada": canada_assets, "Europa": europe_assets, "Japon": japan_assets}


def armar_restricciones(etf_lo_, etf_hi_, verbose=True):
    """Columnas de quadprog: suma 1, 0 <= w <= max_weight, banda de ETF y regiones."""
    A_cols = [np.ones(n)]
    b_vals = [1.0]
    for i in range(n):
        v = np.zeros(n)
        v[i] = 1
        A_cols.append(v)
        b_vals.append(0.0)
    for i in range(n):
        v = np.zeros(n)
        v[i] = -1
        A_cols.append(v)
        b_vals.append(0.0 if i in excluded_etf_set else -max_weight)
    if etf_band_active:
        stk_lo = 1 - etf_hi_
        stk_hi = 1 - etf_lo_
        v_etf_lo = np.zeros(n); v_etf_lo[etf_commodity_assets] = 1
        v_etf_hi = np.zeros(n); v_etf_hi[etf_commodity_assets] = -1
        v_stk_lo = np.zeros(n); v_stk_lo[stock_assets] = 1
        v_stk_hi = np.zeros(n); v_stk_hi[stock_assets] = -1
        A_cols += [v_etf_lo, v_etf_hi, v_stk_lo, v_stk_hi]
        b_vals += [etf_lo_, -etf_hi_, stk_lo, -stk_hi]
        if verbose:
            print(f"   Restriccion ETFs: {etf_lo_ * 100:.0f}% - {etf_hi_ * 100:.0f}% del portafolio "
                  f"(objetivo {pct_etf_deseado * 100:.0f}% +/- {pct_etf_tolerancia * 100:.0f}%)")
    for region_name, idx_region in geo_groups.items():
        if len(idx_region) > 0:
            v_geo = np.zeros(n)
            v_geo[idx_region] = -1
            A_cols.append(v_geo)
            b_vals.append(-max_region_weight)
            if verbose:
                print(f"   Restriccion {region_name}: max {max_region_weight * 100:.0f}% del portafolio")
    return np.column_stack(A_cols), np.array(b_vals)


meq = 1
Amat, bvec = armar_restricciones(etf_lo, etf_hi)

# ------------------------------------------------------------------------------
# CHEQUEO DE FACTIBILIDAD ANTES DE quadprog
# ------------------------------------------------------------------------------
if not qm.restricciones_factibles(Amat, bvec, meq):
    n_etf_opt = len(etf_commodity_assets) if etf_band_active else 0
    n_acc_opt = n - len(excluded_etf_set) - n_etf_opt if etf_band_active else n - len(excluded_etf_set)
    razones = qm.diagnostico_banda_etf(n_etf_opt, n_acc_opt, max_weight,
                                       etf_lo if etf_band_active else 0.0,
                                       etf_hi if etf_band_active else 1.0)
    if not razones:
        razones = [f"la combinacion de max_weight {max_weight:.2f}, la banda de ETF y el tope regional "
                   f"{max_region_weight:.2f} no deja ninguna asignacion valida"]
    print("\n   ADVERTENCIA: las restricciones del optimizador no se pueden cumplir:")
    for r in razones:
        print(f"      - {r}")
    print(f"      ETF en el optimizador ({len(etf_commodity_assets)}): "
          f"{', '.join(assets[i] for i in etf_commodity_assets) or 'ninguno'}")
    if etf_band_active and etf_band_relax_if_infeasible:
        etf_lo_rel, etf_hi_rel = qm.relajar_banda_etf(n_etf_opt, n_acc_opt, max_weight, etf_lo, etf_hi)
        Amat_rel, bvec_rel = armar_restricciones(etf_lo_rel, etf_hi_rel, verbose=False)
        if qm.restricciones_factibles(Amat_rel, bvec_rel, meq):
            print(f"   Banda de ETF relajada (etf_band_relax_if_infeasible=True): "
                  f"{etf_lo * 100:.0f}%-{etf_hi * 100:.0f}% -> {etf_lo_rel * 100:.0f}%-{etf_hi_rel * 100:.0f}%. "
                  "Para cumplir la banda pedida hacen falta mas ETF en el pool o un max_weight mayor.\n")
            etf_lo, etf_hi = etf_lo_rel, etf_hi_rel
            Amat, bvec = Amat_rel, bvec_rel
            etf_band_relaxed = True
    if not etf_band_relaxed:
        raise RuntimeError(
            "Error: restricciones del optimizador infactibles ("
            + "; ".join(razones)
            + "). Amplia el pool (n_pre_filter, n_filter_candidates), sube max_weight o ajusta "
              "pct_etf_deseado / pct_etf_tolerancia"
            + ("" if etf_band_relax_if_infeasible else ", o activa etf_band_relax_if_infeasible")
            + ".")

try:
    sol = quadprog.solve_qp(Dmat, dvec, Amat, bvec, meq)
except Exception as e:
    print(f"  quadprog fallo ({e}) - reintentando con nugget mayor...")
    sol = quadprog.solve_qp(cov_mat + np.eye(n) * 1e-6, dvec, Amat, bvec, meq)

weights_opt = sol[0]
weights_opt = np.maximum(weights_opt, 0)
weights_opt[excluded_etf_assets] = 0.0
weights_opt = weights_opt / weights_opt.sum()
weights_opt = pd.Series(weights_opt, index=assets)

print("  Optimizacion completada")
print(f"  Activos con peso > 1%: {(weights_opt > 0.01).sum()}")
print(f"  Peso maximo: {weights_opt.max() * 100:.2f}% ({weights_opt.idxmax()})")
if etf_band_active:
    _peso_etf = float(weights_opt.iloc[etf_commodity_assets].sum())
    print(f"  Peso en ETF/commodities: {_peso_etf * 100:.2f}% (banda {etf_lo * 100:.0f}%-{etf_hi * 100:.0f}%"
          f"{', relajada desde la pedida' if etf_band_relaxed else ''})")

top_assets_idx = weights_opt.sort_values(ascending=False).head(min(10, n)).index.tolist()
print("\n  Top activos - retorno esperado y diagnosticos de opciones (delta = colchon del filtro):")
print(f"  {'Ticker':<8}  {'Peso%':>8}  {'mu%':>8}  {'delta':>8}  {'MFIS':>8}  {'MFIK':>8}  {'mu_final%':>10}")
print("  " + "-" * 68)
for t_i in top_assets_idx:
    i = assets.index(t_i)
    d_i = f"{delta_aligned[i]:.3f}" if not np.isnan(delta_aligned[i]) else "fallbk"
    print(f"  {t_i:<8}  {weights_opt[t_i] * 100:7.2f}%  {mu[i] * 100:7.3f}%  {d_i:>7}  "
          f"{mfis_aligned[i]:8.3f}  {mfik_aligned[i]:8.3f}  {mu_final[i] * 100:9.3f}%")

for region_name, idx_region in geo_groups.items():
    if len(idx_region) > 0:
        print(f"  Peso {region_name}: {weights_opt.iloc[idx_region].sum() * 100:.1f}%")

_intl_en_opt = [a for a in assets if a in _intl_set]
_intl_con_peso = [a for a in _intl_en_opt if weights_opt[a] > 1e-4]
print(f"  Internacionales en el universo: {_n_intl_universo} | "
      f"en la optimizacion: {len(_intl_en_opt)} | con peso > 0: {len(_intl_con_peso)}")
if _intl_con_peso:
    print("  " + ", ".join(f"{a} {weights_opt[a] * 100:.1f}%" for a in _intl_con_peso))
else:
    print("  Ningun internacional tiene peso. No hay piso de asignacion internacional.")

# ==============================================================================
# RESULTADOS
# ==============================================================================
w_vec = weights_opt.values
ret_opt = float(np.sum(w_vec * mu))
sd_opt = float(np.sqrt(w_vec @ cov_mat @ w_vec))
sharpe_opt = (ret_opt - rf_rate_period) / sd_opt
utility_opt = ret_opt - (lambda_ / 2) * (sd_opt ** 2)
_terms = qm.utility_terms(float(np.sum(w_vec * mu_final)), float(w_vec @ cov_mat @ w_vec), lambda_)
_ratio_pen = _terms["risk_term"] / _terms["mu_term"] if _terms["mu_term"] else np.nan
print("  Terminos en el optimo (mu que ve el optimizador, no el mu crudo del reporte):")
print(f"    mu'w = {_terms['mu_term']:.6f} | lambda/2 w'Sigma w = {_terms['risk_term']:.6f} "
      f"| penalizacion/retorno = {_ratio_pen:.3f}")
if lambda_annual is None and np.isfinite(_ratio_pen) and _ratio_pen < 0.05:
    print("    La penalizacion es pequena frente al retorno. lambda_annual (opt-in) la escala x12;")
    print("    el default no cambia. Ver el comentario de lambda_annual.")


def portfolio_returns_series(returns_df, weights_series):
    return qm.portfolio_returns_skipna(returns_df, weights_series)


portfolio_returns_full = portfolio_returns_series(df_xts[ticker_candidates], weights_opt)
var_parametric = ret_opt - norm.ppf(0.95) * sd_opt
q05 = portfolio_returns_full.quantile(0.05)
cvar_95 = portfolio_returns_full[portfolio_returns_full <= q05].mean()

# ==============================================================================
# VaR/CVaR PROSPECTIVO - CORNISH-FISHER SOBRE CO-MOMENTOS
# ==============================================================================
w_full = weights_opt.reindex(assets).fillna(0.0).values
mfis_w = np.array([bkm_current_moments.get(a, {}).get("mfis", np.nan) for a in assets])
mfik_w = np.array([bkm_current_moments.get(a, {}).get("mfik", np.nan) for a in assets])

panel_source_qu = df_xts[assets].dropna()
_obs_por_ticker = df_xts[assets].notna().sum()
print(f"   Panel conjunto de co-momentos: {len(panel_source_qu)} meses (interseccion). "
      f"Historia por ticker: min {_obs_por_ticker.min()} / mediana {_obs_por_ticker.median():.0f}. "
      "La media y la covarianza no usan esta interseccion.")

if len(panel_source_qu) >= panel_min_obs:
    Z_qu, _ = rk.standardized_panel(panel_source_qu)
    sd_prosp_qu = np.sqrt(np.clip(np.diag(cov_mat), 1e-16, None))
    panel_qu = rk.rescale_panel(Z_qu, panel_source_qu.mean().values, sd_prosp_qu)

    mom_qu = rk.portfolio_moments(w_full, panel_qu)
    port_skew = mom_qu["skew"]
    port_kurt_exc = mom_qu["exkurt"]
    port_sd_cf = sd_opt

    cf_qu = rk.var_cvar_cornish_fisher(
        ret_opt, port_sd_cf, port_skew, port_kurt_exc,
        confidence=cornish_fisher_confidence)
    var_cf = cf_qu["var"]
    cvar_cf = cf_qu["cvar"]

    mask_bkm_ok = np.isfinite(mfis_w) & np.isfinite(mfik_w)
    if mask_bkm_ok.sum() > 0 and w_full[mask_bkm_ok].sum() > 0:
        w_q = w_full[mask_bkm_ok] / w_full[mask_bkm_ok].sum()
        skew_naive_qu = float(np.sum(w_q * mfis_w[mask_bkm_ok]))
        kurt_naive_qu = float(np.sum(w_q * mfik_w[mask_bkm_ok])) - 3.0
        print("\n   MOMENTOS DEL PORTAFOLIO (co-momentos, medida P):")
        print(f"      asimetria:          {port_skew:+.4f}   (atajo Q anterior: {skew_naive_qu:+.4f})")
        print(f"      exceso de curtosis: {port_kurt_exc:+.4f}   (atajo Q anterior: {kurt_naive_qu:+.4f})")

    if not cf_qu["exact"]:
        print("   AVISO: la familia Cornish-Fisher no alcanza estos momentos; se usaron")
        print("   los alcanzables mas cercanos (Maillard, 2012).")
        print(f"   Referencia gaussiana -> VaR {cf_qu['var_gaussian'] * 100:.4f}% | "
              f"CVaR {cf_qu['cvar_gaussian'] * 100:.4f}%")
else:
    port_skew, port_kurt_exc = np.nan, np.nan
    var_cf, cvar_cf = np.nan, np.nan
    print(f"   Advertencia: solo {len(panel_source_qu)} observaciones (<{panel_min_obs}) "
          "para el panel - VaR/CVaR Cornish-Fisher = NaN")

benchmark_series = benchmark_prices.set_index("date")["benchmark_return"]
portfolio_returns_aligned = portfolio_returns_series(
    df_xts[ticker_candidates], weights_opt
).reindex(benchmark_series.index).dropna()
benchmark_aligned = benchmark_series.reindex(portfolio_returns_aligned.index)
tracking_error = (portfolio_returns_aligned - benchmark_aligned).std()
relative_returns = portfolio_returns_aligned - benchmark_aligned
relative_var = relative_returns.mean() - norm.ppf(0.95) * relative_returns.std()
_n_inter = int(df_xts[ticker_candidates].dropna().shape[0])
print(f"  Tracking error: {len(portfolio_returns_aligned)} meses alineados al benchmark "
      f"(interseccion completa de tickers: {_n_inter}; un faltante ya no borra el mes).")

pesos = (
    pd.DataFrame({"symbol": weights_opt.index, "weight": weights_opt.values})
    .query("weight > 0.01")
    .sort_values("weight", ascending=False)
    .reset_index(drop=True)
)

_ann_opt = qm.annualize_monthly(mu=ret_opt, sd=sd_opt)

downside_returns = portfolio_returns_full.values - rf_rate_monthly
downside_neg = downside_returns[downside_returns < 0]
downside_dev = np.sqrt(np.mean(downside_neg ** 2)) if len(downside_neg) else np.nan
sortino_opt = (ret_opt - rf_rate_monthly) / downside_dev

# ==============================================================================
# PORTAFOLIO FINAL
# ==============================================================================
print("\n" + "=" * 60)
print("PORTAFOLIO OPTIMO - PONDERACIONES FINALES")
print("=" * 60)
print(f"    Entrenado con: {min(target_years)}-{max(target_years)} (retornos mensuales)")
print(f"    Horizonte: {horizon_desc} | lambda = {lambda_:.2f}\n")

print(f"  {'Ticker':<8}  {'Peso':>8}")
print("  " + "-" * 50)
for _, row in pesos.iterrows():
    barra = "#" * round(row["weight"] * 100 / 2)
    print(f"  {row['symbol']:<8}  {row['weight'] * 100:6.2f}%  {barra}")
print("  " + "-" * 50)
print(f"  {'TOTAL':<8}  {pesos['weight'].sum() * 100:6.2f}%\n")
print(f"  Activos en portafolio: {len(pesos)}")
print(f"  Peso maximo: {pesos['weight'].max() * 100:.2f}% ({pesos.iloc[0]['symbol']})")
print(f"  Concentracion top 5: {pesos['weight'].head(5).sum() * 100:.2f}%")
print("=" * 60 + "\n")

print(f"\n=== METRICAS DEL PORTAFOLIO ({min(target_years)}-{max(target_years)}, base mensual) ===")
print(f"  Horizonte: {horizon_desc}")
print(f"  Lambda: {lambda_:.2f}")
print(f"  Retorno Esperado mensual: {ret_opt * 100:.4f}%")
print(f"  Volatilidad mensual:      {sd_opt * 100:.4f}%")
print(f"  Sharpe Ratio (mensual):   {sharpe_opt:.4f}")
print(f"  Sortino Ratio (mensual):  {sortino_opt:.4f}")
print(f"  Utilidad Cuadratica:      {utility_opt:.6f}")
print(f"  VaR (95%, Normal):        {var_parametric * 100:.4f}%")
print(f"  CVaR (95%, Historico):    {cvar_95 * 100:.4f}%")
print(f"  VaR Cornish-Fisher ({cornish_fisher_confidence * 100:.0f}%): {var_cf * 100:.4f}%")
print(f"  CVaR Cornish-Fisher ({cornish_fisher_confidence * 100:.0f}%): {cvar_cf * 100:.4f}%")
print(f"  Tracking Error:           {tracking_error * 100:.4f}%")
print(f"  Relative VaR (95%):      {relative_var * 100:.4f}%")

print(f"\n=== METRICAS ANUALIZADAS (retorno x{returns_per_year}, vol x sqrt({returns_per_year}); base {periodo_label}) ===")
print(f"  Retorno anual:     {_ann_opt['mu'] * 100:.2f}%")
print(f"  Volatilidad anual: {_ann_opt['sd'] * 100:.2f}%")

# ==============================================================================
# ATRIBUCION DE RIESGO POR GRIEGAS
# ==============================================================================
print("\n=== ATRIBUCION DE RIESGO POR GRIEGAS (BLACK-SCHOLES) ===")

griegas_df = pd.DataFrame({"symbol": assets, "weight": weights_opt.reindex(assets).values})
if len(polygon_market_df):
    griegas_df = griegas_df.merge(
        polygon_market_df[["symbol", "delta", "gamma", "vega", "theta", "ok"]], on="symbol", how="left"
    )
else:
    for col in ["delta", "gamma", "vega", "theta", "ok"]:
        griegas_df[col] = np.nan

delta_portfolio = np.nansum(weights_opt.reindex(assets).values * delta_aligned)
if delta_strike_mode == "otm":
    print(f"  Colchon delta OTM ponderado: {delta_portfolio:.4f}")
else:
    print(f"  Delta de portafolio (ponderado, incl. fallback BS): {delta_portfolio:.4f}")

peso_con_griegas = griegas_df.loc[griegas_df["gamma"].notna(), "weight"].sum()

if peso_con_griegas > 0:
    vega_portfolio = np.nansum(griegas_df["weight"] * griegas_df["vega"])
    gamma_portfolio = np.nansum(griegas_df["weight"] * griegas_df["gamma"])
    print(f"  Vega de portafolio:  {vega_portfolio:.4f}  (sobre {peso_con_griegas * 100:.1f}% del peso con datos de opciones)")
    print(f"  Gamma de portafolio: {gamma_portfolio:.6f} (sobre {peso_con_griegas * 100:.1f}% del peso con datos de opciones)")
else:
    print("  Sin cobertura suficiente de opciones para reportar Vega/Gamma agregados")

top_griegas = griegas_df[griegas_df["weight"] > 0.01].sort_values("weight", ascending=False).copy()
top_griegas["Peso"] = top_griegas["weight"].map(lambda x: f"{x * 100:.2f}%")
top_griegas["Delta"] = top_griegas["delta"].map(lambda x: "fallback" if pd.isna(x) else f"{x:.3f}")
top_griegas["Gamma"] = top_griegas["gamma"].map(lambda x: "-" if pd.isna(x) else f"{x:.5f}")
top_griegas["Vega"] = top_griegas["vega"].map(lambda x: "-" if pd.isna(x) else f"{x:.3f}")

print("\n  Griegas por activo (peso > 1%):")
print(top_griegas.rename(columns={"symbol": "Symbol"})[["Symbol", "Peso", "Delta", "Gamma", "Vega"]].to_string(index=False))

# ==============================================================================
# FRONTERA EFICIENTE
# ==============================================================================
print("\nGenerando frontera eficiente restringida (barrido de lambda)...")


def solve_qp_portfolio(lambda_val):
    dv = mu_final / lambda_val
    Dm = cov_mat + np.eye(n) * 1e-8
    try:
        s = quadprog.solve_qp(Dm, dv, Amat, bvec, meq)
        w = np.maximum(s[0], 0)
        w[excluded_etf_assets] = 0.0
        w = w / w.sum()
        return pd.Series(w, index=assets)
    except Exception:
        return None


lambdas_frontera = qm.frontier_lambda_grid(lambda_, n=60, lo=0.1, hi=200.0)
frontier_df = qm.frontier_curve(
    solve_qp_portfolio, cov_mat, mu_final, lambdas_frontera, lambda_utility=lambda_)

if frontier_df.empty:
    print("  No hubo soluciones factibles para trazar la frontera restringida.")
else:
    frontier_df = frontier_df.sort_values("risk")
    opt_idx = (frontier_df["lambda_"] - float(lambda_)).abs().idxmin()
    opt_point = frontier_df.loc[opt_idx]
    x_max = float(frontier_df["risk"].max()) * 1.15
    y_min = float(min(frontier_df["ret"].min(), opt_point["ret"]))
    y_max = float(max(frontier_df["ret"].max(), opt_point["ret"]))
    y_pad = max((y_max - y_min) * 0.08, 1e-6)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=frontier_df["risk"], y=frontier_df["ret"], mode="lines+markers",
        name="Frontera restringida",
        line=dict(color="darkgreen", width=2),
        marker=dict(size=5),
        customdata=np.column_stack([frontier_df["lambda_"], frontier_df["utility"]]),
        hovertemplate=("λ=%{customdata[0]:.2f}<br>Riesgo: %{x:.4f}<br>"
                       "Retorno μ_final: %{y:.4f}<br>U(λ ref): %{customdata[1]:.4f}<extra></extra>"),
    ))
    fig.add_trace(go.Scatter(
        x=[opt_point["risk"]], y=[opt_point["ret"]], mode="markers",
        name=f"Optimo (λ={lambda_:.2f})",
        marker=dict(color="red", size=14, symbol="diamond", line=dict(width=1, color="black")),
        hovertemplate=(f"Optimo λ={lambda_:.2f}<br>Riesgo: %{{x:.4f}}<br>"
                       f"Retorno μ_final: %{{y:.4f}}<extra></extra>"),
    ))
    fig.update_layout(
        title=dict(text="Frontera eficiente restringida<br>"
                        f"<sup>Mismas restricciones del QP | μ_final | λ={lambda_:.2f} | "
                        f"{horizon_desc} | {min(target_years)}-{max(target_years)}</sup>"),
        xaxis_title=f"Riesgo ({periodo_label}): σ = sqrt(w'Σw)",
        yaxis_title=f"Retorno esperado ({periodo_label}): w'μ_final",
        xaxis_range=[0, x_max],
        yaxis_range=[y_min - y_pad, y_max + y_pad],
        template="plotly_white",
    )
    fig.show()
    print(f"  {len(frontier_df)} puntos. El optimo (λ={lambda_:.2f}) es uno de ellos: "
          f"σ={opt_point['risk']:.4f}, w'μ_final={opt_point['ret']:.4f}.")

# ==============================================================================
# COMPARACION DE LAMBDAS
# ==============================================================================
print("\n" + "=" * 70)
print("ANALISIS COMPARATIVO: Portafolios por nivel de lambda")
print("=" * 70 + "\n")

print(f"Cada portafolio se resuelve con su lambda, pero la utilidad se mide con el "
      f"lambda configurado ({lambda_:.2f}) y con w'μ_final. El libro no cambia.")
lambda_values = qm.comparison_lambdas(lambda_)
candidatos_lambda = []

for lambda_test in lambda_values:
    print(f"  Optimizando lambda={lambda_test:.2f}... ", end="")
    w = solve_qp_portfolio(lambda_test)
    if w is not None and w.sum() > 0.9:
        candidatos_lambda.append((lambda_test, w.values))
        print("solucion factible")
    else:
        candidatos_lambda.append((lambda_test, None))
        print("No se encontro solucion feasible")

results_comparison = qm.score_candidate_portfolios(
    candidatos_lambda, mu_final, cov_mat, lambda_, rf=rf_rate_period)
for _, fila in results_comparison.iterrows():
    print(f"    λ={fila['lambda_']:.2f} | R(μ_final)={fila['retorno']:.2f}% | "
          f"σ={fila['volatilidad']:.2f}% | U(λ={lambda_:.2f})={fila['utilidad']:.4f}")

if len(results_comparison) > 0:
    print("\n" + "=" * 70)
    print("RESULTADOS COMPARATIVOS")
    print("=" * 70 + "\n")
    print("pen_ret = (λ/2 w'Σw) / w'μ_final con el λ de cada fila: cuanto pesa el riesgo frente al")
    print("retorno en el objetivo. ~0 = casi solo maximiza retorno; ~1 = la penalizacion iguala al retorno.\n")
    disp = results_comparison.copy()
    for col in ["retorno", "volatilidad", "sharpe", "utilidad", "max_peso", "pen_ret"]:
        disp[col] = disp[col].map(lambda x: f"{x:.4f}")
    print(disp[["lambda_", "retorno", "volatilidad", "sharpe", "pen_ret", "n_activos", "max_peso", "utilidad"]]
          .to_string(index=False))
    _fila_cfg = results_comparison.loc[(results_comparison["lambda_"] - float(lambda_)).abs().idxmin()]
    print(f"\n  λ configurado ({lambda_:.2f}): pen_ret={_fila_cfg['pen_ret']:.3f} | "
          f"{int(_fila_cfg['n_activos'])} activos | peso maximo {_fila_cfg['max_peso']:.1f}%")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=results_comparison["volatilidad"], y=results_comparison["retorno"], mode="lines",
                              line=dict(color="steelblue", width=1.5), opacity=0.6,
                              showlegend=False, hoverinfo="skip"))
    bubble_fig = px.scatter(
        results_comparison, x="volatilidad", y="retorno", color="utilidad", size="lambda_",
        color_continuous_scale="RdYlGn", size_max=22,
        text=results_comparison["lambda_"].map(lambda x: f"{x:.1f}"),
        labels={"volatilidad": "Volatilidad (%)", "retorno": "Retorno w'μ_final (%)",
                "utilidad": f"Utilidad al λ={lambda_:.2f}"},
        hover_data={"lambda_": ":.1f", "sharpe": ":.3f", "n_activos": True, "max_peso": ":.1f",
                    "volatilidad": ":.2f", "retorno": ":.2f", "utilidad": ":.4f"},
    )
    bubble_fig.update_traces(textposition="middle right", textfont_size=9)
    for trace in bubble_fig.data:
        fig.add_trace(trace)
    fig.update_layout(bubble_fig.layout)
    fig.update_layout(
        title=dict(text="Portafolios por nivel de aversion al riesgo<br>"
                         f"<sup>Horizonte: {horizon_desc} | {min(target_years)}-{max(target_years)} | "
                         f"utilidad de todos los candidatos al λ configurado ({lambda_:.2f}), retorno w'μ_final</sup>"),
        template="plotly_white",
    )
    fig.show()

    best_row = results_comparison.loc[results_comparison["utilidad"].idxmax()]
    print("\n" + "=" * 70)
    print(f"COMPARACION AL LAMBDA CONFIGURADO ({lambda_:.2f})")
    print("=" * 70 + "\n")
    print(f"  Mayor utilidad de la rejilla, medida con λ={lambda_:.2f} y w'μ_final: "
          f"{best_row['lambda_']:.2f}")
    _ann_best = qm.annualize_monthly(mu=best_row["retorno"] / 100.0, sd=best_row["volatilidad"] / 100.0)
    print(f"  - Retorno w'μ_final ({periodo_label}): {best_row['retorno']:.2f}% ({_ann_best['mu'] * 100:.1f}% anual)")
    print(f"  - Volatilidad ({periodo_label}): {best_row['volatilidad']:.2f}% ({_ann_best['sd'] * 100:.1f}% anual)")
    print(f"  - Sharpe (sobre μ_final): {best_row['sharpe']:.3f}")
    print(f"  - Utilidad al λ configurado: {best_row['utilidad']:.4f}")
    print(f"  - Activos en ese candidato: {int(best_row['n_activos'])}")
    print(f"\n  El portafolio publicado sigue siendo el QP a λ={lambda_:.2f}. "
          "Esta tabla no lo reemplaza.")

print("\nOptimizacion completada exitosamente")

# ==============================================================================
# ANALISIS DE MDD
# ==============================================================================
print("\n\n=== ANALISIS DE MAXIMUM DRAWDOWN DEL PORTAFOLIO ===")

tickers_portfolio = pesos["symbol"].tolist()
weights_dict = dict(zip(pesos["symbol"], pesos["weight"]))


def calc_mdd(returns_vector):
    returns_vector = np.asarray(returns_vector, dtype=float)
    valid = returns_vector[~np.isnan(returns_vector)]
    if len(valid) < 2:
        return np.nan
    cumulative_values = np.cumprod(1 + returns_vector)
    peak = np.maximum.accumulate(cumulative_values)
    drawdown = (cumulative_values - peak) / peak
    mdd = np.nanmin(drawdown)
    if not np.isfinite(mdd):
        return np.nan
    return mdd


_mdd_base = df_prices_monthly
_mdd_fuente = "mensual"
if df_daily_for_mdd is not None and len(df_daily_for_mdd):
    _diaria = df_daily_for_mdd[df_daily_for_mdd["symbol"].isin(tickers_portfolio)]
    if len(_diaria) >= 20 and _diaria["symbol"].nunique() >= 1 and "return" in _diaria.columns:
        _mdd_base = _diaria.rename(columns={"return": "monthly_return"})
        _mdd_fuente = "diaria"
portfolio_hist = _mdd_base[
    _mdd_base["symbol"].isin(tickers_portfolio)
    & (_mdd_base["date"].dt.year >= mdd_start_year)
    & (_mdd_base["date"].dt.year <= max(target_years))
]

_fmt_mdd = "%Y-%m-%d" if _mdd_fuente == "diaria" else "%Y-%m"
print(f"  Datos historicos ({_mdd_fuente}): {portfolio_hist['date'].nunique()} dias "
      f"({len(portfolio_hist)} filas ticker-dia) | "
      f"{portfolio_hist['date'].min().strftime(_fmt_mdd)} a "
      f"{portfolio_hist['date'].max().strftime(_fmt_mdd)}")

portfolio_wide = portfolio_hist.pivot_table(index="date", columns="symbol", values="monthly_return").sort_index()

rows = []
for dt_, row in portfolio_wide.iterrows():
    valid_cols = [t for t in tickers_portfolio if t in portfolio_wide.columns and not pd.isna(row[t])]
    available_tickers = len(valid_cols)
    if available_tickers > 0:
        valid_weights = np.array([weights_dict[t] for t in valid_cols])
        normalized_weights = valid_weights / valid_weights.sum()
        valid_returns = np.array([row[t] for t in valid_cols])
        portfolio_return = float(np.sum(valid_returns * normalized_weights))
    else:
        portfolio_return = np.nan
    rows.append(dict(date=dt_, year=dt_.year, portfolio_return=portfolio_return, available_tickers=available_tickers))

portfolio_returns_by_year = pd.DataFrame(rows)

valid_returns_mdd = portfolio_returns_by_year[
    portfolio_returns_by_year["portfolio_return"].notna() & np.isfinite(portfolio_returns_by_year["portfolio_return"])
]

if len(valid_returns_mdd) >= 2:
    cumulative_values = np.cumprod(1 + valid_returns_mdd["portfolio_return"].values)
    peak = np.maximum.accumulate(cumulative_values)
    drawdown = (cumulative_values - peak) / peak
    global_mdd = np.nanmin(drawdown)
    print(f"\n  MDD Global ({valid_returns_mdd['year'].min()}-{valid_returns_mdd['year'].max()}): {global_mdd * 100:.2f}%")

all_years = pd.DataFrame({"year": range(mdd_start_year, max(target_years) + 1)})

yearly_mdd_calculated = (
    valid_returns_mdd.groupby("year")
    .agg(mdd=("portfolio_return", calc_mdd), n_obs=("portfolio_return", "count"),
         avg_tickers=("available_tickers", "mean"))
    .reset_index()
)

yearly_mdd = all_years.merge(yearly_mdd_calculated, on="year", how="left")
yearly_mdd["has_data"] = yearly_mdd["mdd"].notna()
yearly_mdd["n_obs"] = yearly_mdd["n_obs"].fillna(0)

yearly_mdd_valid = yearly_mdd[yearly_mdd["has_data"] & np.isfinite(yearly_mdd["mdd"])]
median_mdd = np.nan

if len(yearly_mdd_valid) >= 1:
    print("\n=== ESTADISTICAS DE MDD ===")

    resumen_mdd = qm.summarize_yearly_mdd(yearly_mdd_valid["mdd"])
    peor_mdd = resumen_mdd["peor"]
    mejor_mdd = resumen_mdd["mejor"]
    p10_mdd = resumen_mdd["conservador"]
    median_mdd = resumen_mdd["mediana"]
    mean_mdd = resumen_mdd["promedio"]
    if resumen_mdd["n"] >= 3:
        print(f"  Peor escenario historico (sin filtrar): {peor_mdd * 100:.2f}%")
        print(f"  Escenario conservador (P10, sin filtrar): {p10_mdd * 100:.2f}%")
        print(f"  Escenario tipico (mediana, IQR):  {median_mdd * 100:.2f}%")
        print(f"  Promedio (IQR, {resumen_mdd['n_iqr']} de {resumen_mdd['n']} anos): "
              f"{mean_mdd * 100:.2f}%")
        print(f"  Mejor escenario historico (sin filtrar): {mejor_mdd * 100:.2f}%")
    else:
        print(f"  Peor escenario:   {peor_mdd * 100:.2f}%")
        print(f"  Promedio:         {mean_mdd * 100:.2f}%")
        print(f"  Mejor escenario:  {mejor_mdd * 100:.2f}%")

    last_year_data = yearly_mdd_valid.sort_values("year", ascending=False)
    if len(last_year_data) > 0:
        print(f"  MDD mas reciente ({int(last_year_data.iloc[0]['year'])}): {last_year_data.iloc[0]['mdd'] * 100:.2f}%")

    plot_data = yearly_mdd.copy()
    plot_data["mdd_pct"] = np.where(plot_data["has_data"], plot_data["mdd"] * 100, np.nan)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=plot_data["year"], y=plot_data["mdd_pct"], mode="lines+markers",
        line=dict(color="darkred", width=1.5),
        marker=dict(color=plot_data["has_data"].map({True: "darkred", False: "gray"}), size=8),
        hovertemplate="Ano %{x}: %{y:.2f}%<extra></extra>", showlegend=False,
    ))
    if len(yearly_mdd_valid) >= 3:
        fig.add_hline(y=median_mdd * 100, line_dash="dash", line_color="blue",
                      annotation_text=f"Mediana: {median_mdd * 100:.2f}%", annotation_position="top left",
                      annotation_font_color="blue")
        fig.add_hline(y=p10_mdd * 100, line_dash="dash", line_color="orange",
                      annotation_text=f"P10: {p10_mdd * 100:.2f}%", annotation_position="bottom left",
                      annotation_font_color="orange")
    fig.update_layout(
        title=dict(text="Maximum Drawdown Historico del Portafolio<br>"
                         f"<sup>Horizonte: {horizon_desc} | MDD: {mdd_start_year}-{max(target_years)} | "
                         f"{int(yearly_mdd['has_data'].sum())} anos con datos</sup>"),
        xaxis_title="Ano", yaxis_title="MDD (%)",
        xaxis=dict(tickmode="linear", tick0=mdd_start_year, dtick=2, tickangle=45),
        template="plotly_white",
    )
    fig.show()

    yearly_summary = yearly_mdd.sort_values("year", ascending=False).copy()
    yearly_summary["MDD"] = np.where(yearly_summary["has_data"],
                                      yearly_summary["mdd"].map(lambda x: f"{x * 100:.2f}%"), "Sin datos")
    yearly_summary["Obs"] = np.where(yearly_summary["has_data"], yearly_summary["n_obs"].astype(int).astype(str), "-")
    yearly_summary["Tickers_Prom"] = np.where(yearly_summary["has_data"],
                                               yearly_summary["avg_tickers"].map(lambda x: f"{x:.1f}"), "-")
    yearly_summary = yearly_summary.rename(columns={"year": "Anio"})[["Anio", "MDD", "Obs", "Tickers_Prom"]]
    print(yearly_summary.to_string(index=False))

print("\nAnalisis completado exitosamente!")

# ==============================================================================
# RESUMEN EJECUTIVO
# ==============================================================================
print("\n" + "=" * 60)
print("RESUMEN EJECUTIVO FINAL")
print("=" * 60)
print(f"   Periodo de entrenamiento: {min(target_years)}-{max(target_years)}")
print(f"   Horizonte: {horizon_desc}")
print(f"   Activos en portafolio: {len(tickers_portfolio)}")
print(f"   Retorno esperado mensual: {ret_opt * 100:.2f}%")
print(f"   Retorno anualizado:       {_ann_opt['mu'] * 100:.2f}%")
print(f"   Volatilidad mensual:      {sd_opt * 100:.2f}%")
print(f"   Volatilidad anualizada:   {_ann_opt['sd'] * 100:.2f}%")
print(f"   Sharpe Ratio:             {sharpe_opt:.4f}")
print(f"   Sortino Ratio:            {sortino_opt:.4f}")
print(f"   VaR Cornish-Fisher ({cornish_fisher_confidence * 100:.0f}%): {var_cf * 100:.4f}%")
print(f"   CVaR Cornish-Fisher ({cornish_fisher_confidence * 100:.0f}%): {cvar_cf * 100:.4f}%")
if np.isfinite(median_mdd):
    print(f"   MDD tipico historico:     {median_mdd * 100:.2f}%")

print(f"\n--- PORTAFOLIO A EJECUTAR (horizonte: {horizon_desc}) ---\n")
for _, row in pesos.iterrows():
    print(f"   {row['symbol']:<8}  {row['weight'] * 100:.2f}%")
print("=" * 60)

# ==============================================================================
# CALIDAD DE DATOS EN PORTAFOLIO FINAL
# ==============================================================================
print("\n=== CALIDAD DE DATOS EN PORTAFOLIO FINAL ===")

portfolio_data_quality = (
    combined_stats[combined_stats["symbol"].isin(tickers_portfolio)]
    [["symbol", "n_obs", "data_quality_penalty", "sharpe_ratio_adjusted", "sd_return"]]
    .merge(pesos, on="symbol", how="left")
    .sort_values("weight", ascending=False)
)

print(f"  Activos totales: {len(portfolio_data_quality)}")
print(f"  Con datos ideales (>={ideal_observations} obs): "
      f"{(portfolio_data_quality['n_obs'] >= ideal_observations).sum()} "
      f"({(portfolio_data_quality['n_obs'] >= ideal_observations).mean() * 100:.1f}%)")
print(f"  Con penalizacion: {(portfolio_data_quality['data_quality_penalty'] < 1.0).sum()} "
      f"({(portfolio_data_quality['data_quality_penalty'] < 1.0).mean() * 100:.1f}%)")

if (portfolio_data_quality["data_quality_penalty"] < 1.0).any():
    limited_data = portfolio_data_quality[portfolio_data_quality["data_quality_penalty"] < 1.0].copy()
    limited_data["Peso"] = limited_data["weight"].map(lambda x: f"{x * 100:.2f}%")
    limited_data["Penalizacion"] = limited_data["data_quality_penalty"].map(lambda x: f"{x * 100:.1f}%")
    print(limited_data.rename(columns={"symbol": "Symbol", "n_obs": "Obs", "sharpe_ratio_adjusted": "Sharpe"})
          [["Symbol", "Peso", "Obs", "Penalizacion", "Sharpe"]].to_string(index=False))

print("\nScript completado con exito!")

_h_days, _h_end = pipeline_io.horizon_from_months(as_of_date, horizon_months)
pipeline_io.export_portfolio(
    "quadratic_utility",
    dict(zip(pesos["symbol"], pesos["weight"])),
    horizon_days=_h_days,
    horizon_end=_h_end,
    params={
        "lambda": lambda_,
        "lambda_annual": lambda_annual,
        "max_weight": max_weight,
        "max_region_weight": max_region_weight,
        "etf_floor": etf_lo,
        "etf_cap": etf_hi,
        "include_etfs_in_portfolio": include_etfs_in_portfolio,
        "n_pre_filter": n_pre_filter,
        "n_filter_candidates": n_filter_candidates,
        "mu_shrink_k": mu_shrink_k,
        "use_lw_shrinkage": use_lw_shrinkage,
        "cov_halflife_days": cov_halflife_days,
        "horizon_months": horizon_months,
        "bkm_z_threshold": bkm_z_threshold,
        "recent_vol_ratio_max": recent_vol_ratio_max,
        "iv_vs_realized_ratio_max": iv_vs_realized_ratio_max,
        "volatility_percentile": volatility_percentile,
        "correlation_percentile": correlation_percentile,
    },
    metrics={
        "expected_return": float(_ann_opt["mu"]),
        "volatility": float(_ann_opt["sd"]),
    },
)
