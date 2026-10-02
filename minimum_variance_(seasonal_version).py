# ==============================================================================
# OPTIMIZACION DE PORTAFOLIOS - MINIMO RIESGO DE COLA PROSPECTIVO (BKM + CORNISH-FISHER) - VERSION ESTACIONAL
# ==============================================================================

import warnings
warnings.filterwarnings("ignore")

import re
import io
import time
import math
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

import yfinance as yf
import statsmodels.api as sm
from scipy.stats import norm, skew, kurtosis
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform
import quadprog

import plotly.express as px
import plotly.graph_objects as go

import risk_estimators as rk
import polygon_client as pc
import market_data as md
import portfolio_constraints as pq

# ==============================================================================
# SECCION 1: PARAMETROS CONFIGURABLES
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
    print("             fallaran y cada activo caera a volatilidad historica (sin IV real).")

# ------------------------------------------------------------------------------
# BENCHMARK
# ------------------------------------------------------------------------------

benchmark = "SPY"

# ------------------------------------------------------------------------------
# UNIVERSO DE ACTIVOS
# ------------------------------------------------------------------------------
n_top_sp500 = 80
n_top_nasdaq = 80
n_top_international = 15
target_total_tickers = 130

# ------------------------------------------------------------------------------
# HORIZONTE DE DATOS HISTORICOS
# ------------------------------------------------------------------------------
start_date = "2018-01-01"
end_date = date.today()

# ------------------------------------------------------------------------------
# MESES DE EJECUCION
# ------------------------------------------------------------------------------
execution_months = [10]
execution_n_months = 1

# ------------------------------------------------------------------------------
# TASA LIBRE DE RIESGO
# ------------------------------------------------------------------------------
risk_free_rate = 0.047   # alineada con minimum_variance.py (B-9)
risk_free_rate_weekly = risk_free_rate / 52

# ------------------------------------------------------------------------------
# TAMANO DE LOS FILTROS DE CANDIDATOS
# ------------------------------------------------------------------------------
n_pre_seasonal = 45
n_divers_candidates = 30

# ------------------------------------------------------------------------------
# PERCENTILES DE FILTRO Y NUMERO MAXIMO DE ACTIVOS
# ------------------------------------------------------------------------------
volatility_percentile = 0.97
correlation_percentile = 0.90
max_assets_in_portfolio = 6
# Poda hasta max_assets. min_weight saca el peso chico. max_mtr es la regla
# anterior (mayor contribucion marginal: poda defensivos en la cota del 12%).
# min_weight_x_mtr ordena por peso * contribucion, de menor a mayor.
tail_prune_rule = "min_weight"
# Clases duplicadas. El primer ticker de cada grupo se queda.
dedupe_share_classes = True
share_class_groups = (("GOOGL", "GOOG"),)

# ------------------------------------------------------------------------------
# FILTRO ESTACIONAL
# ------------------------------------------------------------------------------
seasonal_min_weeks = 10

# ------------------------------------------------------------------------------
# PARAMETROS BKM Y TAIL RISK
# ------------------------------------------------------------------------------
bkm_moneyness_lo = 0.70
bkm_moneyness_hi = 1.30
bkm_min_options_per_side = 3
bkm_mfik_max = 20.0
# Con pocos strikes OTM el tope sigue en 20. Con una cadena densa sube hasta
# bkm_mfik_max_hard: SPY y otros indices superan 20 sin ser inadmisibles.
bkm_mfik_max_hard = 80.0
tail_risk_filter_confidence = 0.95
cornish_fisher_confidence = 0.95

# ------------------------------------------------------------------------------
# FALLBACK HISTORICO DEL FILTRO DE TAIL RISK
# ------------------------------------------------------------------------------
# False: solo pasan el filtro los activos con momentos BKM validos.
# True: los activos sin BKM (sin cobertura de opciones, no-USD o MFIS/MFIK
# inadmisibles) usan asimetria y curtosis historicas llevadas al horizonte.
tail_risk_hist_fallback = False
tail_risk_min_survivors = 5

# ------------------------------------------------------------------------------
# RESTRICCIONES DE PONDERACION
# ------------------------------------------------------------------------------
max_weight_per_asset = 0.35
min_weight_per_asset = 0.001
# En cada iteracion de la poda se sacan de una vez los activos por debajo de
# este peso, si el resto sigue siendo factible. 0.0 lo desactiva.
prune_below_weight = 0.01

# ------------------------------------------------------------------------------
# ESTRATEGIA DE PONDERACION
# ------------------------------------------------------------------------------
require_full_investment = False
min_total_weight = 1.00
max_total_weight = 1.00

# ------------------------------------------------------------------------------
# RESTRICCION DE PARTICIPACION DE ETFs EN EL PORTAFOLIO FINAL
# ------------------------------------------------------------------------------
use_etf_constraint = True
etf_min_weight = 0.00
etf_max_weight = 0.05

# ------------------------------------------------------------------------------
# ETFs EN EL PORTAFOLIO RESULTANTE
# ------------------------------------------------------------------------------
include_etfs_in_portfolio = True

# ------------------------------------------------------------------------------
# RESTRICCION DE EXPOSICION CAMBIARIA
# ------------------------------------------------------------------------------
use_fx_factor = True
max_fx_exposure = 0.50

# ------------------------------------------------------------------------------
# ANUALIZACION
# ------------------------------------------------------------------------------
annualization_factor = 52

# ------------------------------------------------------------------------------
# IV ATM (~30 DTE) Y GRIEGAS DE DIAGNOSTICO
# ------------------------------------------------------------------------------
# El antiguo "filtro Delta" (delta BS de una call ATM >= delta_min) se elimino
# (M-3): con K = S la delta es N(d1) con d1 = (r + sigma^2/2) sqrt(T) / sigma
# > 0, asi que siempre supera 0.5 y nunca descartaba nada. El riesgo de cola
# se filtra mas abajo con BKM + Cornish-Fisher. La IV ATM se sigue
# consultando para el shrinkage de la covarianza y las griegas de diagnostico.
delta_strike_mode = "atm"
target_dte_iv = 30
dte_tol_iv = 21
dte_min_iv = 21
moneyness_tol_iv = 0.02

# ------------------------------------------------------------------------------
# SHRINKAGE COVARIANZA: IMPLIED vs HISTORICA
# ------------------------------------------------------------------------------
use_iv_shrinkage = True
shrinkage_max = 0.40
shrinkage_min = 0.02
ratio_band = 0.20

# ------------------------------------------------------------------------------
# COVARIANZA HISTORICA: EWMA + SHRINKAGE LEDOIT-WOLF
# ------------------------------------------------------------------------------
# hist_cov_frequency:
#   "daily"  : retornos diarios (mas precision en varianzas, Merton 1980), pero
#              los cierres de Tokio/Europa/EE. UU. no son sincronicos y las
#              correlaciones entre zonas horarias quedan subestimadas (M-2).
#   "weekly" : retornos semanales; el desfase de cierres es una fraccion
#              pequena del intervalo y la correlacion es robusta.
#   "auto"   : weekly si hay algun ticker de bolsa no estadounidense en el
#              pool final, daily si todos cotizan en EE. UU.
hist_cov_frequency = "auto"
cov_halflife_days = 120
cov_halflife_weeks = 26
use_lw_shrinkage = True

# Peso de la covarianza historica en el blend con la implicita de factores.
hist_shrink_alpha = 0.35

# ------------------------------------------------------------------------------
# ALINEACION DE PRECIOS MULTI-MERCADO
# ------------------------------------------------------------------------------
# Festivos locales: cada ticker se rellena hacia adelante como maximo
# max_ffill_days sobre el calendario del benchmark (M-1). Lagunas mas largas
# siguen eliminando la fila.
max_ffill_days = 2
min_price_coverage = 0.80

# ------------------------------------------------------------------------------
# CORRECCION Q -> P (PRIMA DE RIESGO DE VARIANZA)
# ------------------------------------------------------------------------------
use_q_to_p_vol = True
vrp_ratio_bounds = (0.70, 1.00)
vrp_fallback_ratio = 0.90

# ------------------------------------------------------------------------------
# PANEL DE ESCENARIOS PARA MOMENTOS DEL PORTAFOLIO
# ------------------------------------------------------------------------------
panel_min_obs = 104

# ------------------------------------------------------------------------------
# CORRELACION IMPLICITA DE FACTORES (MERCADO + SECTOR + PAIS + FX)
# ------------------------------------------------------------------------------
use_sector_factor = True
use_country_factor = True

# ==============================================================================
# SECCION 2: VALIDACION DEL HORIZONTE
# ==============================================================================

execution_months, _aviso_meses = md.resolve_execution_months(
    execution_months, as_of=end_date, n_months=execution_n_months)
if _aviso_meses:
    print(f"ADVERTENCIA: {_aviso_meses}")

if not (1 <= len(execution_months) <= 3):
    raise ValueError("Error: execution_months debe contener entre 1 y 3 meses.")
if any(m < 1 or m > 12 for m in execution_months):
    raise ValueError("Error: Cada mes debe ser un entero entre 1 y 12.")


def check_consecutive(months):
    if len(months) == 1:
        return True
    diffs = [(months[i + 1] - months[i]) % 12 for i in range(len(months) - 1)]
    return all(d == 1 or d == -11 % 12 for d in diffs) or all(
        (b - a) % 12 == 1 for a, b in zip(months, months[1:])
    )


if not check_consecutive(execution_months):
    raise ValueError(
        "Error: Los meses deben ser consecutivos.\n"
        f"   Recibido: {', '.join(map(str, execution_months))}\n"
        "   Ejemplos validos: [3,4,5] | [11,12,1] | [12,1,2]"
    )

horizon_months = len(execution_months)
horizon_weeks = horizon_months * (52 / 12)
horizon_factor = horizon_weeks
horizon_sqrt = math.sqrt(horizon_weeks)
rf_horizon = risk_free_rate * (horizon_months / 12)

use_iv_for_horizon = True
T_options = horizon_months / 12

MONTH_NAME = ["", "January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]

execution_label = "-".join(MONTH_NAME[m] for m in execution_months)
horizon_label = f"{horizon_months} {'mes' if horizon_months == 1 else 'meses'} ({execution_label})"

print("\n" + "=" * 68)
print("     OPTIMIZACION DE PORTAFOLIO - MINIMO RIESGO DE COLA (BKM + CORNISH-FISHER) - ESTACIONAL")
print("     Retornos: SEMANALES | Entrenamiento: Historico completo")
print("=" * 68 + "\n")
print(f"Horizonte de inversion : {horizon_label}")
print(f"Semanas del horizonte  : {horizon_weeks:.1f} semanas")
print(f"Entrenamiento          : {start_date} -> {end_date:%Y-%m-%d}")
print(f"Anualizacion base      : x{annualization_factor} | Horizonte: x{horizon_weeks:.1f} semanas\n")

# ==============================================================================
# SECCION 3: UNIVERSO DE INVERSION
# ==============================================================================


def safe_scrape_table(url, fallback=None):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"[ADVERTENCIA] HTTP {resp.status_code} al obtener {url}")
            return fallback
        tables = pd.read_html(io.StringIO(resp.text))
        if not tables:
            return fallback
        return tables[0]
    except Exception as e:
        print(f"[ADVERTENCIA] Error al obtener datos de {url}: {e}")
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
# OBTENER TICKERS: S&P 500 (ORDENADO POR CAP. DE MERCADO)
# ==============================================================================
print("[INFO] Obteniendo tickers del S&P 500 (stockanalysis.com)...")
sp500_tbl = safe_scrape_table("https://stockanalysis.com/list/sp-500-stocks/")

if sp500_tbl is None:
    print("  Reintentando con slickcharts.com como fuente alterna...")
    sp500_tbl = safe_scrape_table("https://www.slickcharts.com/sp500")

if sp500_tbl is not None:
    sp500_tbl_clean = clean_symbol_table(sp500_tbl)
    sp500_tickers = sp500_tbl_clean["symbol"].iloc[: min(n_top_sp500, len(sp500_tbl_clean))].unique().tolist()
    print(f"  OK S&P 500: {n_top_sp500} objetivo, {len(sp500_tickers)} unicos obtenidos")
else:
    sp500_tickers = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "BRK-B", "LLY", "AVGO",
                      "TSLA", "JPM", "UNH", "V", "XOM", "MA", "JNJ", "PG", "COST", "HD"]
    print("  ADVERTENCIA: Scraping fallo en ambas fuentes - usando fallback S&P 500 (20 tickers hardcodeados)")

# ==============================================================================
# OBTENER TICKERS: NASDAQ (ORDENADO POR CAP. DE MERCADO)
# ==============================================================================
print("\n[INFO] Obteniendo tickers del NASDAQ (stockanalysis.com)...")
nasdaq_tbl = safe_scrape_table("https://stockanalysis.com/list/nasdaq-stocks/")

if nasdaq_tbl is not None:
    nasdaq_tbl_clean = clean_symbol_table(nasdaq_tbl)
    nasdaq_tickers = nasdaq_tbl_clean["symbol"].iloc[: min(n_top_nasdaq, len(nasdaq_tbl_clean))].unique().tolist()
    print(f"  OK NASDAQ: {n_top_nasdaq} objetivo, {len(nasdaq_tickers)} unicos obtenidos")
else:
    nasdaq_tbl_clean = None
    nasdaq_tickers = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "AVGO", "TSLA", "COST",
                       "NFLX", "AMD", "ADBE", "QCOM", "INTU", "AMAT", "TXN", "MU", "BKNG", "NOW"]
    print("  ADVERTENCIA: Scraping fallo - usando fallback NASDAQ (20 tickers hardcodeados)")

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
    "EWC", "EWG", "EWU", "EWQ", "EWP",
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

n_top_international = min(n_top_international, len(international_tickers_full))
international_tickers = international_tickers_full[:n_top_international]

etf_universe_tickers = list(dict.fromkeys(etf_tickers + commodity_tickers))

# ==============================================================================
# COMBINAR Y LIMPIAR
# ==============================================================================
print("\n[INFO] Combinando y limpiando tickers...")

sp500_tickers_clean = list(dict.fromkeys(t.upper() for t in sp500_tickers))
nasdaq_tickers_clean = list(dict.fromkeys(t.upper() for t in nasdaq_tickers))
etf_tickers_clean = list(dict.fromkeys(t.upper() for t in etf_tickers))
commodity_tickers_clean = list(dict.fromkeys(t.upper() for t in commodity_tickers))
international_tickers_clean = list(dict.fromkeys(t.upper() for t in international_tickers))

tickers_domesticos = list(dict.fromkeys(
    sp500_tickers_clean + nasdaq_tickers_clean + etf_tickers_clean + commodity_tickers_clean
))
tickers_domesticos_ok = [
    t for t in tickers_domesticos
    if not re.search(r"\^|\$", t) and 1 <= len(t) <= 5 and not re.match(r"^[0-9]", t) and t != ""
]

all_tickers = list(dict.fromkeys(tickers_domesticos_ok + international_tickers_clean))

