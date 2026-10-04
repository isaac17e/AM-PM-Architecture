# ==============================================================================
# BLACK-LITTERMAN EXTENDIDO POR MOMENTOS DE ORDEN SUPERIOR MODEL-FREE (BKM)
# ==============================================================================

import warnings
warnings.filterwarnings("ignore")

import math
import os
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd

import yfinance as yf
from scipy.optimize import minimize, linprog
from scipy.stats import norm
from scipy import sparse
import quadprog

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import risk_estimators as rk
import polygon_client as pc
import market_data as md
import bl_metrics as bm

try:
    import statsmodels.api as sm
    HAY_STATSMODELS = True
except ImportError:
    HAY_STATSMODELS = False
    print("Aviso: statsmodels no disponible. Se usara un estimador HAC interno "
          "(Newey-West con kernel de Bartlett) para las primas de riesgo.")

# ==============================================================================
# BLOQUE 0: PARAMETROS CONFIGURABLES
# ==============================================================================

# ------------------------------------------------------------------------------
# API KEY - Polygon.io
# ------------------------------------------------------------------------------
from dotenv import load_dotenv
load_dotenv()
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY")

# ------------------------------------------------------------------------------
# 1. UNIVERSO DE TICKERS
# ------------------------------------------------------------------------------
# El universo es exactamente esta lista: no hay listas paralelas de ETFs ni de
# internacionales. Vale cualquier ticker de Yahoo Finance: acciones, ETFs o
# commodities de EE. UU., y de otras bolsas con su sufijo (RY.TO, AZN.L,
# 7203.T, ASML.AS, 0700.HK...). Un internacional se convierte a USD con la
# moneda que reporta Yahoo y no se consulta en Polygon (sin opciones en
# EE. UU.): usa vol y momentos historicos. Los ADRs (HSBC, BP) son de EE. UU.
TICKERS = [
    "META", "GOOGL", "ORCL", "DELL", "MSFT",
    "BLK", "CRM", "CMCSA", "GS", "REGN",
    "ABNB", "ARES", "LVS", "BXP", "CRWD",
    "YELP", "EBAY", "IT", "EL"
]

# ------------------------------------------------------------------------------
# 2. HORIZONTE TEMPORAL
# ------------------------------------------------------------------------------
MESES_HORIZONTE = 2
DIAS_HABILES_MES = 21
SEMANAS_MES = 4.33

# ------------------------------------------------------------------------------
# 3. PERFIL DE RIESGO
# ------------------------------------------------------------------------------
PERFIL_RIESGO = "agresivo"

# ------------------------------------------------------------------------------
# 4. PARAMETROS DE OPTIMIZACION (POR PERFIL)
# ------------------------------------------------------------------------------
PERFILES = {
    "conservador": dict(omega_scale=5.0, tau=0.025, gamma_ra=6.0),
    "moderado": dict(omega_scale=1.0, tau=0.05, gamma_ra=3.0),
    "agresivo": dict(omega_scale=0.25, tau=0.10, gamma_ra=1.5),
}

# ------------------------------------------------------------------------------
# 5. LIMITES DEL PORTAFOLIO FINAL
# ------------------------------------------------------------------------------
UMBRAL_PESO_MIN = 0.005
MAX_TICKERS_FINAL = 10
PESO_MAX_ACTIVO = 0.35

# ------------------------------------------------------------------------------
# 6. TASA LIBRE DE RIESGO - FALLBACK
# ------------------------------------------------------------------------------
Rf = 0.046

# ------------------------------------------------------------------------------
# 7. DELTA DE MERCADO
# ------------------------------------------------------------------------------
# Independiente del perfil (M-12).
# "historical" es el comportamiento de siempre: exceso de ~2 anos / varianza,
# ambos al horizonte. La media corta puede ser negativa y pi hereda el signo.
# "fixed" usa DELTA_MKT_FIJO (rango habitual de aversion 2-4).
# "implied" = var_Q de la cartera de mercado / var_P. La prima implicita es
# la varianza neutral (Martin: el exceso del mercado es SVIX^2 = MFIV de
# esa cartera) ya disponible en la cadena Q -> P. No es el default: ese
# cociente suele quedar cerca de 1, no en 2.5, porque la prima ya esta en
# unidades de varianza.
DELTA_MKT_MODO = "historical"
DELTA_MKT_FIJO = 2.5

# ------------------------------------------------------------------------------
# 8. ANALISIS DE MAXIMUM DRAWDOWN (MDD)
# ------------------------------------------------------------------------------
MDD_START_YEAR = date.today().year - 2

# ------------------------------------------------------------------------------
# 9. VOLATILIDAD IMPLICITA VIA POLYGON - SSVI
# ------------------------------------------------------------------------------
USAR_IV_POLYGON = True
MIN_STRIKES_SLICE = 5
MIN_DIAS_VENCIMIENTO = 5
# Tope de DTE (calendario) de la calibracion. 2x el horizonte: con 4 meses
# son 243 dias. Los LEAPs (>~250d) quedaban fuera de la ventana de inversion
# y, en varianza total, se comian la perdida y clavaban rho en la cota.
# Si el recorte deja menos de MIN_VENCIMIENTOS_SSVI, se completan con los
# vencimientos mas cortos por encima del tope.
MAX_DIAS_VENCIMIENTO = int(round(2.0 * (MESES_HORIZONTE / 12.0) * 365.0))
MIN_VENCIMIENTOS_SSVI = 3
# Higiene de la cadena antes del ajuste. Precio bajo piso (centavos con IV
# rota) u OI conocido por debajo del minimo no entran. OI ausente se conserva.
SSVI_PRECIO_MIN = 0.10
SSVI_OI_MIN = 10
# True: cada vencimiento pesa igual y el residuo se divide por theta^2.
# Un plazo largo deja de dominar la perdida en w = sigma^2 T.
SSVI_NORMALIZAR_VENCIMIENTO = True
SSVI_K_ABS_MAX = 0.5
# Por vencimiento, |k| <= min(SSVI_K_ABS_MAX, SSVI_K_SD_MAX * sigma_ATM * sqrt(T)).
# En una semana 3 sigma es ~0.10: un put profundo y viejo (k ~ -0.5, IV rota)
# no entra al ajuste. La integral BKM sigue en +/- BKM_N_STD sigma.
SSVI_K_SD_MAX = 3.0
# |rho| cerca de tanh(3.8) ~ 0.999 es la cota del optimizador, no una sonrisa.
# Sin strikes de los dos lados rho tampoco se identifica. Esas alas no entran
# a BKM; se conserva la vol ATM.
SSVI_RHO_ABS_MAX = 0.95
SSVI_K_SIDE_MIN = 0.10
SSVI_MIN_PER_SIDE = 2
# Momentos cuando la sonrisa se rechaza (rmse, rho en la cota, cadena rota).
# "historico": skew y curtosis fisicos del ticker al horizonte.
# "neutro": MFIS=0, MFIK=3.
# "sector": sonrisa del ETF sectorial que asignes en FALLBACK_ETF_POR_TICKER
# ({ticker: ETF}, p. ej. {"MSFT": "XLK"}). Los tickers sin entrada, o cuyo ETF
# no calibra, usan el historico. Vacio por defecto: depende de tu universo.
FALLBACK_MOMENTOS = "historico"
FALLBACK_ETF_POR_TICKER = {}

# ------------------------------------------------------------------------------
# 10. MODULO ECONOMETRICO Q -> P
# ------------------------------------------------------------------------------
# Parametros del Bloque 1D.
PASO_VENTANA_ROLLING = 5
MIN_VENTANAS_ROLLING = 12
NW_LAGS_AUTO = True
NW_LAGS_FIJOS = 6
WINSOR_MOMENTOS = 0.05

N_REP_BOOTSTRAP_MOM = 20
J_POR_REPLICA_MOM = 2000
N_MC_DELTA = 200

THETA_ESSCHER_COTA = (0.0, 25.0)
THETA_PRIOR_CV = 1.0
MAX_PRIMA_HM_SIGMA = 0.35

COTA_SKEW_P = (-2.5, 1.5)
COTA_KURT_P = (1.8, 12.0)
# Misma cota que vrp_ratio_bounds de MV/QU y que rk.q_to_p_vol (B-9).
# hi = 1.0 impone el signo del VRP: la vol fisica no supera a la implicita.
# Antes (0.55, 1.25) dejaba sigma_P > sigma_Q, al reves que el resto del repo.
COTA_RATIO_VOL_P = (0.70, 1.00)

# ------------------------------------------------------------------------------
# 11. COVARIANZA HISTORICA: DIARIA + EWMA + SHRINKAGE LEDOIT-WOLF
# ------------------------------------------------------------------------------
USAR_COV_DIARIA = True
COV_HALFLIFE_DIAS = 120
USAR_SHRINKAGE_LW = True

# ------------------------------------------------------------------------------
# 12. INTEGRACION BAYESIANA NO GAUSSIANA
# ------------------------------------------------------------------------------
# Parametros del Bloque 7.
METODO_POSTERIOR = "entropy_pooling"
N_ESCENARIOS = 12000
BOOTSTRAP_BLOQUE = max(21, (MESES_HORIZONTE * DIAS_HABILES_MES) // 4)
HALF_LIFE_PRIOR = 252
SEMILLA = 20260904
EP_IMPONER_CURTOSIS = True
EP_TOL_ENS = 0.10

# ------------------------------------------------------------------------------
# 13. RIESGO DE COLA Y MODO DE OPTIMIZACION
# ------------------------------------------------------------------------------
# Parametros de los Bloques 7B y 8B.
NIVEL_CONFIANZA_VAR = 0.95
BKM_MFIK_MAX = 20.0
# Tope de MFIK: 20 con cadena corta, hasta BKM_MFIK_MAX_HARD si hay muchos
# strikes OTM observados (no los puntos de la rejilla sintetica). Un indice
# liquido supera 20 sin que el momento sea inadmisible.
BKM_MFIK_MAX_HARD = 80.0
# Alas de la integral BKM. El ajuste es |k|<=0.5; la integral usa las alas
# SSVI (GJ ya chequeado) en +/- BKM_N_STD * sigma * sqrt(T). Recortar al
# k del ajuste dejaba MFIK < 3. +/-6 sigma inflaba el MFIV (META ~4x).
BKM_N_STD = 3.0
BKM_MFIV_RATIO = (0.80, 2.0)
NIVELES_CVAR = (0.95, 0.99)
UMBRAL_OMEGA_RATIO = 0.0

MODO_OPTIMIZACION = "mvsk"
# NOTA DE DISENO (B-10), no se recalibra: LAMBDA3 y LAMBDA4 ponderan momentos
# centrales crudos (skew * sigma^3, exceso de curtosis * sigma^4). Frente a
# mu del horizonte y a (gamma/2) w'Sigma w esos terminos quedan en ordenes
# menores, asi que el objetivo MVSK se comporta casi como media-varianza.
LAMBDA3 = 1.0
LAMBDA4 = 1.0
ALPHA_CVAR_OBJETIVO = 0.95
RETORNO_MIN_CVAR = None
MAX_ESCENARIOS_LP = 4000

# ------------------------------------------------------------------------------
# MODO SMOKE
# ------------------------------------------------------------------------------
# AMPM_SMOKE=1 ejecuta el script con universo chico y sin Polygon, para que
# un test pueda recorrer el camino hasta Cornish-Fisher (el alias `rk` no
# puede quedar pisado por un array).
_es_smoke = os.environ.get("AMPM_SMOKE", "").strip().lower() in {"1", "true", "yes"}
if _es_smoke:
    USAR_IV_POLYGON = False
    # AMPM_SMOKE_TICKERS="AAPL,AZN.L" cambia el universo del smoke.
    TICKERS = os.environ.get("AMPM_SMOKE_TICKERS", "AAPL,MSFT,SPY").split(",")
    N_ESCENARIOS = 60
    N_REP_BOOTSTRAP_MOM = 2
    J_POR_REPLICA_MOM = 30
    N_MC_DELTA = 4
    MAX_ESCENARIOS_LP = 30
    MIN_VENTANAS_ROLLING = 4

# ------------------------------------------------------------------------------
# VALIDACION DE PARAMETROS Y SEMILLA GLOBAL
# ------------------------------------------------------------------------------
if USAR_IV_POLYGON and not POLYGON_API_KEY:
    raise ValueError(
        "USAR_IV_POLYGON = True pero POLYGON_API_KEY no esta definida. "
        "Configura el secreto 'PolygonAPI' en Colab, o pon USAR_IV_POLYGON = False "
        "para usar el metodo historico."
    )

if DELTA_MKT_MODO not in ("historical", "fixed", "implied"):
    raise ValueError("DELTA_MKT_MODO debe ser 'historical', 'fixed' o 'implied'")
if not np.isfinite(DELTA_MKT_FIJO) or DELTA_MKT_FIJO <= 0:
    raise ValueError("DELTA_MKT_FIJO debe ser positivo")
if FALLBACK_MOMENTOS not in ("historico", "neutro", "sector"):
    raise ValueError("FALLBACK_MOMENTOS debe ser 'historico', 'neutro' o 'sector'")
if MAX_DIAS_VENCIMIENTO < MIN_DIAS_VENCIMIENTO:
    raise ValueError("MAX_DIAS_VENCIMIENTO debe ser >= MIN_DIAS_VENCIMIENTO")
if SSVI_PRECIO_MIN < 0 or SSVI_OI_MIN < 0:
    raise ValueError("SSVI_PRECIO_MIN y SSVI_OI_MIN no pueden ser negativos")
if SSVI_K_SD_MAX is not None and (not np.isfinite(SSVI_K_SD_MAX) or SSVI_K_SD_MAX <= 0):
    raise ValueError("SSVI_K_SD_MAX debe ser positivo")

_cap_cardinalidad = MAX_TICKERS_FINAL * PESO_MAX_ACTIVO
if _cap_cardinalidad < 1.0:
    _peso_max_previo = PESO_MAX_ACTIVO
    PESO_MAX_ACTIVO = min(1.0, (1.0 / MAX_TICKERS_FINAL) * 1.05)
    print(f"  AVISO: MAX_TICKERS_FINAL({MAX_TICKERS_FINAL}) x "
          f"PESO_MAX_ACTIVO({_peso_max_previo:.4f}) = {_cap_cardinalidad:.4f} < 1.0 "
          f"=> el optimizador quedaria infactible en sum(w)=1. "
          f"Se ajusta PESO_MAX_ACTIVO a {PESO_MAX_ACTIVO:.4f}.")

rng_global = np.random.default_rng(SEMILLA)


# ==============================================================================
# BLOQUE 0B: HORIZONTE Y UNIVERSO
# ==============================================================================
# El universo es TICKERS tal cual, sin duplicados. No se le aplica el filtro
# de formato US: un sufijo de bolsa (.TO, .L, .T, .HK...) se conserva.
TICKERS = list(dict.fromkeys(str(t).strip().upper() for t in TICKERS if str(t).strip()))
if len(TICKERS) < 2:
    raise ValueError("TICKERS debe tener al menos 2 tickers distintos")
# Internacional = cotiza fuera de EE. UU. (sin cadena de opciones en Polygon).
_intl_universo = [t for t in TICKERS if not pc.is_us_ticker(t)]

horizonte_dias = MESES_HORIZONTE * DIAS_HABILES_MES
horizonte_semanas = MESES_HORIZONTE * SEMANAS_MES
factor_anualizacion = round(52 * (MESES_HORIZONTE / 12))

print("=== HORIZONTE TEMPORAL ===")
print(f"Meses: {MESES_HORIZONTE}")
print(f"Dias habiles: {horizonte_dias}")
print(f"Factor de escala (semanas): {factor_anualizacion}\n")

print("=== UNIVERSO ===")
print(f"Tickers: {len(TICKERS)} | internacionales en el universo (sin opciones US): "
      f"{len(_intl_universo)}{' (' + ', '.join(_intl_universo) + ')' if _intl_universo else ''}")
print(TICKERS)
print()

# ==============================================================================
# MAPEO DE MONEDA POR SUFIJO + PARES FX
# ==============================================================================
# Para la conversion a USD.
# La moneda sale de Yahoo (history_metadata). El sufijo es el respaldo si
# Yahoo no la informa. HSBC y BP son ADRs en USD: no van en el override.
# .TO es CAD, no JPY. Solo se descarga el FX de las monedas del universo; una
# moneda sin par en fx_pairs usa {MONEDA}USD=X (USD por unidad).
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
    ".AS": "EUR", ".BR": "EUR", ".MI": "EUR", ".F": "EUR", ".HE": "EUR",
    ".LS": "EUR", ".IR": "EUR", ".VI": "EUR",
    ".SW": "CHF", ".ST": "SEK", ".CO": "DKK", ".OL": "NOK",
    ".HK": "HKD", ".SS": "CNY", ".SZ": "CNY", ".KS": "KRW", ".TW": "TWD",
    ".AX": "AUD", ".NZ": "NZD", ".SI": "SGD", ".NS": "INR", ".BO": "INR",
    ".SA": "BRL", ".MX": "MXN", ".JO": "ZAR", ".V": "CAD", ".NE": "CAD",
}
ticker_currency_override = {}
provider_currency = {}
ticker_currency = {}

# ==============================================================================
# BLOQUE 1: DESCARGA DE PRECIOS
# ==============================================================================

fecha_fin = date.today()
fecha_inicio = fecha_fin - timedelta(days=365 * 2)

print("=== Descargando precios ===")
print(f"Desde: {fecha_inicio} | Hasta: {fecha_fin}\n")


def _par_fx(cur):
    """Par de Yahoo para `cur`: el de fx_pairs o {CUR}USD=X (USD por unidad)."""
    return fx_pairs.get(cur) or {"ticker": f"{cur}USD=X", "invert": False}


def descargar_fx_moneda(cur, start, end):
    """Serie FX en USD por unidad de `cur`, o None."""
    info = _par_fx(cur)
    fin = pd.Timestamp(end).normalize() + pd.Timedelta(days=1)
    try:
        hist = yf.Ticker(info["ticker"]).history(start=start, end=fin.date(), auto_adjust=True)
        if hist is None or hist.empty:
            return None
        s = hist["Close"].copy()
        s.index = pd.to_datetime(s.index).tz_localize(None)
        if info["invert"]:
            s = 1.0 / s
        return s.sort_index()
    except Exception:
        return None


_fx_fallidos = set()


def asegurar_fx(cur, fx_prices):
    """Descarga el FX de `cur` una sola vez por corrida (tambien si falla)."""
    if fx_prices is None or not cur or cur == "USD" or cur in fx_prices or cur in _fx_fallidos:
        return
    s = descargar_fx_moneda(cur, _fx_desde.date(), fecha_fin)
    if s is not None and len(s):
        fx_prices[cur] = s
        print(f"  FX {cur}: {_par_fx(cur)['ticker']}")
    else:
        _fx_fallidos.add(cur)


