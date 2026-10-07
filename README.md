# AM-PM

Python scripts for **portfolio construction** on market data (Yahoo Finance) and the options chain from **Polygon.io**.

The repository combines classical portfolio optimization (quadratic utility, minimum tail risk, Black-Litterman) with forward-looking information from the options market: implied volatility, Bakshi-Kapadia-Madan (BKM) risk-neutral moments, risk-neutral to physical (Q→P) corrections, and Cornish-Fisher tail risk.

> ⚠️ **Disclaimer**: this code is quantitative research. It is not investment advice. The default parameters (universes, tickers, rates) are examples and should be adjusted before any real use.

The active-management and visualization scripts (`entry_signal_tool.py`, `active_management.py`, `portfolio_risk_score_leverage.py`, `portfolio_gex_field.py`) were removed from this repository. They are not part of the pipeline below.

---

## Table of contents

- [Workflow architecture](#workflow-architecture)
- [Pull request merge order](#pull-request-merge-order)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Methodology knobs that do not change the default](#methodology-knobs-that-do-not-change-the-default)
- [Scripts](#scripts)
- [Tests](#tests)
- [Key concepts](#key-concepts)
- [Notes on the Polygon API](#notes-on-the-polygon-api)

---

## Workflow architecture

Each optimizer is a standalone script. Shared estimation lives in imported modules, not in a second copy of the formulas.

```
   polygon_client.py          rate limit, cache, pagination, OTM chain, ticker format
   risk_estimators.py         EWMA+LW, Q→P, Cornish-Fisher, time scaling, trapezoid
   market_data.py             currency from the provider, bounded ffill, partial weeks
   portfolio_constraints.py   quadprog weight bands (minimum variance)
   qu_metrics.py              quadratic-utility helpers (correlation, horizon, lambda, tails)
   bl_metrics.py              Black-Litterman units, market delta, log-return drawdown
   pipeline_io.py             portfolio JSON export and optional BL input file
                 │
   quadratic_utility.py              (+ quadratic_utility_(seasonal_version).py)
   minimum_variance.py               (+ minimum_variance_(seasonal_version).py)
   black_litterman.py
                 │
                 ▼
        portfolio weights, console summary, Plotly charts
```

### `polygon_client.py`
Shared Polygon.io access: a process-wide rate limiter (`POLYGON_CALLS_PER_MINUTE`, default 100), retries with exponential backoff, jitter, and `Retry-After`, pagination that never treats a truncated chain as complete, a disk cache (permanent for history, TTL for snapshots), and `polygon_format_ticker` (`BRK-B` → `BRK.B`). Non-US suffixes are not sent to the options chain. `fetch_otm_chain` also returns, in `info["pares"]`, the strikes of the chosen expiry that have both a call and a put; they feed `risk_estimators.calibrate_iv_carry`.

### `risk_estimators.py`
Estimation the optimizers share: EWMA covariance with Ledoit-Wolf shrinkage, Q→P vol and correlation, co-moment portfolio skewness and kurtosis, Cornish-Fisher VaR/ES (Maillard, 2012), `scale_moments` / `implied_variance_to_horizon` for changing the horizon, and `trapezoid` (`np.trapezoid` on NumPy 2, `np.trapz` on 1.x). BKM integration goes through `trapezoid`; no script calls `np.trapezoid` directly.

`calibrate_iv_carry` fixes the rate behind Polygon's `implied_volatility`. Polygon inverts each IV with its own carry, which it does not publish; repricing that IV at the script's `rf` gave prices off the market (MCD, Oct 2026: ATM call 25.5% vs put 22.2% on the same strike) and a jump at the money in the OTM chain that biased MFIS upward. The carry is the one that makes the call and put of each strike (within ±10% of spot) satisfy put-call parity at `rf`. `minimum_variance.py`, `quadratic_utility.py` and their seasonal versions reprice the BKM chain with it and convert the ATM IV with `iv_at_rate`; with no pairs, or a carry at the bound, they keep `rf`.

### `market_data.py`
Currency comes from the provider (`yfinance` `history_metadata`). A manual override is used only when the provider is silent, and a contradiction is reported rather than applied (HSBC and BP are USD ADRs). Prices in minor units (GBp, ZAc) are scaled before FX. Daily panels align to one calendar with a bounded forward-fill. A weekly `resample("W")` drops the in-progress week.

### `portfolio_constraints.py`
Quadprog constraint columns for minimum variance: per-asset bounds, full investment, the ETF band, and the FX cap. The optimizer and the efficient frontier use the same block. `bs_call_delta` documents why an ATM delta filter (`K = S`, `delta_min = 0.30`) never dropped a name.

### `qu_metrics.py`
Quadratic-utility pieces that do not need Polygon: average absolute correlation of a full matrix row, the history window through the last complete month, monthly annualization (return ×12, vol ×√12), optional annual-lambda conversion, MFIS tail choice, minimum history per ticker, pairwise covariance, skip-na portfolio returns, the SPY dispersion basket, and the historical OTM grid used to rebuild MFIS.

### `bl_metrics.py`
Black-Litterman units (annual SSVI vol versus horizon variance), the three market-delta modes, and maximum drawdown of log returns via `exp(cumsum)`.

---

## Pull request merge order

The fixes are stacked. Merge them in this order, retargeting the next PR to `main` after each merge:

1. **#2** `cursor/shared-modules-fixes-2e98` — `polygon_client.py`, `risk_estimators.py`, tests. Base: `main`.
2. **#3** `cursor/minimum-variance-fixes-2e98` — both minimum-variance scripts, `market_data.py`, `portfolio_constraints.py`. Base: #2.
3. **#4** `cursor/quadratic-utility-fixes-2e98` — both quadratic-utility scripts, `qu_metrics.py`. Base: #3.
4. **This PR** — `black_litterman.py`, `bl_metrics.py`, this README. Base: #4.

---

## Requirements

- Python 3.9 or higher
- A [Polygon.io](https://polygon.io) API key for any path that reads the options chain

Libraries are pinned in `requirements.txt` (NumPy ≥ 1.24, pandas, SciPy, requests, python-dotenv, yfinance, pandas-datareader, beautifulsoup4, lxml, statsmodels, quadprog, plotly, pytest). `quadprog` needs a C compiler; on Windows a prebuilt wheel is easier.

---

## Installation

```bash
git clone https://github.com/isaac17e/AM-PM.git
cd AM-PM

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the repository root (it is covered by `.gitignore`):

```env
POLYGON_API_KEY=your_api_key_here
POLYGON_CALLS_PER_MINUTE=100
RISK_PROFILE=agresivo
```

| Variable | Role |
|---|---|
| `POLYGON_API_KEY` | Polygon key. Without it, every options call returns `sin_api_key` and is not retried. `black_litterman.py` with `USAR_IV_POLYGON = True` stops at startup. The other optimizers continue on the historical fallback and print why each ticker missed the chain. |
| `POLYGON_CALLS_PER_MINUTE` | Rate cap. Default **100** calls/minute. `POLYGON_CALLS_PER_MIN` is the old name and is used only when the new one is unset. Use `5` on the free tier. `0`, `none`, or `unlimited` turns the limiter off. HTTP 429 and transient 5xx are retried with exponential backoff and jitter; a numeric `Retry-After` is waited out as given. |
| `POLYGON_SNAPSHOT_TTL_MIN` | Kept for compatibility. Live snapshots and anything dated today are not written to the cache. |
| `POLYGON_CACHE_DIR` | Cache directory, shared across runs. Default `~/.cache/am-pm/polygon` (outside the repo and the run folder). |
| `PORTFOLIO_OUT_DIR` | Where each optimizer writes `portfolio_latest.json` at the end of a run. Default `/workspace/pipeline/portfolio`. If the directory cannot be created or written, the script prints a warning and finishes anyway. |
| `BL_INPUT_FILE` | Optional JSON for `black_litterman.py`. If unset, missing, or invalid, the hardcoded `TICKERS` and views are used. |
| `RISK_PROFILE` | `conservador`, `moderado`, or `agresivo`. Applies that optimizer's preset. Unset keeps the profile already written in the file (`agresivo` in every optimizer). `--risk-profile` overrides this variable. |

`bkm_hist_max_minutes` (default **60**, top of `quadratic_utility.py` and its seasonal copy) is a budget, not a switch that skips the whole historical z-score. The script counts only US tickers with a finite current MFIS, charges about `bkm_hist_contracts_estimate` (26) priced contracts per uncached date, and walks the candidate ranking until the call budget is used. Names that do not fit are logged as `historia_no_procesada_presupuesto` (they stay in the book, and the log says they were not scored). Each OTM contract's daily aggregates are requested once for the span of sample dates, then sliced with the same ±5 day rule. The on-disk key is `mfis_hist_v3`. Only dates strictly before today are stored, so the next run pays the uncached dates. `bkm_max_workers` defaults to 12; the rate limiter is still global.

**Parameters are edited in the configuration block at the top of each file.** The only CLI flag is `--risk-profile` (`conservador`, `moderado`, or `agresivo`), which overrides `RISK_PROFILE`. With neither set, the run keeps the profile hardcoded in that file. Run a script with `python script_name.py`. Plotly charts open in the browser.

`minimum_variance.py`, `minimum_variance_(seasonal_version).py`, `quadratic_utility.py`, and `quadratic_utility_(seasonal_version).py` each keep a `RISK_PRESETS` dict (the columns in `docs/risk_profile_audit.html`). The numbers above that dict are the agresivo preset, so an unset profile does not change the book. `black_litterman.py` already selects with `PERFILES` (`omega_scale`, `tau`, `gamma_ra`); the same env var and flag override `PERFIL_RIESGO`.

### ETFs in the resulting portfolio

Minimum variance and quadratic utility have a `True`/`False` switch that decides whether ETFs may appear in the **final portfolio**. Black-Litterman has none: its universe is whatever you put in `TICKERS`, ETFs included.

| Script | Switch | ETF limit applied when `True` |
|---|---|---|
| `minimum_variance.py`, `minimum_variance_(seasonal_version).py` | `include_etfs_in_portfolio` | `etf_min_weight` – `etf_max_weight` (if `use_etf_constraint = True`) |
| `quadratic_utility.py`, `quadratic_utility_(seasonal_version).py` | `include_etfs_in_portfolio` | `pct_etf_deseado` ± `pct_etf_tolerancia` |

- `True`: ETFs can be held, and their share stays within the limit shown above.
- `False`: the final portfolio holds only stocks and commodities (`commodity_tickers`, e.g. `SLV`, `UNG`, which stay eligible even though they trade as ETFs). The ETF limit no longer applies.

The switch only affects the final optimization. ETFs are still downloaded and used everywhere else: sector and country factors, covariance matrices and candidate filters. With `False` their weight is simply set to 0. Because this makes the eligible pool smaller, the scripts stop with a clear error if too few stocks/commodities remain to add up to 100% under the per-asset cap.

---

## Methodology knobs that do not change the default

These exist so the choice is explicit. Leaving them at the default reproduces the previous behavior.

| Knob | Where | Default | What the other settings do |
|---|---|---|---|
| `lambda_annual` | both quadratic-utility scripts | `None` (keeps `lambda_` at 0.5 or 0.8, monthly) | If set, monthly λ = `lambda_annual × 12`. That inflates the risk penalty. The ranking-preserving conversion, if λ was defined on annual μ and annual Σ, would leave λ unchanged because the 12 cancels. The summary prints μ′w against (λ/2) w′Σw at the optimum. |
| `bkm_tail_mode` | both quadratic-utility scripts | `"upper"` | Drops z above the MFIS threshold (call demand; the old label was `cobertura_anomala`). `"lower"` drops z below minus the threshold (put demand, an actual hedge). `"both"` drops whichever side is hit, with `cola_superior` / `cola_inferior`. |
| `DELTA_MKT_MODO` | `black_litterman.py` | `"historical"` | Equilibrium π = δ Σ w. Historical δ is the 2-year excess return over horizon variance and can be negative. `"fixed"` uses `DELTA_MKT_FIJO` (2.5). `"implied"` is market risk-neutral variance over market physical variance (Martin: the market's excess return is its SVIX²). That ratio usually sits near 1, not near 2.5, because the premium is already in variance units. The run prints the mode and all three numbers. |

---

## Scripts

### 1. Portfolio construction

#### `quadratic_utility.py`
Portfolio optimizer based on **quadratic utility maximization** (`U = μ'w − λ/2 · w'Σw`), with μ and Σ monthly.

Pipeline:
1. Builds the universe (S&P 500 and NASDAQ names, commodities, ETFs, international tickers). Currency comes from the provider, with suffix fallback; prices are converted to USD.
2. Computes descriptive statistics and **Fama-French 3-factor betas**. Excess return is the stock's monthly return minus that month's French RF column.
3. **Joint candidate selection via QUBO/Ising**: brute force when the search space is small, simulated annealing otherwise.
4. Filters: recent volatility, IV vs. realized volatility, and a **BKM MFIS** z-score. The historical MFIS series uses the same OTM rule and moneyness bounds as the live chain (real strikes, real DTE, unadjusted prices).
   - Refills never undo a hard filter: when the IV or MFIS stage falls below its survivor floor, replacements skip names the IV-vs-recent-vol filter already dropped, and a name that never went through that filter must pass it. The recent-vol threshold and `n_filter_candidates` cap stay soft (refill in ascending ratio order).
   - **Reachable ETF floor**: the band needs `ceil((pct_etf_deseado − pct_etf_tolerancia) / max_weight)` ETFs in the optimizer. If the filters leave fewer, the script adds ETFs that pass the hard filters, first from the post-delta pool and then from a reserve of ETFs ranked just below the QUBO cut (`etf_floor_reserve_factor`). MFIS refills give ETFs priority while the floor is short.
   - Before `quadprog`, an LP feasibility check runs on the same constraints. If they cannot be met, the script prints why (e.g. `2 ETF x 0.12 = 24% < 45%`) and, with `etf_band_relax_if_infeasible = True`, lowers the floor to what is reachable; with `False` it stops with that diagnosis. Feasible runs are unchanged.
5. Covariance is a **shrinkage between implied (BKM) and historical covariance**. The historical leg uses daily returns, bounded calendar alignment, EWMA, and Ledoit-Wolf. Implied vols use each chain's real DTE, then Q→P. A sector implied correlation needs at least `sector_implied_min_names` names (default 4); a two-name sector keeps the global correlation. Expected return is one vector for both the QUBO selection and the QP: the historical monthly mean shrunk toward the Fama-French 3-factor return, `μ_i = w_i·μ_hist + (1−w_i)·μ_FF3` with `w_i = n_i / (n_i + mu_shrink_k)` (default 140 months, so ~12 years of history weighs 50/50 and 36 months ~20% historical). `mu_shrink_k = 0` restores the plain historical mean. The delta cushion is only an eligibility filter: it does not scale expected returns. Risk aversion in the QP lives only in `lambda_` (the selection score has no low-volatility term either: `weight_sharpe = 0.70`, `weight_decorr = 0.30`). The lambda comparison table prints `pen_ret = (λ/2 w'Σw) / w'μ_final` per λ, to calibrate `lambda_` against how much the risk penalty actually weighs.
6. Optimizes with `quadprog`. Output: the constrained efficient frontier (a lambda sweep of the same QP, plotted as σ = sqrt(w′Σw) against w′μ_final, so the optimum sits on the curve), a lambda comparison scored entirely at the configured lambda on μ_final, Greeks, maximum drawdown, and an executive summary. Annualization is return ×12 and vol ×√12 from the monthly figures (`qu_metrics.annualize_monthly`). The printed book return can still show raw μ; the frontier and the lambda figure use μ_final.

Key parameters: `lambda_`, `lambda_annual`, `max_weight`, `horizon_months`, `target_total_tickers`, `bkm_z_threshold`, `bkm_tail_mode`, `bkm_hist_max_minutes`, `cornish_fisher_confidence`, `cov_halflife_days`, `use_q_to_p_vol`, `use_q_to_p_correlation`.

#### `minimum_variance.py`
Optimizer for **minimum prospective tail risk (BKM + Cornish-Fisher)**.

- Ranks names by a **Cornish-Fisher VaR** built from risk-neutral moments, scaled with the chain's real DTE.
- The tail-risk portfolio is pruned down to `max_assets_in_portfolio` by **smallest weight** (`tail_prune_rule = "min_weight"`). `"max_mtr"` keeps the previous rule (drop the largest marginal tail contribution). Duplicate share classes are removed (`share_class_groups`, default keep `GOOGL` and drop `GOOG`).
- **Implied correlation by factors**: market + sector + country + FX, with the same Q→P correction on the factors as on the assets.
- Blends that covariance with a historical one from daily returns (EWMA + Ledoit-Wolf), after a bounded forward-fill so one market's holiday does not delete the row.
- Portfolio tail risk uses co-moments of a scenario panel. Skewness and kurtosis are scaled to the horizon with the same function as the per-asset filter.
- Constraints (max/min weight, ETF band, FX cap) are shared with the efficient frontier.
- The delta screen is off: an ATM call delta is above 0.5 whenever the strike is the spot, so `delta_min = 0.30` never removed a name.

#### `black_litterman.py`
**Black-Litterman** on exactly the names in `TICKERS` (Block 0, section 1): stocks, ETFs or commodities, US or any other exchange with its Yahoo suffix (`AZN.L`, `7203.T`, `ASML.AS`, `0700.HK`). There is no separate international or ETF list and no ETF cap. Prices and market caps are converted to USD with the currency Yahoo reports (suffix as fallback); FX is downloaded only for the currencies in the universe, using `{CUR}USD=X` when the pair is not in `fx_pairs`. Non-US names are not sent to Polygon (`sin_opciones_us`) and use historical vol and moments. There is no regional weight cap and no minimum international weight. `FALLBACK_ETF_POR_TICKER` is empty by default; fill it only if you use `FALLBACK_MOMENTOS = "sector"`. `AMPM_SMOKE=1` runs a three-name US universe (`AMPM_SMOKE_TICKERS` overrides it).

- Equilibrium returns `π = δ Σ w` from reverse CAPM. Market-cap weights are the reference. δ defaults to the historical estimate; see the methodology table.
- Implied volatility from Polygon with an **SSVI** fit on `|k| <= 0.5` (`SSVI_K_ABS_MAX`), weighted by relative vega and open interest. The ATM vol is annual (`sqrt(total variance / T)`) and is **kept when the smile is rejected**. A fit with `|rho| >= 0.95` or without both wings (`SSVI_K_SIDE_MIN`, `SSVI_MIN_PER_SIDE`) is logged as degenerate and falls back to the ATM source: the wings are not integrated. An accepted smile feeds BKM over **±3 sigma** of the SSVI wings (`BKM_N_STD`), not over the `|k| <= 0.5` calibration window. Σ and the MFIV fallback are the horizon quantities (`bl_metrics`). The Q→P vol ratio is applied only when the vol source is implied (`ssvi` or `atm`). A historical vol is left as the horizon variance. MFIV-vs-ATM and the MFIK cap still apply.
- **BKM** on the SSVI surface builds `Q` and `Ω`. Integration uses `risk_estimators.trapezoid`.
- Q→P is a cross-sectional Mincer-Zarnowitz regression (n is the cross-section after the price filter: low power; left as designed) plus an Esscher transform. `COTA_RATIO_VOL_P = (0.70, 1.00)` matches minimum variance and quadratic utility, so physical vol is not allowed above implied vol.
- Correlation for `Σ_P` comes from daily returns with EWMA and Ledoit-Wolf.
- Posterior views can be combined by entropy pooling. Optimization is MVSK or CVaR. `lambda3` and `lambda4` are derived from the profile's `gamma_ra` (fourth-order Taylor expansion of CRRA utility on raw central moments): `λ3 = γ(γ+1)/2`, `λ4 = γ(γ+1)(γ+2)/6`, so 1.875 / 2.19 (aggressive), 6 / 10 (moderate), 21 / 56 (conservative). γ is the only risk lever. The run summary prints each utility term at the optimum and warns when the fourth-order term exceeds half the variance term, where the truncated series stops approximating CRRA well.
- The historical tail panel uses overlapping horizon windows on about two years of daily data. The window count is not the number of independent observations; that is documented in the output and left overlapping on purpose.
- Maximum drawdown of the optimized portfolio uses log returns (`exp(cumsum)`), and the portfolio log return is `log(1 + Σ w (e^r − 1))`, not the weighted sum of logs.

Manager views are edited in **Block 6** of the file, or passed in `BL_INPUT_FILE` (see [Pipeline JSON](#pipeline-json)).

Risk-free fallback `Rf` in this file stays at `0.046`. Minimum variance and quadratic utility use `0.047`.

#### Seasonal versions
`minimum_variance_(seasonal_version).py` and `quadratic_utility_(seasonal_version).py` mirror the pipelines above, but restrict part of the analysis to **specific months** (`execution_months` / `rebalance_months`, default `[9]`). `None` builds that list from the run date (`execution_n_months` / `rebalance_n_months` consecutive months). An explicit list that does not include the current month prints a warning and is left unchanged.

What is seasonal:
- The sample used for the seasonal volatility ratio, and the minimum observation count (`seasonal_min_weeks`).
- In minimum variance, the drift `mu_T` inside the Cornish-Fisher filter, and the historical vol used as the Q→P reference for that filter, are computed on months in `execution_months`.

What is not seasonal:
- **BKM moments are the live chain** (about 30 DTE; an expiry at or beyond the target, and at least `dte_min_iv` / `polygon_dte_min` days, is preferred over a nearer short-dated expiry), not a September surface. VaR scales those moments to the target tenor. The per-asset CVaR/VaR filter is seasonal only in that drift and in the historical vol reference.
- Moments from the seasonal window replace BKM **only** when `tail_risk_hist_fallback=True` (default `False`).
- The **covariance matrix uses the full sample**. Restricting Σ to one month of the year would leave a handful of observations per year.

The seasonal quadratic-utility script keeps a single QUBO pass. Its `rf_rate` is `0.047`, same as the base script. Its delta screen matches the base script: OTM cushion (`delta_strike_mode="otm"`, aggressive `delta_min=0.15`), scaled with `sqrt(T)` where `T` is `len(rebalance_months)` (one month for `[10]`, two for `[10, 11]`). Polygon's ATM delta does not bypass that mode. As in the base script, the cushion is only an eligibility filter (no μ multiplier), the selection score has no low-volatility term, and μ is the historical mean shrunk toward Fama-French (`mu_shrink_k`).

---

## Pipeline JSON

At the end of a run, every optimizer writes UTF-8 JSON (`indent=2`) to `PORTFOLIO_OUT_DIR`: `portfolio_latest.json` and `portfolio_<optimizer>_<YYYYMMDDTHHMMSS>.json`. The write is atomic (`.tmp` then replace). Timestamps are ISO 8601 with the America/Bogota offset. Weights below `1e-6` are dropped and the rest are rounded to 6 decimal places and rescaled so they sum to 1. `tickers` is that same order, largest weight first. `metrics.expected_return` and `metrics.volatility` are annualized decimals when the script has them (quadratic utility uses monthly ×12 and ×√12; minimum variance uses its annual columns; Black-Litterman scales the horizon moments by `12 / MESES_HORIZONTE`).

`horizon_days` / `horizon_end` come from the script's own horizon. A month count (`MESES_HORIZONTE`, `horizon_months`) is calendar days from the run date to that date plus N months. A seasonal month list (`execution_months`, `rebalance_months`) is the calendar length of that month window, ending on its last day (the window that contains today, otherwise the next one).

`risk_profile` is the profile that ran (`agresivo`, `moderado`, or `conservador`) for every optimizer. With nothing selected it is `agresivo`, which is the preset already written in each file, so the weights are unchanged and the field is no longer null. `params` records the knobs that script actually has: `gamma` plus `lambda3` / `lambda4` for Black-Litterman, `lambda` for quadratic utility, weight caps, the ETF floor and cap, max assets or the candidate cap, shrinkage, and the main thresholds.

`BL_INPUT_FILE` replaces `TICKERS`. Two shapes are accepted.

A universe file (only `tickers` is read; views stay the Block 6 defaults, and a default view is dropped when any of its tickers is absent):

```json
{"schema_version": 1, "tickers": ["AAPL", "MSFT"], "source": "Corp_FR_Optimization"}
```

A views file. Each view is one row of `P` and one entry of `Q`, in horizon-return units, same as Block 6. `name` is optional. A relative view has two coefficients; an absolute view has one.

```json
{
  "schema_version": 1,
  "tickers": ["DELL", "META", "GS", "REGN", "EBAY", "ARES"],
  "source": "manager",
  "views": [
    {"name": "View_1", "p": {"DELL": 1.0, "META": -1.0}, "q": 0.15},
    {"name": "View_2", "p": {"GS": 1.0, "REGN": -1.0}, "q": 0.10},
    {"name": "View_3", "p": {"EBAY": 1.0, "ARES": -1.0}, "q": 0.08}
  ]
}
```

`views: []` means no views (the Gaussian posterior stays at equilibrium). Omitting `views` keeps the defaults. An invalid file is ignored with a warning.

## Tests

```bash
python -m pytest
```

Tests cover the shared modules and the extracted optimizer logic (FX and calendar alignment, quadprog constraints, time scaling, Cornish-Fisher, Polygon client behavior with recorded responses, quadratic-utility metrics, Black-Litterman units, delta modes, and log-return drawdown). `tests/test_pipeline_io.py` checks the portfolio JSON writer and `BL_INPUT_FILE` parsing with no network. `tests/test_script_smoke.py` parses every optimizer for a module-level name that shadows an import (`rk = ...` used to hide `risk_estimators`) and runs `black_litterman.py` under `AMPM_SMOKE=1` with mocked prices. They do not call Polygon and they do not run a full universe.

---

## Key concepts

- **BKM (Bakshi, Kapadia, and Madan, 2003)**: risk-neutral variance, skewness, and kurtosis (MFIV, MFIS, MFIK) from OTM option prices. MFIV is the variance integrated over the life of the contracts, not an annual variance. Annualize with the chain's real DTE, then scale to the portfolio horizon.
- **Cornish-Fisher**: adjusts a normal quantile for skewness and kurtosis. The S and K in the expansion are parameters, not the moments of the resulting distribution. The scripts solve for the parameters that reproduce the observed moments (Maillard, 2012). Pairs that violate K ≥ 1 + S² or exceed the MFIK cap are rejected rather than clipped: MFIV is kept, and MFIS/MFIK become NaN (or the neutral 0/3 in Black-Litterman). The cap starts at `bkm_mfik_max` (20) on a thin chain and rises linearly to `bkm_mfik_max_hard` (80) as the number of OTM strikes goes from 8 to 60. A dense index chain (SPY) can sit above 20 and still be kept. Black-Litterman counts observed SSVI strikes, not the integration grid.
- **DTE window**: `dte_tol_iv` (minimum variance) and `polygon_dte_tol` (quadratic utility) default to **21** days, so a monthly expiry at 15 or 50 DTE is inside a 30-day target. The chosen expiry prefers DTE ≥ `dte_min_iv` / `polygon_dte_min` (21) and DTE ≥ the target, so 50 beats 15. The printed MFIS/MFIK stay on the chain's real DTE. Cornish-Fisher VaR and the MFIS z-score scale skewness and excess kurtosis to the target tenor. The MFIK cap's excess over 3 scales with `ref_dte / chain_dte`. US listings, including class shares such as `BRK-B` / `BRK.B`, are detected by `polygon_client.is_us_ticker`; exchange suffixes (`.L`, `.TO`, `.AS`, `.SW`, `.HK`, and the rest of the known list) are not sent to the options API.
- **Polygon entitlements**: this plan includes options and reference only. A stock snapshot or stock aggregate returns 403, is not retried, and is printed once. Spot and prices come from Yahoo. Option aggregates stay on `O:` contract tickers. Non-US names in quadratic utility are labeled `sin_opciones_us` and are not sent to Polygon.
- **Risk-neutral vs. physical measure (Q vs. P)**: implied variance and implied correlation embed risk premia. The scripts estimate a bounded ratio of realized to implied moments. The upper bound is 1, so physical vol does not exceed implied vol.
- **EWMA + Ledoit-Wolf**: historical covariance from daily returns, weighted toward the recent regime, then shrunk toward a constant-correlation target.
- **Co-moments**: portfolio skewness and kurtosis are not the weighted average of the marginal moments. The scripts evaluate them on a scenario panel.
- **QUBO/Ising**: candidate selection as a quadratic binary problem. Individual quality is in the linear terms; correlation is in the pairwise penalty.

---

## Notes on the Polygon API

- The free *Stocks Basic* tier allows **5 calls per minute**. Set `POLYGON_CALLS_PER_MINUTE=5`. The default is 100. Raise it on the paid options plan if you want more throughput; `0` or `unlimited` turns the limiter off. A 429 waits for `Retry-After` when Polygon sends one; otherwise the client backs off exponentially with jitter, and the same backoff covers 500/502/503/504 and dropped connections.
- A full optimizer run walks hundreds of tickers. Lower `n_top_sp500`, `n_top_nasdaq`, and `target_total_tickers` for a short test.
- `bkm_max_workers` (default 12) is the BKM thread pool. The rate limiter is still global, so the threads share `POLYGON_CALLS_PER_MINUTE`.
- Yahoo class shares are sent to Polygon with a dot (`BRK-B` → `BRK.B`). Exchange suffixes (`.TO`, `.L`, `.AS`, and the rest of `is_us_ticker`'s list) are not sent to the options endpoints.
- When an options query fails, the ticker falls back to a historical estimate and the summary lists the reason. Read that table before trusting an "implied" book.
- Historical MFIS in quadratic utility spends `bkm_hist_max_minutes` on the highest-ranked US names that already have a finite current MFIS. The log prints how many received a z-score, how many were left unprocessed, and the elapsed seconds. The cache directory is `~/.cache/am-pm/polygon` unless `POLYGON_CACHE_DIR` is set. Today's option chain is not stored there.

---

## License

No license declared in the repository.