if target_total_tickers > 0 and len(all_tickers) < target_total_tickers:
    shortage = target_total_tickers - len(all_tickers)
    print(f"[INFO] Poblacion ({len(all_tickers)}) por debajo del objetivo ({target_total_tickers}) "
          f"- completando {shortage} tickers...")

    if len(international_tickers_full) > n_top_international:
        extra_intl = [t for t in dict.fromkeys(x.upper() for x in international_tickers_full[n_top_international:])
                      if t not in all_tickers]
        if extra_intl:
            to_add = extra_intl[:shortage]
            all_tickers = list(dict.fromkeys(all_tickers + to_add))
            shortage -= len(to_add)
            print(f"  + {len(to_add)} internacionales adicionales")

    if shortage > 0 and nasdaq_tbl_clean is not None and len(nasdaq_tbl_clean) > len(nasdaq_tickers):
        extra_nasdaq = [t for t in nasdaq_tbl_clean["symbol"].iloc[len(nasdaq_tickers):].unique().tolist()
                         if t not in all_tickers]
        if extra_nasdaq:
            to_add = extra_nasdaq[:shortage]
            all_tickers = list(dict.fromkeys(all_tickers + to_add))
            shortage -= len(to_add)
            print(f"  + {len(to_add)} NASDAQ adicionales")

    if shortage > 0:
        print(f"  ADVERTENCIA: No se pudo alcanzar target_total_tickers; faltan {shortage}")

all_tickers = list(dict.fromkeys(all_tickers))
if dedupe_share_classes:
    all_tickers, _clases = md.dedupe_share_classes(all_tickers, share_class_groups)
    for se_queda, se_van in _clases:
        print(f"[INFO] Clase duplicada: se queda {se_queda}, sale {', '.join(se_van)}")
print(f"[INFO] Total de tickers FINAL (unicos): {len(all_tickers)}\n")

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
# Overrides manuales. Solo se usan si el proveedor no informa la moneda; si la
# contradicen se avisa y gana el proveedor. El antiguo {"HSBC": "GBP",
# "BP": "GBP"} era incorrecto: ambos son ADRs de NYSE cotizados en USD (A-2).
ticker_currency_override = {}

# Se rellena tras la descarga con history_metadata["currency"] de yfinance.
provider_currency = {}
ticker_currency = {}


def is_non_us_exchange(ticker):
    return not pc.is_us_ticker(ticker)


def get_currency_for_ticker(ticker):
    if ticker in ticker_currency:
        return ticker_currency[ticker]
    if ticker in ticker_currency_override:
        return md.normalize_currency(ticker_currency_override[ticker])
    return md.currency_from_suffix(ticker, ticker_currency_by_suffix) or "USD"


# ==============================================================================
# SECCION 4: REPORTE DEL UNIVERSO
# ==============================================================================

print("\n" + "=" * 67)
print("UNIVERSO DE INVERSION")
print("=" * 67)
print(f"- Tickers del S&P 500 (top {n_top_sp500} por cap.):      {len(sp500_tickers)}")
print(f"- Tickers del NASDAQ (top {n_top_nasdaq} por cap.):      {len(nasdaq_tickers)}")
print(f"- ETFs (todas las categorias):                {len(etf_tickers)}")
print(f"- Commodities:                                {len(commodity_tickers)}")
print(f"- Internacionales (top {n_top_international} de {len(international_tickers_full)}): "
      f"{len(international_tickers)}")
print(f"- Objetivo de poblacion total (target_total_tickers): {target_total_tickers}")
print(f"- Total unicos tras combinar + rellenar:      {len(all_tickers)}\n")

# ==============================================================================
# SECCION 5: DESCARGA Y PREPARACION DE DATOS
# ==============================================================================

print("=" * 67)
print("DESCARGA DE DATOS HISTORICOS")
print("=" * 67 + "\n")

print("[INFO] Descargando precios diarios desde Yahoo Finance...")
print(f"[INFO] Periodo: {start_date} -> {end_date:%Y-%m-%d}")
print("[INFO] Se convertiran a retornos SEMANALES para el entrenamiento\n")


def download_ticker_data(ticker, start, end, max_retries=3):
    """Precios ajustados diarios. La moneda del proveedor queda en data.attrs["currency"]."""
    for attempt in range(max_retries):
        try:
            tk = yf.Ticker(ticker)
            data = tk.history(start=start, end=end, auto_adjust=True)
            if data is not None and len(data) > 0:
                meta = getattr(tk, "history_metadata", None) or {}
                data = data[["Close"]].rename(columns={"Close": "adjusted"}).reset_index()
                data = data.rename(columns={"Date": "date"})
                data["date"] = pd.to_datetime(data["date"]).dt.tz_localize(None)
                data["symbol"] = ticker
                data = data[["date", "symbol", "adjusted"]]
                data.attrs["currency"] = meta.get("currency")
                return data
        except Exception:
            time.sleep(1)
    return None


stock_data_list = {}
successful_tickers = []
failed_tickers = []

n_total = len(all_tickers)
for i, ticker in enumerate(all_tickers, start=1):
    data = download_ticker_data(ticker, start_date, end_date)
    if data is not None and len(data) > 0:
        cur_prov = data.attrs.get("currency")
        if cur_prov:
            provider_currency[ticker] = cur_prov
            # GBp / ZAc: el proveedor cotiza en unidad menor; se lleva a la unidad mayor.
            data["adjusted"] = data["adjusted"] * md.price_scale_factor(cur_prov)
        stock_data_list[ticker] = data
        successful_tickers.append(ticker)
    else:
        failed_tickers.append(ticker)
        print(f"   {ticker}: sin cotizacion en Yahoo; se excluye")
    if i % 25 == 0 or i == n_total:
        print(f"   Descargados {i}/{n_total}...")

print(f"\nOK Descargados exitosamente: {len(successful_tickers)} tickers")
if failed_tickers:
    print(f"X Fallaron: {len(failed_tickers)} tickers")
    print(f"   Tickers fallidos: {', '.join(failed_tickers[:10])}"
          f"{'...' if len(failed_tickers) > 10 else ''}")

stock_data = pd.concat(stock_data_list.values(), ignore_index=True) if stock_data_list else pd.DataFrame()

# ------------------------------------------------------------------------------
# MONEDA FINAL POR TICKER: proveedor > override manual > sufijo > USD (A-2)
# ------------------------------------------------------------------------------
ticker_currency, currency_conflicts = md.resolve_currencies(
    successful_tickers, ticker_currency_by_suffix, overrides=ticker_currency_override,
    provider=provider_currency)
n_sin_proveedor = sum(1 for t in successful_tickers if t not in provider_currency)
print(f"\n[INFO] Moneda por ticker: {len(provider_currency)} informadas por el proveedor"
      f"{f', {n_sin_proveedor} por sufijo/default' if n_sin_proveedor else ''}")
for c in currency_conflicts:
    print(f"  ADVERTENCIA moneda de {c['ticker']}: {c['fuente']} dice {c['manual']} pero el proveedor "
          f"reporta {c['proveedor']} - se usa {c['proveedor']}")
monedas_presentes = sorted(set(ticker_currency.values()))
print(f"[INFO] Monedas presentes: {', '.join(monedas_presentes)}")

print("\n[INFO] Descargando benchmark (SPY)...")
benchmark_data = download_ticker_data(benchmark, start_date, end_date)

if len(stock_data) == 0 or benchmark_data is None or len(benchmark_data) == 0:
    raise RuntimeError("Error: No se descargaron datos suficientes.")

# ==============================================================================
# DESCARGA DE PARES FX (PARA CONVERTIR PRECIOS DE INTERNACIONALES A USD)
# ==============================================================================
print("\n[INFO] Descargando pares FX para conversion a USD...")
fx_data = {}
for cur, info in fx_pairs.items():
    d = download_ticker_data(info["ticker"], start_date, end_date)
    if d is not None and len(d) > 0:
        fx_data[cur] = d.set_index("date")["adjusted"]
        print(f"  OK {cur} ({info['ticker']})")
    else:
        print(f"  ADVERTENCIA: no se pudo descargar {info['ticker']} para {cur} "
              f"- los tickers en {cur} quedaran en moneda local")

# ==============================================================================
# CONVERTIR A RETORNOS SEMANALES (PRECIOS INTERNACIONALES CONVERTIDOS A USD)
# ==============================================================================
print("\n[INFO] Convirtiendo precios diarios -> retornos semanales...")

prices_wide = stock_data.pivot_table(index="date", columns="symbol", values="adjusted")

# ------------------------------------------------------------------------------
# ALINEACION MULTI-MERCADO (M-1): calendario del benchmark + ffill acotado
# ------------------------------------------------------------------------------
# Antes: prices_wide.dropna() borraba la fila entera cuando CUALQUIER mercado
# (Tokio, Londres, Toronto, ...) estaba cerrado: ~12% de los dias, con huecos
# de 4-5 dias que distorsionaban los retornos "diarios" y el ultimo precio
# semanal. Ahora cada ticker se rellena hasta max_ffill_days sobre los dias
# de negociacion de SPY y solo se descartan las filas con lagunas mayores.
benchmark_calendar = pd.DatetimeIndex(benchmark_data["date"])
prices_wide_clean, align_info = md.align_prices_to_calendar(
    prices_wide, benchmark_calendar, max_ffill=max_ffill_days, min_coverage=min_price_coverage)
valid_tickers = list(prices_wide_clean.columns)
print(f"[INFO] Tickers con cobertura >= {min_price_coverage * 100:.0f}% del calendario SPY: {len(valid_tickers)}"
      + (f" (descartados: {', '.join(align_info['dropped_low_coverage'][:8])}"
         f"{'...' if len(align_info['dropped_low_coverage']) > 8 else ''})"
         if align_info["dropped_low_coverage"] else ""))
print(f"[INFO] Dias rellenados por festivos locales (ffill <= {max_ffill_days}): "
      f"{int(align_info['n_filled'].sum())} celdas en "
      f"{int((align_info['n_filled'] > 0).sum())} tickers | "
      f"filas eliminadas por lagunas mayores: {align_info['n_rows_dropped']} de "
      f"{align_info['n_rows_dropped'] + align_info['n_rows']}")

if len(prices_wide_clean) == 0:
    raise RuntimeError("Error: No hay datos despues de alinear los precios.")

# Ultima semana parcial (B-6): resample("W") etiqueta el domingo; si el ultimo
# dato no llega al viernes, la ultima fila mezcla una semana incompleta.
last_daily_date = prices_wide_clean.index.max()
prices_weekly, semana_parcial = md.drop_partial_last_week(
    prices_wide_clean.resample("W").last(), last_daily_date)
if semana_parcial:
    print(f"[INFO] Ultima semana parcial descartada (ultimo dato diario: {last_daily_date:%Y-%m-%d})")

fx_weekly_price_usd = {}
for cur, s in fx_data.items():
    w, _ = md.drop_partial_last_week(s.resample("W").last(), last_daily_date)
    fx_weekly_price_usd[cur] = (1 / w) if fx_pairs[cur]["invert"] else w
fx_weekly_price_usd = pd.DataFrame(fx_weekly_price_usd)

print("[INFO] Convirtiendo precios de tickers no-USD a USD...")
prices_weekly_usd = prices_weekly.copy()
n_convertidos = 0
for t in prices_weekly_usd.columns:
    cur = get_currency_for_ticker(t)
    if cur != "USD":
        if cur in fx_weekly_price_usd.columns:
            fx_series = fx_weekly_price_usd[cur].reindex(prices_weekly_usd.index).ffill()
            prices_weekly_usd[t] = prices_weekly_usd[t] * fx_series
            n_convertidos += 1
        else:
            print(f"  ADVERTENCIA: sin serie FX para {t} ({cur}) - queda en moneda local")
print(f"  OK Tickers convertidos a USD: {n_convertidos}")

weekly_returns = np.log(prices_weekly_usd / prices_weekly_usd.shift(1)).dropna(how="all")
weekly_returns = weekly_returns.dropna()

# ==============================================================================
# RETORNOS DIARIOS EN USD: INSUMO DE LA COVARIANZA HISTORICA
# ==============================================================================
fx_daily_price_usd = {}
for cur, s in fx_data.items():
    fx_daily_price_usd[cur] = (1 / s) if fx_pairs[cur]["invert"] else s
fx_daily_price_usd = pd.DataFrame(fx_daily_price_usd) if fx_daily_price_usd else pd.DataFrame()

prices_daily_usd = prices_wide_clean.copy()
for t in prices_daily_usd.columns:
    cur = get_currency_for_ticker(t)
    if cur != "USD" and cur in fx_daily_price_usd.columns:
        fx_series = fx_daily_price_usd[cur].reindex(prices_daily_usd.index).ffill()
        prices_daily_usd[t] = prices_daily_usd[t] * fx_series

daily_returns = np.log(prices_daily_usd / prices_daily_usd.shift(1)).dropna(how="all")
daily_returns = daily_returns.replace([np.inf, -np.inf], np.nan)
print(f"[INFO] Retornos diarios disponibles para Sigma: {len(daily_returns)} dias")

fx_weekly_returns = np.log(fx_weekly_price_usd / fx_weekly_price_usd.shift(1)).dropna(how="all")

benchmark_daily = benchmark_data.set_index("date")["adjusted"]
benchmark_weekly_prices, _ = md.drop_partial_last_week(benchmark_daily.resample("W").last(), last_daily_date)
benchmark_returns_full = np.log(benchmark_weekly_prices / benchmark_weekly_prices.shift(1)).dropna()
benchmark_returns_full = benchmark_returns_full.rename("SPY").to_frame()

common_dates = weekly_returns.index.intersection(benchmark_returns_full.index)
weekly_returns = weekly_returns.loc[common_dates]
benchmark_returns_full = benchmark_returns_full.loc[common_dates]

n_weeks = len(weekly_returns)
n_years = round(n_weeks / 52, 1)
print(f"[INFO] Semanas disponibles para entrenamiento: {n_weeks} (~{n_years} anios)")
print(f"[INFO] Tickers validos: {weekly_returns.shape[1]}\n")

log_returns = weekly_returns.copy()
benchmark_returns = benchmark_returns_full.copy()

print(f"[INFO] Entrenamiento con {len(log_returns)} semanas completas "
      f"({log_returns.index.min():%Y-%m-%d} -> {log_returns.index.max():%Y-%m-%d})")
print(f"[INFO] Horizonte de inversion: {horizon_label}\n")

if log_returns.isna().any().any() or np.isinf(log_returns.values).any():
    print("[ADVERTENCIA] Limpiando NAs/Inf...")
    bad_mask = log_returns.isna().any() | np.isinf(log_returns).any()
    bad_cols = log_returns.columns[bad_mask]
    good_cols = [c for c in log_returns.columns if c not in bad_cols]
    log_returns = log_returns[good_cols]
    print(f"   Tickers restantes: {log_returns.shape[1]}")

if log_returns.shape[1] < 5:
    raise RuntimeError("Error: Quedan menos de 5 tickers validos.")

# ==============================================================================
# SECCION 6: ANALISIS DESCRIPTIVO Y SELECCION
# ==============================================================================

print("\n" + "=" * 67)
print("ANALISIS DE SELECCION DE ACTIVOS")
print(f"Entrenamiento: {n_weeks} semanas | Horizonte: {horizon_label} (~{horizon_weeks:.1f} semanas)")
print("=" * 67 + "\n")


def max_drawdown_from_returns(returns_series):
    """MDD de una serie de LOG-retornos (riqueza = exp(cumsum)), B-1."""
    return rk.max_drawdown(returns_series, log_returns=True)


asset_stats = pd.DataFrame({
    "Symbol": log_returns.columns,
    "Mean_Return": log_returns.mean().values * annualization_factor,
    "Volatility": log_returns.std().values * math.sqrt(annualization_factor),
})
asset_stats["Sharpe"] = (asset_stats["Mean_Return"] - risk_free_rate) / asset_stats["Volatility"]

correlations = log_returns.apply(lambda col: col.corr(benchmark_returns.iloc[:, 0]))
asset_stats["Correlation_SPY"] = correlations.values

mdd_values = log_returns.apply(lambda col: max_drawdown_from_returns(col))
asset_stats["Max_Drawdown"] = mdd_values.values