def descargar_precio(ticker, start, end, max_retries=3, fx_prices=None):
    """Cierres entre start y end, con end inclusivo, en USD.

    yfinance trata `end` como exclusivo. Para que el ultimo cierre pueda ser
    el del dia de la cadena (y no el de ayer) se pide el dia siguiente.
    GBp/ZAc se pasan a libras/rand antes del FX. Sin par FX el precio queda
    en moneda local y se avisa.
    """
    fin = pd.Timestamp(end).normalize() + pd.Timedelta(days=1)
    for _ in range(max_retries):
        try:
            yf_tk = yf.Ticker(ticker)
            hist = yf_tk.history(start=start, end=fin.date(), auto_adjust=True)
            if hist is not None and len(hist) > 0:
                s = hist["Close"].copy()
                s.index = pd.to_datetime(s.index).tz_localize(None)
                meta = getattr(yf_tk, "history_metadata", None) or {}
                cur_prov = meta.get("currency")
                if cur_prov:
                    provider_currency[ticker] = cur_prov
                s = s * md.price_scale_factor(cur_prov)
                cur_map, conflictos = md.resolve_currencies(
                    [ticker], ticker_currency_by_suffix,
                    overrides=ticker_currency_override,
                    provider={ticker: cur_prov} if cur_prov else {},
                )
                ticker_currency[ticker] = cur_map[ticker]
                for c in conflictos:
                    print(f"  ADVERTENCIA moneda {c['ticker']}: {c['fuente']} {c['manual']} "
                          f"contradice al proveedor {c['proveedor']}; se usa {c['proveedor']}")
                cur = ticker_currency[ticker]
                if cur != "USD":
                    asegurar_fx(cur, fx_prices)
                    if fx_prices is not None and cur in fx_prices:
                        s = md.convertir_serie_a_usd(s, fx_prices[cur])
                    else:
                        print(f"  ADVERTENCIA {ticker}: sin FX para {cur}; el precio queda en moneda local")
                return s
        except Exception:
            time.sleep(1)
    return None


# FX solo de las monedas que aparezcan en el universo, al descargar cada precio.
_fx_desde = min(pd.Timestamp(fecha_inicio), pd.Timestamp(date(MDD_START_YEAR, 1, 1)))
fx_prices_diarios = {}

tickers_ok = []
precios_dict = {}
for tk in TICKERS:
    serie = descargar_precio(tk, fecha_inicio, fecha_fin, fx_prices=fx_prices_diarios)
    if serie is None or len(serie) == 0:
        print(f"  Error descargando {tk}")
        continue
    precios_dict[tk] = serie
    tickers_ok.append(tk)

print(f"Tickers descargados: {len(tickers_ok)} / {len(TICKERS)}")
_no_usd = {t: ticker_currency.get(t) for t in tickers_ok if ticker_currency.get(t, "USD") != "USD"}
if _no_usd:
    print("  Convertidos a USD: " + ", ".join(f"{t} ({c})" for t, c in _no_usd.items())
          + (f" | sin FX (quedan en moneda local): {', '.join(sorted(_fx_fallidos))}" if _fx_fallidos else ""))

precios_diarios = pd.DataFrame(precios_dict)[tickers_ok]
if len(precios_diarios) == 0 or pd.isna(precios_diarios.index.max()):
    print(f"  AVISO: no hay cierres. El spot de los momentos usara la cadena si existe.")
else:
    _ultima_barra = pd.Timestamp(precios_diarios.index.max()).normalize()
    if _ultima_barra.date() < fecha_fin:
        print(f"  AVISO: no hay cierre de {fecha_fin}. Ultima barra: {_ultima_barra.date()}. "
              f"Si la cadena de opciones es de hoy, el spot de los momentos sale de la cadena.")
    else:
        print(f"  Ultima barra: {_ultima_barra.date()} (incluye el dia de hoy).")

# Festivo en Tokio o Frankfurt no debe borrar el dia de Nueva York (M-1).
# Solo cuando hay bolsa no estadounidense: el universo US se queda igual.
if len(precios_diarios.columns) and any(not pc.is_us_ticker(t) for t in precios_diarios.columns):
    _ref_cal = precios_diarios.notna().sum().idxmax()
    _cal = precios_diarios.index[precios_diarios[_ref_cal].notna()]
    if len(_cal) >= 2:
        precios_diarios, _info_cal = md.align_prices_to_calendar(
            precios_diarios, _cal, max_ffill=2, min_coverage=0.80)
        _bajos = list(_info_cal.get("dropped_low_coverage") or [])
        if _bajos:
            print(f"  Cobertura < 80% fuera del calendario de {_ref_cal}: {', '.join(map(str, _bajos))}")
        print(f"  Precios alineados a {_ref_cal}: {_info_cal.get('n_rows')} filas (ffill maximo 2 dias)")

precios_semanales = precios_diarios.resample("W").last()
precios_semanales, _semana_parcial = md.drop_partial_last_week(
    precios_semanales, precios_diarios.index.max())
if _semana_parcial:
    print("  Semana en curso incompleta descartada del resample semanal.")

retornos_sem = np.log(precios_semanales / precios_semanales.shift(1)).dropna(how="all")

pct_na = retornos_sem.isna().mean()
tickers_limpios = pct_na[pct_na < 0.05].index.tolist()
retornos_sem = retornos_sem[tickers_limpios].dropna()

tickers = tickers_limpios
n = len(tickers)

print(f"Tickers en universo BL: {n}")
if n < len(TICKERS):
    excluidos = [t for t in TICKERS if t not in tickers]
    print(f"  Excluidos: {', '.join(excluidos)}")

# ==============================================================================
# COVARIANZA SEMANAL: BASE DIARIA + EWMA + SHRINKAGE
# ==============================================================================
Sigma_sem = None
if USAR_COV_DIARIA:
    ret_dia_cov = np.log(precios_diarios[tickers] / precios_diarios[tickers].shift(1))
    ret_dia_cov = ret_dia_cov.replace([np.inf, -np.inf], np.nan).dropna()
    if len(ret_dia_cov) >= 120:
        Sigma_sem_df, cov_info_bl = rk.cov_ewma_shrunk(
            ret_dia_cov, halflife=COV_HALFLIFE_DIAS, scale=252.0 / 52.0,
            shrink=USAR_SHRINKAGE_LW)
        Sigma_sem = np.asarray(Sigma_sem_df)
        sem_muestral = retornos_sem.cov().values
        print("\n=== Covarianza semanal (EWMA + Ledoit-Wolf, base diaria) ===")
        print(f"  obs diarias: {cov_info_bl['n_obs']} | t_eff (Kish): {cov_info_bl['t_eff']:.1f} "
              f"| delta shrinkage: {cov_info_bl['delta']:.3f}")
        print(f"  vol semanal media: muestral={np.sqrt(np.diag(sem_muestral)).mean() * 100:.3f}% -> "
              f"EWMA+LW={np.sqrt(np.diag(Sigma_sem)).mean() * 100:.3f}%")
        print(f"  correlacion promedio: muestral={rk.average_correlation(sem_muestral):.4f} -> "
              f"EWMA+LW={rk.average_correlation(Sigma_sem):.4f}")
    else:
        print(f"\n  ADVERTENCIA Solo {len(ret_dia_cov)} dias - se usa covarianza semanal muestral")

if Sigma_sem is None:
    Sigma_sem = retornos_sem.cov().values

# Al horizonte (semanal x factor de semanas), no anual (M-11). mu_historico igual.
Sigma_hist = Sigma_sem * factor_anualizacion
D_hist_inv = np.diag(1 / np.sqrt(np.diag(Sigma_hist)))
Corr_hist = D_hist_inv @ Sigma_hist @ D_hist_inv
Sigma_hist_df = pd.DataFrame(Sigma_hist, index=tickers, columns=tickers)
mu_historico = retornos_sem.mean().values * factor_anualizacion

print("\n=== Retornos historicos escalados al horizonte ===")
print(pd.Series(np.round(mu_historico, 4), index=tickers))

# ==============================================================================
# BLOQUE 1B: VOLATILIDAD IMPLICITA VIA POLYGON (SSVI)
# ==============================================================================

fuente_vol = {t: "historica" for t in tickers}

if USAR_IV_POLYGON:

    tau_horizonte = MESES_HORIZONTE / 12

    print("\n=== Extrayendo volatilidad implicita ATM via Polygon (SSVI) ===")
    print(f"Horizonte objetivo (tau): {tau_horizonte:.4f} anios")
    print(f"Vencimientos: {MIN_DIAS_VENCIMIENTO}-{MAX_DIAS_VENCIMIENTO} dias "
          f"(minimo {MIN_VENCIMIENTOS_SSVI} si el tope deja menos) | "
          f"perdida normalizada por vencimiento: {SSVI_NORMALIZAR_VENCIMIENTO} | "
          f"precio >= {SSVI_PRECIO_MIN:.2f} | OI >= {SSVI_OI_MIN:g} | "
          f"|k| <= min({SSVI_K_ABS_MAX}, {SSVI_K_SD_MAX:g}*sigma*sqrt(T)) | "
          f"fallback de momentos: {FALLBACK_MOMENTOS}\n")

    def polygon_fetch_chain(ticker, api_key, max_pages=40):
        """Cadena completa de opciones paginada; falla si queda incompleta."""
        url = (f"{pc.BASE_URL}/v3/snapshot/options/"
               f"{pc.polygon_format_ticker(ticker)}?limit=250")
        results, completo, status = pc.get_all(url, api_key=api_key, max_pages=max_pages)
        if not completo:
            raise ValueError(f"cadena incompleta (status {status})")
        return results

    def parse_chain(chain_raw):
        filas = []
        for c in chain_raw:
            try:
                details = c.get("details", {})
                last_quote = c.get("last_quote", {}) or {}
                day = c.get("day", {}) or {}
                underlying = c.get("underlying_asset", {}) or {}

                precio_opcion = np.nan
                if last_quote.get("midpoint") is not None:
                    precio_opcion = last_quote["midpoint"]
                elif day.get("close") not in (None, 0):
                    precio_opcion = day["close"]

                filas.append(dict(
                    strike=details.get("strike_price"),
                    expiracion=pd.to_datetime(details.get("expiration_date")),
                    tipo=details.get("contract_type"),
                    iv=c.get("implied_volatility", np.nan),
                    precio=precio_opcion,
                    oi=c.get("open_interest", np.nan),
                    spot=underlying.get("price", np.nan),
                ))
            except Exception:
                continue
        return pd.DataFrame(filas)

    def phi_powerlaw(theta, eta, gamma):
        return eta * theta ** (-gamma)

    def ssvi_w(k, theta, rho, eta, gamma):
        phi = phi_powerlaw(theta, eta, gamma)
        return theta / 2 * (1 + rho * phi * k + np.sqrt((phi * k + rho) ** 2 + (1 - rho ** 2)))

    def calibrar_ssvi_ticker(ticker, api_key, tau_obj,
                              min_strikes=MIN_STRIKES_SLICE,
                              min_dias=MIN_DIAS_VENCIMIENTO):
        chain_raw = polygon_fetch_chain(ticker, api_key)
        if len(chain_raw) == 0:
            raise ValueError("Cadena vacia")
        df = parse_chain(chain_raw)
        # sqrt(w/T) es la vol ANUAL y no depende de las alas. Se conserva
        # aunque el RMSE de la sonrisa supere el umbral.
        return bm.calibrar_superficie_ssvi(
            df, tau_obj, pd.Timestamp(date.today()),
            min_strikes=min_strikes, min_dias=min_dias,
            max_dias=MAX_DIAS_VENCIMIENTO, min_vencimientos=MIN_VENCIMIENTOS_SSVI,
            k_abs_max=SSVI_K_ABS_MAX, k_sd_max=SSVI_K_SD_MAX,
            precio_min=SSVI_PRECIO_MIN, oi_min=SSVI_OI_MIN,
            rho_abs_max=SSVI_RHO_ABS_MAX, k_side_min=SSVI_K_SIDE_MIN,
            min_per_side=SSVI_MIN_PER_SIDE,
            normalizar_vencimiento=SSVI_NORMALIZAR_VENCIMIENTO)

    def _fmt_num(x, spec):
        return format(float(x), spec) if x is not None and np.isfinite(x) else "n/d"

    def _diag_ssvi(resultado):
        """Vencimientos usados, error relativo, rho y si la sonrisa entra o cae al fallback."""
        dte = (f"{resultado.get('dias_min')}-{resultado.get('dias_max')}"
               if resultado.get("dias_min") is not None else "n/d")
        if resultado.get("usar_alas"):
            decision = "aceptada"
        else:
            porque = resultado.get("motivo_fallback") or ", ".join(resultado.get("motivos") or [])
            decision = f"fallback {FALLBACK_MOMENTOS} ({porque or 'sonrisa rechazada'})"
        extra = ""
        if resultado.get("extendio_tope"):
            extra += " | tope extendido para completar el minimo de vencimientos"
        if resultado.get("n_drop_higiene"):
            extra += (f" | higiene precio={resultado.get('n_drop_precio', 0)}"
                      f" oi={resultado.get('n_drop_oi', 0)}"
                      f" monotonia={resultado.get('n_drop_monotonia', 0)}")
        extra += f" | ventana_k={int(resultado.get('n_drop_k_sd') or 0)}"
        return (f"vencimientos: {resultado.get('n_vencimientos')}/"
                f"{resultado.get('n_vencimientos_cadena', '?')} | "
                f"DTE {dte} (tope {resultado.get('max_dias', MAX_DIAS_VENCIMIENTO)}) | "
                f"rmse_rel={_fmt_num(resultado.get('rmse_rel'), '.3f')} | "
                f"rho={_fmt_num(resultado.get('rho'), '.3f')} | {decision}{extra}")

    sigma_iv_horizon = {t: np.nan for t in tickers}
    sigma_iv_annual = {t: np.nan for t in tickers}
    detalle_ssvi = {}
    resultado_ssvi = {}
    motivo_calibracion = {}
    detalle_sector = {}

    for tk in tickers:
        # Opciones solo en cadena US. Un internacional sin contrato en Polygon
        # sigue el camino historico (sin_opciones_us), no se consulta la API.
        if not pc.is_us_ticker(tk):
            sigma_iv_horizon[tk] = bm.iv_vol_at_horizon(
                np.nan, float(Sigma_hist_df.loc[tk, tk]), tau_horizonte)
            fuente_vol[tk] = "historica"
            motivo_calibracion[tk] = "sin_opciones_us"
            print(f"  {tk}: sin_opciones_us -> vol historica al horizonte = "
                  f"{sigma_iv_horizon[tk]:.4f}")
            continue
        print(f"  Calibrando SSVI: {tk} ... ", end="")
        try:
            resultado = calibrar_ssvi_ticker(tk, POLYGON_API_KEY, tau_horizonte)
        except Exception as e:
            print(f"FALLBACK ({e}) ", end="")
            resultado = None
            motivo_calibracion[tk] = str(e)

        if resultado is not None and resultado.get("usar_alas"):
            anual = resultado["sigma_atm_annual"]
            sigma_iv_annual[tk] = anual
            sigma_iv_horizon[tk] = bm.iv_vol_at_horizon(
                anual, float(Sigma_hist_df.loc[tk, tk]), tau_horizonte)
            detalle_ssvi[tk] = resultado
            resultado_ssvi[tk] = resultado
            fuente_vol[tk] = "ssvi"
            print(f"OK ({resultado['metodo']}) - sigma_ATM anual = {anual:.4f} "
                  f"| al horizonte = {sigma_iv_horizon[tk]:.4f} "
                  f"| {_diag_ssvi(resultado)} "
                  f"| GJ_max = {resultado['gj_max']:.3f} (<=4 sin arbitraje)")
        elif resultado is not None and resultado.get("fuente") == "atm":
            anual = resultado["sigma_atm_annual"]
            sigma_iv_annual[tk] = anual
            sigma_iv_horizon[tk] = bm.iv_vol_at_horizon(
                anual, float(Sigma_hist_df.loc[tk, tk]), tau_horizonte)
            resultado_ssvi[tk] = resultado
            fuente_vol[tk] = "atm"
            print(f"ATM (k=[{_fmt_num(resultado.get('k_min'), '.2f')}, "
                  f"{_fmt_num(resultado.get('k_max'), '.2f')}], "
                  f"puts={resultado.get('n_put')}, calls={resultado.get('n_call')}) "
                  f"- sigma_ATM anual = {anual:.4f} "
                  f"| al horizonte = {sigma_iv_horizon[tk]:.4f} "
                  f"| {_diag_ssvi(resultado)} "
                  f"| alas no usadas en BKM")
        else:
            sigma_iv_horizon[tk] = bm.iv_vol_at_horizon(
                np.nan, float(Sigma_hist_df.loc[tk, tk]), tau_horizonte)
            fuente_vol[tk] = "historica"
            razon = motivo_calibracion.get(tk, "sin superficie")
            print(f"-> vol historica al horizonte = {sigma_iv_horizon[tk]:.4f} "
                  f"| fallback {FALLBACK_MOMENTOS} ({razon})")

    if FALLBACK_MOMENTOS == "sector":
        etfs_sector = []
        for tk in tickers:
            etf = FALLBACK_ETF_POR_TICKER.get(tk)
            if etf and etf not in etfs_sector:
                etfs_sector.append(etf)
        print(f"\n  Sonrisas sectoriales para el fallback ({', '.join(etfs_sector) or 'ninguna'}):")
        _sin_etf = [tk for tk in tickers if tk not in FALLBACK_ETF_POR_TICKER]
        if _sin_etf:
            print(f"  Sin ETF en FALLBACK_ETF_POR_TICKER (usan historico): {', '.join(_sin_etf)}")
        for etf in etfs_sector:
            if etf in detalle_ssvi and detalle_ssvi[etf].get("usar_alas"):
                detalle_sector[etf] = detalle_ssvi[etf]
                print(f"  {etf}: reutilizada del universo | {_diag_ssvi(detalle_ssvi[etf])}")
                continue
            print(f"  Calibrando SSVI sector: {etf} ... ", end="")
            try:
                res_etf = calibrar_ssvi_ticker(etf, POLYGON_API_KEY, tau_horizonte)
            except Exception as e:
                print(f"sin sonrisa ({e})")
                continue
            if res_etf is not None and res_etf.get("usar_alas"):
                detalle_sector[etf] = res_etf
                print(f"OK | {_diag_ssvi(res_etf)}")
            else:
                porque = (res_etf or {}).get("motivo_fallback") or "rechazada"
                print(f"sin sonrisa usable ({porque})")

    print(f"\n=== Volatilidades ATM al horizonte de {MESES_HORIZONTE} meses "
          f"(SSVI anualizada y luego escalada; M-11) ===")
    print(pd.Series({t: round(sigma_iv_horizon[t], 4) for t in tickers}))

    sigma_iv_horizon_vec = np.array([sigma_iv_horizon[t] for t in tickers])
    D_IV_horizon = np.diag(sigma_iv_horizon_vec)
    Sigma_horizon = D_IV_horizon @ Corr_hist @ D_IV_horizon
    Sigma_horizon = pd.DataFrame(Sigma_horizon, index=tickers, columns=tickers)