asset_stats = asset_stats[
    asset_stats["Sharpe"].notna() & asset_stats["Volatility"].notna() & asset_stats["Correlation_SPY"].notna()
    & np.isfinite(asset_stats["Sharpe"]) & np.isfinite(asset_stats["Volatility"])
].sort_values("Correlation_SPY").reset_index(drop=True)

print(f"[INFO] Activos con metricas validas: {len(asset_stats)}\n")

vol_threshold = asset_stats["Volatility"].quantile(volatility_percentile)
corr_threshold = asset_stats["Correlation_SPY"].abs().quantile(correlation_percentile)

asset_stats["Passes_Vol"] = asset_stats["Volatility"] <= vol_threshold
asset_stats["Passes_Corr"] = asset_stats["Correlation_SPY"].abs() <= corr_threshold
asset_stats["Passes_Return"] = asset_stats["Mean_Return"] > 0
asset_stats["Passes_All"] = asset_stats["Passes_Vol"] & asset_stats["Passes_Corr"] & asset_stats["Passes_Return"]
asset_stats = asset_stats.sort_values("Volatility").reset_index(drop=True)

selected_pre_seasonal = (
    asset_stats[asset_stats["Passes_All"]].sort_values("Volatility").head(n_pre_seasonal)["Symbol"].tolist()
)

if len(selected_pre_seasonal) < 5:
    print("\n[ADVERTENCIA] Muy pocos activos pasan todos los filtros. Relajando filtro de correlacion...")
    selected_pre_seasonal = (
        asset_stats[asset_stats["Passes_Vol"] & asset_stats["Passes_Return"]]
        .sort_values("Volatility").head(n_pre_seasonal)["Symbol"].tolist()
    )

print(f"\n[INFO] Pool pre-filtro estacional: {len(selected_pre_seasonal)} candidatos "
      f"(max configurado: {n_pre_seasonal})")

# ==============================================================================
# FILTRO DELTA (BLACK-SCHOLES)
# ==============================================================================


def get_spot_safe(ticker):
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


_polygon_cache = {}


def get_polygon_option_snapshot(ticker):
    if ticker in _polygon_cache:
        return _polygon_cache[ticker]

    resultado = None
    transitorio = False
    try:
        S = get_spot_safe(ticker)
        if pd.isna(S) or S <= 0:
            raise ValueError("sin spot Yahoo para filtrar la llamada a Polygon")

        hoy = date.today()
        fecha_min = (hoy + timedelta(days=max(target_dte_iv - dte_tol_iv, 1))).strftime("%Y-%m-%d")
        fecha_max = (hoy + timedelta(days=target_dte_iv + dte_tol_iv)).strftime("%Y-%m-%d")
        strike_min = round(S * (1 - moneyness_tol_iv), 2)
        strike_max = round(S * (1 + moneyness_tol_iv), 2)

        url = (
            f"https://api.polygon.io/v3/snapshot/options/{pc.polygon_format_ticker(ticker)}?"
            f"contract_type=call&"
            f"strike_price.gte={strike_min:.2f}&strike_price.lte={strike_max:.2f}&"
            f"expiration_date.gte={fecha_min}&expiration_date.lte={fecha_max}&"
            f"limit=250"
        )

        results, completo, status = pc.get_all(url, api_key=POLYGON_API_KEY)
        if not completo:
            transitorio = pc.es_transitorio(status)
            raise ValueError(f"cadena incompleta (status {status})")
        if not results:
            raise ValueError("sin resultados")

        df = pd.json_normalize(results)
        hoy_ts = pd.Timestamp(hoy)
        df["strike"] = df["details.strike_price"]
        df["expiracion"] = pd.to_datetime(df["details.expiration_date"])
        df["dte"] = (df["expiracion"] - hoy_ts).dt.days

        df = df[(df["dte"] >= target_dte_iv - dte_tol_iv) & (df["dte"] <= target_dte_iv + dte_tol_iv)].copy()
        if len(df) == 0:
            raise ValueError("sin contratos en la ventana ~30 DTE")

        rango = pc.expiry_rank_columns(df["dte"], target_dte_iv, np.ones(len(df)), dte_min_iv)
        df = df.assign(**rango)
        df["_moneyness"] = (df["strike"] / S - 1).abs()
        df = df.sort_values(pc.EXPIRY_SORT_COLS + ["_moneyness"])
        elegido = df.iloc[0]

        spot_final = elegido.get("underlying_asset.price", np.nan)
        spot_final = float(spot_final) if not pd.isna(spot_final) else S

        resultado = dict(
            spot=spot_final,
            iv=float(elegido.get("implied_volatility", np.nan)) if not pd.isna(elegido.get("implied_volatility", np.nan)) else np.nan,
            delta=float(elegido.get("greeks.delta", np.nan)) if not pd.isna(elegido.get("greeks.delta", np.nan)) else np.nan,
            gamma=float(elegido.get("greeks.gamma", np.nan)) if not pd.isna(elegido.get("greeks.gamma", np.nan)) else np.nan,
            vega=float(elegido.get("greeks.vega", np.nan)) if not pd.isna(elegido.get("greeks.vega", np.nan)) else np.nan,
            theta=float(elegido.get("greeks.theta", np.nan)) if not pd.isna(elegido.get("greeks.theta", np.nan)) else np.nan,
        )
    except Exception:
        resultado = None

    if not transitorio:
        _polygon_cache[ticker] = resultado
    return resultado


def get_atm_iv_safe(ticker):
    if get_currency_for_ticker(ticker) != "USD":
        return np.nan
    poly = get_polygon_option_snapshot(ticker)
    if poly is not None and not pd.isna(poly["iv"]) and poly["iv"] > 0:
        return poly["iv"]
    return np.nan


# ==============================================================================
# FUNCIONES BKM (Bakshi, Kapadia y Madan, 2003)
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


def bkm_fetch_otm_chain(ticker, target_dte, dte_tol, S, moneyness_lo, moneyness_hi):
    """Cadena OTM paginada de un unico vencimiento (el mas cercano a target_dte)."""
    hoy = date.today()
    fecha_min = (hoy + timedelta(days=max(target_dte - dte_tol, 1))).strftime("%Y-%m-%d")
    fecha_max = (hoy + timedelta(days=target_dte + dte_tol)).strftime("%Y-%m-%d")
    return pc.fetch_otm_chain(
        pc.polygon_format_ticker(ticker), S, fecha_min, fecha_max,
        round(S * moneyness_lo, 2), round(S * moneyness_hi, 2),
        target_dte, api_key=POLYGON_API_KEY, strike_fmt="{:.2f}", min_dte=dte_min_iv)


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


def _bkm_vacio(motivo):
    return dict(mfiv=np.nan, mfis=np.nan, mfik=np.nan, mu=np.nan, ok=False, motivo=motivo)


def bkm_compute_moments(S, r, T, calls_df, puts_df):
    n_c = 0 if calls_df is None else len(calls_df)
    n_p = 0 if puts_df is None else len(puts_df)
    if T <= 0 or S <= 0:
        return _bkm_vacio("spot_o_plazo_invalido")
    if n_c < bkm_min_options_per_side or n_p < bkm_min_options_per_side:
        return _bkm_vacio(f"pocas_opciones_otm (calls={n_c}, puts={n_p}, min={bkm_min_options_per_side})")

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

    # rk.trapezoid: np.trapezoid (numpy >= 2) o np.trapz. Antes np.trapezoid
    # fallaba con numpy 1.x dentro de este try y TODOS los activos caian al
    # historico en silencio (A-1).
    try:
        V = rk.trapezoid(fC_V, Kc) + rk.trapezoid(fP_V, Kp)
        W = rk.trapezoid(fC_W, Kc) - rk.trapezoid(fP_W, Kp)
        X = rk.trapezoid(fC_X, Kc) + rk.trapezoid(fP_X, Kp)
    except Exception as e:
        return _bkm_vacio(f"integracion_fallida ({type(e).__name__})")

    erT = math.exp(r * T)
    mu = erT - 1 - erT / 2 * V - erT / 6 * W - erT / 24 * X
    mfiv = erT * V - mu ** 2
    if not np.isfinite(mfiv) or mfiv <= 0:
        return _bkm_vacio("mfiv_no_positiva")

    mfis = (erT * W - 3 * mu * erT * V + 2 * mu ** 3) / mfiv ** 1.5
    mfik = (erT * X - 4 * mu * erT * W + 6 * erT * mu ** 2 * V - 3 * mu ** 4) / mfiv ** 2

    motivo = None
    dte_chain = float(T) * rk.DAYS_PER_YEAR
    cap_mfik = rk.mfik_cap_tenor(
        n_c + n_p, dte_chain, ref_dte=float(target_dte_iv),
        base=bkm_mfik_max, hard=bkm_mfik_max_hard)
    if not rk.higher_moments_admissible(mfis, mfik, cap_mfik):
        motivo = (f"momentos_inadmisibles (MFIS={mfis:.2f}, MFIK={mfik:.2f}, "
                  f"tope={cap_mfik:.1f} a {dte_chain:.0f}d vs ref {target_dte_iv}d "
                  f"con {n_c + n_p} strikes OTM; MFIV se conserva)")
        mfis, mfik = np.nan, np.nan

    return dict(mfiv=mfiv, mfis=float(mfis), mfik=float(mfik), mu=mu, ok=True, motivo=motivo)


def bkm_get_current_moments(ticker, target_dte, dte_tol, rf):
    S = get_spot_safe(ticker)
    if pd.isna(S) or S <= 0:
        mom = _bkm_vacio("sin_spot_yahoo")
        mom.update(spot=np.nan, dte=np.nan, transitorio=False)
        return mom
    calls_df, puts_df, info_cadena = bkm_fetch_otm_chain(ticker, target_dte, dte_tol, S,
                                                         bkm_moneyness_lo, bkm_moneyness_hi)
    if not info_cadena["completo"]:
        status = info_cadena["status"]
        mom = _bkm_vacio("sin_api_key" if status == "sin_api_key" else f"cadena_incompleta (status {status})")
        mom.update(spot=S, dte=np.nan, expiracion=None, transitorio=pc.es_transitorio(status))
        return mom
    if calls_df.empty and puts_df.empty:
        mom = _bkm_vacio("sin_cadena_en_ventana_dte")
        mom.update(spot=S, dte=np.nan, expiracion=None, transitorio=False)
        return mom

    # Plazo REAL de los contratos elegidos (A-3): la MFIV es la varianza
    # integrada hasta ese vencimiento, no hasta target_dte ni hasta el
    # horizonte del portafolio.
    dte = info_cadena["dte"] if np.isfinite(info_cadena["dte"]) and info_cadena["dte"] > 0 else target_dte
    T = rk.to_years(dte=dte)
    calls_df = bkm_iv_chain_to_prices(S, rf, T, calls_df)
    puts_df = bkm_iv_chain_to_prices(S, rf, T, puts_df)
    mom = bkm_compute_moments(S, rf, T, calls_df, puts_df)
    mom.update(spot=S, dte=int(dte), expiracion=info_cadena["expiracion"], transitorio=False)
    return mom


bkm_moments_cache = {}


def bkm_get_current_moments_cached(ticker):
    if ticker in bkm_moments_cache:
        return bkm_moments_cache[ticker]
    if not use_iv_for_horizon:
        mom = _bkm_vacio("opciones desactivadas")
        mom.update(spot=np.nan, dte=np.nan)
    elif get_currency_for_ticker(ticker) != "USD" or is_non_us_exchange(ticker):
        mom = _bkm_vacio("sin_opciones_en_polygon (no cotiza en EE. UU.)")
        mom.update(spot=np.nan, dte=np.nan)
    else:
        mom = bkm_get_current_moments(ticker, target_dte_iv, dte_tol_iv, risk_free_rate)
    if not mom.get("transitorio"):
        bkm_moments_cache[ticker] = mom
    return mom


def bkm_annual_vol(ticker, medida="Q"):
    """Vol anual desde la MFIV del ticker, anualizada con el DTE real de la cadena (A-3).

    medida="P" aplica la correccion Q->P con la vol historica del propio ticker.
    NaN si no hay MFIV valida.
    """
    mom = bkm_get_current_moments_cached(ticker)
    if not (mom["ok"] and np.isfinite(mom["mfiv"]) and mom["mfiv"] > 0):
        return np.nan
    vol_q = rk.implied_variance_to_horizon(mom["mfiv"], mom["dte"], 1.0)["annual_vol"]
    if medida == "Q" or not use_q_to_p_vol:
        return vol_q
    hv = log_returns[ticker].std() * math.sqrt(annualization_factor) if ticker in log_returns.columns else np.nan
    return rk.q_to_p_vol(vol_q, hv, ratio_bounds=vrp_ratio_bounds, fallback_ratio=vrp_fallback_ratio)[0]


def bkm_motivo_fallback(ticker):
    """Motivo por el que un ticker no tiene momentos BKM completos (None si los tiene)."""
    mom = bkm_moments_cache.get(ticker)
    if mom is None:
        return "no consultado"
    if mom.get("ok") and np.isfinite(mom.get("mfis", np.nan)):
        return None
    return mom.get("motivo") or "desconocido"


def bkm_resumen_fallbacks(tickers, titulo):
    """Tabla por ticker y conteo por motivo de los que cayeron al estimador historico (A-1)."""
    filas = []
    for t in tickers:
        mom = bkm_moments_cache.get(t, {})
        filas.append(dict(Ticker=t,
                          MFIV="OK" if np.isfinite(mom.get("mfiv", np.nan)) else "-",
                          MFIS_MFIK="OK" if np.isfinite(mom.get("mfis", np.nan)) else "-",
                          DTE=mom.get("dte", np.nan),
                          Motivo=bkm_motivo_fallback(t) or "BKM completo"))
    df = pd.DataFrame(filas)
    n_fb = int((df["Motivo"] != "BKM completo").sum())
    print(f"\n  {titulo}: {len(df) - n_fb} con BKM completo | {n_fb} con fallback historico")
    if n_fb:
        conteo = df.loc[df["Motivo"] != "BKM completo", "Motivo"].str.replace(r" \(.*\)$", "", regex=True)
        for motivo, n in conteo.value_counts().items():
            print(f"     {n:>3}  {motivo}")
    disp = df.copy()
    disp["DTE"] = disp["DTE"].map(lambda x: f"{int(x)}" if pd.notna(x) else "-")
    print("  " + disp.to_string(index=False).replace("\n", "\n  "))
    return df


# ==============================================================================
# SPOT E IV ATM (~30 DTE) PARA SHRINKAGE Y GRIEGAS DE DIAGNOSTICO
# ==============================================================================
# El filtro Delta BS que vivia aqui se elimino (M-3): con K = S la delta de la
# call era siempre > 0.5 (observado: 0.535-0.563) y delta_min = 0.30 no
# descartaba ningun activo. Una version "con sentido" (probabilidad implicita
# de caer mas de x%) seria la version gaussiana del filtro de cola BKM +
# Cornish-Fisher que sigue, asi que se evita duplicarlo.
print(f"\nConsultando spot + IV ATM (~{target_dte_iv} DTE) para {len(selected_pre_seasonal)} activos "
      "(uso: shrinkage de covarianza y griegas de diagnostico)...")
spot_cache = {t: get_spot_safe(t) for t in selected_pre_seasonal}
iv_cache = {t: get_atm_iv_safe(t) for t in selected_pre_seasonal}
n_iv_atm = sum(1 for v in iv_cache.values() if pd.notna(v))
print(f"  OK IV ATM obtenida: {n_iv_atm} de {len(selected_pre_seasonal)} (el resto usa vol historica)\n")

# ==============================================================================
# FILTRO ESTACIONAL DE TAIL RISK BKM: VaR_CF (Cornish-Fisher)
# ==============================================================================
print(f"\nAplicando filtro de Tail Risk BKM estacional ({execution_label}) - "
      f"VaR_CF a {tail_risk_filter_confidence * 100:.0f}% de confianza...")
print(f"  VaR_CF al horizonte de {target_dte_iv} dias. MFIS/MFIK de la tabla son los de la cadena; "
      "la cola se calcula con esos momentos escalados al objetivo.")

log_returns_seasonal = log_returns.loc[log_returns.index.month.isin(execution_months), selected_pre_seasonal]

n_seasonal_weeks = len(log_returns_seasonal)
print(f"  OK Semanas dentro de {execution_label} disponibles: {n_seasonal_weeks}")

if tail_risk_hist_fallback:
    print("  Fallback historico ACTIVO: los activos sin BKM valido usan momentos historicos estacionales")


def momentos_cola_historicos(r_semanal, dte=None):
    """Vol, asimetria y exceso de curtosis al plazo `dte` (dias) desde retornos semanales.

    Escalado iid centralizado en rk.scale_moments con h = dte / 7 semanas:
    sigma_T = sigma_w sqrt(h), S_T = S_w / sqrt(h), ExK_T = ExK_w / h.
    Devuelve None si el par resultante no es admisible.
    """
    r = pd.Series(r_semanal).dropna()
    sd_w = r.std()
    if len(r) < 6 or not np.isfinite(sd_w) or sd_w <= 0:
        return None
    dte = target_dte_iv if dte is None or not np.isfinite(dte) else dte
    esc = rk.scale_moments(rk.to_years(weeks=1), rk.to_years(weeks=dte / 7),
                           sd=sd_w, skew=float(skew(r)), exkurt=float(kurtosis(r)))
    if not rk.higher_moments_admissible(esc["skew"], esc["exkurt"] + 3.0, bkm_mfik_max):
        return None
    return dict(sigma_T=esc["sd"], skew=esc["skew"], exkurt=esc["exkurt"], dte=dte)


tail_risk_rows = []
for ticker in selected_pre_seasonal:
    r_seasonal = log_returns_seasonal[ticker].dropna()
    n_obs = len(r_seasonal)
    mu_weekly_seasonal = r_seasonal.mean() if n_obs > 5 else np.nan

    mom = bkm_get_current_moments_cached(ticker)

    fila = dict(Symbol=ticker, MFIV=np.nan, MFIS=np.nan, MFIK=np.nan, VaR_CF=np.nan,
                Seasonal_SD=r_seasonal.std() if n_obs > 1 else np.nan, N_Obs=n_obs, Fuente=None, DTE=np.nan)
    if n_obs < seasonal_min_weeks:
        tail_risk_rows.append(fila)
        continue
    if mom["ok"] and np.isfinite(mom["mfis"]):
        # Momentos crudos de la cadena, escalados al DTE objetivo antes del VaR.
        # La vol Q se lleva a P con la vol historica ESTACIONAL, tambien al
        # objetivo. La tabla guarda MFIS/MFIK sin escalar. La estacionalidad
        # entra por mu_T, esa vol de referencia y N_Obs, no por la superficie.
        dte_chain = mom["dte"] if np.isfinite(mom.get("dte", np.nan)) else target_dte_iv
        esc = rk.scale_bkm_moments(mom["mfiv"], mom["mfis"], mom["mfik"], dte_chain, target_dte_iv)
        sigma_T_q = math.sqrt(esc["mfiv"])
        sd_seasonal_w = r_seasonal.std()
        if use_q_to_p_vol and np.isfinite(sd_seasonal_w) and sd_seasonal_w > 0:
            hv_T = sd_seasonal_w * math.sqrt(target_dte_iv / 7)
            sigma_T = rk.q_to_p_vol(sigma_T_q, hv_T, ratio_bounds=vrp_ratio_bounds,
                                    fallback_ratio=vrp_fallback_ratio)[0]
        else:
            sigma_T = sigma_T_q
        s_T, exk_T = esc["mfis"], esc["mfik"] - 3.0
        dte_t = target_dte_iv
        fila.update(MFIV=mom["mfiv"], MFIS=mom["mfis"], MFIK=mom["mfik"], Fuente="BKM", DTE=dte_chain)
    elif tail_risk_hist_fallback and (hist := momentos_cola_historicos(r_seasonal)) is not None:
        sigma_T, s_T, exk_T, dte_t = hist["sigma_T"], hist["skew"], hist["exkurt"], hist["dte"]
        fila.update(Fuente="Historico", DTE=dte_t)
    else:
        tail_risk_rows.append(fila)
        continue

    mu_T = mu_weekly_seasonal * (dte_t / 7) if not pd.isna(mu_weekly_seasonal) else 0.0
    cola = rk.cornish_fisher_tail(1 - tail_risk_filter_confidence, s_T, exk_T)
    fila["VaR_CF"] = -(mu_T + sigma_T * cola["q"])
    tail_risk_rows.append(fila)

tail_risk_stats = pd.DataFrame(tail_risk_rows)
tail_risk_stats = tail_risk_stats[
    (tail_risk_stats["N_Obs"] >= seasonal_min_weeks) & tail_risk_stats["VaR_CF"].notna()
].sort_values("VaR_CF").reset_index(drop=True)

n_con_tail = len(tail_risk_stats)
n_sin_tail = len(selected_pre_seasonal) - n_con_tail
n_hist_tail = int((tail_risk_stats["Fuente"] == "Historico").sum())

print(f"  OK Candidatos previos al filtro: {len(selected_pre_seasonal)}")
print(f"  OK Con VaR_CF calculable (estacional, >={seasonal_min_weeks} sem): {n_con_tail} "
      f"(BKM: {n_con_tail - n_hist_tail} | historico: {n_hist_tail})")
print(f"  ADVERTENCIA Descartados (sin cobertura BKM, MFIS/MFIK inadmisibles o datos estacionales insuficientes): {n_sin_tail}")

tail_risk_final = tail_risk_stats.head(n_divers_candidates)

print(f"  OK Seleccionados (<={n_divers_candidates}, menor VaR_CF estacional): {len(tail_risk_final)}")

if len(tail_risk_final) < tail_risk_min_survivors:
    print("\n  Diagnostico de llamadas a Polygon:")
    pc.print_diagnostics("    ")
    raise RuntimeError(
        f"Error: solo {len(tail_risk_final)} activos tienen VaR_CF estacional calculable "
        f"(minimo tail_risk_min_survivors = {tail_risk_min_survivors}).\n"
        f"   Consultas a Polygon fallidas por limite de tasa o red tras reintentos: "
        f"{pc.n_fallos_transitorios()}.\n"
        "   Revisa POLYGON_API_KEY y POLYGON_CALLS_PER_MIN, reduce seasonal_min_weeks "
        "o activa tail_risk_hist_fallback = True."
    )

if len(tail_risk_final) < n_divers_candidates * 0.5:
    print(f"\n  ADVERTENCIA: solo {len(tail_risk_final)} tickers sobrevivieron el filtro de Tail Risk estacional.")
    print(f"     Considera reducir seasonal_min_weeks (actual: {seasonal_min_weeks}), ampliar start_date,")
    print("     o ampliar bkm_moneyness_lo/hi.")

tail_risk_final = tail_risk_final.merge(asset_stats[["Symbol", "Volatility", "Sharpe"]], on="Symbol", how="left")

print(f"\n  Candidatos finales ordenados por VaR_CF estacional (Tail Risk Score, {execution_label}):")
seasonal_display = tail_risk_final.copy()
seasonal_display["VaR_CF"] = seasonal_display["VaR_CF"].map(lambda x: f"{x * 100:.3f}%")
seasonal_display["MFIV"] = seasonal_display["MFIV"].map(lambda x: f"{x:.5f}" if pd.notna(x) else "N/D")
seasonal_display["MFIS"] = seasonal_display["MFIS"].map(lambda x: f"{x:.3f}" if pd.notna(x) else "N/D")
seasonal_display["MFIK"] = seasonal_display["MFIK"].map(lambda x: f"{x:.3f}" if pd.notna(x) else "N/D")
seasonal_display["SD_Estacional"] = seasonal_display["Seasonal_SD"].map(lambda x: f"{x:.4f}")
seasonal_display["Sharpe"] = seasonal_display["Sharpe"].map(lambda x: f"{x:.3f}")
print(seasonal_display.rename(columns={"N_Obs": "Semanas"})
      [["Symbol", "Fuente", "VaR_CF", "MFIV", "MFIS", "MFIK", "SD_Estacional", "Semanas", "Sharpe"]]
      .to_string(index=False))

selected_tickers = tail_risk_final["Symbol"].tolist()
spot_cache = {t: spot_cache[t] for t in selected_tickers}
iv_cache = {t: iv_cache[t] for t in selected_tickers}
print(f"\nOK Conjunto tras filtro de Tail Risk BKM estacional: {len(selected_tickers)} tickers\n")

log_returns_selected = log_returns[selected_tickers]

# ==============================================================================
# SECCION 7: ESTADISTICAS DESCRIPTIVAS
# ==============================================================================

print("\n" + "=" * 67)
print("ESTADISTICAS DESCRIPTIVAS DE ACTIVOS SELECCIONADOS")
print(f"Anualizacion x{annualization_factor} | Horizonte: {horizon_label} (~{horizon_weeks:.1f} sem)")
print("=" * 67 + "\n")

descriptive_stats = pd.DataFrame({
    "Symbol": log_returns_selected.columns,
    "Media_Semanal": log_returns_selected.mean().values,
    "SD_Semanal": log_returns_selected.std().values,
    "Retorno_Horizonte": log_returns_selected.mean().values * horizon_weeks,
    "Volatilidad_Horizonte": log_returns_selected.std().values * horizon_sqrt,
    "Retorno_Anual": log_returns_selected.mean().values * annualization_factor,
    "Volatilidad_Anual": log_returns_selected.std().values * math.sqrt(annualization_factor),
    "Asimetria_P": [skew(log_returns_selected[c].dropna()) for c in log_returns_selected.columns],
    "Curtosis_P": [kurtosis(log_returns_selected[c].dropna()) for c in log_returns_selected.columns],
    "Max_Drawdown": [max_drawdown_from_returns(log_returns_selected[c]) for c in log_returns_selected.columns],
})

descriptive_stats["MFIV_T"] = [bkm_moments_cache.get(c, {}).get("mfiv", np.nan) for c in log_returns_selected.columns]
descriptive_stats["MFIS_Q"] = [bkm_moments_cache.get(c, {}).get("mfis", np.nan) for c in log_returns_selected.columns]
descriptive_stats["MFIK_Q"] = [bkm_moments_cache.get(c, {}).get("mfik", np.nan) for c in log_returns_selected.columns]
# Anualizada con el DTE real de cada cadena, no con el horizonte del portafolio (A-3)
descriptive_stats["MFIV_Vol_Anual_Q"] = [bkm_annual_vol(c, medida="Q") for c in log_returns_selected.columns]

disp = descriptive_stats.copy()
for col in ["Retorno_Horizonte", "Volatilidad_Horizonte", "Retorno_Anual", "Volatilidad_Anual",
            "Max_Drawdown", "MFIV_Vol_Anual_Q"]:
    disp[col] = disp[col].map(lambda x: f"{x * 100:.2f}%" if pd.notna(x) else "N/D")
disp["Asimetria_P"] = disp["Asimetria_P"].round(2)
disp["Curtosis_P"] = disp["Curtosis_P"].round(2)
disp["MFIS_Q"] = disp["MFIS_Q"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "N/D")
disp["MFIK_Q"] = disp["MFIK_Q"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "N/D")
print(disp[["Symbol", "Retorno_Horizonte", "Volatilidad_Horizonte", "Retorno_Anual", "Volatilidad_Anual",
            "Asimetria_P", "Curtosis_P", "Max_Drawdown", "MFIV_Vol_Anual_Q", "MFIS_Q", "MFIK_Q"]]
      .to_string(index=False))

# ==============================================================================
# SECCION 8: OPTIMIZACION DE PORTAFOLIOS
# ==============================================================================

print("\n" + "=" * 67)
print("OPTIMIZACION DE PORTAFOLIOS - MINIMO RIESGO DE COLA (BKM) - ESTACIONAL")
print(f"Datos: {n_weeks} semanas | Horizonte: {horizon_label} (~{horizon_weeks:.1f} sem) | "
      f"Activos: {len(selected_tickers)}")
print("=" * 67 + "\n")

mean_ret = log_returns_selected.mean()
sd_ret = log_returns_selected.std()

# ==============================================================================
# MATRIZ DE COVARIANZA: MFIV (BKM) MODEL-FREE IMPLIED VARIANCE
# ==============================================================================
benchmark_iv = "SPY"

print("\nEstimando MFIV (BKM) para covarianza forward-looking...")

# Vol anual Q por activo, anualizada con el DTE real de su cadena (A-3). La
# correccion Q->P se aplica abajo sobre el vector completo (incluye fallbacks).
iv_assets_implied = np.array([bkm_annual_vol(t, medida="Q") for t in selected_tickers])

n_iv_ok = np.sum(~pd.isna(iv_assets_implied))
n_iv_na = np.sum(pd.isna(iv_assets_implied))
print(f"  OK MFIV (BKM) validas: {n_iv_ok} | Sin datos (fallback historico): {n_iv_na}")

sd_hist_annual = sd_ret.values * math.sqrt(annualization_factor)
iv_final = np.where(~pd.isna(iv_assets_implied), iv_assets_implied, sd_hist_annual)
iv_final = np.where(pd.isna(iv_final), sd_hist_annual, iv_final)

# ==============================================================================
# CORRECCION Q -> P: LA MFIV INCLUYE LA PRIMA DE RIESGO DE VARIANZA
# ==============================================================================
iv_final_q = iv_final.copy()
if use_q_to_p_vol:
    iv_final, vrp_ratio = rk.q_to_p_vol(
        iv_final_q, sd_hist_annual,
        ratio_bounds=vrp_ratio_bounds, fallback_ratio=vrp_fallback_ratio)
    print("\n  CORRECCION Q -> P (prima de riesgo de varianza):")
    print(f"     ratio sigma_P/sigma_Q: min={vrp_ratio.min():.3f} | "
          f"mediana={np.median(vrp_ratio):.3f} | max={vrp_ratio.max():.3f}")
    print(f"     vol implicita media:   Q={np.nanmean(iv_final_q) * 100:.2f}% -> "
          f"P={np.nanmean(iv_final) * 100:.2f}%")
else:
    vrp_ratio = np.ones_like(iv_final)
    print("\n  ADVERTENCIA use_q_to_p_vol=False - se optimiza con vol bajo medida Q "
          "(sobrestima el riesgo fisico)")

print("\n  DIAGNOSTICO DE ESCALA:")
print(f"     sd_ret (semanal, primeros 3):      {sd_ret.values[0]:.6f} | {sd_ret.values[1]:.6f} | {sd_ret.values[2]:.6f}")
print(f"     sd_hist_annual (primeros 3):       {sd_hist_annual[0]:.6f} | {sd_hist_annual[1]:.6f} | {sd_hist_annual[2]:.6f}")
print(f"     iv_final (post Q->P, primeros 3):  {iv_final[0]:.6f} | {iv_final[1]:.6f} | {iv_final[2]:.6f}")