else:
    print("\n=== USAR_IV_POLYGON = False - usando Sigma 100% historica al horizonte ===")
    Sigma_horizon = Sigma_hist_df.copy()
    tau_horizonte = MESES_HORIZONTE / 12
    detalle_ssvi = {}
    resultado_ssvi = {}
    motivo_calibracion = {}
    detalle_sector = {}


# ==============================================================================
# BLOQUE 1C: MODULO BKM - MOMENTOS RISK-NEUTRAL DE ORDEN SUPERIOR
# ==============================================================================

from scipy.stats import norm

Rf_anual_bkm = Rf


def bs_price(S, K, T, r, sigma, tipo="call"):
    if T <= 0 or sigma <= 0:
        return max(0.0, (S - K) if tipo == "call" else (K - S))
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if tipo == "call":
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def sigma_desde_ssvi(K, F, T, rho, eta, gamma, theta_tau):
    k = np.log(K / F)
    w = ssvi_w(k, theta_tau, rho, eta, gamma)
    w = max(w, 1e-8)
    return np.sqrt(w / T)


def otm_price_ssvi(K, S, F, T, r, rho, eta, gamma, theta_tau):
    sigma_k = sigma_desde_ssvi(K, F, T, rho, eta, gamma, theta_tau)
    tipo = "put" if K < S else "call"
    return bs_price(S, K, T, r, sigma_k, tipo=tipo)


def calcular_bkm_moments(S, F, T, r, rho, eta, gamma, theta_tau,
                          n_std=BKM_N_STD, n_puntos=400, k_min=None, k_max=None):
    sigma_atm = sigma_desde_ssvi(F, F, T, rho, eta, gamma, theta_tau)
    K_min, K_max = bm.integration_strike_bounds(
        F, sigma_atm, T, n_std=n_std, k_min=k_min, k_max=k_max)
    strikes = np.linspace(K_min, K_max, n_puntos)

    precios = np.array([
        otm_price_ssvi(K, S, F, T, r, rho, eta, gamma, theta_tau)
        for K in strikes
    ])

    lnKS = np.log(strikes / S)

    peso_V = 2.0 * (1 - lnKS) / strikes ** 2
    peso_W = (6.0 * lnKS - 3.0 * lnKS ** 2) / strikes ** 2
    peso_X = (12.0 * lnKS ** 2 - 4.0 * lnKS ** 3) / strikes ** 2

    V_T = rk.trapezoid(peso_V * precios, strikes)
    W_T = rk.trapezoid(peso_W * precios, strikes)
    X_T = rk.trapezoid(peso_X * precios, strikes)

    mu_T = (np.exp(r * T) - 1
            - np.exp(r * T) / 2 * V_T
            - np.exp(r * T) / 6 * W_T
            - np.exp(r * T) / 24 * X_T)

    MFIV = np.exp(r * T) * V_T - mu_T ** 2
    if MFIV <= 0 or not np.isfinite(MFIV):
        return dict(MFIV=np.nan, MFIS=np.nan, MFIK=np.nan,
                     V_T=V_T, W_T=W_T, X_T=X_T)

    MFIS = (np.exp(r * T) * W_T - 3 * mu_T * np.exp(r * T) * V_T + 2 * mu_T ** 3) / MFIV ** 1.5
    MFIK = (np.exp(r * T) * X_T - 4 * mu_T * np.exp(r * T) * W_T
            + 6 * mu_T ** 2 * np.exp(r * T) * V_T - 3 * mu_T ** 4) / MFIV ** 2

    return dict(MFIV=MFIV, MFIS=MFIS, MFIK=MFIK, V_T=V_T, W_T=W_T, X_T=X_T)


def _momento_pendiente(motivo, mfiv=np.nan):
    """Sonrisa rechazada: MFIS/MFIK se rellenan tras el bootstrap fisico."""
    return dict(MFIV=mfiv, MFIS=np.nan, MFIK=np.nan, V_T=np.nan, W_T=np.nan, X_T=np.nan,
                fuente_momentos="fallback", motivo_fallback=motivo)


def _spot_bkm(tk, det):
    """Cierre del dia de la cadena, o el spot del snapshot si esa barra no esta."""
    serie = precios_diarios[tk].dropna()
    cierre = float(serie.iloc[-1]) if len(serie) else np.nan
    fecha_cierre = pd.Timestamp(serie.index[-1]).date() if len(serie) else None
    elec = bm.elegir_spot_momentos(
        cierre, fecha_cierre, date.today(), (det or {}).get("spot_cadena"))
    if elec["fuente"] != "cierre":
        print(f"  {tk}: spot de momentos = {elec['spot']:.2f} ({elec['fuente']}; "
              f"cierre {elec['fecha_cierre']} = {elec['cierre']}; "
              f"cadena = {elec['spot_cadena']})")
    elif (np.isfinite(elec["spot_cadena"]) and np.isfinite(elec["cierre"])
          and elec["cierre"] > 0
          and abs(elec["cierre"] / elec["spot_cadena"] - 1.0) > 0.02):
        print(f"  {tk}: cierre y spot de la cadena difieren "
              f"({elec['cierre']:.2f} vs {elec['spot_cadena']:.2f}); se usa el cierre del dia")
    return elec["spot"]


print("\n=== Calculando momentos BKM (MFIV, MFIS, MFIK) por ticker ===")

bkm_moments = {}
r_bkm = Rf_anual_bkm

for tk in tickers:
    if tk not in detalle_ssvi:
        det_r = resultado_ssvi.get(tk) or {}
        razon = det_r.get("motivo_fallback") or motivo_calibracion.get(tk) or "sin superficie"
        print(f"  {tk}: sin sonrisa usable, se omite BKM | "
              f"fallback {FALLBACK_MOMENTOS} ({razon})")
        bkm_moments[tk] = _momento_pendiente(razon)
        continue

    det = detalle_ssvi[tk]
    try:
        S_tk = _spot_bkm(tk, det)
        if not (np.isfinite(S_tk) and S_tk > 0):
            raise ValueError("sin spot")
        F_tk = S_tk * np.exp(r_bkm * tau_horizonte)
        theta_tau_tk = det["sigma_atm_annual"] ** 2 * tau_horizonte
        # Sin k_min/k_max: la integral es +/- BKM_N_STD sigma al horizonte,
        # sobre las alas SSVI. El k del ajuste (|k|<=0.5) no recorta.
        resultado_bkm = calcular_bkm_moments(
            S=S_tk, F=F_tk, T=tau_horizonte, r=r_bkm,
            rho=det["rho"], eta=det["eta"], gamma=det["gamma"],
            theta_tau=theta_tau_tk, n_std=BKM_N_STD,
        )
        ala = BKM_N_STD * det["sigma_atm_annual"] * math.sqrt(tau_horizonte)
        banda = bm.mfiv_vs_atm(resultado_bkm["MFIV"], theta_tau_tk, *BKM_MFIV_RATIO)
        if not banda["ok"]:
            print(f"  {tk}: MFIV/varianza ATM = {banda['ratio']} fuera de "
                  f"{BKM_MFIV_RATIO}; se usa la varianza ATM y el fallback "
                  f"{FALLBACK_MOMENTOS} para MFIS/MFIK")
            resultado_bkm = {
                **resultado_bkm, "MFIV": banda["mfiv"], "MFIS": np.nan, "MFIK": np.nan,
                "fuente_momentos": "fallback", "motivo_fallback": "mfiv_fuera_de_banda",
            }
        else:
            cap_mfik = rk.mfik_cap(
                det.get("n_strikes", 0), base=BKM_MFIK_MAX, hard=BKM_MFIK_MAX_HARD)
            if not rk.higher_moments_admissible(
                    resultado_bkm["MFIS"], resultado_bkm["MFIK"], cap_mfik):
                print(f"  {tk}: MFIS/MFIK inadmisibles ({resultado_bkm['MFIS']:.3f}, "
                      f"{resultado_bkm['MFIK']:.3f}, tope {cap_mfik:.1f} con "
                      f"{det.get('n_strikes', 0)} strikes) -> fallback {FALLBACK_MOMENTOS}")
                resultado_bkm = {
                    **resultado_bkm, "MFIS": np.nan, "MFIK": np.nan,
                    "fuente_momentos": "fallback", "motivo_fallback": "momentos_inadmisibles",
                }
            else:
                resultado_bkm = {
                    **resultado_bkm, "fuente_momentos": "ssvi", "motivo_fallback": "",
                }
        bkm_moments[tk] = resultado_bkm
        if resultado_bkm.get("fuente_momentos") == "ssvi":
            print(f"  {tk}: MFIV={resultado_bkm['MFIV']:.4f} | MFIS={resultado_bkm['MFIS']:.3f} "
                  f"| MFIK={resultado_bkm['MFIK']:.3f} | spot={S_tk:.2f} | integral k=+/-{ala:.2f} "
                  f"({BKM_N_STD:.0f} sigma; ajuste |k|<={SSVI_K_ABS_MAX}) | aceptada")
    except Exception as e:
        print(f"  {tk}: fallback {FALLBACK_MOMENTOS} ({e})")
        bkm_moments[tk] = _momento_pendiente(str(e))

print("\n=== Sonrisas aceptadas (el resto espera el fallback de momentos) ===")
_aceptadas = [t for t in tickers if bkm_moments[t].get("fuente_momentos") == "ssvi"]
if _aceptadas:
    print(pd.DataFrame({
        "MFIS": [round(bkm_moments[t]["MFIS"], 3) for t in _aceptadas],
        "MFIK": [round(bkm_moments[t]["MFIK"], 3) for t in _aceptadas],
    }, index=_aceptadas))
else:
    print("  Ninguna sonrisa aceptada.")

# ==============================================================================
# BLOQUE 1D: MODULO ECONOMETRICO Q -> P
# ==============================================================================

print("\n" + "=" * 79)
print("BLOQUE 1D: AJUSTE ECONOMETRICO Q -> P (VRP / SRP / KRP)")
print("=" * 79)

retornos_dia = np.log(precios_diarios / precios_diarios.shift(1)).dropna(how="all")
retornos_dia = retornos_dia[tickers]

H_VENTANA = horizonte_dias

R_dia = retornos_dia.dropna().values
T_dia = R_dia.shape[0]

peso_tiempo = np.exp(-np.log(2.0) * (T_dia - 1 - np.arange(T_dia)) / HALF_LIFE_PRIOR)
peso_tiempo = peso_tiempo / peso_tiempo.sum()


# ==============================================================================
# 1D.0  BOOTSTRAP ESTACIONARIO POR BLOQUES
# ==============================================================================
# Compartido con el Bloque 7.

def bootstrap_estacionario(R, J, H, L_bloque, pesos_inicio, rng, chunk=2000):
    """Panel (J x n) de log-retornos agregados a H dias.

    Se remuestrean FILAS COMPLETAS, de modo que la dependencia transversal
    (correlaciones y colas conjuntas) se preserva sin imponer copula alguna.
    Con probabilidad 1/L se salta a un nuevo indice inicial (muestreado con
    decaimiento exponencial en el tiempo); si no, se avanza un dia con
    envoltura circular. Longitudes de bloque geometricas => estacionariedad
    del esquema de remuestreo (Politis-Romano, 1994).
    """
    T_, n_ = R.shape
    p_salto = 1.0 / max(L_bloque, 1)
    salida = np.empty((J, n_))
    hecho = 0
    while hecho < J:
        m = min(chunk, J - hecho)
        idx = np.empty((m, H), dtype=np.int64)
        idx[:, 0] = rng.choice(T_, size=m, p=pesos_inicio)
        saltos = rng.random((m, H - 1)) < p_salto
        nuevos = rng.choice(T_, size=(m, H - 1), p=pesos_inicio)
        for h in range(1, H):
            avance = (idx[:, h - 1] + 1) % T_
            idx[:, h] = np.where(saltos[:, h - 1], nuevos[:, h - 1], avance)
        salida[hecho:hecho + m] = R[idx].sum(axis=1)
        hecho += m
    return salida


# ==============================================================================
# 1D.1a  ESTIMADOR DE VENTANAS RODANTES
# ==============================================================================
# Diagnostico.

def momentos_realizados_rolling(serie_diaria, H=H_VENTANA, paso=PASO_VENTANA_ROLLING):
    """Momentos realizados del retorno agregado a H dias, en ventanas rodantes.

        RV_t    = sum_{d in t} r_d^2                    (exacto, sin supuestos)
        RSkew_t = sum r_d^3 / RV_t^{3/2}                (agregacion iid)
        RKurt_t = 3 + (H*sum r_d^4/RV_t^2 - 3)/H        (agregacion iid)

    RV_t es la varianza realizada del retorno a H dias. Las otras dos suponen
    incrementos iid (Skew_H = Skew_d/sqrt(H), ExKurt_H = ExKurt_d/H), lo que
    hace que converjan MECANICAMENTE a 0 y 3 al crecer H: a 4 meses ese
    estimador es vacio y por eso solo se conserva como diagnostico frente al
    bootstrap por bloques, que es el estimador primario.
    """
    r = pd.Series(serie_diaria).dropna().values
    if len(r) < H + paso:
        return np.array([]), np.array([]), np.array([])

    rv_l, rs_l, rk_l = [], [], []
    for fin in range(H, len(r) + 1, paso):
        w = r[fin - H:fin]
        rv = float(np.sum(w ** 2))
        if rv <= 0 or not np.isfinite(rv):
            continue
        rs = float(np.sum(w ** 3) / rv ** 1.5)
        kurt_d = float(H * np.sum(w ** 4) / rv ** 2)
        rk = 3.0 + (kurt_d - 3.0) / H
        if not (np.isfinite(rs) and np.isfinite(rk)):
            continue
        rv_l.append(rv); rs_l.append(rs); rk_l.append(rk)
    return np.array(rv_l), np.array(rs_l), np.array(rk_l)


def winsorizar(x, p=WINSOR_MOMENTOS):
    """Winsorizacion simetrica: acota outliers sin descartar observaciones."""
    if len(x) == 0 or p <= 0:
        return x
    lo, hi = np.quantile(x, [p, 1 - p])
    return np.clip(x, lo, hi)


def _nw_lags(T, H=H_VENTANA, paso=PASO_VENTANA_ROLLING):
    """Rezagos Newey-West. Como minimo el solapamiento mecanico H/paso."""
    if NW_LAGS_AUTO:
        L = int(np.floor(4 * (max(T, 2) / 100.0) ** (2.0 / 9.0)))
    else:
        L = NW_LAGS_FIJOS
    L_solape = int(np.ceil(H / max(paso, 1))) - 1
    return int(max(1, min(max(L, L_solape), max(1, T - 2))))