# Varianza del factor de mercado en la MISMA medida (P) que la de los activos
# (M-4). Antes SPY y los ETFs sectoriales entraban en Q mientras los activos
# ya estaban corregidos, y la varianza "explicada" podia superar la total.
spy_hist_annual = benchmark_returns.iloc[:, 0].std() * math.sqrt(annualization_factor)
iv_spy_implied_q = bkm_annual_vol(benchmark_iv, medida="Q") if use_iv_for_horizon else np.nan
print(f"     iv_spy_implied (MFIV, Q):          {iv_spy_implied_q if not pd.isna(iv_spy_implied_q) else np.nan}")

if pd.isna(iv_spy_implied_q):
    print("  ADVERTENCIA Sin MFIV para SPY - usando vol historica como fallback")
    iv_spy_implied = spy_hist_annual
elif use_q_to_p_vol:
    iv_spy_implied = rk.q_to_p_vol(iv_spy_implied_q, spy_hist_annual, ratio_bounds=vrp_ratio_bounds,
                                   fallback_ratio=vrp_fallback_ratio)[0]
    print(f"     iv_spy_implied (post Q->P):        {iv_spy_implied:.6f}")
else:
    iv_spy_implied = iv_spy_implied_q

# ==============================================================================
# MODELO DE CORRELACION IMPLICITA: FACTORES (MERCADO + SECTOR + PAIS + FX)
# ==============================================================================
n_sel = len(selected_tickers)

print("\nConstruyendo modelo de correlacion de factores (mercado + sector + pais + fx)...")

sector_etf_map = {
    "Information Technology": "XLK",
    "Health Care": "XLV",
    "Financials": "XLF",
    "Energy": "XLE",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "VOX",
}