def media_hac(x):
    """Media muestral y error estandar robusto a heterocedasticidad y
    autocorrelacion (Newey-West / Bartlett). Necesario porque las ventanas
    rodantes se solapan y por tanto estan fuertemente autocorrelacionadas."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    T = len(x)
    if T == 0:
        return np.nan, np.nan, 0
    if T == 1:
        return float(x[0]), np.nan, 1

    L = _nw_lags(T)
    if HAY_STATSMODELS:
        try:
            mod = sm.OLS(x, np.ones(T)).fit(cov_type="HAC",
                                            cov_kwds=dict(maxlags=L, use_correction=True))
            return float(mod.params[0]), float(mod.bse[0]), T
        except Exception:
            pass

    mu = float(np.mean(x))
    e = x - mu
    S = float(np.dot(e, e) / T)
    for l in range(1, L + 1):
        S += 2.0 * (1.0 - l / (L + 1.0)) * float(np.dot(e[l:], e[:-l]) / T)
    return mu, float(np.sqrt(max(S, 1e-18) / T)), T


filas_roll = []
for tk in tickers:
    # kurt_roll, no `rk`: ese nombre es el modulo risk_estimators.
    rv, rs, kurt_roll = momentos_realizados_rolling(retornos_dia[tk])
    if len(rv) < MIN_VENTANAS_ROLLING:
        filas_roll.append(dict(ticker=tk, n_ventanas=len(rv),
                               RV_med=float(Sigma_hist_df.loc[tk, tk]), RV_se=np.nan,
                               RS_roll=0.0, RK_roll=3.0))
        continue
    rv, rs, kurt_roll = winsorizar(rv), winsorizar(rs), winsorizar(kurt_roll)
    rv_m, rv_se, _ = media_hac(rv)
    rs_m, _, _ = media_hac(rs)
    rk_m, _, _ = media_hac(kurt_roll)
    filas_roll.append(dict(ticker=tk, n_ventanas=len(rv),
                           RV_med=rv_m, RV_se=rv_se, RS_roll=rs_m, RK_roll=rk_m))

rolling = pd.DataFrame(filas_roll).set_index("ticker").loc[tickers]

# ==============================================================================
# 1D.1b  ESTIMADOR BOOTSTRAP DE LA DISTRIBUCION A H DIAS
# ==============================================================================
# Estimador primario.

def momentos_horizonte_bootstrap(R, H, n_rep=N_REP_BOOTSTRAP_MOM,
                                 J_rep=J_POR_REPLICA_MOM, rng=None):
    """Momentos fisicos del retorno a H dias y su error estandar.

    Estimador PRIMARIO de la asimetria y la curtosis fisicas: los bloques
    preservan la agrupacion de volatilidad y los saltos, de modo que la
    distribucion a H dias no converge artificialmente a la normal como si
    ocurre bajo la agregacion iid de las ventanas rodantes.

    Cada replica genera J_rep trayectorias por bootstrap estacionario y calcula
    varianza, asimetria y curtosis de la distribucion agregada. La media entre
    replicas es el estimador puntual; la desviacion estandar entre replicas es
    el error estandar (variabilidad de remuestreo).
    """
    rng = rng_global if rng is None else rng
    n_ = R.shape[1]
    var_r = np.empty((n_rep, n_)); sk_r = np.empty((n_rep, n_)); ku_r = np.empty((n_rep, n_))
    for m in range(n_rep):
        Xb = bootstrap_estacionario(R, J_rep, H, BOOTSTRAP_BLOQUE, peso_tiempo, rng)
        c = Xb - Xb.mean(axis=0)
        v = (c ** 2).mean(axis=0)
        sd = np.sqrt(np.maximum(v, 1e-18))
        var_r[m] = v
        sk_r[m] = (c ** 3).mean(axis=0) / sd ** 3
        ku_r[m] = (c ** 4).mean(axis=0) / sd ** 4
    return (var_r.mean(0), var_r.std(0, ddof=1),
            sk_r.mean(0), sk_r.std(0, ddof=1),
            ku_r.mean(0), ku_r.std(0, ddof=1))


print(f"\nEstimando momentos fisicos a {H_VENTANA} dias por bootstrap estacionario "
      f"({N_REP_BOOTSTRAP_MOM} replicas x {J_POR_REPLICA_MOM} trayectorias)...")

(var_bs, var_bs_se, skew_bs, skew_bs_se,
 kurt_bs, kurt_bs_se) = momentos_horizonte_bootstrap(R_dia, H_VENTANA)

var_P_est = rolling["RV_med"].values.copy()
var_P_se = np.where(np.isfinite(rolling["RV_se"].values), rolling["RV_se"].values,
                    var_bs_se)
var_P_se = np.where(var_P_se > 0, var_P_se, 0.10 * var_P_est + 1e-10)

skew_P_est, skew_P_se = skew_bs, np.maximum(skew_bs_se, 1e-4)
kurt_P_est, kurt_P_se = kurt_bs, np.maximum(kurt_bs_se, 1e-4)

print("\n=== Momentos fisicos estimados al horizonte ===")
print(pd.DataFrame({
    "Var_P": np.round(var_P_est, 5), "se": np.round(var_P_se, 5),
    "Var_P_bootstrap": np.round(var_bs, 5),
    "Skew_P": np.round(skew_P_est, 3), "se_S": np.round(skew_P_se, 3),
    "Skew_iid_roll": np.round(rolling["RS_roll"].values, 3),
    "Kurt_P": np.round(kurt_P_est, 3), "se_K": np.round(kurt_P_se, 3),
    "Kurt_iid_roll": np.round(rolling["RK_roll"].values, 3),
}, index=tickers).to_string())
print("  (las columnas *_iid_roll son el estimador de ventanas rodantes bajo "
      "agregacion iid;\n   convergen mecanicamente a 0 y 3 al crecer H y por eso "
      "no se usan como estimador primario)")


def _sanear_momento_fisico(skew, kurt):
    """Lleva un par fisico a las cotas del modelo y a la desigualdad de Pearson."""
    try:
        s = float(skew)
        k = float(kurt)
    except (TypeError, ValueError):
        return np.nan, np.nan
    if not (np.isfinite(s) and np.isfinite(k)):
        return np.nan, np.nan
    s = float(np.clip(s, *COTA_SKEW_P))
    k = float(np.clip(k, *COTA_KURT_P))
    k = max(k, s ** 2 + 1.05)
    return s, k


_cache_momentos_sector = {}


def _momentos_sector(tk):
    """MFIS/MFIK del ETF sectorial, si FALLBACK_MOMENTOS == 'sector' y la sonrisa entro."""
    if FALLBACK_MOMENTOS != "sector":
        return np.nan, np.nan
    etf = FALLBACK_ETF_POR_TICKER.get(tk)
    if not etf or etf not in detalle_sector:
        return np.nan, np.nan
    if etf in _cache_momentos_sector:
        return _cache_momentos_sector[etf]
    det = detalle_sector[etf]
    try:
        S = float(det.get("spot_cadena", np.nan))
        if not (np.isfinite(S) and S > 0):
            if etf in precios_diarios.columns:
                serie_etf = precios_diarios[etf].dropna()
                S = float(serie_etf.iloc[-1]) if len(serie_etf) else np.nan
            else:
                serie_etf = descargar_precio(etf, fecha_fin - timedelta(days=10), fecha_fin,
                                             fx_prices=fx_prices_diarios)
                S = float(serie_etf.iloc[-1]) if serie_etf is not None and len(serie_etf) else np.nan
        if not (np.isfinite(S) and S > 0):
            raise ValueError("sin spot del ETF")
        theta = det["sigma_atm_annual"] ** 2 * tau_horizonte
        mom = calcular_bkm_moments(
            S=S, F=S * np.exp(r_bkm * tau_horizonte), T=tau_horizonte, r=r_bkm,
            rho=det["rho"], eta=det["eta"], gamma=det["gamma"],
            theta_tau=theta, n_std=BKM_N_STD)
        banda = bm.mfiv_vs_atm(mom["MFIV"], theta, *BKM_MFIV_RATIO)
        cap = rk.mfik_cap(det.get("n_strikes", 0), base=BKM_MFIK_MAX, hard=BKM_MFIK_MAX_HARD)
        if not banda["ok"] or not rk.higher_moments_admissible(mom["MFIS"], mom["MFIK"], cap):
            raise ValueError("momentos del ETF fuera de banda")
        par = (float(mom["MFIS"]), float(mom["MFIK"]))
    except Exception as e:
        print(f"  {etf}: sonrisa sectorial no usable ({e})")
        par = (np.nan, np.nan)
    _cache_momentos_sector[etf] = par
    return par


print(f"\n=== Fallback de momentos (modo {FALLBACK_MOMENTOS}) ===")
n_fallback_momentos = 0
for i, tk in enumerate(tickers):
    mom = bkm_moments[tk]
    if mom.get("fuente_momentos") == "ssvi" and np.isfinite(mom.get("MFIS", np.nan)):
        continue
    s_h, k_h = _sanear_momento_fisico(skew_bs[i], kurt_bs[i])
    s_sec, k_sec = _momentos_sector(tk)
    if np.isfinite(s_sec):
        s_sec, k_sec = _sanear_momento_fisico(s_sec, k_sec)
    fb = bm.momentos_fallback(
        FALLBACK_MOMENTOS, s_h, k_h, s_sec, k_sec, kurt_max=COTA_KURT_P[1])
    mom["MFIS"] = fb["mfis"]
    mom["MFIK"] = fb["mfik"]
    mom["fuente_momentos"] = fb["fuente"]
    n_fallback_momentos += 1
    print(f"  {tk}: fallback {fb['fuente']} | MFIS={fb['mfis']:.3f} | "
          f"MFIK={fb['mfik']:.3f} | motivo: {mom.get('motivo_fallback') or 'sin sonrisa'}")
if n_fallback_momentos == 0:
    print("  Ningun ticker entro al fallback.")

MFIS_vec = np.array([bkm_moments[t]["MFIS"] for t in tickers], dtype=float)
MFIK_vec = np.array([bkm_moments[t]["MFIK"] for t in tickers], dtype=float)
mask_sonrisa = np.array(
    [bkm_moments[t].get("fuente_momentos") == "ssvi" for t in tickers], dtype=bool)

print("\n=== Momentos de orden superior por ticker ===")
print(pd.DataFrame({
    "MFIS": np.round(MFIS_vec, 3),
    "MFIK": np.round(MFIK_vec, 3),
    "fuente": [bkm_moments[t].get("fuente_momentos", "") for t in tickers],
}, index=tickers))

# ==============================================================================
# 1D.2  REGRESION DE CALIBRACION MINCER-ZARNOWITZ -> PRIMAS DE RIESGO
# ==============================================================================

MFIV_vec = np.array([bkm_moments[t]["MFIV"] for t in tickers], dtype=float)
n_mfiv_fallback = 0
for i, tk in enumerate(tickers):
    # La diagonal de Sigma_horizon ya es varianza al horizonte. Antes, con
    # SSVI bien y BKM mal, aqui entraba sigma_atm^2 anual (~1/tau veces mayor).
    previo = MFIV_vec[i]
    MFIV_vec[i] = bm.mfiv_or_horizon_variance(previo, float(Sigma_horizon.iloc[i, i]))
    if not (np.isfinite(previo) and previo > 0):
        n_mfiv_fallback += 1
if n_mfiv_fallback:
    print(f"  MFIV de respaldo (varianza al horizonte, no anual) en {n_mfiv_fallback} tickers")


def mincer_zarnowitz(y, x, se_y, nombre, dominio=None, piso=None):
    """WLS de y (momento fisico) sobre x (momento implicito), pesos 1/se_y^2.

    Regresion de calibracion en la seccion transversal de los n activos:

        Momento_fisico_i = a + b * Momento_implicito_i + u_i,   w_i = 1/se_i^2

    El pronostico fisico es el valor ajustado y la prima de riesgo del momento
    es el residuo estructural entre el implicito y ese pronostico:

        VRP_i = MFIV_i - (a_V + b_V * MFIV_i),   idem SRP y KRP

    No es circular, a diferencia de restar la media realizada -- que devolveria
    el propio momento realizado y destruiria la informacion prospectiva de la
    superficie: b conserva la dispersion transversal de las opciones y a y
    (1 - b) corrigen el sesgo.

    `piso` activa la version MULTIPLICATIVA del modelo. La varianza y la
    curtosis estan acotadas por abajo (var > 0, kurt >= 1), de modo que una
    prima ADITIVA puede empujar el pronostico fuera del dominio: restar una
    prima media de 2.5 a una curtosis implicita de 3.5 daria 1.0, inadmisible.
    Con `piso` la regresion se corre en logaritmos del exceso sobre esa cota,

        log(y - piso) = a + b * log(x - piso) + u

    y se retransforma con el estimador de smearing de Duan, E[exp(u)], que
    corrige el sesgo de Jensen al volver a niveles. El pronostico resultante
    respeta el dominio por construccion. La asimetria, que no esta acotada, se
    estima en niveles.

    Si la pendiente no es informativa se degrada al modelo restringido b = 1
    (prima constante, de nivel o de escala segun el caso); si el momento
    implicito no tiene dispersion, a la media ponderada.
    """
    y_orig = np.asarray(y, float); x_orig = np.asarray(x, float)
    se_orig = np.asarray(se_y, float)
    w = 1.0 / np.maximum(se_orig, 1e-12) ** 2
    w = w / w.mean()

    log_mode = piso is not None
    if log_mode:
        eps = 1e-6
        y = np.log(np.maximum(y_orig - piso, eps))
        x = np.log(np.maximum(x_orig - piso, eps))
        se_y = se_orig / np.maximum(y_orig - piso, eps)
    else:
        y, x, se_y = y_orig, x_orig, se_orig

    def a_nivel(fit_log, resid=None):
        """Retransformacion con smearing de Duan."""
        smear = float(np.mean(np.exp(resid))) if resid is not None else 1.0
        return piso + np.exp(fit_log) * smear

    if np.std(x) < 1e-12 or len(y) < 4:
        ajuste = np.full_like(y, float(np.average(y, weights=w)))
        if log_mode:
            ajuste = a_nivel(ajuste, y - np.average(y, weights=w))
        if dominio is not None:
            ajuste = np.clip(ajuste, dominio[0], dominio[1])
        return dict(fit=ajuste, se_fit=se_orig, a=np.nan, b=np.nan,
                    t_b=np.nan, r2=np.nan, modelo="media_ponderada", nombre=nombre)

    Xr = np.column_stack([np.ones_like(x), x])
    if HAY_STATSMODELS:
        mod = sm.WLS(y, Xr, weights=w).fit(cov_type="HC3")
        a, b = float(mod.params[0]), float(mod.params[1])
        se_b = float(mod.bse[1])
        r2 = float(mod.rsquared)
        se_media = np.sqrt(np.maximum(
            np.sum((Xr @ mod.cov_params()) * Xr, axis=1), 0.0))
    else:
        W = np.diag(w)
        XtWX_inv = np.linalg.pinv(Xr.T @ W @ Xr)
        beta = XtWX_inv @ (Xr.T @ W @ y)
        a, b = float(beta[0]), float(beta[1])
        resid = y - Xr @ beta
        s2 = float(resid @ (w * resid) / max(len(y) - 2, 1))
        V = s2 * XtWX_inv
        se_b = float(np.sqrt(max(V[1, 1], 0.0)))
        sst = float(np.sum(w * (y - np.average(y, weights=w)) ** 2))
        r2 = 1.0 - float(np.sum(w * resid ** 2)) / max(sst, 1e-18)
        se_media = np.sqrt(np.maximum(np.sum((Xr @ V) * Xr, axis=1), 0.0))

    t_b = b / se_b if se_b > 0 else np.nan

    usable = (np.isfinite(t_b) and abs(t_b) >= 1.0 and 0.02 <= b <= 3.0)
    if usable:
        ajuste_lin = a + b * x
        resid = y - ajuste_lin
        modelo = "mincer_zarnowitz" + ("_log" if log_mode else "")
    else:
        prima_nivel = float(np.average(x - y, weights=w))
        ajuste_lin = x - prima_nivel
        resid = y - ajuste_lin
        se_media = np.full_like(x, float(np.sqrt(
            np.average(resid ** 2, weights=w) / len(x))))
        modelo = ("escala_constante(b=1)" if log_mode else "nivel_constante(b=1)")

    se_pred_esc = np.sqrt(se_media ** 2 + np.asarray(se_y, float) ** 2)

    if log_mode:
        ajuste = a_nivel(ajuste_lin, resid)
        se_fit = np.maximum(ajuste - piso, 1e-12) * se_pred_esc
    else:
        ajuste = ajuste_lin
        se_fit = se_pred_esc

    if dominio is not None:
        ajuste = np.clip(ajuste, dominio[0], dominio[1])

    return dict(fit=ajuste, se_fit=se_fit, a=a, b=b, t_b=t_b, r2=r2,
                modelo=modelo, nombre=nombre)


def pronostico_con_sonrisa(y, x, se, nombre, mask, dominio=None, piso=None):
    """MZ en las sonrisas aceptadas. El fallback conserva su momento (x).

    Meter el fallback en la transversal (antes era 0 y 3) sesga a y b. Con
    menos de 4 sonrisas no hay regresion: cada nombre se queda con su fisico.
    """
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    se = np.asarray(se, dtype=float)
    mask = np.asarray(mask, dtype=bool)
    n_sonrisa = int(mask.sum())
    fit = np.array(y, dtype=float, copy=True)
    se_fit = np.array(se, dtype=float, copy=True)
    if n_sonrisa >= 4:
        reg = mincer_zarnowitz(
            y[mask], x[mask], se[mask], nombre, dominio=dominio, piso=piso)
        fit[mask] = reg["fit"]
        se_fit[mask] = reg["se_fit"]
        a, b, t_b, r2 = reg["a"], reg["b"], reg["t_b"], reg["r2"]
        modelo = reg["modelo"]
    else:
        a = b = t_b = r2 = np.nan
        modelo = "fisico (sin sonrisas suficientes)"
    if np.any(~mask):
        fit[~mask] = x[~mask]
    return dict(fit=fit, se_fit=se_fit, a=a, b=b, t_b=t_b, r2=r2,
                modelo=modelo, nombre=nombre, n_sonrisa=n_sonrisa)


reg_V = mincer_zarnowitz(var_P_est, MFIV_vec, var_P_se, "Varianza",
                         dominio=(1e-8, np.inf), piso=0.0)
reg_S = pronostico_con_sonrisa(
    skew_P_est, MFIS_vec, skew_P_se, "Asimetria", mask_sonrisa, dominio=COTA_SKEW_P)
reg_K = pronostico_con_sonrisa(
    kurt_P_est, MFIK_vec, kurt_P_se, "Curtosis", mask_sonrisa,
    dominio=COTA_KURT_P, piso=1.0)

print("\n=== Regresiones de calibracion Mincer-Zarnowitz (seccion transversal, "
      f"n = {n} activos, WLS) ===")
print(pd.DataFrame([
    dict(Momento=r["nombre"], Modelo=r["modelo"],
         a=round(r["a"], 4) if np.isfinite(r["a"]) else np.nan,
         b=round(r["b"], 4) if np.isfinite(r["b"]) else np.nan,
         t_b=round(r["t_b"], 2) if np.isfinite(r["t_b"]) else np.nan,
         R2=round(r["r2"], 3) if np.isfinite(r["r2"]) else np.nan)
    for r in (reg_V, reg_S, reg_K)
]).to_string(index=False))
print("  (b < 1 => el momento implicito sobre-reacciona respecto del fisico, "
      "que es el patron documentado)")
print(f"  NOTA (B-10): Mincer-Zarnowitz es transversal con n = {n}. Con ~19 nombres "
      "la potencia es baja y a, b salen ruidosos. No se cambia el estimador.")
print(f"  Asimetria y curtosis: la regresion usa {int(mask_sonrisa.sum())} sonrisas aceptadas; "
      f"{int((~mask_sonrisa).sum())} tickers conservan el fallback {FALLBACK_MOMENTOS} "
      f"(SRP = KRP = 0 ahi).")

# ==============================================================================
# PRONOSTICOS FISICOS Y PRIMAS DE RIESGO
# ==============================================================================
var_P = reg_V["fit"].copy()
skew_P = reg_S["fit"].copy()
kurt_P = reg_K["fit"].copy()

se_var_P, se_skew_P, se_kurt_P = reg_V["se_fit"], reg_S["se_fit"], reg_K["se_fit"]

VRP = MFIV_vec - var_P
SRP = MFIS_vec - skew_P
KRP = MFIK_vec - kurt_P

t_VRP = VRP / np.maximum(se_var_P, 1e-12)
t_SRP = SRP / np.maximum(se_skew_P, 1e-12)
t_KRP = KRP / np.maximum(se_kurt_P, 1e-12)

print("\n=== Primas de riesgo de momentos (Q - P) al horizonte de "
      f"{MESES_HORIZONTE} meses ===")
print(pd.DataFrame({
    "MFIV_Q": np.round(MFIV_vec, 5), "Var_P_fit": np.round(var_P, 5),
    "VRP": np.round(VRP, 5), "t_VRP": np.round(t_VRP, 2),
    "MFIS_Q": np.round(MFIS_vec, 3), "Skew_P_fit": np.round(skew_P, 3),
    "SRP": np.round(SRP, 3), "t_SRP": np.round(t_SRP, 2),
    "MFIK_Q": np.round(MFIK_vec, 3), "Kurt_P_fit": np.round(kurt_P, 3),
    "KRP": np.round(KRP, 3), "t_KRP": np.round(t_KRP, 2),
}, index=tickers).to_string())

print(f"\n  VRP medio: {np.nanmean(VRP):+.5f}  "
      "(> 0 = la varianza implicita excede a la fisica, el signo esperado)")
print(f"  SRP medio: {np.nanmean(SRP):+.4f}  "
      "(< 0 = la asimetria implicita es mas negativa que la fisica)")
print(f"  KRP medio: {np.nanmean(KRP):+.4f}  "
      "(> 0 = la curtosis implicita excede a la fisica)")

# ==============================================================================
# 1D.3  COTAS DE SENSATEZ Y CUMULANTES FISICOS
# ==============================================================================

es_implicita = np.array(
    [fuente_vol.get(t, "historica") in ("ssvi", "atm") for t in tickers])
var_P, n_clip_vol = bm.apply_vol_q_to_p(var_P, MFIV_vec, es_implicita, COTA_RATIO_VOL_P)
n_hist_vol = int((~es_implicita).sum())
print("\n  Fuente de vol por ticker (ssvi=sonrisa, atm=theta sin alas, historica=sin ratio Q->P):")
print(pd.Series({t: fuente_vol.get(t, "historica") for t in tickers}).to_string())
if n_hist_vol:
    print(f"  Q->P de volatilidad omitido en {n_hist_vol} tickers con fuente historica")

n_clip_skew = int(np.sum((skew_P < COTA_SKEW_P[0]) | (skew_P > COTA_SKEW_P[1])))
skew_P = np.clip(skew_P, *COTA_SKEW_P)
n_clip_kurt = int(np.sum((kurt_P < COTA_KURT_P[0]) | (kurt_P > COTA_KURT_P[1])))
kurt_P = np.clip(kurt_P, *COTA_KURT_P)
kurt_P = np.maximum(kurt_P, skew_P ** 2 + 1.05)

if n_clip_vol or n_clip_skew or n_clip_kurt:
    print(f"\n  Cotas de sensatez activadas -> vol: {n_clip_vol} | "
          f"skew: {n_clip_skew} | kurt: {n_clip_kurt} activos")

sigma_P_vec = np.sqrt(var_P)

k2_P = var_P
k3_P = skew_P * sigma_P_vec ** 3
k4_P = (kurt_P - 3.0) * sigma_P_vec ** 4

k2_Q_obs = MFIV_vec
k3_Q_obs = MFIS_vec * MFIV_vec ** 1.5
k4_Q_obs = (MFIK_vec - 3.0) * MFIV_vec ** 2

se_k2_vec = np.maximum(se_var_P, 1e-10)
se_k3_vec = np.maximum(se_skew_P * sigma_P_vec ** 3, 1e-12)
se_k4_vec = np.maximum(se_kurt_P * sigma_P_vec ** 4, 1e-14)


# ==============================================================================
# 1D.4  COVARIANZA BAJO LA MEDIDA FISICA P
# ==============================================================================

D_P = np.diag(sigma_P_vec)
Sigma_P = pd.DataFrame(D_P @ Corr_hist @ D_P, index=tickers, columns=tickers)

print(f"\n  Sigma_P construida. Vol media Q: {np.mean(np.sqrt(MFIV_vec)):.4f} | "
      f"vol media P: {np.mean(sigma_P_vec):.4f} | "
      f"reduccion: {(1 - np.mean(sigma_P_vec) / np.mean(np.sqrt(MFIV_vec))) * 100:.1f}%")


# ==============================================================================
# BLOQUE 2: MARKET CAPS VIA YAHOO FINANCE -> w_mkt
# ==============================================================================

print("\n=== Extrayendo market caps via Yahoo Finance ===")


# Market cap en USD con la misma moneda de los precios: yfinance lo da en la
# moneda de cotizacion (AZN.L en peniques via fast_info, 7203.T en yenes) y
# sin convertir un internacional dominaba w_mkt.
_monedas_bl = {t: ticker_currency.get(t) for t in tickers}
_fx_spot_bl = {m: float(s.dropna().iloc[-1]) for m, s in fx_prices_diarios.items() if len(s.dropna())}
_caps_bl = md.market_caps_usd(
    tickers, ticker_currency_by_suffix,
    {m: _par_fx(m) for m in set(filter(None, _monedas_bl.values())) if m != "USD"},
    fx_provider=lambda pares: {m: _fx_spot_bl[m] for m in pares if m in _fx_spot_bl},
    monedas=_monedas_bl, cap_ttl_hours=24)
market_caps_raw = pd.Series({t: np.nan if _caps_bl["usd"][t] is None else _caps_bl["usd"][t]
                             for t in tickers})

print("Market caps extraidos (USD):")
print(pd.DataFrame({
    "moneda": pd.Series(_caps_bl["moneda"]),
    "market_cap_usd": market_caps_raw.map(lambda x: f"{x:,.0f}" if not pd.isna(x) else "NA"),
}).to_string())

if market_caps_raw.isna().all():
    print("  Yahoo Finance no devolvio datos - usando pesos iguales")
    market_caps_raw = pd.Series(1.0, index=tickers)
else:
    n_na = market_caps_raw.isna().sum()
    if n_na > 0:
        print(f"  Tickers sin market cap ({n_na}) - imputados con mediana del universo")
        market_caps_raw = market_caps_raw.fillna(market_caps_raw.median())

w_mkt = (market_caps_raw / market_caps_raw.sum()).values

print("\nPesos de mercado (w_mkt):")
print(pd.Series(np.round(w_mkt, 4), index=tickers))

# ==============================================================================
# BLOQUE 3: PERFIL DE RIESGO -> TAU, OMEGA_SCALE, GAMMA_RA
# ==============================================================================

perfil = PERFILES[PERFIL_RIESGO]
tau = perfil["tau"]
gamma_ra = perfil["gamma_ra"]

desc_perfiles = dict(
    conservador="Portafolio cercano al benchmark. Views con poco peso.",
    moderado="Balance entre consenso de mercado y vision activa.",
    agresivo="Portafolio con fuerte inclinacion hacia los views del gestor.",
)

# ==============================================================================
# DELTA DE MERCADO
# ==============================================================================
# No depende del perfil. Modo: DELTA_MKT_MODO (M-12).
Rf_h = Rf * (MESES_HORIZONTE / 12)
ret_mkt_hist = float(w_mkt @ mu_historico)
var_mkt_hist = float(w_mkt @ Sigma_hist @ w_mkt)
D_Q_horizon = np.diag(np.sqrt(np.maximum(MFIV_vec, 0.0)))
var_mkt_q = float(w_mkt @ (D_Q_horizon @ Corr_hist @ D_Q_horizon) @ w_mkt)
var_mkt_p = float(w_mkt @ Sigma_P.values @ w_mkt)
delta_mkt, delta_info = bm.market_delta(
    DELTA_MKT_MODO,
    excess_hist=ret_mkt_hist - Rf_h,
    var_hist=var_mkt_hist,
    delta_fixed=DELTA_MKT_FIJO,
    var_q=var_mkt_q,
    var_p=var_mkt_p,
)

print(f"\n=== PERFIL: {PERFIL_RIESGO.upper()} ===")
print(f"Descripcion: {desc_perfiles[PERFIL_RIESGO]}")
_impl = delta_info["implied"]
_impl_txt = f"{_impl:.4f}" if np.isfinite(_impl) else "n/a"
print(f"Delta de mercado (modo {delta_info['mode']}): {delta_mkt:.4f} | "
      f"historico={delta_info['historical']:.4f} | fijo={delta_info['fixed']:.2f} | "
      f"implicito={_impl_txt}")
if delta_info["fallback"]:
    print(f"  {delta_info['fallback']}")
if delta_info["mode"] == "historical" and np.isfinite(delta_mkt) and delta_mkt < 0:
    print("  La media de ~2 anos dio exceso negativo: pi hereda ese signo. "
          "DELTA_MKT_MODO = 'fixed' o 'implied' no usa esa muestra.")
print(f"Tau (t): {tau} | Omega scale: {perfil['omega_scale']} | Gamma_RA: {gamma_ra}")

# ==============================================================================
# BLOQUE 4: RETORNOS DE EQUILIBRIO pi - CAPM INVERTIDO
# ==============================================================================

Sigma_mat = Sigma_P.values
pi_eq = delta_mkt * (Sigma_mat @ w_mkt)

print("\n=== Retornos de equilibrio pi (prior) ===")
print(pd.Series(np.round(pi_eq, 4), index=tickers))


# ==============================================================================
# BLOQUE 4B: PROYECCION Q -> P POR TRANSFORMADA DE ESSCHER
# ==============================================================================

print("\n" + "=" * 79)
print("BLOQUE 4B: PROYECCION Q -> P (TRANSFORMADA DE ESSCHER)")
print("=" * 79)

theta_ancla = float(np.clip(delta_mkt, THETA_ESSCHER_COTA[0], THETA_ESSCHER_COTA[1]))
print(f"\n  delta_mkt (aversion al riesgo implicita del mercado): {delta_mkt:.3f}")
if not (THETA_ESSCHER_COTA[0] <= delta_mkt <= THETA_ESSCHER_COTA[1]):
    print(f"  Aviso: delta_mkt fuera del rango admisible {THETA_ESSCHER_COTA}; "
          f"el ancla se fija en {theta_ancla:.3f}"
          + (" (hipotesis nula Q = P)" if theta_ancla == 0.0 else ""))
print(f"  Ancla de theta: {theta_ancla:.3f} | rango admisible: "
      f"{THETA_ESSCHER_COTA} | difusion del ancla: {THETA_PRIOR_CV:.0%}")

# ==============================================================================
# 4B.1  TRANSFORMADA DE ESSCHER: ESTIMACION DE THETA POR GMM ANCLADO
# ==============================================================================

def cumulantes_Q_desde_P(theta, k2p, k3p, k4p):
    """k_n^Q = sum_m k_{n+m}^P (-theta)^m / m!, truncado en el 4.o cumulante."""
    return (k2p - theta * k3p + 0.5 * theta ** 2 * k4p,
            k3p - theta * k4p)


def estimar_theta_esscher(k2p, k3p, k4p, k2q, k3q, se_k2, se_k3,
                          ancla=None, cv_ancla=THETA_PRIOR_CV):
    """GMM ponderado y anclado de un parametro sobre dos condiciones de momento.

        min_theta  w2*(k2_Q(th) - k2q)^2 + w3*(k3_Q(th) - k3q)^2
                   + wa*(th - ancla)^2

    w2, w3 = inversa de la varianza estimada de cada prima (GMM eficiente de
    dos etapas simplificado). wa = 1/(cv_ancla*ancla)^2 reescalado a la misma
    unidad que las otras condiciones; su papel es identificar theta cuando
    k4_P ~ 0 vuelve plana la condicion del 3.er cumulante. Devuelve
    (theta, en_cota, J) donde J es el residuo GMM normalizado de las dos
    condiciones de momento (diagnostico de sobre-identificacion).
    """
    ancla = theta_ancla if ancla is None else ancla
    w2 = 1.0 / max(se_k2 ** 2, 1e-20)
    w3 = 1.0 / max(se_k3 ** 2, 1e-20)
    esc = w2 + w3
    w2, w3 = w2 / esc, w3 / esc

    rango = THETA_ESSCHER_COTA[1] - THETA_ESSCHER_COTA[0]
    sd_ancla = cv_ancla * max(abs(ancla), 0.5 * rango)
    wa = (k2q ** 2) / sd_ancla ** 2

    def objetivo(th):
        th = float(np.atleast_1d(th)[0])
        c2, c3 = cumulantes_Q_desde_P(th, k2p, k3p, k4p)
        return (w2 * (c2 - k2q) ** 2 + w3 * (c3 - k3q) ** 2
                + wa * (th - ancla) ** 2)

    rejilla = np.linspace(THETA_ESSCHER_COTA[0], THETA_ESSCHER_COTA[1], 251)
    th0 = float(rejilla[int(np.argmin([objetivo(t) for t in rejilla]))])
    res = minimize(objetivo, np.array([th0]), method="L-BFGS-B",
                   bounds=[THETA_ESSCHER_COTA])
    th = float(res.x[0]) if res.success else th0

    c2, c3 = cumulantes_Q_desde_P(th, k2p, k3p, k4p)
    J = float(w2 * (c2 - k2q) ** 2 + w3 * (c3 - k3q) ** 2)
    en_cota = bool(abs(th - THETA_ESSCHER_COTA[0]) < 1e-6
                   or abs(th - THETA_ESSCHER_COTA[1]) < 1e-6)
    return th, en_cota, J


def primas_esscher(theta, k2p, k3p, k4p):
    """Descomposicion de la prima total k1_P - k1_Q.

        total    = theta*k2 - theta^2/2*k3 + theta^3/6*k4
        gaussian = theta*k2                        <- ya recogida por pi_eq
        HM       = -theta^2/2*k3 + theta^3/6*k4    <- componente no gaussiana
    """
    gauss = theta * k2p
    hm = -0.5 * theta ** 2 * k3p + (theta ** 3 / 6.0) * k4p
    return gauss + hm, gauss, hm


theta_esscher = np.zeros(n); en_cota = np.zeros(n, dtype=bool); J_gmm = np.zeros(n)
prima_total = np.zeros(n); prima_gauss = np.zeros(n); prima_hm = np.zeros(n)

for i in range(n):
    theta_esscher[i], en_cota[i], J_gmm[i] = estimar_theta_esscher(
        k2_P[i], k3_P[i], k4_P[i], k2_Q_obs[i], k3_Q_obs[i],
        se_k2_vec[i], se_k3_vec[i])
    prima_total[i], prima_gauss[i], prima_hm[i] = primas_esscher(
        theta_esscher[i], k2_P[i], k3_P[i], k4_P[i])

tope_hm = MAX_PRIMA_HM_SIGMA * sigma_P_vec
n_topados = int(np.sum(np.abs(prima_hm) > tope_hm))
prima_hm = np.clip(prima_hm, -tope_hm, tope_hm)

# ==============================================================================
# 4B.2  INCERTIDUMBRE DE LA PRIMA NO GAUSSIANA
# ==============================================================================
# Alimenta Omega.

se_prima_hm = np.zeros(n)
for i in range(n):
    v_d = var_P[i] + se_var_P[i] * rng_global.standard_normal(N_MC_DELTA)
    s_d = skew_P[i] + se_skew_P[i] * rng_global.standard_normal(N_MC_DELTA)
    k_d = kurt_P[i] + se_kurt_P[i] * rng_global.standard_normal(N_MC_DELTA)
    draws = np.empty(N_MC_DELTA)
    for m in range(N_MC_DELTA):
        v_p = float(np.clip(v_d[m], (COTA_RATIO_VOL_P[0] ** 2) * MFIV_vec[i],
                            (COTA_RATIO_VOL_P[1] ** 2) * MFIV_vec[i]))
        s_p = float(np.clip(s_d[m], *COTA_SKEW_P))
        k_p = max(float(np.clip(k_d[m], *COTA_KURT_P)), s_p ** 2 + 1.05)
        sd = math.sqrt(v_p)
        c2, c3, c4 = v_p, s_p * sd ** 3, (k_p - 3.0) * sd ** 4
        th, _, _ = estimar_theta_esscher(c2, c3, c4, MFIV_vec[i], k3_Q_obs[i],
                                         se_k2_vec[i], se_k3_vec[i])
        draws[m] = np.clip(primas_esscher(th, c2, c3, c4)[2],
                           -tope_hm[i], tope_hm[i])
    se_prima_hm[i] = float(np.std(draws, ddof=1))

print("\n=== Proyeccion Q -> P y descomposicion de la prima de riesgo ===")
print("(prima_gauss ya esta recogida en pi_eq via el CAPM invertido; "
      "prima_HM es el termino no gaussiano que ajusta Q)")
print(pd.DataFrame({
    "sigma_Q": np.round(np.sqrt(MFIV_vec), 4),
    "sigma_P": np.round(sigma_P_vec, 4),
    "skew_Q": np.round(MFIS_vec, 3), "skew_P": np.round(skew_P, 3),
    "kurt_Q": np.round(MFIK_vec, 3), "kurt_P": np.round(kurt_P, 3),
    "theta": np.round(theta_esscher, 3),
    "prima_gauss": np.round(prima_gauss, 4),
    "prima_HM": np.round(prima_hm, 4),
    "se_HM": np.round(se_prima_hm, 4),
    "t_HM": np.round(prima_hm / np.maximum(se_prima_hm, 1e-10), 2),
    "J_gmm": np.round(J_gmm, 4),
}, index=tickers).to_string())
print("  (J_gmm = residuo de sobre-identificacion: valores altos indican que el "
      "truncamiento\n   en el 4.o cumulante no logra reconciliar Q y P para ese "
      "activo)")

n_cota_sup = int(np.sum(theta_esscher >= THETA_ESSCHER_COTA[1] - 1e-6))
if n_cota_sup:
    print(f"  Aviso: theta alcanzo su cota SUPERIOR en {n_cota_sup} activos "
          f"(rango admitido {THETA_ESSCHER_COTA}); bajo truncamiento en el 4.o "
          "cumulante la reconciliacion Q-P de esos activos es solo parcial.")
if float(np.mean(theta_esscher)) < 1e-3:
    print("  Nota: theta ~ 0 en todo el universo => no se detecta prima de "
          "momentos superiores y el modelo se reduce, correctamente, al "
          "Black-Litterman gaussiano estandar.")
if n_topados:
    print(f"  Aviso: prima_HM topada en {n_topados} activos por la cota economica "
          f"de {MAX_PRIMA_HM_SIGMA:.0%} de sigma_P.")


# ==============================================================================
# BLOQUE 5: TABLA DE REFERENCIA PARA VIEWS
# ==============================================================================

referencia_views = pd.DataFrame({
    "Ticker": tickers,
    "Pi_eq": np.round(pi_eq, 4),
    "Mu_historico": np.round(mu_historico, 4),
})
referencia_views["Diff_Hist_Pi"] = np.round(referencia_views["Mu_historico"] - referencia_views["Pi_eq"], 4)

print("\n=== REFERENCIA PARA FORMULAR VIEWS (Historico vs pi) ===")
print("(Diff > 0: retorno historico supera el equilibrio de mercado)")
print(referencia_views.sort_values("Diff_Hist_Pi", ascending=False).to_string(index=False))

# ==============================================================================
# BLOQUE 6: VIEWS DEL GESTOR
# ==============================================================================
# Edita aqui los views: pasos 1 a 3.

# ==============================================================================
# PASO 1: DEFINE CUANTOS VIEWS TIENES
# ==============================================================================
N_VIEWS = 3

# ==============================================================================
# PASO 2: CONSTRUYE LA MATRIZ P
# ==============================================================================
P = pd.DataFrame(0.0, index=[f"View_{i+1}" for i in range(N_VIEWS)], columns=tickers)

if os.environ.get("AMPM_SMOKE", "").strip().lower() in {"1", "true", "yes"}:
    cols = list(P.columns)
    for i, (a, b) in enumerate(((0, 1), (1, 2), (0, 2))):
        if i < len(P.index) and b < len(cols):
            P.iloc[i, a] = 1.0
            P.iloc[i, b] = -1.0
else:
    P.loc["View_1", "DELL"] = 1
    P.loc["View_1", "META"] = -1

    P.loc["View_2", "GS"] = 1
    P.loc["View_2", "REGN"] = -1

    P.loc["View_3", "EBAY"] = 1
    P.loc["View_3", "ARES"] = -1

print("\n=== Matriz P (views del gestor) ===")
print(P.round(4))

# ==============================================================================
# PASO 3: DEFINE EL VECTOR Q
# ==============================================================================
Q = pd.Series({
    "View_1": 0.15,
    "View_2": 0.10,
    "View_3": 0.08,
})

print("\n=== Vector Q (magnitudes del gestor) ===")
print(Q.round(4))

# ==============================================================================
# BLOQUE 6B: PUENTE Q -> P SOBRE (Q, Omega) + NUCLEO GAUSSIANO BL
# ==============================================================================

P_mat = P.values
Q_vec = Q.values.reshape(-1, 1)
pi_eq_col = pi_eq.reshape(-1, 1)
tauSigma = tau * Sigma_mat

# ==============================================================================
# (i) Q BAJO LA MEDIDA FISICA
# ==============================================================================
ajuste_Q_hm = P_mat @ prima_hm
Q_P = Q.values + ajuste_Q_hm

print("\n" + "=" * 79)
print("BLOQUE 6B: PUENTE ECONOMETRICO Q -> P")
print("=" * 79)
print("\n=== Ajuste vectorial de Q por prima de riesgo no gaussiana ===")
print(pd.DataFrame({
    "Q_riesgo_neutral": np.round(Q.values, 4),
    "P.prima_HM": np.round(ajuste_Q_hm, 4),
    "Q_fisico": np.round(Q_P, 4),
}, index=Q.index).to_string())

# ==============================================================================
# (ii) OMEGA BAJO LA MEDIDA FISICA
# ==============================================================================
Omega_mercado = np.diag(np.diag(tau * P_mat @ Sigma_mat @ P_mat.T)) * perfil["omega_scale"]
Var_prima = np.diag(se_prima_hm ** 2)
Omega_estimacion = np.diag(np.diag(P_mat @ Var_prima @ P_mat.T))
Omega_P = Omega_mercado + Omega_estimacion

print("\n=== Descomposicion de Omega (varianzas, no desviaciones) ===")
print(pd.DataFrame({
    "Riesgo_mercado": np.diag(Omega_mercado),
    "Riesgo_estimacion": np.diag(Omega_estimacion),
    "Omega_total": np.diag(Omega_P),
    "%_estimacion": np.round(100 * np.diag(Omega_estimacion) /
                             np.maximum(np.diag(Omega_P), 1e-18), 1),
}, index=Q.index).to_string())

# ==============================================================================
# NUCLEO GAUSSIANO DE BLACK-LITTERMAN
# ==============================================================================
Q_P_col = Q_P.reshape(-1, 1)
sorpresa = Q_P_col - P_mat @ pi_eq_col
M_bl = P_mat @ tauSigma @ P_mat.T + Omega_P
M_bl_inv = np.linalg.inv(M_bl)
mu_BL = (pi_eq_col + tauSigma @ P_mat.T @ M_bl_inv @ sorpresa).flatten()
Sigma_BL = Sigma_mat + tauSigma - tauSigma @ P_mat.T @ M_bl_inv @ P_mat @ tauSigma
Sigma_BL = pd.DataFrame(Sigma_BL, index=tickers, columns=tickers)

comparacion = pd.DataFrame({
    "Ticker": tickers,
    "Pi_eq": np.round(pi_eq, 4),
    "Mu_hist": np.round(mu_historico, 4),
    "Prima_HM": np.round(prima_hm, 4),
    "Mu_BL": np.round(mu_BL, 4),
})
comparacion["Ajuste_BL"] = np.round(comparacion["Mu_BL"] - comparacion["Pi_eq"], 4)

print("\n=== Posterior gaussiano: pi vs historico vs mu_BL ===")
print(comparacion.to_string(index=False))
print(f"\nNorma Frobenius |Sigma_BL - Sigma_P|: "
      f"{np.linalg.norm(Sigma_BL.values - Sigma_mat):.6f}")

# ==============================================================================
# BLOQUE 7: INTEGRACION BAYESIANA NO GAUSSIANA
# ==============================================================================

from scipy.special import logsumexp

print("\n" + "=" * 79)
print("BLOQUE 7: POSTERIOR NO GAUSSIANO")
print("=" * 79)

# ==============================================================================
# 7.1  PANEL DE ESCENARIOS PRIOR
# ==============================================================================
# Bootstrap estacionario, funcion del Bloque 1D.

print(f"\nGenerando panel de {N_ESCENARIOS} escenarios "
      f"(bootstrap estacionario, bloque medio {BOOTSTRAP_BLOQUE} dias, "
      f"half-life {HALF_LIFE_PRIOR} dias)...")

X_raw = bootstrap_estacionario(R_dia, N_ESCENARIOS, horizonte_dias,
                               BOOTSTRAP_BLOQUE, peso_tiempo, rng_global)

mu_raw = X_raw.mean(axis=0)
sd_raw = X_raw.std(axis=0, ddof=1)
sd_raw = np.where(sd_raw > 0, sd_raw, 1.0)
X_prior = (X_raw - mu_raw) / sd_raw * sigma_P_vec + pi_eq

f_prior = np.full(N_ESCENARIOS, 1.0 / N_ESCENARIOS)

print(f"  Panel listo: {X_prior.shape[0]} x {X_prior.shape[1]}")
print(f"  Asimetria media del prior:  {pd.DataFrame(X_prior).skew().mean():+.3f}")
print(f"  Curtosis media del prior:   {pd.DataFrame(X_prior).kurt().mean() + 3:.3f}")


# ==============================================================================
# 7.2  UTILIDADES DE MOMENTOS PONDERADOS
# ==============================================================================

def momentos_ponderados(X, p):
    """Media, covarianza, asimetria y curtosis estandarizadas por activo."""
    mu = p @ X
    Xc = X - mu
    Sig = (Xc * p[:, None]).T @ Xc
    sd = np.sqrt(np.maximum(np.diag(Sig), 1e-18))
    sk = (p @ (Xc ** 3)) / sd ** 3
    ku = (p @ (Xc ** 4)) / sd ** 4
    return mu, Sig, sk, ku


def momentos_portafolio(w, X, p):
    """Momentos centrales del retorno del portafolio bajo (X, p).

    Equivale a w'mu, w'Sigma w, w'M3(w x w) y w'M4(w x w x w) pero se calcula
    en O(J*n) en vez de construir tensores de co-momentos de tamano n^3 y n^4.
    """
    r = X @ w
    mu = float(p @ r)
    d = r - mu
    m2 = float(p @ d ** 2)
    m3 = float(p @ d ** 3)
    m4 = float(p @ d ** 4)
    return mu, m2, m3, m4


# ==============================================================================
# 7.3  OPCION A: ENTROPY POOLING
# ==============================================================================

def entropy_pooling(f, A, b, tol_residuo=1e-6, maxiter=800):
    """Posterior de minima entropia relativa sujeto a E_p[A] = b.

    Parametros
    ----------
    f : (J,)   probabilidades prior
    A : (K, J) matriz de features (una fila por restriccion de momento)
    b : (K,)   valores objetivo

    Devuelve (p, info). El problema dual es
        min_lambda  log sum_j f_j exp(-lambda' V_j),  V = (A - b) / escala
    convexo y sin restricciones; su gradiente es -E_p[V], de modo que el optimo
    satisface exactamente las restricciones cuando son factibles.
    """
    K, J = A.shape
    escala = A.std(axis=1, ddof=1)
    escala = np.where(escala > 1e-14, escala, 1.0)
    V = (A - b[:, None]) / escala[:, None]
    log_f = np.log(np.maximum(f, 1e-300))

    def dual(lam):
        z = log_f - lam @ V
        lse = logsumexp(z)
        p = np.exp(z - lse)
        return float(lse), -(V @ p)

    res = minimize(dual, np.zeros(K), jac=True, method="L-BFGS-B",
                   options=dict(maxiter=maxiter, ftol=1e-14, gtol=1e-10))

    lam = res.x
    z = log_f - lam @ V
    p = np.exp(z - logsumexp(z))
    p = np.maximum(p, 0.0)
    p = p / p.sum()

    residuo = np.abs(V @ p)
    kl = float(np.sum(p * (np.log(np.maximum(p, 1e-300)) - log_f)))
    ens = float(np.exp(-np.sum(p * np.log(np.maximum(p, 1e-300)))) / J)

    info = dict(exito=bool(res.success), kl=kl, ens=ens,
                residuo_max=float(residuo.max()),
                factible=bool(residuo.max() < max(tol_residuo, 1e-4)),
                lam=lam, mensaje=str(res.message))
    return p, info


def construir_restricciones(X, mu_obj, var_obj, skew_obj, kurt_obj, nivel):
    """Bloques de restricciones por nivel de momento.

    nivel = 2 -> media y varianza
    nivel = 3 -> + asimetria
    nivel = 4 -> + curtosis
    """
    filas, objetivos, etiquetas = [], [], []
    sd_obj = np.sqrt(var_obj)

    for i in range(X.shape[1]):
        filas.append(X[:, i]); objetivos.append(mu_obj[i]); etiquetas.append(f"mean_{i}")
    for i in range(X.shape[1]):
        filas.append((X[:, i] - mu_obj[i]) ** 2); objetivos.append(var_obj[i])
        etiquetas.append(f"var_{i}")
    if nivel >= 3:
        for i in range(X.shape[1]):
            filas.append((X[:, i] - mu_obj[i]) ** 3)
            objetivos.append(skew_obj[i] * sd_obj[i] ** 3)
            etiquetas.append(f"skew_{i}")
    if nivel >= 4:
        for i in range(X.shape[1]):
            filas.append((X[:, i] - mu_obj[i]) ** 4)
            objetivos.append(kurt_obj[i] * sd_obj[i] ** 4)
            etiquetas.append(f"kurt_{i}")

    return np.array(filas), np.array(objetivos), etiquetas


# ==============================================================================
# OBJETIVOS DE MOMENTO EXTRAIDOS DEL MODELO
# ==============================================================================
mu_obj = mu_BL.copy()
var_obj = np.diag(Sigma_BL.values).copy()
skew_obj = skew_P.copy()
kurt_obj = kurt_P.copy()


# ==============================================================================
# 7.4  OPCION B: INCLINACION DE GRAM-CHARLIER / EDGEWORTH
# ==============================================================================

def he3(z):
    return z ** 3 - 3 * z


def he4(z):
    return z ** 4 - 6 * z ** 2 + 3


def gram_charlier_pdf_ratio(z, s, k):
    """g(z)/phi(z) = 1 + (S/6) He_3(z) + ((K-3)/24) He_4(z).

    Serie tipo A truncada en el 4.o momento. Puede volverse negativa fuera de
    la region de validez de Barton-Dennis, por lo que se trunca por abajo.
    """
    return 1.0 + (s / 6.0) * he3(z) + ((k - 3.0) / 24.0) * he4(z)


def posterior_gram_charlier(X, f, mu_obj, var_obj, skew_obj, kurt_obj):
    """Reponderacion del panel por el factor de Gram-Charlier activo a activo.

    Es el analogo por muestreo de importancia de expandir la densidad posterior
    del vector de retornos en serie de Edgeworth alrededor de la normal
    N(mu_BL, Sigma_BL) sumando las contribuciones del 3.er y 4.o momento BKM.
    """
    Z = (X - mu_obj) / np.sqrt(var_obj)
    log_w = np.zeros(X.shape[0])
    for i in range(X.shape[1]):
        ratio = gram_charlier_pdf_ratio(Z[:, i], skew_obj[i], kurt_obj[i])
        log_w += np.log(np.maximum(ratio, 1e-6))
    log_p = np.log(np.maximum(f, 1e-300)) + log_w
    p = np.exp(log_p - logsumexp(log_p))
    p = p / p.sum()
    ens = float(np.exp(-np.sum(p * np.log(np.maximum(p, 1e-300)))) / len(p))
    kl = float(np.sum(p * (np.log(np.maximum(p, 1e-300)) - np.log(np.maximum(f, 1e-300)))))
    negativos = int(np.sum(gram_charlier_pdf_ratio(Z, skew_obj, kurt_obj) < 0))
    return p, dict(exito=True, kl=kl, ens=ens, residuo_max=np.nan,
                   factible=True, densidades_negativas=negativos,
                   mensaje="gram_charlier")


# ==============================================================================
# 7.5  RESOLUCION CON DEGRADACION CONTROLADA
# ==============================================================================

metodo_posterior_usado = None
info_post = None

if METODO_POSTERIOR == "entropy_pooling":
    niveles = [4, 3, 2] if EP_IMPONER_CURTOSIS else [3, 2]
    nombres_nivel = {4: "media+var+skew+kurt", 3: "media+var+skew", 2: "media+var"}

    for niv in niveles:
        A_ep, b_ep, _ = construir_restricciones(
            X_prior, mu_obj, var_obj, skew_obj, kurt_obj, niv)
        print(f"\n  Entropy Pooling nivel {niv} ({nombres_nivel[niv]}): "
              f"{A_ep.shape[0]} restricciones sobre {N_ESCENARIOS} escenarios...")
        p_post, info = entropy_pooling(f_prior, A_ep, b_ep)
        print(f"    exito={info['exito']} | residuo_max={info['residuo_max']:.2e} | "
              f"KL={info['kl']:.4f} | ENS={info['ens'] * 100:.1f}% de J")
        if info["factible"] and info["ens"] >= EP_TOL_ENS:
            metodo_posterior_usado = f"entropy_pooling_n{niv}"
            info_post = info
            break
        print("    -> rechazado (infactible o ENS demasiado bajo); se relaja un nivel")

    if metodo_posterior_usado is None:
        print("\n  Entropy Pooling no alcanzo una solucion aceptable. "
              "Se recurre a la expansion de Gram-Charlier (Opcion B).")
        p_post, info_post = posterior_gram_charlier(
            X_prior, f_prior, mu_obj, var_obj, skew_obj, kurt_obj)
        metodo_posterior_usado = "gram_charlier_fallback"
else:
    p_post, info_post = posterior_gram_charlier(
        X_prior, f_prior, mu_obj, var_obj, skew_obj, kurt_obj)
    metodo_posterior_usado = "gram_charlier"
    print(f"\n  Gram-Charlier: KL={info_post['kl']:.4f} | "
          f"ENS={info_post['ens'] * 100:.1f}% de J | "
          f"celdas con densidad negativa truncadas: "
          f"{info_post.get('densidades_negativas', 0)}")

# ==============================================================================
# 7.6  MOMENTOS DEL POSTERIOR NO GAUSSIANO
# ==============================================================================

mu_post, Sigma_post_arr, skew_post, kurt_post = momentos_ponderados(X_prior, p_post)
Sigma_post = pd.DataFrame(Sigma_post_arr, index=tickers, columns=tickers)

print(f"\n=== Posterior obtenido por: {metodo_posterior_usado} ===")
print(f"  Entropia relativa D(p||f): {info_post['kl']:.4f} nats")
print(f"  Numero efectivo de escenarios: {info_post['ens'] * 100:.1f}% de {N_ESCENARIOS}")

tabla_post = pd.DataFrame({
    "mu_BL_obj": np.round(mu_obj, 4),
    "mu_post": np.round(mu_post, 4),
    "sd_obj": np.round(np.sqrt(var_obj), 4),
    "sd_post": np.round(np.sqrt(np.diag(Sigma_post_arr)), 4),
    "skew_obj": np.round(skew_obj, 3),
    "skew_post": np.round(skew_post, 3),
    "kurt_obj": np.round(kurt_obj, 3),
    "kurt_post": np.round(kurt_post, 3),
}, index=tickers)

print("\n=== Ajuste del posterior a los momentos objetivo ===")
print(tabla_post.to_string())

# ==============================================================================
# BLOQUE 7B: MODULO DE RIESGO DE COLA (VaR, CVaR / EXPECTED SHORTFALL)
# ==============================================================================

def _pesos_normalizados(m, probabilidades):
    if probabilidades is None:
        return np.full(m, 1.0 / m)
    p = np.asarray(probabilidades, dtype=float)
    return p / p.sum()


def var_cvar_historico(perdidas, p, alpha):
    """VaR y CVaR exactos de una distribucion discreta ponderada de perdidas.

    ES_alpha = 1/(1-alpha) * [ sum_{L>q} p_i L_i + (1-alpha - sum_{L>q} p_i) q ]
    (formula exacta que reparte correctamente la masa del propio cuantil).
    """
    orden = np.argsort(perdidas)
    L = perdidas[orden]
    w = p[orden]
    acum = np.cumsum(w)
    idx = int(np.searchsorted(acum, alpha, side="left"))
    idx = min(idx, len(L) - 1)
    var = float(L[idx])

    cola = L > var
    masa_cola = float(w[cola].sum())
    suma_cola = float(np.sum(w[cola] * L[cola]))
    resto = max(1.0 - alpha - masa_cola, 0.0)
    cvar = (suma_cola + resto * var) / (1.0 - alpha)
    return var, float(cvar)


def var_cvar_cornish_fisher(mu, sigma, s, k, alpha):
    """VaR y CVaR (como perdidas) bajo la distribucion de Cornish-Fisher.

    s y k son la asimetria y la curtosis REALES del portafolio. No se enchufan
    como parametros de la expansion (eso invierte el orden del cuantil con
    colas pesadas): rk.cornish_fisher_tail busca los parametros que reproducen
    esos momentos (Maillard, 2012) y da el cuantil y el ES en forma cerrada.
    """
    cola = rk.cornish_fisher_tail(1.0 - alpha, s, k - 3.0)
    return float(-(mu + sigma * cola["q"])), float(-(mu + sigma * cola["es"]))


def calcular_metricas_riesgo_cola(w, retornos_df, nivel_confianza=0.95,
                                  probabilidades=None, rf_periodo=0.0,
                                  umbral_omega=None, etiqueta=""):
    """Metricas de riesgo de cola de un portafolio.

    Parametros
    ----------
    w : array (n,) o pd.Series
        Pesos del portafolio.
    retornos_df : pd.DataFrame (m x n) o np.ndarray
        Panel de retornos por activo al horizonte de analisis. Puede ser la
        serie historica realizada o el panel de escenarios del posterior.
    nivel_confianza : float
        Nivel del VaR principal (por defecto 0.95).
    probabilidades : array (m,), opcional
        Probabilidades de cada fila. None => equiponderadas. Permite evaluar
        directamente el posterior de Entropy Pooling.
    rf_periodo : float
        Tasa libre de riesgo del periodo; sirve de MAR para el Sortino.
    umbral_omega : float, opcional
        Umbral tau del Omega ratio. None => UMBRAL_OMEGA_RATIO.

    Devuelve
    --------
    pd.Series con VaR historico y Cornish-Fisher, CVaR historico y CF a los
    niveles de NIVELES_CVAR, Sortino, Omega y estadisticos de apoyo.

        Sortino = (E[r] - MAR) / sqrt(E[min(r - MAR, 0)^2])
        Omega   = E[(r - tau)+] / E[(tau - r)+]
    """
    if isinstance(w, pd.Series):
        w_arr = w.values.astype(float)
    else:
        w_arr = np.asarray(w, dtype=float)

    X = retornos_df.values if isinstance(retornos_df, pd.DataFrame) else np.asarray(retornos_df)
    if X.shape[1] != len(w_arr):
        raise ValueError(f"Dimension incompatible: X tiene {X.shape[1]} activos "
                         f"y w tiene {len(w_arr)}")

    p = _pesos_normalizados(X.shape[0], probabilidades)
    r = X @ w_arr

    mu = float(p @ r)
    d = r - mu
    m2 = float(p @ d ** 2)
    sigma = math.sqrt(max(m2, 1e-18))
    s_std = float(p @ d ** 3) / sigma ** 3
    k_std = float(p @ d ** 4) / sigma ** 4

    perdidas = -r
    tau_omega = UMBRAL_OMEGA_RATIO if umbral_omega is None else umbral_omega

    out = {"Retorno_esperado": mu, "Volatilidad": sigma,
           "Skewness": s_std, "Kurtosis": k_std}

    out["CF_exacta"] = float(rk.cornish_fisher_params(s_std, k_std - 3.0)[2])

    var_h, cvar_h = var_cvar_historico(perdidas, p, nivel_confianza)
    var_cf, cvar_cf = var_cvar_cornish_fisher(mu, sigma, s_std, k_std, nivel_confianza)
    var_gauss = -(mu + sigma * norm.ppf(1.0 - nivel_confianza))
    nc = int(round(nivel_confianza * 100))
    out[f"VaR{nc}_historico"] = var_h
    out[f"VaR{nc}_gaussiano"] = var_gauss
    out[f"VaR{nc}_CornishFisher"] = var_cf

    for a in NIVELES_CVAR:
        v_h, c_h = var_cvar_historico(perdidas, p, a)
        _, c_cf = var_cvar_cornish_fisher(mu, sigma, s_std, k_std, a)
        na = int(round(a * 100))
        out[f"CVaR{na}_historico"] = c_h
        out[f"CVaR{na}_CornishFisher"] = c_cf

    exceso_mar = r - rf_periodo
    downside = np.sqrt(float(p @ np.minimum(exceso_mar, 0.0) ** 2))
    out["Sortino"] = float((mu - rf_periodo) / downside) if downside > 1e-12 else np.nan

    ganancia = float(p @ np.maximum(r - tau_omega, 0.0))
    perdida = float(p @ np.maximum(tau_omega - r, 0.0))
    out["Omega"] = float(ganancia / perdida) if perdida > 1e-12 else np.inf

    out["Sharpe"] = float((mu - rf_periodo) / sigma) if sigma > 1e-12 else np.nan
    out["Prob_perdida"] = float(p[r < 0].sum())
    out["Peor_escenario"] = float(r.min())

    return pd.Series(out, name=etiqueta if etiqueta else None)

# ==============================================================================
# BLOQUE 8B: OPTIMIZACION - MODO MVSK O MODO CVaR
# ==============================================================================

print("\n" + "=" * 79)
print(f"BLOQUE 8B: OPTIMIZACION (modo = {MODO_OPTIMIZACION.upper()})")
print("=" * 79)

mu_opt = mu_post.copy()

def utilidad_mvsk_negativa(w, X, p, gamma, lam3, lam4):
    """-U(w) con U = E[r] - (g/2)m2 + (l3/3)m3 - (l4/4)m4."""
    mu_w, m2, m3, m4 = momentos_portafolio(w, X, p)
    return -(mu_w - (gamma / 2.0) * m2 + (lam3 / 3.0) * m3 - (lam4 / 4.0) * m4)


def optimizar_mvsk(X, p, gamma, lam3, lam4, activos_permitidos=None, w_ini=None):
    n_ = X.shape[1]
    if activos_permitidos is None:
        activos_permitidos = np.ones(n_, dtype=bool)
    bounds = [(0.0, PESO_MAX_ACTIVO) if activos_permitidos[i] else (0.0, 0.0)
              for i in range(n_)]
    if w_ini is None:
        w_ini = activos_permitidos.astype(float)
        w_ini = w_ini / w_ini.sum()
    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    res = minimize(utilidad_mvsk_negativa, w_ini, args=(X, p, gamma, lam3, lam4),
                   method="SLSQP", bounds=bounds, constraints=cons,
                   options=dict(maxiter=600, ftol=1e-11))
    if not res.success:
        print(f"  Aviso SLSQP: {res.message}")
    return bm.clip_negligible_weights(res.x), res


def optimizar_min_cvar(X, p, alpha, retorno_min, mu_vec,
                       activos_permitidos=None, max_escenarios=MAX_ESCENARIOS_LP,
                       rng=None):
    """LP de Rockafellar-Uryasev. Devuelve (w, info).

        min_{w, zeta, u}   zeta + 1/((1-alpha) M) sum_j u_j
        s.a.  u_j >= -x_j'w - zeta,  u_j >= 0
              mu'w >= retorno_min,  sum w = 1,  0 <= w <= w_max

    El optimo en zeta es el propio VaR_alpha y el valor objetivo es el CVaR.
    Al ser un programa lineal el optimo es global, sin la convergencia local
    de SLSQP.

    El panel se remuestrea por importancia con probabilidades p para que el LP
    trabaje con escenarios equiponderados de tamano manejable sin sesgar la
    distribucion posterior.
    """
    rng = rng_global if rng is None else rng
    J_, n_ = X.shape
    if activos_permitidos is None:
        activos_permitidos = np.ones(n_, dtype=bool)

    if J_ > max_escenarios:
        idx = rng.choice(J_, size=max_escenarios, replace=True, p=p)
        Xs = X[idx]
    else:
        idx = rng.choice(J_, size=J_, replace=True, p=p)
        Xs = X[idx]
    M = Xs.shape[0]

    c = np.concatenate([np.zeros(n_), [1.0], np.full(M, 1.0 / ((1.0 - alpha) * M))])

    A1 = sparse.hstack([
        sparse.csr_matrix(-Xs),
        sparse.csr_matrix(-np.ones((M, 1))),
        -sparse.identity(M, format="csr"),
    ], format="csr")
    b1 = np.zeros(M)

    A2 = sparse.csr_matrix(
        np.concatenate([-mu_vec, [0.0], np.zeros(M)]).reshape(1, -1))
    b2 = np.array([-retorno_min])

    A_ub = sparse.vstack([A1, A2], format="csr")
    b_ub = np.concatenate([b1, b2])

    A_eq = sparse.csr_matrix(
        np.concatenate([np.ones(n_), [0.0], np.zeros(M)]).reshape(1, -1))
    b_eq = np.array([1.0])

    bounds = ([(0.0, PESO_MAX_ACTIVO) if activos_permitidos[i] else (0.0, 0.0)
               for i in range(n_)]
              + [(None, None)]
              + [(0.0, None)] * M)

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")

    if not res.success:
        return None, dict(exito=False, mensaje=res.message)

    w = np.clip(res.x[:n_], 0.0, None)
    w = w / w.sum()
    return w, dict(exito=True, cvar=float(res.fun), var=float(res.x[n_]),
                   mensaje=res.message, n_escenarios=M)


def aplicar_limites_cartera(w, umbral=UMBRAL_PESO_MIN, max_activos=MAX_TICKERS_FINAL):
    """Umbral de peso minimo + cardinalidad maxima. Devuelve la mascara final."""
    mask = w >= umbral
    if mask.sum() == 0:
        mask = np.zeros_like(w, dtype=bool)
        mask[int(np.argmax(w))] = True
    if mask.sum() > max_activos:
        idx_top = np.argsort(np.where(mask, w, -np.inf))[::-1][:max_activos]
        mask = np.zeros_like(w, dtype=bool)
        mask[idx_top] = True
    return mask


def _retorno_min_factible(retorno_deseado, mu_vec, activos_permitidos=None, etiqueta=""):
    """Recorta el retorno objetivo del LP de CVaR al maximo alcanzable dentro
    del conjunto de activos permitidos (mu_max = max(mu_vec) sobre el
    soporte). Un retorno_min por encima de ese maximo vuelve el LP infactible
    solo por la restriccion de retorno, sin que eso refleje ningun problema
    real de riesgo: se ajusta dinamicamente en vez de fallar."""
    mu_disp = mu_vec if activos_permitidos is None else mu_vec[activos_permitidos]
    r_max = float(np.max(mu_disp))
    if retorno_deseado > r_max:
        print(f"  Aviso: retorno objetivo ({retorno_deseado:.4f}) supera el maximo "
              f"retorno alcanzable{etiqueta} ({r_max:.4f}); se ajusta al maximo.")
        return r_max
    return retorno_deseado


# ==============================================================================
# RETORNO MINIMO EXIGIDO EN MODO CVaR
# ==============================================================================
retorno_min_deseado = (float(w_mkt @ mu_opt) if RETORNO_MIN_CVAR is None
                       else float(RETORNO_MIN_CVAR))
retorno_min_efectivo = _retorno_min_factible(retorno_min_deseado, mu_opt,
                                             etiqueta=" en el universo completo")

# ==============================================================================
# PRIMERA PASADA
# ==============================================================================
if MODO_OPTIMIZACION == "cvar":
    print(f"\n  Minimizando CVaR_{ALPHA_CVAR_OBJETIVO:.0%} con "
          f"E[r] >= {retorno_min_efectivo:.4f} "
          f"({'benchmark de mercado' if RETORNO_MIN_CVAR is None else 'fijado por el usuario'})")
    w_bruto, info_opt = optimizar_min_cvar(
        X_prior, p_post, ALPHA_CVAR_OBJETIVO, retorno_min_efectivo, mu_opt)
    if w_bruto is None:
        print(f"  LP infactible ({info_opt['mensaje']}). Se recurre al modo MVSK.")
        w_bruto, info_opt = optimizar_mvsk(X_prior, p_post, gamma_ra, LAMBDA3, LAMBDA4)
        modo_efectivo = "mvsk (fallback)"
    else:
        print(f"  LP resuelto sobre {info_opt['n_escenarios']} escenarios | "
              f"VaR={info_opt['var']:.4f} | CVaR={info_opt['cvar']:.4f}")
        modo_efectivo = "cvar"
else:
    print(f"\n  Maximizando utilidad MVSK | gamma={gamma_ra} | "
          f"lambda3={LAMBDA3} | lambda4={LAMBDA4}")
    w_bruto, info_opt = optimizar_mvsk(X_prior, p_post, gamma_ra, LAMBDA3, LAMBDA4)
    modo_efectivo = "mvsk"

# ==============================================================================
# SEGUNDA PASADA: RE-OPTIMIZACION SOBRE EL SOPORTE FINAL
# ==============================================================================
mask_final = aplicar_limites_cartera(w_bruto)
print(f"  Soporte final: {int(mask_final.sum())} activos "
      f"(umbral {UMBRAL_PESO_MIN:.1%}, maximo {MAX_TICKERS_FINAL})")

if modo_efectivo == "cvar":
    retorno_min_soporte = _retorno_min_factible(
        retorno_min_efectivo, mu_opt, activos_permitidos=mask_final,
        etiqueta=" en el soporte reducido")
    w_re, info_re = optimizar_min_cvar(X_prior, p_post, ALPHA_CVAR_OBJETIVO,
                                       retorno_min_soporte, mu_opt,
                                       activos_permitidos=mask_final)
    if w_re is None:
        print(f"  Re-optimizacion CVaR infactible en el soporte reducido "
              f"({info_re['mensaje']}); se usa el bruto truncado y renormalizado.")
    w_opt = w_re if w_re is not None else (w_bruto * mask_final) / (w_bruto * mask_final).sum()
else:
    w_ini = np.where(mask_final, w_bruto, 0.0)
    w_ini = w_ini / w_ini.sum()
    w_opt, _ = optimizar_mvsk(X_prior, p_post, gamma_ra, LAMBDA3, LAMBDA4,
                              activos_permitidos=mask_final, w_ini=w_ini)

w_opt = np.where(w_opt < 1e-10, 0.0, w_opt)
w_opt = w_opt / w_opt.sum()
w_mvsk = pd.Series(w_opt, index=tickers)

print(f"\n=== Pesos optimos - Portafolio BL+BKM ({modo_efectivo.upper()}) ===")
print(w_mvsk[w_mvsk > 0].sort_values(ascending=False).round(4).to_string())

_regiones_bl = {}
for _tk in tickers:
    _reg = md.region_de_ticker(_tk)
    if _reg == "US" and not pc.is_us_ticker(_tk):
        _reg = "Otras bolsas"
    _regiones_bl.setdefault(_reg, []).append(_tk)
for _region in ("US", "Canada", "Europa", "Japon", "Otras bolsas"):
    _idx = _regiones_bl.get(_region, [])
    if _idx:
        print(f"  Peso {_region}: {w_mvsk.loc[_idx].sum() * 100:.1f}% "
              f"({len(_idx)} en la optimizacion)")

_intl_en_opt = [a for a in tickers if not pc.is_us_ticker(a)]
_intl_con_peso = [a for a in _intl_en_opt if w_mvsk[a] > 1e-4]
if _intl_universo:
    print(f"  Internacionales en el universo: {len(_intl_universo)} | "
          f"en la optimizacion: {len(_intl_en_opt)} | con peso > 0: {len(_intl_con_peso)}")
    if _intl_con_peso:
        print("  " + ", ".join(f"{a} {w_mvsk[a] * 100:.1f}%" for a in _intl_con_peso))
    else:
        print("  Ningun internacional tiene peso. No hay piso de asignacion internacional.")

# ==============================================================================
# BLOQUE 8C: PORTAFOLIO MARKOWITZ TRADICIONAL
# ==============================================================================
# Portafolio de control.

print("\n" + "=" * 79)
print("BLOQUE 8C: PORTAFOLIO MARKOWITZ TRADICIONAL (CONTROL)")
print("=" * 79)


def markowitz_clasico(mu_vec, Sigma_arr, gamma, w_max=PESO_MAX_ACTIVO):
    """QP de media-varianza long-only con el MISMO tope por activo que el
    optimizador del Bloque 8B, para que la comparacion sea justa.

        max_w  mu'w - (gamma/2) w'Sigma w   s.a.  sum w = 1,  0 <= w <= w_max

    quadprog resuelve el QP con restricciones de desigualdad; si falla (matriz
    no definida positiva, por ejemplo) se recurre a SLSQP.
    """
    n_ = len(mu_vec)
    w_max = min(max(w_max, 1.0 / n_), 1.0)
    try:
        G = gamma * (Sigma_arr + Sigma_arr.T) / 2.0 + np.eye(n_) * 1e-8
        Amat = np.column_stack([np.ones(n_), np.eye(n_), -np.eye(n_)])
        bvec = np.concatenate([[1.0], np.zeros(n_), np.full(n_, -w_max)])
        w = quadprog.solve_qp(G, mu_vec, Amat, bvec, meq=1)[0]
        return bm.clip_negligible_weights(w)
    except Exception as e:
        print(f"  quadprog fallo ({e}); se usa SLSQP")
        obj = lambda w: -(w @ mu_vec - (gamma / 2.0) * w @ Sigma_arr @ w)
        cons = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]
        res = minimize(obj, np.full(n_, 1.0 / n_), method="SLSQP",
                       bounds=[(0.0, w_max)] * n_, constraints=cons)
        return bm.clip_negligible_weights(res.x)


w_mkw_bruto = markowitz_clasico(mu_historico, Sigma_hist, gamma_ra)
mask_mkw = aplicar_limites_cartera(w_mkw_bruto)

idx_mkw = np.where(mask_mkw)[0]
w_sub = markowitz_clasico(mu_historico[idx_mkw],
                          Sigma_hist[np.ix_(idx_mkw, idx_mkw)], gamma_ra)
w_mkw = np.zeros(n)
w_mkw[idx_mkw] = w_sub
w_markowitz = pd.Series(w_mkw, index=tickers)

print("\n=== Pesos - Markowitz tradicional (mu_hist, Sigma_hist) ===")
print(w_markowitz[w_markowitz > 0].sort_values(ascending=False).round(4).to_string())

# ==============================================================================
# BLOQUE 9: METRICAS COMPARATIVAS DE RIESGO DE COLA
# ==============================================================================

etiqueta_horizonte = f"{MESES_HORIZONTE} mes(es)"

print("\n" + "=" * 79)
print(f"BLOQUE 9: METRICAS DE RIESGO DE COLA ({etiqueta_horizonte})")
print("=" * 79)

# ==============================================================================
# PANEL HISTORICO DE RETORNOS AL HORIZONTE
# ==============================================================================
# Ventanas solapadas.
ret_hist_horizonte = (retornos_dia[tickers]
                      .rolling(horizonte_dias)
                      .sum()
                      .dropna())
print(f"\nPanel historico: {len(ret_hist_horizonte)} ventanas solapadas de "
      f"{horizonte_dias} dias | Panel posterior: {N_ESCENARIOS} escenarios")
_n_indep = max(1, int(np.floor(len(retornos_dia) / max(horizonte_dias, 1))))
print(f"  NOTA (B-10): las ventanas se solapan. Observaciones aproximadamente "
      f"independientes en 2 anos: ~{_n_indep}, no el conteo de ventanas. "
      "Se dejan solapadas a proposito.")

portafolios = {
    "Mercado (w_mkt)": pd.Series(w_mkt, index=tickers),
    "Markowitz (control)": w_markowitz,
    f"BL+BKM {modo_efectivo.upper()}": w_mvsk,
}

# ==============================================================================
# (1) BAJO EL POSTERIOR DEL MODELO
# ==============================================================================
metricas_post = pd.DataFrame({
    nombre: calcular_metricas_riesgo_cola(
        w, X_prior, nivel_confianza=NIVEL_CONFIANZA_VAR,
        probabilidades=p_post, rf_periodo=Rf_h, etiqueta=nombre)
    for nombre, w in portafolios.items()
})

# ==============================================================================
# (2) BAJO LOS RETORNOS HISTORICOS REALIZADOS
# ==============================================================================
metricas_hist = pd.DataFrame({
    nombre: calcular_metricas_riesgo_cola(
        w, ret_hist_horizonte, nivel_confianza=NIVEL_CONFIANZA_VAR,
        rf_periodo=Rf_h, etiqueta=nombre)
    for nombre, w in portafolios.items()
})

nc = int(round(NIVEL_CONFIANZA_VAR * 100))
orden_filas = [
    "Retorno_esperado", "Volatilidad", "Skewness", "Kurtosis", "CF_exacta",
    f"VaR{nc}_historico", f"VaR{nc}_gaussiano", f"VaR{nc}_CornishFisher",
] + [f"CVaR{int(round(a * 100))}_historico" for a in NIVELES_CVAR] \
  + [f"CVaR{int(round(a * 100))}_CornishFisher" for a in NIVELES_CVAR] \
  + ["Sharpe", "Sortino", "Omega", "Prob_perdida", "Peor_escenario"]

print(f"\n--- (1) Bajo el POSTERIOR del modelo ({metodo_posterior_usado}) ---")
print(metricas_post.loc[orden_filas].round(4).to_string())

print("\n--- (2) Bajo los RETORNOS HISTORICOS realizados (validacion) ---")
print(metricas_hist.loc[orden_filas].round(4).to_string())

# ==============================================================================
# LECTURA DEL EFECTO DE LOS MOMENTOS SUPERIORES
# ==============================================================================
print("\n--- Efecto de los momentos de orden superior sobre el VaR ---")
print("(VaR_CF - VaR_gaussiano > 0 => la normalidad SUBESTIMA la perdida)")
brecha = (metricas_post.loc[f"VaR{nc}_CornishFisher"]
          - metricas_post.loc[f"VaR{nc}_gaussiano"])
print(pd.DataFrame({
    f"VaR{nc}_gauss": metricas_post.loc[f"VaR{nc}_gaussiano"].round(4),
    f"VaR{nc}_CF": metricas_post.loc[f"VaR{nc}_CornishFisher"].round(4),
    "Brecha": brecha.round(4),
    "Brecha_%": (100 * brecha / metricas_post.loc[f"VaR{nc}_gaussiano"]).round(1),
}).to_string())

# ==============================================================================
# VARIABLES DE COMPATIBILIDAD PARA LOS BLOQUES SIGUIENTES
# ==============================================================================
w_mvsk_vec = w_mvsk.values
mu_BL_vec = mu_post.copy()
ret_port, m2_port, m3_port, m4_port = momentos_portafolio(w_mvsk_vec, X_prior, p_post)
vol_port = math.sqrt(max(m2_port, 1e-18))
sharpe_BL = float(metricas_post.loc["Sharpe", f"BL+BKM {modo_efectivo.upper()}"])
sharpe_mkt = float(metricas_post.loc["Sharpe", "Mercado (w_mkt)"])
sharpe_mkw = float(metricas_post.loc["Sharpe", "Markowitz (control)"])

print(f"\n=== Resumen del portafolio BL+BKM ({modo_efectivo.upper()}) ===")
print(f"  Retorno esperado:  {ret_port:.4f}")
print(f"  Volatilidad:       {vol_port:.4f}")
print(f"  Skewness (m3):     {m3_port:.6f}")
print(f"  Kurtosis (m4):     {m4_port:.6f}")
print(f"  Sharpe:            {sharpe_BL:.4f}   (mercado: {sharpe_mkt:.4f} | "
      f"Markowitz: {sharpe_mkw:.4f})")
print(f"  Rf al horizonte:   {Rf_h:.4f}")

# ==============================================================================
# BLOQUE 10: VISUALIZACION
# ==============================================================================

comp_sorted = comparacion.sort_values("Ajuste_BL")
colores_ajuste = ["#70AD47" if v > 0 else "#ED7D31" for v in comp_sorted["Ajuste_BL"]]
nombres_port = list(portafolios.keys())
colores_port = ["#4472C4", "#FFC000", "#70AD47"]

fig = make_subplots(
    rows=3, cols=2,
    subplot_titles=(
        f"Retornos esperados - {etiqueta_horizonte}",
        "Pesos: Mercado vs Markowitz vs BL+BKM",
        f"VaR{nc} y CVaR: gaussiano vs Cornish-Fisher",
        "Ratios ajustados por riesgo de cola",
        "Primas de riesgo de momentos (Q - P)",
        "Ajuste mu_BL vs pi (views + prima no gaussiana)",
    ),
    vertical_spacing=0.10,
)

fig.add_trace(go.Bar(x=comparacion["Ticker"], y=comparacion["Pi_eq"], name="pi (equilibrio)",
                     marker_color="#4472C4"), row=1, col=1)
fig.add_trace(go.Bar(x=comparacion["Ticker"], y=comparacion["Mu_hist"], name="Historico",
                     marker_color="#FFC000"), row=1, col=1)
fig.add_trace(go.Bar(x=tickers, y=mu_post, name="mu posterior (no gaussiano)",
                     marker_color="#ED7D31"), row=1, col=1)

for nombre, color in zip(nombres_port, colores_port):
    fig.add_trace(go.Bar(x=tickers, y=portafolios[nombre].values, name=nombre,
                         marker_color=color, showlegend=True), row=1, col=2)

filas_riesgo = [f"VaR{nc}_gaussiano", f"VaR{nc}_CornishFisher",
                f"CVaR{int(round(NIVELES_CVAR[0] * 100))}_historico",
                f"CVaR{int(round(NIVELES_CVAR[-1] * 100))}_historico"]
etq_riesgo = [f"VaR{nc} gauss", f"VaR{nc} CF",
              f"CVaR{int(round(NIVELES_CVAR[0] * 100))}",
              f"CVaR{int(round(NIVELES_CVAR[-1] * 100))}"]
for nombre, color in zip(nombres_port, colores_port):
    fig.add_trace(go.Bar(x=etq_riesgo, y=[metricas_post.loc[f, nombre] for f in filas_riesgo],
                         name=nombre, marker_color=color, showlegend=False), row=2, col=1)

for nombre, color in zip(nombres_port, colores_port):
    fig.add_trace(go.Bar(x=["Sharpe", "Sortino", "Omega"],
                         y=[metricas_post.loc["Sharpe", nombre],
                            metricas_post.loc["Sortino", nombre],
                            metricas_post.loc["Omega", nombre]],
                         name=nombre, marker_color=color, showlegend=False), row=2, col=2)

fig.add_trace(go.Bar(x=tickers, y=VRP, name="VRP", marker_color="#4472C4",
                     showlegend=False), row=3, col=1)
fig.add_trace(go.Bar(x=tickers, y=SRP, name="SRP", marker_color="#ED7D31",
                     showlegend=False), row=3, col=1)
fig.add_trace(go.Bar(x=tickers, y=KRP / 10.0, name="KRP/10", marker_color="#A5A5A5",
                     showlegend=False), row=3, col=1)

fig.add_trace(go.Bar(x=comp_sorted["Ticker"], y=comp_sorted["Ajuste_BL"],
                     marker_color=colores_ajuste, showlegend=False,
                     name="Ajuste BL"), row=3, col=2)
fig.add_hline(y=0, line_color="black", row=3, col=2)

for r, c in [(1, 1), (1, 2), (3, 1), (3, 2)]:
    fig.update_xaxes(tickangle=90, row=r, col=c)
fig.update_yaxes(title_text="Retorno esperado", row=1, col=1)
fig.update_yaxes(title_text="Peso", row=1, col=2)
fig.update_yaxes(title_text="Perdida", row=2, col=1)
fig.update_yaxes(title_text="Ratio", row=2, col=2)
fig.update_yaxes(title_text="Prima (Q - P)", row=3, col=1)
fig.update_yaxes(title_text="mu_post - pi", row=3, col=2)

fig.update_layout(
    title=(f"Black-Litterman + BKM extendido - {etiqueta_horizonte}<br>"
           f"<sup>Perfil: {PERFIL_RIESGO.upper()} | Posterior: {metodo_posterior_usado} | "
           f"Optimizacion: {modo_efectivo.upper()}</sup>"),
    barmode="group",
    template="plotly_white",
    height=1250,
    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
)
fig.show()

# ==============================================================================
# DISTRIBUCION POSTERIOR DEL PORTAFOLIO vs NORMAL
# ==============================================================================
r_port_esc = X_prior @ w_mvsk_vec
orden_esc = np.argsort(r_port_esc)
r_ord = r_port_esc[orden_esc]
p_ord = p_post[orden_esc]

fig2 = go.Figure()
fig2.add_trace(go.Histogram(x=r_port_esc, histnorm="probability density",
                            nbinsx=90, name="Posterior (no gaussiano)",
                            marker_color="#4472C4", opacity=0.55))
grid = np.linspace(r_ord.min(), r_ord.max(), 400)
fig2.add_trace(go.Scatter(x=grid,
                          y=norm.pdf(grid, ret_port, vol_port),
                          mode="lines", name="Normal(mu, sigma) equivalente",
                          line=dict(color="#ED7D31", width=2)))
var_cf_port = metricas_post.loc[f"VaR{nc}_CornishFisher", f"BL+BKM {modo_efectivo.upper()}"]
cvar_port = metricas_post.loc[f"CVaR{nc}_historico", f"BL+BKM {modo_efectivo.upper()}"]
fig2.add_vline(x=-var_cf_port, line_dash="dash", line_color="darkorange",
               annotation_text=f"VaR{nc} CF: {var_cf_port * 100:.2f}%",
               annotation_position="top left")
fig2.add_vline(x=-cvar_port, line_dash="dash", line_color="darkred",
               annotation_text=f"CVaR{nc}: {cvar_port * 100:.2f}%",
               annotation_position="bottom left")
fig2.update_layout(
    title=("Distribucion posterior del retorno del portafolio BL+BKM<br>"
           f"<sup>Asimetria: {metricas_post.loc['Skewness', f'BL+BKM {modo_efectivo.upper()}']:.3f} | "
           f"Curtosis: {metricas_post.loc['Kurtosis', f'BL+BKM {modo_efectivo.upper()}']:.3f} | "
           f"Horizonte: {etiqueta_horizonte}</sup>"),
    xaxis_title=f"Retorno a {etiqueta_horizonte}", yaxis_title="Densidad",
    template="plotly_white", height=520,
)
fig2.show()

# ==============================================================================
# BLOQUE 11: MAXIMUM DRAWDOWN (MDD) DEL PORTAFOLIO OPTIMIZADO
# ==============================================================================

print("\n=== ANALISIS DE MAXIMUM DRAWDOWN DEL PORTAFOLIO ===")
print(f"Periodo de analisis MDD: desde {MDD_START_YEAR}")


def calc_mdd(r):
    """MDD de log-retornos: riqueza = exp(cumsum) (B-1)."""
    return bm.mdd_from_log_returns(r)


tickers_bl = w_mvsk[w_mvsk > 0].index.tolist()
weights_bl = w_mvsk[tickers_bl]

fecha_mdd_inicio = date(MDD_START_YEAR, 1, 1)

series_ok = {}
for tk in tickers_bl:
    serie = descargar_precio(tk, fecha_mdd_inicio, date.today(), fx_prices=fx_prices_diarios)
    # BRK.B <-> BRK-B solo en EE. UU.: en un internacional el punto es la bolsa.
    if (serie is None or len(serie) == 0) and pc.is_us_ticker(tk):
        alt = tk.replace(".", "-") if "." in tk else tk.replace("-", ".")
        serie = descargar_precio(alt, fecha_mdd_inicio, date.today(), fx_prices=fx_prices_diarios)
        if serie is not None and len(serie) > 0:
            print(f"  Nota: {tk} recuperado como {alt}")
    if serie is None or len(serie) == 0:
        print(f"  Aviso: no se pudo obtener precio de {tk} para MDD - se excluye de este analisis")
        continue
    series_ok[tk] = serie

if len(series_ok) == 0:
    precios_mdd = None
    print("  Error preparando precios para MDD: ningun ticker del portafolio tiene precios disponibles")
else:
    precios_mdd = pd.DataFrame(series_ok)
    tickers_bl = [t for t in tickers_bl if t in precios_mdd.columns]
    weights_bl = w_mvsk[tickers_bl]
    weights_bl = weights_bl / weights_bl.sum()

if precios_mdd is not None and len(precios_mdd) >= 10:

    retornos_diarios_mdd = np.log(precios_mdd / precios_mdd.shift(1)).dropna(how="all")

    def port_ret_row(fila):
        # Log exacto del portafolio. La suma de logs solo coincide a primer orden.
        return bm.log_portfolio_return(fila, weights_bl)

    retornos_diarios_mdd = retornos_diarios_mdd[tickers_bl]
    port_ret = retornos_diarios_mdd.apply(port_ret_row, axis=1)
    port_ret = port_ret[port_ret.notna() & np.isfinite(port_ret)]

    print(f"  Observaciones diarias validas: {len(port_ret)}")
    print(f"  Cobertura: {port_ret.index.min():%Y-%m-%d} a {port_ret.index.max():%Y-%m-%d}")

    mdd_global = calc_mdd(port_ret)
    print(f"\n  MDD Global ({MDD_START_YEAR} - hoy): {mdd_global * 100:.2f}%")

    years_series = port_ret.index.year
    anios_disponibles = sorted(years_series.unique())

    mdd_anual_rows = []
    for y in anios_disponibles:
        r_y = port_ret[years_series == y]
        mdd_anual_rows.append(dict(year=y, mdd=calc_mdd(r_y), n_obs=len(r_y)))
    mdd_anual = pd.DataFrame(mdd_anual_rows)
    mdd_anual = mdd_anual[np.isfinite(mdd_anual["mdd"])]

    print("\n  MDD por ano:")
    disp = mdd_anual.copy()
    disp["mdd_pct"] = (disp["mdd"] * 100).round(2)
    print(disp[["year", "mdd_pct", "n_obs"]].to_string(index=False))

    print("\n=== ESTADISTICAS DE MDD ===")

    if len(mdd_anual) >= 3:
        q1 = mdd_anual["mdd"].quantile(0.25)
        q3 = mdd_anual["mdd"].quantile(0.75)
        iqr = q3 - q1
        mdd_clean = mdd_anual[(mdd_anual["mdd"] >= q1 - 1.5 * iqr) & (mdd_anual["mdd"] <= q3 + 1.5 * iqr)]
        if len(mdd_clean) < 2:
            mdd_clean = mdd_anual
    else:
        mdd_clean = mdd_anual

    mdd_mediana = mdd_clean["mdd"].median()
    # MDD es negativo: el escenario conservador es la cola baja (P10). El P90
    # quedaba mas leve que la mediana.
    mdd_p10 = mdd_clean["mdd"].quantile(0.10)
    mdd_media = mdd_clean["mdd"].mean()
    mdd_peor = mdd_clean["mdd"].min()
    mdd_mejor = mdd_clean["mdd"].max()

    print(f"  Peor escenario historico:      {mdd_peor * 100:.2f}%")
    print(f"  Escenario conservador (P10):   {mdd_p10 * 100:.2f}%")
    print(f"  Escenario tipico (mediana):    {mdd_mediana * 100:.2f}%")
    print(f"  Promedio:                      {mdd_media * 100:.2f}%")
    print(f"  Mejor escenario historico:     {mdd_mejor * 100:.2f}%")

    ultimo_anio = mdd_anual.iloc[-1]
    print(f"  MDD mas reciente ({int(ultimo_anio['year'])}):         {ultimo_anio['mdd'] * 100:.2f}%")

    anios_completos = pd.DataFrame({"year": range(MDD_START_YEAR, date.today().year + 1)})
    plot_data = anios_completos.merge(mdd_anual, on="year", how="left")
    plot_data["mdd_pct"] = plot_data["mdd"] * 100
    plot_data["con_dato"] = plot_data["mdd_pct"].notna()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=plot_data["year"], y=plot_data["mdd_pct"], mode="lines+markers",
        line=dict(color="darkred", width=1.5),
        marker=dict(color=plot_data["con_dato"].map({True: "darkred", False: "gray"}), size=8),
        hovertemplate="Ano %{x}: %{y:.2f}%<extra></extra>", showlegend=False,
    ))
    fig.add_hline(y=mdd_mediana * 100, line_dash="dash", line_color="steelblue",
                  annotation_text=f"Mediana: {mdd_mediana * 100:.2f}%", annotation_position="top left",
                  annotation_font_color="steelblue")
    fig.add_hline(y=mdd_p10 * 100, line_dash="dash", line_color="darkorange",
                  annotation_text=f"P10: {mdd_p10 * 100:.2f}%", annotation_position="bottom left",
                  annotation_font_color="darkorange")
    fig.update_layout(
        title=dict(text="Maximum Drawdown Historico - Portafolio BL + BKM<br>"
                         f"<sup>Perfil: {PERFIL_RIESGO.upper()} | Horizonte: {etiqueta_horizonte} | "
                         f"MDD global ({MDD_START_YEAR}-hoy): {mdd_global * 100:.2f}% | "
                         f"{int(plot_data['con_dato'].sum())} anos con datos</sup>"),
        xaxis_title="Ano", yaxis_title="MDD (%)",
        xaxis=dict(tickmode="linear", tick0=MDD_START_YEAR, dtick=1, tickangle=45),
        template="plotly_white",
    )
    fig.show()
    print("  Grafico de MDD generado.")

else:
    print("  Datos insuficientes para calcular MDD (minimo 10 observaciones).")
    print("  Verifica que MDD_START_YEAR este dentro de la ventana de 2 anios.")

_pf = f"BL+BKM {modo_efectivo.upper()}"
print("\n" + "=" * 79)
print("FIN - BLACK-LITTERMAN EXTENDIDO POR MOMENTOS DE ORDEN SUPERIOR (BKM)")
print("=" * 79)
print(f"  Perfil de riesgo:       {PERFIL_RIESGO.upper()}")
print(f"  Horizonte:              {etiqueta_horizonte} ({horizonte_dias} dias habiles)")
print(f"  Universo:               {n} tickers | Views: {N_VIEWS}")
print(f"  Ajuste Q -> P:          Mincer-Zarnowitz (VRP/SRP/KRP) + Esscher por GMM")
print(f"  Posterior:              {metodo_posterior_usado} "
      f"(ENS {info_post['ens'] * 100:.1f}% de {N_ESCENARIOS} escenarios)")
print(f"  Optimizacion:           {modo_efectivo.upper()}")
print(f"  VaR{nc} Cornish-Fisher:   {metricas_post.loc[f'VaR{nc}_CornishFisher', _pf]:.4f}")
print(f"  CVaR{nc} historico:       {metricas_post.loc[f'CVaR{nc}_historico', _pf]:.4f}")
print(f"  Sortino / Omega:        {metricas_post.loc['Sortino', _pf]:.3f} / "
      f"{metricas_post.loc['Omega', _pf]:.3f}")
print(f"  MDD analizado desde:    {MDD_START_YEAR}")

if USAR_IV_POLYGON:
    print("\nDiagnostico de llamadas a Polygon:")
    pc.print_diagnostics()