ticker_sector_etf = {}
if use_sector_factor:
    try:
        sector_tbl = safe_scrape_table("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        if sector_tbl is None:
            raise ValueError("scraping de sectores fallo")
        sector_tbl = sector_tbl.copy()
        sector_tbl.columns = [str(c).strip().lower().replace(" ", "_") for c in sector_tbl.columns]
        sector_col = "gics_sector" if "gics_sector" in sector_tbl.columns else None
        if sector_col is None:
            raise ValueError("no se encontro columna GICS Sector")
        sector_tbl["symbol"] = sector_tbl["symbol"].astype(str).str.upper().str.replace(".", "-", regex=False)
        sector_tbl["sector_etf"] = sector_tbl[sector_col].map(sector_etf_map)
        sector_tbl = sector_tbl[sector_tbl["sector_etf"].notna()]
        ticker_sector_etf = dict(zip(sector_tbl["symbol"], sector_tbl["sector_etf"]))
    except Exception:
        print("  ADVERTENCIA No se pudo obtener el mapeo de sectores (Wikipedia) - cae a modelo de 1 factor (solo mercado) para domesticos")
        ticker_sector_etf = {}

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
    ticker_sector_etf.update(international_sector_etf_map)

asset_sector_etf = {t: ticker_sector_etf.get(t) for t in selected_tickers}

sectores_presentes = sorted(set(v for v in asset_sector_etf.values() if v is not None))
sectores_sin_precio = [s for s in sectores_presentes if s not in log_returns.columns]
if sectores_sin_precio:
    print(f"  ADVERTENCIA ETFs sectoriales sin precios descargados (se ignoran): {', '.join(sectores_sin_precio)}")
    asset_sector_etf = {t: (None if v in sectores_sin_precio else v) for t, v in asset_sector_etf.items()}

sectores_unicos = sorted(set(v for v in asset_sector_etf.values() if v is not None))
k_sectores = len(sectores_unicos)

n_con_sector = sum(1 for v in asset_sector_etf.values() if v is not None)
print(f"  OK Sector asignado: {n_con_sector} de {n_sel} activos | {k_sectores} sectores distintos en el pool"
      + (f" ({', '.join(sectores_unicos)})" if k_sectores > 0 else ""))

# ==============================================================================
# MAPEO DE PAIS/REGION PARA TICKERS INTERNACIONALES
# ==============================================================================

country_etf_by_suffix = {
    ".TO": "EWC",
    ".DE": "EWG",
    ".L": "EWU",
    ".PA": "EWQ",
    ".MC": "EWP",
    ".T": "EWJ",
}

country_etf_ticker_override = {
    "HSBC": "EWU",
    "BP": "EWU",
}


def get_country_etf_for_ticker(ticker):
    if ticker in country_etf_ticker_override:
        return country_etf_ticker_override[ticker]
    for suf, etf in country_etf_by_suffix.items():
        if ticker.endswith(suf):
            return etf
    return None


asset_country_etf = {}
if use_country_factor:
    asset_country_etf = {t: get_country_etf_for_ticker(t) for t in selected_tickers}

paises_presentes = sorted(set(v for v in asset_country_etf.values() if v is not None))
paises_sin_precio = [p for p in paises_presentes if p not in log_returns.columns]
if paises_sin_precio:
    print(f"  ADVERTENCIA ETFs de pais sin precios descargados (se ignoran): {', '.join(paises_sin_precio)}")
    asset_country_etf = {t: (None if v in paises_sin_precio else v) for t, v in asset_country_etf.items()}

paises_unicos = sorted(set(v for v in asset_country_etf.values() if v is not None))
k_paises = len(paises_unicos)

n_con_pais = sum(1 for v in asset_country_etf.values() if v is not None)
print(f"  OK Pais asignado: {n_con_pais} de {n_sel} activos | {k_paises} paises distintos en el pool"
      + (f" ({', '.join(paises_unicos)})" if k_paises > 0 else ""))

# ==============================================================================
# MAPEO DE MONEDA PARA TICKERS INTERNACIONALES (FACTOR FX)
# ==============================================================================

asset_currency = {}
if use_fx_factor:
    asset_currency = {t: get_currency_for_ticker(t) for t in selected_tickers}

currencies_presentes = sorted(set(
    v for v in asset_currency.values() if v != "USD" and v in fx_weekly_returns.columns
))
k_currencies = len(currencies_presentes)

n_con_fx = sum(1 for v in asset_currency.values() if v != "USD" and v in fx_weekly_returns.columns)
print(f"  OK Moneda no-USD con factor FX: {n_con_fx} de {n_sel} activos | {k_currencies} monedas distintas en el pool"
      + (f" ({', '.join(currencies_presentes)})" if k_currencies > 0 else ""))

# ==============================================================================
# BETAS DE FACTORES POR ACTIVO: r_i ~ r_MKT + r_SECTOR + r_PAIS + r_FX
# ==============================================================================
beta_hist_implied = {}
beta_sector_implied = {}
beta_country_implied = {}
beta_fx_implied = {}

r_mkt_full = benchmark_returns.iloc[:, 0]
var_spy_w = r_mkt_full.var()

for t in selected_tickers:
    r_i = log_returns_selected[t]
    sec_etf = asset_sector_etf.get(t)
    pais_etf = asset_country_etf.get(t)
    cur = asset_currency.get(t)
    fit_ok = False

    covariate_cols = {}
    if sec_etf is not None:
        covariate_cols["sec"] = log_returns[sec_etf].rename("sec")
    if pais_etf is not None:
        covariate_cols["pais"] = log_returns[pais_etf].rename("pais")
    if use_fx_factor and cur is not None and cur != "USD" and cur in fx_weekly_returns.columns:
        covariate_cols["fx"] = fx_weekly_returns[cur].rename("fx")

    if covariate_cols:
        aligned = pd.concat([r_i.rename(t), r_mkt_full.rename("mkt")] + list(covariate_cols.values()), axis=1).dropna()
        if len(aligned) >= 10:
            try:
                X = sm.add_constant(aligned[["mkt"] + list(covariate_cols.keys())])
                y = aligned[t]
                model = sm.OLS(y, X).fit()
                cf = model.params
                if not cf.isna().any() and len(cf) == len(covariate_cols) + 2:
                    beta_hist_implied[t] = cf["mkt"]
                    beta_sector_implied[t] = cf["sec"] if "sec" in covariate_cols else 0.0
                    beta_country_implied[t] = cf["pais"] if "pais" in covariate_cols else 0.0
                    beta_fx_implied[t] = cf["fx"] if "fx" in covariate_cols else 0.0
                    fit_ok = True
            except Exception:
                fit_ok = False

    if not fit_ok:
        aligned2 = pd.concat([r_i, r_mkt_full.rename("mkt")], axis=1).dropna()
        if len(aligned2) >= 6:
            beta_hist_implied[t] = aligned2[t].cov(aligned2["mkt"]) / var_spy_w
        else:
            beta_hist_implied[t] = 1.0
        beta_sector_implied[t] = 0.0
        beta_country_implied[t] = 0.0
        beta_fx_implied[t] = 0.0

beta_hist_arr = np.array([beta_hist_implied[t] for t in selected_tickers])
beta_sector_arr = np.array([beta_sector_implied[t] for t in selected_tickers])
beta_country_arr = np.array([beta_country_implied[t] for t in selected_tickers])
beta_fx_arr = np.array([beta_fx_implied[t] for t in selected_tickers])

print(f"     beta_mercado (primeros 3):        {beta_hist_arr[0]:.4f} | {beta_hist_arr[1]:.4f} | {beta_hist_arr[2]:.4f}")
print(f"     beta_sector (primeros 3):          {beta_sector_arr[0]:.4f} | {beta_sector_arr[1]:.4f} | {beta_sector_arr[2]:.4f}")
print(f"     beta_pais (primeros 3):            {beta_country_arr[0]:.4f} | {beta_country_arr[1]:.4f} | {beta_country_arr[2]:.4f}")
print(f"     beta_fx (primeros 3):              {beta_fx_arr[0]:.4f} | {beta_fx_arr[1]:.4f} | {beta_fx_arr[2]:.4f}")

# ==============================================================================
# MATRIZ DE FACTORES F: MKT + CADA SECTOR PRESENTE + CADA PAIS PRESENTE + CADA MONEDA PRESENTE
# ==============================================================================
factor_names = ["MKT"] + sectores_unicos + paises_unicos + currencies_presentes

factor_returns_mat = pd.DataFrame(index=log_returns.index, columns=factor_names, dtype=float)
factor_returns_mat["MKT"] = r_mkt_full.reindex(log_returns.index)
for s in sectores_unicos:
    factor_returns_mat[s] = log_returns[s]
for p in paises_unicos:
    factor_returns_mat[p] = log_returns[p]
for c in currencies_presentes:
    factor_returns_mat[c] = fx_weekly_returns[c].reindex(log_returns.index)

corr_factors = factor_returns_mat.corr()

iv_factor = {f: np.nan for f in factor_names}
iv_factor["MKT"] = iv_spy_implied
n_factores_q_a_p = 0
# ETFs sectoriales y de pais: MFIV anualizada con su DTE real y corregida Q->P
# con su propia vol historica (M-4), igual que los activos. Sin MFIV -> historica.
for f in sectores_unicos + paises_unicos:
    iv_f = bkm_annual_vol(f, medida="P") if use_iv_for_horizon else np.nan
    if pd.isna(iv_f) or iv_f <= 0:
        iv_f = log_returns[f].std() * math.sqrt(annualization_factor)
    else:
        n_factores_q_a_p += 1
    iv_factor[f] = iv_f
for c in currencies_presentes:
    iv_c = fx_weekly_returns[c].std() * math.sqrt(annualization_factor)
    iv_factor[c] = iv_c
print(f"     factores sector/pais con MFIV (Q->P aplicado): {n_factores_q_a_p} de "
      f"{len(sectores_unicos) + len(paises_unicos)}")

iv_factor_weekly = np.array([iv_factor[f] / math.sqrt(annualization_factor) for f in factor_names])
D_factor = np.diag(iv_factor_weekly)
F_mat = D_factor @ corr_factors.loc[factor_names, factor_names].values @ D_factor

# ==============================================================================
# MATRIZ DE CARGAS B Y COVARIANZA EXPLICADA POR FACTORES
# ==============================================================================
B_load = np.zeros((n_sel, len(factor_names)))
mkt_idx = factor_names.index("MKT")
B_load[:, mkt_idx] = beta_hist_arr
for i, t in enumerate(selected_tickers):
    sec_etf = asset_sector_etf.get(t)
    if sec_etf is not None:
        j = factor_names.index(sec_etf)
        B_load[i, j] = beta_sector_implied[t]
    pais_etf = asset_country_etf.get(t)
    if pais_etf is not None:
        j = factor_names.index(pais_etf)
        B_load[i, j] = beta_country_implied[t]
    cur = asset_currency.get(t)
    if use_fx_factor and cur is not None and cur in currencies_presentes:
        j = factor_names.index(cur)
        B_load[i, j] = beta_fx_implied[t]

Cov_explained = B_load @ F_mat @ B_load.T

print(f"     diag(Cov_explained) rango (semanal): {np.diag(Cov_explained).min():.6f} - {np.diag(Cov_explained).max():.6f}")

# ==============================================================================
# VOLATILIDAD OBJETIVO POR ACTIVO: IV vs HISTORICA (shrinkage), o IV pura
# ==============================================================================
if use_iv_shrinkage:
    sd_hist_annual_weekly = sd_hist_annual / math.sqrt(annualization_factor)
    iv_hist_ratio = iv_final / sd_hist_annual

    dist_from_1 = np.abs(iv_hist_ratio - 1)
    shrink_frac = np.tanh(dist_from_1 / ratio_band)
    lambda_i = shrinkage_min + (shrinkage_max - shrinkage_min) * shrink_frac

    iv_final_weekly = iv_final / math.sqrt(annualization_factor)
    vol_final_weekly = (1 - lambda_i) * iv_final_weekly + lambda_i * sd_hist_annual_weekly
    vol_final_weekly = np.where(pd.isna(vol_final_weekly), sd_hist_annual_weekly, vol_final_weekly)

    print("\n  SHRINKAGE POR ACTIVO (vol implied vs historica, ancla = ratio IV/Hist):")
    print(f"     ratio IV/Hist (primeros 3):        {iv_hist_ratio[0]:.3f} | {iv_hist_ratio[1]:.3f} | {iv_hist_ratio[2]:.3f}")
    print(f"     lambda_i rango:                    {lambda_i.min():.3f} - {lambda_i.max():.3f}")
    print(f"     lambda_i promedio (peso historica): {lambda_i.mean():.3f}")
else:
    vol_final_weekly = iv_final / math.sqrt(annualization_factor)

print(f"     vol_final semanal rango:           {vol_final_weekly.min() * 100:.4f}% - {vol_final_weekly.max() * 100:.4f}%")

# ==============================================================================
# VARIANZA IDIOSINCRATICA
# ==============================================================================
explained_var = np.diag(Cov_explained)
idio_floor = 1e-8
idio_var_raw = vol_final_weekly ** 2 - explained_var
idio_var = np.maximum(idio_var_raw, idio_floor)

cov_mat = Cov_explained + np.diag(idio_var)
cov_mat = pd.DataFrame(cov_mat, index=selected_tickers, columns=selected_tickers)

print(f"     varianza explicada por mercado+sector+pais+fx (rango): {explained_var.min():.6f} - {explained_var.max():.6f}")
print(f"     varianza idiosincratica anadida (rango):       {idio_var.min():.6f} - {idio_var.max():.6f}")
# Activos cuya varianza explicada por factores supera la total: la
# idiosincratica se trunca al piso y su correlacion implicita queda
# sobreestimada (M-4). Con factores y activos en la misma medida deberian
# ser pocos; si son muchos, revisar betas o la correccion Q->P.
idio_en_piso = [t for t, v in zip(selected_tickers, idio_var_raw) if v <= idio_floor]
print(f"     activos con varianza idiosincratica en el piso ({idio_floor:g}): {len(idio_en_piso)} de {n_sel}"
      + (f" -> {', '.join(idio_en_piso)}" if idio_en_piso else ""))
print(f"     diag(cov_mat) final rango:         {np.diag(cov_mat.values).min():.6f} - {np.diag(cov_mat.values).max():.6f}")
print(f"     sqrt(diag(cov_mat)) = vol semanal: {np.sqrt(np.diag(cov_mat.values)).min() * 100:.4f}% - "
      f"{np.sqrt(np.diag(cov_mat.values)).max() * 100:.4f}%")

# ==============================================================================
# BLEND CON COVARIANZA HISTORICA (EWMA diaria + Ledoit-Wolf)
# ==============================================================================
cov_scale_d2w = 252.0 / annualization_factor

# Frecuencia de la covarianza historica (M-2). Con tickers de bolsas no
# estadounidenses en el pool, los cierres diarios no son sincronicos y la
# correlacion diaria Asia/Europa vs EE. UU. queda subestimada: el optimizador
# los veria como diversificadores. En "auto" se pasa a semanal en ese caso.
tickers_no_us_pool = [t for t in selected_tickers if is_non_us_exchange(t)]
if hist_cov_frequency == "auto":
    cov_freq_usada = "weekly" if tickers_no_us_pool else "daily"
else:
    cov_freq_usada = hist_cov_frequency
print(f"\n  Frecuencia covarianza historica: {cov_freq_usada} (config: {hist_cov_frequency}; "
      f"tickers de bolsa no-EE. UU. en el pool: {len(tickers_no_us_pool)})")

daily_sel = None
if cov_freq_usada == "daily":
    faltantes = [t for t in selected_tickers if t not in daily_returns.columns]
    if faltantes:
        print(f"  ADVERTENCIA {len(faltantes)} tickers sin serie diaria "
              f"(se usa la semanal): {', '.join(faltantes[:5])}")
    else:
        daily_sel = daily_returns[selected_tickers].dropna()

if daily_sel is not None and len(daily_sel) >= 60:
    cov_hist_simple, cov_info = rk.cov_ewma_shrunk(
        daily_sel, halflife=cov_halflife_days, scale=cov_scale_d2w,
        shrink=use_lw_shrinkage)
    cov_hist_simple = np.asarray(cov_hist_simple)
    print("\n  COVARIANZA HISTORICA (EWMA + Ledoit-Wolf, base diaria):")
    print(f"     observaciones diarias: {cov_info['n_obs']} | t_eff (Kish): {cov_info['t_eff']:.1f}")
    print(f"     halflife: {cov_halflife_days} dias | delta shrinkage: {cov_info['delta']:.3f} "
          f"({cov_info['delta'] * 100:.0f}% hacia correlacion constante)")
elif len(log_returns_selected.dropna()) >= 60:
    cov_hist_simple, cov_info = rk.cov_ewma_shrunk(
        log_returns_selected, halflife=cov_halflife_weeks, scale=1.0,
        shrink=use_lw_shrinkage)
    cov_hist_simple = np.asarray(cov_hist_simple)
    print("\n  COVARIANZA HISTORICA (EWMA + Ledoit-Wolf, base semanal):")
    print(f"     observaciones semanales: {cov_info['n_obs']} | t_eff (Kish): {cov_info['t_eff']:.1f}")
    print(f"     halflife: {cov_halflife_weeks} semanas | delta shrinkage: {cov_info['delta']:.3f} "
          f"({cov_info['delta'] * 100:.0f}% hacia correlacion constante)")
else:
    cov_hist_simple = log_returns_selected.cov().values
    print("\n  COVARIANZA HISTORICA: muestral semanal (sin datos suficientes para EWMA)")

cov_muestral_ref = log_returns_selected.cov().values
print(f"     vol semanal media: muestral={np.sqrt(np.diag(cov_muestral_ref)).mean() * 100:.3f}% -> "
      f"EWMA+LW={np.sqrt(np.diag(cov_hist_simple)).mean() * 100:.3f}%")

off_diag_factor = cov_mat.values - np.diag(np.diag(cov_mat.values))
off_diag_hist = cov_hist_simple - np.diag(np.diag(cov_hist_simple))
diff_offdiag = np.abs(off_diag_hist - off_diag_factor)
print(f"\n  BLEND CON COVARIANZA HISTORICA (alpha={hist_shrink_alpha:.2f}):")
print(f"     |cov_hist - cov_factor| fuera de diagonal, promedio: {diff_offdiag[np.triu_indices_from(diff_offdiag, k=1)].mean():.6f}")
print(f"     |cov_hist - cov_factor| fuera de diagonal, max:      {diff_offdiag[np.triu_indices_from(diff_offdiag, k=1)].max():.6f}")

cov_mat_values = (1 - hist_shrink_alpha) * cov_mat.values + hist_shrink_alpha * cov_hist_simple

cov_mat = pd.DataFrame(cov_mat_values, index=selected_tickers, columns=selected_tickers)

print(f"     diag(cov_mat) tras blend, rango: "
      f"{np.diag(cov_mat.values).min():.6f} - {np.diag(cov_mat.values).max():.6f}")

eig_vals = np.linalg.eigvalsh(cov_mat.values)
print(f"  Eigenvalue minimo (Sigma final): {eig_vals.min():.6f}")
if not np.all(eig_vals >= -1e-8):
    print("  ADVERTENCIA Sigma final no es PSD - proyectando al cono PSD...")
    cov_mat = rk.nearest_psd(cov_mat, eps_rel=1e-8)

print(f"  OK cov_mat final (factores implicitos + blend historico EWMA/Ledoit-Wolf): "
      f"{cov_mat.shape[0]} x {cov_mat.shape[1]} activos")
print(f"  Rango MFIV anualizada: {iv_final.min() * 100:.1f}% - {iv_final.max() * 100:.1f}%")
print(f"  Rango beta_mercado: {beta_hist_arr.min():.3f} - {beta_hist_arr.max():.3f} | "
      f"Rango beta_sector: {beta_sector_arr.min():.3f} - {beta_sector_arr.max():.3f} | "
      f"Rango beta_pais: {beta_country_arr.min():.3f} - {beta_country_arr.max():.3f} | "
      f"Rango beta_fx: {beta_fx_arr.min():.3f} - {beta_fx_arr.max():.3f}")

# ==============================================================================
# OPTIMIZACION MINIMO RIESGO DE COLA (quadprog, SOBRE Sigma_modificada)
# ==============================================================================
etf_excluded_from_portfolio = set(etf_tickers) - set(commodity_tickers)
use_etf_band = use_etf_constraint and include_etfs_in_portfolio

if include_etfs_in_portfolio:
    optimization_pool = list(selected_tickers)
else:
    etfs_removed = [t for t in selected_tickers if t in etf_excluded_from_portfolio]
    optimization_pool = [t for t in selected_tickers if t not in etf_excluded_from_portfolio]
    print("[INFO] include_etfs_in_portfolio = False: el portafolio resultante solo tendra acciones y commodities")
    print(f"[INFO] ETFs excluidos como candidatos del optimizador ({len(etfs_removed)}): "
          f"{', '.join(etfs_removed) if etfs_removed else 'ninguno'}")
    print(f"[INFO] Activos elegibles para el portafolio: {len(optimization_pool)} de {len(selected_tickers)}")
    if len(optimization_pool) * max_weight_per_asset < min_total_weight - 1e-9:
        raise RuntimeError(
            f"Error: con include_etfs_in_portfolio = False quedan {len(optimization_pool)} acciones/commodities "
            f"elegibles y max_weight_per_asset = {max_weight_per_asset:.2f} no alcanza min_total_weight = "
            f"{min_total_weight:.2f}.\n   Amplia el pool (n_pre_seasonal, volatility_percentile, "
            "correlation_percentile) o sube max_weight_per_asset."
        )

n_etf_en_pool = sum(1 for t in optimization_pool if t in etf_universe_tickers)
if use_etf_band:
    _etf_min, _etf_max, _nota_banda = pq.relax_group_band(
        n_etf_en_pool, len(optimization_pool) - n_etf_en_pool, max_weight_per_asset,
        etf_min_weight, etf_max_weight)
    etf_min_weight, etf_max_weight = _etf_min, _etf_max
    if _nota_banda:
        print(f"  ADVERTENCIA Banda ETF: {_nota_banda}")
    if n_etf_en_pool == 0:
        use_etf_band = False
if use_etf_band:
    print(f"[INFO] Restriccion de participacion ETF activa: {etf_min_weight * 100:.0f}%-{etf_max_weight * 100:.0f}% "
          f"del capital invertido")
    print(f"[INFO] ETFs/commodities en el pool tras filtros previos: {n_etf_en_pool} de {len(optimization_pool)} activos")
    if n_etf_en_pool == 0:
        print("  ADVERTENCIA Ningun ETF sobrevivio a los filtros de score/volatilidad/correlacion/")
        print("     estacionalidad/Tail Risk - la restriccion de % ETF no tendra efecto.")
        print("     Revisa volatility_percentile, correlation_percentile o seasonal_min_weeks si")
        print("     quieres que mas ETFs lleguen a esta etapa.")

n_fx_en_pool = sum(1 for t in optimization_pool if get_currency_for_ticker(t) != "USD")
if use_fx_factor:
    print(f"[INFO] Restriccion de exposicion cambiaria activa: maximo {max_fx_exposure * 100:.0f}% "
          f"del capital invertido en tickers no-USD")
    print(f"[INFO] Tickers no-USD en el pool tras filtros previos: {n_fx_en_pool} de {len(optimization_pool)} activos")
    if n_fx_en_pool == 0:
        print("  ADVERTENCIA Ningun ticker no-USD sobrevivio a los filtros previos - la restriccion")
        print("     de exposicion cambiaria no tendra efecto.")

print(f"\n[INFO] Ejecutando optimizacion iterativa - maximo {max_assets_in_portfolio} activos...")
print("[INFO] Poda ETF/FX-aware activa (constraints_feasible)\n")


def constraints_feasible(tickers_list):
    if len(tickers_list) == 0:
        return False
    if use_etf_band:
        n_etf = sum(1 for t in tickers_list if t in etf_universe_tickers)
        n_stock = len(tickers_list) - n_etf
        if n_stock * max_weight_per_asset < (1 - etf_max_weight) - 1e-9:
            return False
        if n_etf * max_weight_per_asset < etf_min_weight - 1e-9:
            return False
    if use_fx_factor:
        n_fx = sum(1 for t in tickers_list if get_currency_for_ticker(t) != "USD")
        n_usd = len(tickers_list) - n_fx
        if n_usd * max_weight_per_asset < (1 - max_fx_exposure) - 1e-9:
            return False
    return True


def build_qp_constraints(tickers_subset):
    """Restricciones de quadprog para un subconjunto. Ver pq.build_weight_constraints (B-5)."""
    return pq.build_weight_constraints(
        len(tickers_subset),
        min_weight=min_weight_per_asset,
        max_weight=max_weight_per_asset,
        min_total=min_total_weight,
        max_total=max_total_weight,
        require_full_investment=require_full_investment,
        is_etf=[t in etf_universe_tickers for t in tickers_subset],
        use_etf_band=use_etf_band,
        etf_min_weight=etf_min_weight,
        etf_max_weight=etf_max_weight,
        is_non_usd=[get_currency_for_ticker(t) != "USD" for t in tickers_subset],
        use_fx_cap=use_fx_factor,
        max_fx_exposure=max_fx_exposure,
    )


def run_minvar_qp(tickers_subset):
    cm = cov_mat.loc[tickers_subset, tickers_subset].values
    n = len(tickers_subset)
    reg = 1e-6 * np.mean(np.diag(cm))
    Dm = 2 * cm + np.eye(n) * reg
    dv = np.zeros(n)

    cons = build_qp_constraints(tickers_subset)
    Amat_base, bvec_base = cons["Amat_base"], cons["bvec_base"]
    Amat_full, bvec_full, meq = cons["Amat_full"], cons["bvec_full"], cons["meq"]
    extra_cols = cons["has_extra"]

    def solve_attempt(Amat_try, bvec_try):
        try:
            sol = quadprog.solve_qp(Dm, dv, Amat_try, bvec_try, meq)
            w = np.maximum(sol[0], 0)
            return pd.Series(w, index=tickers_subset)
        except Exception as e:
            print(f"    ADVERTENCIA quadprog.solve_qp error: {e}")
            return None

    w = solve_attempt(Amat_full, bvec_full)

    if w is None and extra_cols:
        print("  ADVERTENCIA Restriccion de % ETF/exposicion cambiaria infactible para este subset - "
              "optimizando sin restricciones adicionales")
        w = solve_attempt(Amat_base, bvec_base)

    if w is None:
        print("  ADVERTENCIA quadprog fallo para subset")

    return w


alpha_final = 1 - cornish_fisher_confidence

_panel_pool_df = log_returns_selected[selected_tickers].dropna()
if len(_panel_pool_df) >= panel_min_obs:
    Z_pool, _ = rk.standardized_panel(_panel_pool_df)
    Z_pool_cols = list(_panel_pool_df.columns)
    print(f"  Panel de co-momentos: {Z_pool.shape[0]} semanas x {Z_pool.shape[1]} activos")
else:
    Z_pool, Z_pool_cols = None, []
    print(f"  ADVERTENCIA Panel insuficiente ({len(_panel_pool_df)} < {panel_min_obs} semanas): "
          "la poda usara contribucion marginal a la varianza")


def compute_marginal_cvar_contrib(tickers_subset, w_vec, cm_sub):
    mu_vec = mean_ret.loc[tickers_subset].values

    w_sum = w_vec.sum()
    var_p = float(w_vec @ cm_sub @ w_vec)
    if w_sum <= 0 or var_p <= 1e-12 or Z_pool is None:
        return pd.Series(w_vec * (cm_sub @ w_vec), index=tickers_subset)

    sigma_p = math.sqrt(var_p)

    idx = [Z_pool_cols.index(t) for t in tickers_subset]
    sd_prosp = np.sqrt(np.clip(np.diag(cm_sub), 1e-16, None))
    panel_sub = Z_pool[:, idx] * sd_prosp

    grad = rk.portfolio_moment_gradients(w_vec, panel_sub)

    es_std, d_es_dS, d_es_dK = rk.cornish_fisher_es_gradient(alpha_final, grad["skew"], grad["exkurt"])
    mes_alpha = -es_std

    d_sigma_dw = (cm_sub @ w_vec) / sigma_p
    d_mes_dw = -(d_es_dS * grad["d_skew_dw"] + d_es_dK * grad["d_exkurt_dw"])

    d_risk_dw = -mu_vec + mes_alpha * d_sigma_dw + sigma_p * d_mes_dw

    return pd.Series(w_vec * d_risk_dw, index=tickers_subset)


current_tickers = list(optimization_pool)
iteration = 0
w_last_valid = None
tickers_last_valid = None

while True:
    iteration += 1
    w_iter = run_minvar_qp(current_tickers)

    if w_iter is None:
        print("  ADVERTENCIA Optimizacion fallo para este subset - usando la ultima solucion valida")
        break

    w_last_valid = w_iter
    tickers_last_valid = current_tickers

    active = w_iter[w_iter > 0.001]
    n_active = len(active)

    cm_iter = cov_mat.loc[current_tickers, current_tickers].values
    w_vec = w_iter.values
    vol_iter = math.sqrt(float(w_vec @ cm_iter @ w_vec))

    print(f"  Iteracion {iteration}: {n_active} activos activos | Vol semanal (tail-adj): {vol_iter * 100:.4f}%")

    bajo_umbral = [t for t in current_tickers if w_iter[t] < prune_below_weight]
    if bajo_umbral:
        remaining = [t for t in current_tickers if t not in bajo_umbral]
        if (len(remaining) >= 3
                and len(remaining) * max_weight_per_asset >= min_total_weight - 1e-9
                and constraints_feasible(remaining)):
            current_tickers = remaining
            print(f"    -> Recortando {len(bajo_umbral)} activos con peso < "
                  f"{prune_below_weight * 100:.1f}%: {', '.join(bajo_umbral)}")
            continue
        print(f"    (no se recortan en bloque los {len(bajo_umbral)} activos con peso < "
              f"{prune_below_weight * 100:.1f}% - dejaria el portafolio infactible)")

    if n_active <= max_assets_in_portfolio:
        break

    mtr = compute_marginal_cvar_contrib(current_tickers, w_vec, cm_iter)
    # Solo se ordenan los activos por encima del piso de 0.1%: los que ya estan
    # en el piso no reducen n_active y no aparecen en `active`.
    orden_poda = pq.prune_order(active, mtr, tail_prune_rule)

    drop_ticker = None
    for candidate in orden_poda:
        remaining = [t for t in current_tickers if t != candidate]
        if constraints_feasible(remaining):
            drop_ticker = candidate
            break
        else:
            print(f"    (saltando '{candidate}' como candidato a eliminar - "
                  f"dejaria la banda ETF/FX estructuralmente infactible)")

    if drop_ticker is None:
        drop_ticker = orden_poda[0]
        print("    ADVERTENCIA: ninguna eliminacion preserva la banda ETF/FX factible - "
              f"eliminando igual ({tail_prune_rule})")

    current_tickers = [t for t in current_tickers if t != drop_ticker]
    print(f"    -> Eliminando '{drop_ticker}' ({tail_prune_rule}, "
          f"MTR={mtr[drop_ticker]:.6f}, peso {w_iter[drop_ticker] * 100:.3f}%)")

    if len(current_tickers) < 3:
        print("  ADVERTENCIA Quedan menos de 3 activos - deteniendo iteracion")
        break

if w_last_valid is None:
    raise RuntimeError(
        "Error: la optimizacion de minimo riesgo de cola no encontro ninguna solucion factible.\n"
        "   Revisa: (1) que cov_mat sea PSD, (2) min_weight_per_asset * n_activos <= max_total_weight,\n"
        "   (3) max_weight_per_asset * n_activos >= min_total_weight, (4) la restriccion ETF\n"
        "   (etf_min_weight/etf_max_weight) si use_etf_constraint e include_etfs_in_portfolio = True, y (5) la restriccion\n"
        "   de exposicion cambiaria (max_fx_exposure) si use_fx_factor = True."
    )

w_iter = w_last_valid
selected_tickers = w_iter[w_iter > 0.001].index.tolist()
w_final_implied = w_iter[selected_tickers]

print(f"\nOK Portafolio final: {len(selected_tickers)} activos (limite: {max_assets_in_portfolio})")
print(f"  Activos: {', '.join(selected_tickers)}\n")

log_returns_selected = log_returns[selected_tickers]
mean_ret = log_returns_selected.mean()
cov_mat = cov_mat.loc[selected_tickers, selected_tickers]
sd_ret = log_returns_selected.std()

opt_min_var = dict(weights=w_final_implied, selected=selected_tickers)

# ==============================================================================
# SECCION 9: FRONTERA EFICIENTE
# ==============================================================================

print("[INFO] Calculando Frontera Eficiente...")

min_ret = mean_ret.min() * horizon_weeks
max_ret = mean_ret.max() * horizon_weeks
target_returns = np.linspace(min_ret, max_ret, 50)

n = len(selected_tickers)
Dmat_ef = 2 * cov_mat.values + np.eye(n) * (1e-6 * np.mean(np.diag(cov_mat.values)))
dvec_ef = np.zeros(n)

# Mismas restricciones que el optimizador (cotas, inversion total, banda ETF,
# tope FX) mas el retorno objetivo (B-5). Los puntos infactibles se cuentan en
# vez de silenciarse: quadprog lanza ValueError cuando no hay solucion.
cons_ef = build_qp_constraints(selected_tickers)
efficient_frontier_rows = []
n_ef_infactibles = 0
for target_ret in target_returns:
    target_weekly = target_ret / horizon_weeks
    Amat, bvec, meq_ef = pq.with_return_target(cons_ef, mean_ret.values, target_weekly)
    try:
        sol = quadprog.solve_qp(Dmat_ef, dvec_ef, Amat, bvec, meq_ef)
    except ValueError:
        n_ef_infactibles += 1
        continue
    w_sol = sol[0].copy()
    w_sol[w_sol < 1e-6] = 0

    ret = float(np.sum(w_sol * mean_ret.values)) * horizon_weeks
    risk = math.sqrt(float(w_sol @ cov_mat.values @ w_sol)) * horizon_sqrt
    efficient_frontier_rows.append(dict(Return=ret, Risk=risk))

efficient_frontier = pd.DataFrame(efficient_frontier_rows, columns=["Return", "Risk"])
print(f"[INFO] Frontera eficiente calculada con {len(efficient_frontier)} puntos"
      f"{f' ({n_ef_infactibles} objetivos infactibles con las bandas ETF/FX)' if n_ef_infactibles else ''}.")

# ==============================================================================
# SECCION 10: EXTRACCION DE METRICAS
# ==============================================================================


def extract_metrics(opt_obj, label):
    w_raw = opt_obj["weights"]
    common = [t for t in w_raw.index if t in log_returns_selected.columns]
    w = w_raw[common]
    mr = mean_ret[common]
    cm = cov_mat.loc[common, common]
    ret_mat = log_returns_selected[common]

    total_weight = w.sum()
    cash_position = 1 - total_weight

    w_vec = w.values
    ret_horizon = float(np.sum(w_vec * mr.values)) * horizon_weeks
    risk_horizon = math.sqrt(float(w_vec @ cm.values @ w_vec)) * horizon_sqrt
    sharpe_horizon = (ret_horizon - rf_horizon) / risk_horizon

    ret_annual = float(np.sum(w_vec * mr.values)) * annualization_factor
    risk_annual = math.sqrt(float(w_vec @ cm.values @ w_vec)) * math.sqrt(annualization_factor)
    sharpe_annual = (ret_annual - risk_free_rate) / risk_annual

    ret_weekly = float(np.sum(w_vec * mr.values))
    risk_weekly = math.sqrt(float(w_vec @ cm.values @ w_vec))

    # Log-retorno exacto del portafolio (B-2); el efectivo no invertido rinde 0.
    port_returns = rk.portfolio_log_returns(ret_mat, w)
    mdd = max_drawdown_from_returns(port_returns)

    port_excess = port_returns.values - risk_free_rate_weekly
    downside_neg = port_excess[port_excess < 0]
    downside_dev = math.sqrt(np.mean(downside_neg ** 2)) if len(downside_neg) else np.nan
    sortino_horizon = (ret_horizon - rf_horizon) / (downside_dev * horizon_sqrt)
    sortino_annual = (ret_annual - risk_free_rate) / (downside_dev * math.sqrt(annualization_factor))

    return dict(
        Label=label, Return_Horizon=ret_horizon, Risk_Horizon=risk_horizon,
        Sharpe_Horizon=sharpe_horizon, Sortino_Horizon=sortino_horizon, RF_Horizon=rf_horizon,
        Return_Annual=ret_annual, Risk_Annual=risk_annual, Sharpe_Annual=sharpe_annual,
        Sortino_Annual=sortino_annual, Return_Weekly=ret_weekly, Risk_Weekly=risk_weekly,
        MaxDrawdown=mdd, Weights=w, Total_Weight=total_weight, Cash_Position=cash_position,
    )


metrics_minvar = extract_metrics(opt_min_var, "Minimo Riesgo de Cola")

# ==============================================================================
# VaR/CVaR (Expected Shortfall) prospectivo global, Cornish-Fisher
# ==============================================================================

w_final_bkm = metrics_minvar["Weights"]
w_final_vals = w_final_bkm.values
tickers_final = list(w_final_bkm.index)

mfis_final = np.array([bkm_moments_cache.get(t, {}).get("mfis", np.nan) for t in tickers_final])
mfik_final = np.array([bkm_moments_cache.get(t, {}).get("mfik", np.nan) for t in tickers_final])

panel_source = log_returns_selected[tickers_final].dropna()

if len(panel_source) >= panel_min_obs:
    Z_panel, _ = rk.standardized_panel(panel_source)
    sd_prospectiva = np.sqrt(np.diag(cov_mat.loc[tickers_final, tickers_final].values))
    panel_final = rk.rescale_panel(Z_panel, panel_source.mean().values, sd_prospectiva)

    mom_port = rk.portfolio_moments(w_final_vals, panel_final)
    port_skew_final = mom_port["skew"]           # semanal
    port_kurt_exc_final = mom_port["exkurt"]     # semanal

    mask_q = np.isfinite(mfis_final) & np.isfinite(mfik_final)
    if mask_q.sum() > 0 and w_final_vals[mask_q].sum() > 0:
        w_q = w_final_vals[mask_q] / w_final_vals[mask_q].sum()
        skew_naive = float(np.sum(w_q * mfis_final[mask_q]))
        kurt_naive = float(np.sum(w_q * mfik_final[mask_q])) - 3.0
    else:
        skew_naive, kurt_naive = np.nan, np.nan

    print("\n  MOMENTOS DEL PORTAFOLIO (co-momentos, medida P):")
    print(f"     panel: {len(panel_source)} semanas x {len(tickers_final)} activos")
    print(f"     asimetria:          {port_skew_final:+.4f}"
          + (f"   (atajo Q anterior: {skew_naive:+.4f})" if np.isfinite(skew_naive) else ""))
    print(f"     exceso de curtosis: {port_kurt_exc_final:+.4f}"
          + (f"   (atajo Q anterior: {kurt_naive:+.4f})" if np.isfinite(kurt_naive) else ""))

    port_sd_horizon = metrics_minvar["Risk_Horizon"]
    port_mu_horizon = metrics_minvar["Return_Horizon"]

    # El panel es semanal; mu y sigma ya estan al horizonte. Asimetria y exceso
    # de curtosis se llevan al horizonte con la regla iid (S/sqrt(h), K/h),
    # la misma que usa el filtro por activo (A-4). Antes se mezclaban momentos
    # semanales con sigma al horizonte y el CVaR quedaba sobreestimado.
    esc_port = rk.scale_moments(rk.to_years(weeks=1), rk.to_years(weeks=horizon_weeks),
                                skew=port_skew_final, exkurt=port_kurt_exc_final)
    port_skew_horizon = esc_port["skew"]
    port_kurt_exc_horizon = esc_port["exkurt"]

    cf_res = rk.var_cvar_cornish_fisher(
        port_mu_horizon, port_sd_horizon, port_skew_horizon, port_kurt_exc_horizon,
        confidence=cornish_fisher_confidence)

    var_cf_final = cf_res["var"]
    cvar_cf_final = cf_res["cvar"]

    if not cf_res["exact"]:
        print("     AVISO: la familia Cornish-Fisher no alcanza estos momentos; se usaron")
        print("     los alcanzables mas cercanos (Maillard, 2012).")
        print(f"     Referencia gaussiana -> VaR {cf_res['var_gaussian'] * 100:.4f}% | "
              f"CVaR {cf_res['cvar_gaussian'] * 100:.4f}%")
else:
    port_skew_final, port_kurt_exc_final = np.nan, np.nan
    port_skew_horizon, port_kurt_exc_horizon = np.nan, np.nan
    var_cf_final, cvar_cf_final = np.nan, np.nan
    print(f"  ADVERTENCIA: solo {len(panel_source)} semanas (<{panel_min_obs}) para el panel "
          "- VaR/CVaR Cornish-Fisher = NaN")

# ==============================================================================
# SECCION 11: VISUALIZACIONES
# ==============================================================================

print("\n[INFO] Generando visualizaciones...")

df_points = pd.DataFrame({
    "Label": ["Minimo Riesgo de Cola"],
    "Risk": [metrics_minvar["Risk_Horizon"]],
    "Return": [metrics_minvar["Return_Horizon"]],
})

asset_metrics = pd.DataFrame({
    "Symbol": log_returns_selected.columns,
    "Return": mean_ret.values * horizon_weeks,
    "Risk": sd_ret.values * horizon_sqrt,
})

ef_sorted = efficient_frontier.sort_values("Risk") if len(efficient_frontier) > 0 else efficient_frontier
frontier_plot_df = pd.DataFrame({
    "Nombre": "Frontera eficiente", "Categoria": "Frontera eficiente",
    "Risk": ef_sorted["Risk"], "Return": ef_sorted["Return"],
}) if len(ef_sorted) > 0 else pd.DataFrame(columns=["Nombre", "Categoria", "Risk", "Return"])
activos_plot_df = pd.DataFrame({
    "Nombre": asset_metrics["Symbol"], "Categoria": "Activos individuales",
    "Risk": asset_metrics["Risk"], "Return": asset_metrics["Return"],
})
optimo_plot_df = pd.DataFrame({
    "Nombre": df_points["Label"], "Categoria": "Portafolio optimo",
    "Risk": df_points["Risk"], "Return": df_points["Return"],
})

fig = px.scatter(
    pd.concat([frontier_plot_df, activos_plot_df, optimo_plot_df], ignore_index=True),
    x="Risk", y="Return", color="Categoria", hover_name="Nombre",
    color_discrete_map={
        "Frontera eficiente": "#08519c",
        "Activos individuales": "#ff7f00",
        "Portafolio optimo": "#2ca25f",
    },
    labels={"Risk": f"Riesgo acumulado horizonte ({horizon_label})",
            "Return": f"Retorno esperado acumulado ({horizon_label})", "Categoria": ""},
)
if len(ef_sorted) > 0:
    fig.add_trace(go.Scatter(x=ef_sorted["Risk"], y=ef_sorted["Return"], mode="lines",
                              line=dict(color="#08519c", width=2), opacity=0.6,
                              name="Frontera eficiente", showlegend=False, hoverinfo="skip"))
fig.update_traces(marker=dict(size=6, opacity=0.5), selector=dict(name="Frontera eficiente"))
fig.update_traces(marker=dict(size=9, opacity=0.75), selector=dict(name="Activos individuales"))
fig.update_traces(marker=dict(size=16, line=dict(width=1.5, color="black")), selector=dict(name="Portafolio optimo"))
fig.update_layout(
    title=dict(text="Frontera Eficiente - Minimo Riesgo de Cola (BKM, estacional)<br>"
                     f"<sup>Horizonte: {horizon_label} (~{horizon_weeks:.1f} sem) | Periodo datos: {start_date} -> "
                     f"{end_date:%Y-%m-%d} | {len(selected_tickers)} activos</sup>"),
    xaxis_tickformat=".1%", yaxis_tickformat=".1%",
    template="plotly_white",
)
fig.show()


def prepare_weights_with_cash(weights, total_weight, label):
    df = pd.DataFrame({"Symbol": weights.index, "Weight": weights.values, "Portfolio": label})
    if not require_full_investment and abs(1 - total_weight) > 0.001:
        df = pd.concat([df, pd.DataFrame({"Symbol": ["EFECTIVO"], "Weight": [1 - total_weight],
                                           "Portfolio": [label]})], ignore_index=True)
    return df


df_weights = prepare_weights_with_cash(metrics_minvar["Weights"], metrics_minvar["Total_Weight"], "Minimo Riesgo de Cola")

df_weights_plot = df_weights.sort_values("Weight", ascending=True)
fig = px.bar(
    df_weights_plot, x="Weight", y="Symbol", orientation="h",
    text=df_weights_plot["Weight"].map(lambda x: f"{x * 100:.1f}%"),
    labels={"Weight": "Peso del portafolio", "Symbol": ""},
    color_discrete_sequence=["#2ca25f"],
)
fig.update_traces(textposition="outside", marker_line_width=0,
                   hovertemplate="%{y}: %{x:.2%}<extra></extra>")
fig.update_layout(
    title=dict(text="Asignacion Optima de Activos - Minimo Riesgo de Cola (estacional)<br>"
                     f"<sup>Horizonte: {horizon_label} | Peso max por activo: {max_weight_per_asset * 100:.0f}%</sup>"),
    xaxis_tickformat=".0%",
    template="plotly_white",
    showlegend=False,
    height=max(400, 24 * len(df_weights_plot)),
)
fig.show()

corr_matrix = log_returns_selected.corr()
try:
    dist = 1 - corr_matrix.abs()
    condensed = squareform(dist.values, checks=False)
    Z = linkage(condensed, method="average")
    order = leaves_list(Z)
    corr_ordered = corr_matrix.iloc[order, order]
except Exception:
    corr_ordered = corr_matrix

fig = px.imshow(
    corr_ordered.values, x=corr_ordered.columns, y=corr_ordered.columns,
    color_continuous_scale="RdBu", zmin=-1, zmax=1, text_auto=".2f", aspect="auto",
    labels=dict(color="Correlacion"),
)
fig.update_xaxes(tickangle=90)
fig.update_traces(textfont_size=8, hovertemplate="%{x} vs %{y}: %{z:.2f}<extra></extra>")
fig.update_layout(
    title=f"Matriz de Correlacion - {len(selected_tickers)} activos seleccionados",
    template="plotly_white",
)
fig.show()

# ==============================================================================
# SECCION 12: RESUMEN FINAL
# ==============================================================================

print("\n" + "=" * 65)
print("PORTAFOLIO OPTIMO - MINIMO RIESGO DE COLA (BKM + CORNISH-FISHER) - ESTACIONAL")
print("=" * 65)
print(f"    Entrenado con : {n_weeks} semanas ({start_date} -> {end_date:%Y-%m-%d})")
print(f"    Horizonte     : {horizon_label} (~{horizon_weeks:.1f} semanas)")
print(f"    RF horizonte  : {rf_horizon * 100:.4f}%\n")

w_final = metrics_minvar["Weights"]
w_final = w_final[w_final > 0.001].sort_values(ascending=False)

print(f"  {'Ticker':<8}  {'Peso':>8}")
print("  " + "-" * 52)
for nm, val in w_final.items():
    barra = "#" * round(val * 100 / 2)
    print(f"  {nm:<8}  {val * 100:6.2f}%   {barra}")
print("  " + "-" * 52)
print(f"  {'TOTAL':<8}  {w_final.sum() * 100:6.2f}%\n")

if abs(metrics_minvar["Cash_Position"]) > 0.001:
    if metrics_minvar["Cash_Position"] > 0:
        print(f"  Posicion en efectivo: {metrics_minvar['Cash_Position'] * 100:.2f}%\n")
    else:
        print(f"  ADVERTENCIA Apalancamiento: {abs(metrics_minvar['Cash_Position']) * 100:.2f}%\n")

print(f"  Activos en portafolio : {len(w_final)}")
print(f"  Peso maximo           : {w_final.max() * 100:.2f}% ({w_final.index[0]})")
print(f"  Concentracion top 3   : {w_final.head(3).sum() * 100:.2f}%")

fx_weight_final = sum(w_final.get(t, 0.0) for t in w_final.index if get_currency_for_ticker(t) != "USD")
print(f"  Exposicion cambiaria  : {fx_weight_final * 100:.2f}% (limite: {max_fx_exposure * 100:.0f}%)")
print("=" * 65 + "\n")

# ==============================================================================
# ATRIBUCION DE RIESGO SINTETICA (GRIEGAS BLACK-SCHOLES) - DIAGNOSTICO
# ==============================================================================
print("ATRIBUCION DE RIESGO SINTETICA (GRIEGAS BSM) - DIAGNOSTICO")
print("=" * 65)

T_greeks = horizon_months / 12
mu_weekly_g = log_returns[list(w_final.index)].mean()

greeks_rows = []
for tk in w_final.index:
    S = spot_cache.get(tk, np.nan)
    iv = iv_cache.get(tk, np.nan)
    if iv is None or pd.isna(iv) or iv <= 0:
        iv = log_returns[tk].std() * math.sqrt(annualization_factor)
    if S is None or pd.isna(S) or S <= 0 or pd.isna(iv) or iv <= 0:
        greeks_rows.append(dict(Ticker=tk, Weight=w_final[tk], Delta=np.nan, Gamma=np.nan, Vega=np.nan, Theta=np.nan))
        continue

    mu_i = mu_weekly_g.get(tk, 0.0)
    mu_i = 0.0 if pd.isna(mu_i) else mu_i

    if delta_strike_mode == "atm":
        K = S
    elif delta_strike_mode == "rf":
        K = S * (1 + risk_free_rate * T_greeks)
    elif delta_strike_mode == "mu":
        K = S * (1 + mu_i * horizon_weeks)
    else:
        K = S

    d1 = (math.log(S / K) + (risk_free_rate + iv ** 2 / 2) * T_greeks) / (iv * math.sqrt(T_greeks))
    d2 = d1 - iv * math.sqrt(T_greeks)

    delta_i = norm.cdf(d1)
    gamma_raw = norm.pdf(d1) / (S * iv * math.sqrt(T_greeks))
    vega_raw = S * norm.pdf(d1) * math.sqrt(T_greeks) / 100
    theta_raw = (-(S * norm.pdf(d1) * iv) / (2 * math.sqrt(T_greeks))
                 - risk_free_rate * K * math.exp(-risk_free_rate * T_greeks) * norm.cdf(d2)) / 365

    gamma_i = gamma_raw / S
    vega_i = vega_raw / S
    theta_i = theta_raw / S

    greeks_rows.append(dict(Ticker=tk, Weight=w_final[tk], Delta=delta_i, Gamma=gamma_i, Vega=vega_i, Theta=theta_i))

greeks_df = pd.DataFrame(greeks_rows)

print(f"  {'Ticker':<8} {'Peso':>7} {'Delta':>8} {'Gamma/$':>10} {'Vega/$':>8} {'Theta/$':>9}")
print("  " + "-" * 58)
for _, row in greeks_df.iterrows():
    delta_str = "N/D" if pd.isna(row["Delta"]) else f"{row['Delta']:.3f}"
    gamma_str = "N/D" if pd.isna(row["Gamma"]) else f"{row['Gamma']:.6f}"
    vega_str = "N/D" if pd.isna(row["Vega"]) else f"{row['Vega']:.6f}"
    theta_str = "N/D" if pd.isna(row["Theta"]) else f"{row['Theta']:.6f}"
    print(f"  {row['Ticker']:<8} {row['Weight'] * 100:6.2f}% "
          f"{delta_str:>8} {gamma_str:>10} {vega_str:>8} {theta_str:>9}")
print("  " + "-" * 58)

delta_port = np.nansum(greeks_df["Weight"] * greeks_df["Delta"])
gamma_port = np.nansum(greeks_df["Weight"] * greeks_df["Gamma"])
vega_port = np.nansum(greeks_df["Weight"] * greeks_df["Vega"])
theta_port = np.nansum(greeks_df["Weight"] * greeks_df["Theta"])

print(f"  {'PORTF.':<8} {'':>7} {delta_port:8.3f} {gamma_port:10.6f} {vega_port:8.6f} {theta_port:9.6f}")
print("\n  Gamma/Vega/Theta normalizadas por precio del subyacente (por $1 de")
print("  exposicion, no por accion) para ser comparables entre tickers.")
print("  Vega por 1% de cambio en IV | Theta por dia | Delta sin normalizar (adimensional)")
print("=" * 65 + "\n")

# ==============================================================================
# ATRIBUCION DE RIESGO DE COLA (BKM)
# ==============================================================================
print("ATRIBUCION DE RIESGO DE COLA (BKM) - DIAGNOSTICO")
print("=" * 65)

tail_attr_rows = []
print("  MFIS/MFIK son momentos bajo la medida Q: incluyen aversion al riesgo de")
print("  cola, no solo riesgo. Se reportan como DIAGNOSTICO; ya no se suman a la")
print("  diagonal de Sigma. El riesgo de cola del portafolio se mide con los")
print("  co-momentos del panel empirico (medida P).")
print("-" * 65)

for tk in w_final.index:
    mom_tk = bkm_moments_cache.get(tk, {})
    tail_attr_rows.append(dict(Ticker=tk, Weight=w_final[tk],
                                MFIS=mom_tk.get("mfis", np.nan),
                                MFIK=mom_tk.get("mfik", np.nan)))

tail_attr_df = pd.DataFrame(tail_attr_rows)
print(f"  {'Ticker':<8} {'Peso':>7} {'MFIS (Q)':>10} {'MFIK (Q)':>10}")
print("  " + "-" * 40)
for _, row in tail_attr_df.iterrows():
    mfis_str = "N/D" if pd.isna(row["MFIS"]) else f"{row['MFIS']:.3f}"
    mfik_str = "N/D" if pd.isna(row["MFIK"]) else f"{row['MFIK']:.3f}"
    print(f"  {row['Ticker']:<8} {row['Weight'] * 100:6.2f}% {mfis_str:>10} {mfik_str:>10}")
print("  " + "-" * 40)
print(f"  Asimetria del portafolio (P, co-momentos, semanal): {port_skew_final:+.4f}"
      f"  -> horizonte: {port_skew_horizon:+.4f}")
print(f"  Exceso de curtosis del portafolio (P, semanal):     {port_kurt_exc_final:+.4f}"
      f"  -> horizonte: {port_kurt_exc_horizon:+.4f}")
if pd.notna(var_cf_final):
    print(f"  VaR Cornish-Fisher ({cornish_fisher_confidence * 100:.0f}%, horizonte):  {var_cf_final * 100:.4f}%")
    print(f"  CVaR Cornish-Fisher ({cornish_fisher_confidence * 100:.0f}%, horizonte): {cvar_cf_final * 100:.4f}%")
else:
    print("  VaR/CVaR Cornish-Fisher: N/D")
print("=" * 65 + "\n")

print("=" * 68)
print("              METRICAS DEL PORTAFOLIO OPTIMO")
print("=" * 68 + "\n")

summary_table = pd.DataFrame({
    "Metrica": [
        f"Retorno Esperado  ({horizon_label})",
        f"Volatilidad       ({horizon_label})",
        f"Sharpe Ratio      ({horizon_label})",
        f"Sortino Ratio     ({horizon_label})",
        "Retorno Esperado  (Anual, ref.)",
        "Volatilidad       (Anual, ref.)",
        "Sharpe Ratio      (Anual, ref.)",
        "Sortino Ratio     (Anual, ref.)",
        "Maximum Drawdown",
        "Retorno Semanal (raw)",
        "Volatilidad Semanal (raw)",
        "Sharpe Semanal (raw)",
        f"VaR Cornish-Fisher ({cornish_fisher_confidence * 100:.0f}%, horizonte)",
        f"CVaR Cornish-Fisher ({cornish_fisher_confidence * 100:.0f}%, horizonte)",
        "Peso Total Invertido",
        "Posicion en Efectivo",
        "Exposicion Cambiaria",
    ],
    "Valor": [
        f"{metrics_minvar['Return_Horizon'] * 100:.2f}%",
        f"{metrics_minvar['Risk_Horizon'] * 100:.2f}%",
        round(metrics_minvar["Sharpe_Horizon"], 3),
        round(metrics_minvar["Sortino_Horizon"], 3),
        f"{metrics_minvar['Return_Annual'] * 100:.2f}%",
        f"{metrics_minvar['Risk_Annual'] * 100:.2f}%",
        round(metrics_minvar["Sharpe_Annual"], 3),
        round(metrics_minvar["Sortino_Annual"], 3),
        f"{metrics_minvar['MaxDrawdown'] * 100:.2f}%",
        f"{metrics_minvar['Return_Weekly'] * 100:.2f}%",
        f"{metrics_minvar['Risk_Weekly'] * 100:.2f}%",
        round((metrics_minvar["Return_Weekly"] - risk_free_rate_weekly) / metrics_minvar["Risk_Weekly"], 3),
        f"{var_cf_final * 100:.4f}%" if pd.notna(var_cf_final) else "N/D",
        f"{cvar_cf_final * 100:.4f}%" if pd.notna(cvar_cf_final) else "N/D",
        f"{metrics_minvar['Total_Weight'] * 100:.2f}%",
        f"{metrics_minvar['Cash_Position'] * 100:.2f}%",
        f"{fx_weight_final * 100:.2f}%",
    ],
})

print(summary_table.to_string(index=False))

print("\n" + "=" * 65)
print(f"RESUMEN EJECUTIVO - EJECUTAR EN: {execution_label.upper()}")
print("=" * 65 + "\n")

for nm, val in w_final.items():
    print(f"   {nm:<8}  {val * 100:.2f}%")

print(f"\n   -- Metricas del horizonte ({horizon_label}) --")
print(f"   Retorno esperado  : {metrics_minvar['Return_Horizon'] * 100:.2f}%")
print(f"   Volatilidad       : {metrics_minvar['Risk_Horizon'] * 100:.2f}%")
print(f"   Sharpe Ratio      : {metrics_minvar['Sharpe_Horizon']:.3f}")
print(f"   Sortino Ratio     : {metrics_minvar['Sortino_Horizon']:.3f}")
_cf_pct = f"{cornish_fisher_confidence * 100:.0f}%"
print(f"   VaR Cornish-Fisher ({_cf_pct})  : " + (f"{var_cf_final * 100:.4f}%" if pd.notna(var_cf_final) else "N/D"))
print(f"   CVaR Cornish-Fisher ({_cf_pct}) : " + (f"{cvar_cf_final * 100:.4f}%" if pd.notna(cvar_cf_final) else "N/D"))
print("\n   -- Referencia anual --")
print(f"   Retorno esperado  : {metrics_minvar['Return_Annual'] * 100:.2f}%")
print(f"   Volatilidad       : {metrics_minvar['Risk_Annual'] * 100:.2f}%")
print(f"   Sharpe Ratio      : {metrics_minvar['Sharpe_Annual']:.3f}")
print(f"   Sortino Ratio     : {metrics_minvar['Sortino_Annual']:.3f}")
print("=" * 65)

# ==============================================================================
# COBERTURA BKM: QUIEN CAYO AL ESTIMADOR HISTORICO Y POR QUE (A-1)
# ==============================================================================
print("\n" + "=" * 65)
print("COBERTURA BKM (momentos implicitos vs fallback historico)")
print("=" * 65)
bkm_resumen_fallbacks(list(w_final.index), "Portafolio final")
consultados = [t for t in bkm_moments_cache if t not in w_final.index]
if consultados:
    motivos_resto = pd.Series([bkm_motivo_fallback(t) or "BKM completo" for t in consultados])
    motivos_resto = motivos_resto.str.replace(r" \(.*\)$", "", regex=True)
    n_fb_resto = int((motivos_resto != "BKM completo").sum())
    print(f"\n  Resto de tickers consultados ({len(consultados)}): {len(consultados) - n_fb_resto} con BKM completo | "
          f"{n_fb_resto} con fallback historico")
    for motivo, n in motivos_resto[motivos_resto != "BKM completo"].value_counts().items():
        print(f"     {n:>3}  {motivo}")
print("=" * 65)

print("\nDiagnostico de llamadas a Polygon:")
pc.print_diagnostics()

print("\nScript completado con exito!")
