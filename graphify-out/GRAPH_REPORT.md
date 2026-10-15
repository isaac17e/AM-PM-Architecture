# Graph Report - AM-PM-Architecture  (2026-10-15)

## Corpus Check
- 34 files · ~133,745 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 3, .ini 1)

## Summary
- 1490 nodes · 3335 edges · 108 communities (77 shown, 31 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 89 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `08c49285`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- bl_metrics.py
- test_pipeline_io.py
- numpy
- polygon_client.py
- cornish_fisher_tail
- beta_range_reachable
- test_polygon_client.py
- market_data.py
- test_portfolio_constraints.py
- test_market_data.py
- test_cycle2_fixes.py
- test_qu_metrics.py
- otm_log_moneyness
- to_years
- minimum_variance_(seasonal_version).py
- minimum_variance.py
- test_market_cap_internacional.py
- _GetterFalso
- math
- get_spot_history
- test_ajuste_iv_tasa.py
- bl_metrics.py
- black_litterman.py
- risk_estimators.py
- frames_from_yf_download
- quadratic_utility_(seasonal_version).py
- test_mv_cola_y_delta.py
- test_universo_y_delta_estacional.py
- quadratic_utility.py
- fit_ssvi
- test_etf_floor_refill.py
- scale_moments
- test_risk_profile.py
- Risk Profile Audit (configuration per investor profile)
- cornish_fisher_es_gradient
- pathlib
- test_script_smoke.py
- Quadratic utility maximization U = mu'w - lambda/2 w'Sigma w
- resolve_horizon
- test_tail_prune_loop.py
- descargar_precio
- Black-Litterman with reverse CAPM equilibrium, SSVI, BKM and MVSK/CVaR
- normalize_currency
- set_rate_limit
- select_optimal_candidates
- score_candidate_portfolios
- requirements.txt dependency pins
- max_drawdown
- QU/MV normal: profile is a portfolio beta band (0.60-0.80 / 0.80-0.95 / >=0.95), 2026-10-11
- mincer_zarnowitz
- build_weight_constraints
- _asegurar_momentos_actuales
- bkm_fechas_pendientes
- qu_metrics.py
- mfis_check_deadline
- _momentos_sector
- drop_partial_last_week
- calcular_bkm_moments
- spot_series_for
- fetch_option_aggs
- parse_horizon_months
- frontier_curve
- bkm_seleccion_fecha
- clip_negligible_weights
- elegir_spot_momentos
- AM-PM Portfolio Construction Repository
- calcular_metricas_riesgo_cola
- higher_moments_admissible
- average_abs_correlation
- mfis_tail_decision
- resumen_ajuste_iv
- select_historical_otm
- horizon_from_months
- quadratic_utility.py run: QUBO + filters to 5-asset portfolio (ANET, AVGO, LLY, ORLY, NTES), lambda 1.5, 2-month horizon
- covariance_min_history
- _YahooFalso
- estimar_theta_esscher
- horizon_from_month_list
- resolve_bl_mode
- scale_option_deltas
- bootstrap_estacionario
- posterior_gram_charlier
- utilidad_mvsk_negativa
- bkm_motivo_fallback
- bkm_motivo_fallback
- _Limitador
- portfolio_returns_skipna
- entropy_pooling
- _evaluar_historia_bkm
- clip_implied_correlation
- mfiv_annual_vol
- plan_bkm_history_budget
- sector_implied_ready
- stitch_covariance
- summarize_yearly_mdd
- _precargar_spots_bkm
- _diag_ssvi
- default_ff_cache_dir
- shrink_mu_to_prior
- download_ticker_data
- _pct
- test_bl_horizonte_previews.py
- test_horizon_is_resolved_before_any_use
- _momento_pendiente
- momentos_ponderados
- optimizar_min_cvar
- tabla_ratio_vol_reciente

## God Nodes (most connected - your core abstractions)
1. `get_json()` - 27 edges
2. `to_years()` - 25 edges
3. `calibrate_iv_carry()` - 20 edges
4. `Risk Profile Audit (configuration per investor profile)` - 20 edges
5. `fetch_otm_chain()` - 19 edges
6. `fit_ssvi()` - 18 edges
7. `es_transitorio()` - 18 edges
8. `calibrar_superficie_ssvi()` - 17 edges
9. `bs_price()` - 15 edges
10. `get_all()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `QU/MV normal: profile is a portfolio beta band (0.60-0.80 / 0.80-0.95 / >=0.95), 2026-10-11` --semantically_similar_to--> `Portfolio beta band (beta_port_lo/hi, beta_asset_min/max, Blume shrink) replaces vol/corr percentiles and ETF quota`  [INFERRED] [semantically similar]
  docs/risk_profile_audit.html → README.md
- `QU run lambda sweep and frontier (pen_ret 0.141 at lambda 1.5)` --semantically_similar_to--> `Lambda calibration with pen_ret`  [INFERRED] [semantically similar]
  salidas_minimum_variance_y_quadratic_utility.txt → docs/risk_profile_audit.html
- `mu = historical mean shrunk toward Fama-French (mu_shrink_k = 140)` --semantically_similar_to--> `Expected return shrunk toward Fama-French 3-factor (mu_shrink_k)`  [INFERRED] [semantically similar]
  docs/risk_profile_audit.html → README.md
- `LP feasibility check (reachable beta band, regional caps) and ETF refill` --semantically_similar_to--> `Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12)`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `lambda3/lambda4 derived from gamma (CRRA Taylor expansion)` --semantically_similar_to--> `BL lambda3/lambda4 closed form from gamma`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared estimation modules feeding the three optimizers** — polygon_client, risk_estimators, market_data, portfolio_constraints, qu_metrics, bl_metrics, pipeline_io, quadratic_utility, minimum_variance, black_litterman [EXTRACTED 1.00]
- **Beta-band risk profile (README, audit, constraints, optimizers)** — readme_beta_band, docs_risk_profile_audit_beta_band, portfolio_constraints, quadratic_utility, minimum_variance [INFERRED 0.85]
- **Options-implied tail risk pipeline (BKM, Q to P, Cornish-Fisher)** — readme_bkm, readme_q_to_p, readme_cornish_fisher, readme_co_moments, readme_ssvi_fit [INFERRED 0.85]
- **Risk-profile calibration (gamma ladder, CRRA lambdas, lambda-only aversion, pen_ret)** — docs_risk_profile_audit_gamma_ladder, docs_risk_profile_audit_crra_lambdas, docs_risk_profile_audit_lambda_only_risk_aversion, docs_risk_profile_audit_lambda_calibration [INFERRED 0.85]

## Communities (108 total, 31 thin omitted)

### Community 0 - "bl_metrics.py"
Cohesion: 0.10
Nodes (30): crra_taylor_lambdas(), integration_strike_bounds(), market_delta(), variance_annual_to_horizon(), _cadena_ssvi(), _precios_con_paridad(), test_apply_vol_q_to_p_does_not_haircut_historical_vol(), test_calibrar_superficie_ignora_leaps_y_quotes_rotos() (+22 more)

### Community 1 - "test_pipeline_io.py"
Cohesion: 0.12
Nodes (14): load_bl_input(), select_views(), _escribir(), _leer(), test_atomic_replace(), test_bl_input_invalid_or_missing(), test_bl_input_universe_uses_only_tickers(), test_bl_input_views_shape() (+6 more)

### Community 2 - "numpy"
Cohesion: 0.08
Nodes (40): log_portfolio_return(), momentos_realizados_rolling(), implied_variance_to_horizon(), market_beta(), nearest_psd(), portfolio_log_returns(), q_to_p_vol(), seasonal_vol_ratio() (+32 more)

### Community 3 - "polygon_client.py"
Cohesion: 0.07
Nodes (33): _avisar_403(), _avisar_sin_api_key(), cache_get(), cache_permitida(), cache_set(), _con_api_key(), es_snapshot(), _espera_reintento() (+25 more)

### Community 4 - "cornish_fisher_tail"
Cohesion: 0.14
Nodes (14): cornish_fisher_domain(), cornish_fisher_moments(), cornish_fisher_params(), a_parametros(), residuo(), cornish_fisher_tail(), cornish_fisher_z(), test_cornish_fisher_es_matches_numerical_integration() (+6 more)

### Community 5 - "beta_range_reachable"
Cohesion: 0.16
Nodes (10): beta_band_columns(), beta_coverage_additions(), _rango(), beta_range_reachable(), relax_beta_band(), test_banda_sin_techo(), test_beta_band_columns_son_homogeneas(), test_cobertura_de_beta_agrega_solo_lo_que_falta() (+2 more)

### Community 6 - "test_polygon_client.py"
Cohesion: 0.06
Nodes (39): polygon_fetch_chain(), bkm_fetch_otm_chain(), bkm_fetch_otm_chain(), calls_per_minute_from_env(), default_cache_dir(), es_transitorio(), fetch_otm_chain(), get_all() (+31 more)

### Community 7 - "market_data.py"
Cohesion: 0.07
Nodes (22): _campo(), combinar_tickers(), _con_reintentos(), convertir_serie_a_usd(), currency_from_suffix(), dedupe_share_classes(), default_market_cap_cache_path(), es_ticker_formato_us() (+14 more)

### Community 8 - "test_portfolio_constraints.py"
Cohesion: 0.06
Nodes (40): bs_call_delta(), clip_to_band(), prune_order(), relax_group_band(), with_return_target(), cornish_fisher_at_horizon(), qp_inputs_at_horizon(), var_cvar_cornish_fisher() (+32 more)

### Community 9 - "test_market_data.py"
Cohesion: 0.14
Nodes (19): align_prices_to_calendar(), resolve_currencies(), resolve_execution_months(), _bdays(), _precios_dos_mercados(), test_align_drops_low_coverage_ticker(), test_align_fills_local_holiday_instead_of_dropping_row(), test_align_long_gap_not_filled_beyond_limit() (+11 more)

### Community 10 - "test_cycle2_fixes.py"
Cohesion: 0.09
Nodes (18): resolve_risk_free_rate(), _clave_cap(), mfis_max_minutes_from_env(), orden_prioridad_mfis(), clave(), texto_delta_shrinkage(), _Resp, _get() (+10 more)

### Community 11 - "test_qu_metrics.py"
Cohesion: 0.12
Nodes (17): dispersion_usable(), dispersion_weights(), history_window(), pool_sin_no_procesados_mfis(), _formato_us_viejo(), test_combinar_tickers_conserva_sufijos_que_el_filtro_us_tiraba(), test_dispersion_cap_share_is_the_basket_over_known_spy_caps(), test_dispersion_weights_cap_weighted_spy_names_with_iv() (+9 more)

### Community 12 - "otm_log_moneyness"
Cohesion: 0.50
Nodes (3): otm_log_moneyness(), test_horizonte_cambia_la_moneyness_efectiva(), test_moneyness_escala_con_uno_y_dos_meses_de_rebalanceo()

### Community 13 - "to_years"
Cohesion: 0.10
Nodes (25): get_polygon_option_snapshot(), get_polygon_option_snapshot(), is_non_us_exchange(), expiry_rank_columns(), is_us_ticker(), pares_call_put(), bkm_get_current_moments(), bkm_iv_chain_to_prices() (+17 more)

### Community 14 - "minimum_variance_(seasonal_version).py"
Cohesion: 0.12
Nodes (15): bkm_annual_vol(), bkm_compute_moments(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), bs_price(), clean_symbol_table() (+7 more)

### Community 15 - "minimum_variance.py"
Cohesion: 0.12
Nodes (13): bkm_annual_vol(), bkm_compute_moments(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), clean_symbol_table(), constraints_feasible() (+5 more)

### Community 16 - "test_market_cap_internacional.py"
Cohesion: 0.11
Nodes (16): tabla_market_cap_texto(), _ordenar(), _proveedores(), test_cache_corrupta_no_rompe(), test_cache_evita_repetir_llamadas_y_vence_con_el_ttl(), test_convierte_a_usd_con_la_moneda_del_sufijo(), test_fast_info_en_peniques_se_lleva_a_libras(), test_n_top_mayor_que_la_lista_devuelve_todo() (+8 more)

### Community 17 - "_GetterFalso"
Cohesion: 0.14
Nodes (13): _escribir_atomico(), fetch_fama_french(), parse_fama_french_zip(), _ff(), _GetterFalso, _Resp, test_ff_cache_corrupta_cuenta_como_failed_y_un_zip_invalido_no_pisa_la_cache(), test_ff_descarga_ok_usa_https_timeout_y_guarda_cache() (+5 more)

### Community 18 - "math"
Cohesion: 0.18
Nodes (14): _atomic_write(), build_previews_payload(), _date_or_none(), export_portfolio(), _export_portfolio(), _int_or_none(), _jsonify(), _metrics() (+6 more)

### Community 19 - "get_spot_history"
Cohesion: 0.13
Nodes (15): get_spot_history(), _retry_spot_single(), _usable_spot(), _cierres(), test_get_spot_history_downloads_the_batch_once_and_workers_only_read(), batch(), single(), test_get_spot_history_falls_through_to_the_next_provider() (+7 more)

### Community 20 - "test_ajuste_iv_tasa.py"
Cohesion: 0.29
Nodes (11): _contrato(), _fuente(), _funcion(), test_atm_snapshot_fetches_both_sides_and_adjusts_iv(), test_bs_price_matches_closed_form_and_parity(), test_calibrate_iv_carry_without_pairs_keeps_script_rate(), test_chain_to_prices_uses_calibrated_carry(), test_current_moments_calibrate_before_pricing() (+3 more)

### Community 21 - "bl_metrics.py"
Cohesion: 0.07
Nodes (21): apply_vol_q_to_p(), calibrar_superficie_ssvi(), _fecha_naive(), forward_por_paridad(), iv_vol_at_horizon(), mfiv_or_horizon_variance(), momentos_fallback(), seleccionar_vencimientos() (+13 more)

### Community 22 - "black_litterman.py"
Cohesion: 0.11
Nodes (9): aplicar_limites_cartera(), calibrar_ssvi_ticker(), construir_restricciones(), parse_chain(), port_ret_row(), primas_esscher(), _retorno_min_factible(), _sanear_momento_fisico() (+1 more)

### Community 23 - "risk_estimators.py"
Cohesion: 0.09
Nodes (18): average_correlation(), cov_ewma_shrunk(), effective_sample_size(), ewma_cov(), ewma_weights(), ledoit_wolf_constant_correlation(), martin_wagner_excess_return(), q_to_p_correlation() (+10 more)

### Community 24 - "frames_from_yf_download"
Cohesion: 0.11
Nodes (10): default_spot_providers(), _frame_from_close(), frames_from_yf_download(), _naive_dates(), yfinance_spot_batch(), yfinance_spot_single(), test_frames_from_yf_download_reads_both_multiindex_orders(), test_yfinance_batch_is_one_unadjusted_download() (+2 more)

### Community 25 - "quadratic_utility_(seasonal_version).py"
Cohesion: 0.06
Nodes (32): armar_restricciones(), _asegurar_momentos_actuales(), bkm_clave_historia(), bkm_fechas_pendientes(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_iv_chain_to_prices(), bkm_reconstruct_mfis_history() (+24 more)

### Community 26 - "test_mv_cola_y_delta.py"
Cohesion: 0.20
Nodes (13): _bucle_de_cola(), _descartes(), _fuente(), _funcion(), test_conteo_estable_entre_horizontes(), test_conteos_por_umbral_conservador_moderado_agresivo(), test_defaults_del_filtro_delta_en_mv(), test_fallback_historico_activo_por_defecto() (+5 more)

### Community 27 - "test_universo_y_delta_estacional.py"
Cohesion: 0.09
Nodes (25): bs_call_delta_from_vol(), delta_cushion(), evaluar_delta_candidato(), filtro_delta_otm(), _finito(), pasa_filtro_delta(), test_nombres_sin_vol_se_conservan_y_polygon_manda_sobre_historica(), _cojines() (+17 more)

### Community 28 - "quadratic_utility.py"
Cohesion: 0.14
Nodes (8): clean_symbol_table(), _datos_con_precios(), _ff3_betas(), fila_iv_vs_reciente(), _parse_market_cap(), polygon_get_sector_etf(), polygon_get_sic_description(), rechaza_iv_vs_reciente()

### Community 29 - "fit_ssvi"
Cohesion: 0.16
Nodes (14): fit_ssvi(), objetivo(), _params(), _penalty(), _relativos(), _sigmoid(), _grupos_vencimiento(), ssvi_total_variance() (+6 more)

### Community 30 - "test_etf_floor_refill.py"
Cohesion: 0.05
Nodes (40): candidatos_reposicion(), completar_etfs(), contar_etfs(), diagnostico_banda_etf(), etfs_necesarios(), relajar_banda_etf(), reserva_etf(), restricciones_factibles() (+32 more)

### Community 31 - "scale_moments"
Cohesion: 0.18
Nodes (7): annualize(), scale_moments(), test_annualize_shortcut(), test_scale_moments_identity_and_basic_rules(), test_scale_moments_iid_skew_kurt_exact_for_gamma_sums(), test_scale_moments_weekly_skew_to_optimizer_horizon(), test_scale_moments_weekly_to_month_arrays()

### Community 32 - "test_risk_profile.py"
Cohesion: 0.21
Nodes (10): _cli_risk_profile(), resolve_risk_profile(), _literales(), _presets(), test_el_perfil_de_qu_y_mv_es_una_banda_de_beta(), test_preset_agresivo_no_cambia_los_literales(), test_presets_de_mv_y_qu_coinciden_con_la_auditoria(), test_resolve_default_si_no_hay_env_ni_cli() (+2 more)

### Community 33 - "Risk Profile Audit (configuration per investor profile)"
Cohesion: 0.18
Nodes (13): Asset Allocation (FICs) am_pm/profiles.py mandates, Risk Profile Audit (configuration per investor profile), Black-Litterman PERFILES (omega_scale, tau, gamma_ra), COL Portfolio Architecture (proposed profile bands, max Sharpe), QU OTM delta filter as annual IV cap, International ticker format filter and region caps, Lambda calibration with pen_ret, mu = historical mean shrunk toward Fama-French (mu_shrink_k = 140) (+5 more)

### Community 34 - "cornish_fisher_es_gradient"
Cohesion: 0.20
Nodes (8): compute_marginal_cvar_contrib(), compute_marginal_cvar_contrib(), cornish_fisher_es_gradient(), portfolio_moment_gradients(), portfolio_moments(), test_cornish_fisher_es_gradient_vs_finite_differences(), test_portfolio_moment_gradients_vs_finite_differences(), test_portfolio_moments_match_direct_computation()

### Community 36 - "test_script_smoke.py"
Cohesion: 0.22
Nodes (11): _alias_importados(), _asignaciones_de_modulo(), _correr_bl(), _nombres(), sombras_de_import(), test_bl_input_file_overrides_tickers_and_views(), test_bl_risk_profile_env_and_cli(), test_bl_universe_file_drops_default_views() (+3 more)

### Community 37 - "Quadratic utility maximization U = mu'w - lambda/2 w'Sigma w"
Cohesion: 0.22
Nodes (8): Investor risk profiles (Conservador / Moderado / Agresivo), BKM risk-neutral moments (MFIV, MFIS, MFIK), Cornish-Fisher VaR/ES (Maillard 2012), include_etfs_in_portfolio switch, calibrate_iv_carry: Polygon IV carry from put-call parity, RISK_PROFILE env var and --risk-profile flag (RISK_PRESETS / PERFILES), Seasonal versions of minimum variance and quadratic utility, MV run covariance: factor-implied blended with EWMA+Ledoit-Wolf (alpha 0.35, delta 0.224)

### Community 38 - "resolve_horizon"
Cohesion: 0.20
Nodes (9): resolve_horizon(), resolve_horizon_months(), test_horizon_blank_env_is_unset(), test_horizon_default_when_nothing_set(), test_horizon_env_beats_default(), test_horizon_input_file_beats_env(), test_horizon_input_without_key_falls_back_to_env(), test_horizon_invalid_env_is_clear_error() (+1 more)

### Community 39 - "test_tail_prune_loop.py"
Cohesion: 0.26
Nodes (6): _bucle_de_poda(), _correr(), test_block_cut_is_skipped_when_it_leaves_too_few_names(), test_min_weight_keeps_capped_defensives(), test_names_below_threshold_are_cut_in_one_step(), test_prune_loop_survives_floor_weights()

### Community 40 - "descargar_precio"
Cohesion: 0.24
Nodes (4): asegurar_fx(), descargar_fx_moneda(), descargar_precio(), _par_fx()

### Community 41 - "Black-Litterman with reverse CAPM equilibrium, SSVI, BKM and MVSK/CVaR"
Cohesion: 0.25
Nodes (5): Market delta modes (historical, fixed, implied via SVIX), Entropy pooling posterior views, Methodology knobs (lambda_annual, bkm_tail_mode, DELTA_MKT_MODO), SSVI smile fit on |k|<=0.5, MV run Q to P correction: sigma_P/sigma_Q median 0.962, mean vol 20.94% to 18.84%

### Community 42 - "normalize_currency"
Cohesion: 0.17
Nodes (8): normalize_currency(), price_scale_factor(), download_period_returns(), get_currency_for_ticker(), download_period_returns(), get_currency_for_ticker(), test_normalize_currency(), test_price_scale_factor()

### Community 43 - "set_rate_limit"
Cohesion: 0.17
Nodes (6): estimate_minutes(), set_rate_limit(), polygon_aislado(), entorno_aislado(), test_limiter_spaces_calls(), test_set_rate_limit_updates_limiter_and_estimate()

### Community 44 - "select_optimal_candidates"
Cohesion: 0.25
Nodes (5): beta_band_text(), armar_restricciones(), qubo_energy(), select_candidates_qubo(), select_optimal_candidates()

### Community 45 - "score_candidate_portfolios"
Cohesion: 0.17
Nodes (8): comparison_lambdas(), lambda_monthly_from_annual(), score_candidate_portfolios(), utility_terms(), test_lambda_monthly_from_annual_scales_by_twelve_and_is_opt_in(), test_lambda_scores_use_the_reference_lambda_and_mu_final(), test_pen_ret_is_nan_when_return_is_not_positive(), test_utility_terms_show_when_the_penalty_binds()

### Community 46 - "requirements.txt dependency pins"
Cohesion: 0.18
Nodes (11): Test suite (pytest, no network), numpy>=1.24, pandas>=2.0, plotly>=5.18, pytest>=7.0, quadprog>=0.1.11, requests>=2.28, requirements.txt dependency pins (+3 more)

### Community 47 - "max_drawdown"
Cohesion: 0.22
Nodes (8): mdd_from_log_returns(), extract_metrics(), max_drawdown(), test_mdd_log_matches_exp_cumsum_not_simple_compounding(), test_max_drawdown_log_and_simple_differ(), test_max_drawdown_log_returns_known_path(), test_max_drawdown_monotone_is_zero_and_short_series_is_nan(), test_max_drawdown_simple_returns_known_path()

### Community 48 - "QU/MV normal: profile is a portfolio beta band (0.60-0.80 / 0.80-0.95 / >=0.95), 2026-10-11"
Cohesion: 0.25
Nodes (7): Open anomalies (share-class dedup in QU, XLK/QQQ overlap, MV delta filter, LW shrinkage 1.0), Pending revalidation of the beta band with real data (only synthetic runs), Parameters removed since 2026-09-01 audit, tail_prune_rule: prune by min_weight (or max_mtr) with share-class dedup, BKM coverage table: full BKM vs historical fallback (RY.TO sin_opciones_en_polygon), MV iterative pruning to 6 assets by min_weight under ETF/FX-aware constraints, minimum_variance.py run: 231-ticker universe to 6-asset tail-risk portfolio (BRK-B, PG, VZ, MCD, JNJ, RY.TO)

### Community 49 - "mincer_zarnowitz"
Cohesion: 0.20
Nodes (4): media_hac(), mincer_zarnowitz(), _nw_lags(), pronostico_con_sonrisa()

### Community 50 - "build_weight_constraints"
Cohesion: 0.20
Nodes (5): build_qp_constraints(), run_minvar_qp(), build_qp_constraints(), run_minvar_qp(), build_weight_constraints()

### Community 52 - "bkm_fechas_pendientes"
Cohesion: 0.33
Nodes (4): bkm_clave_historia(), bkm_fechas_pendientes(), _plan_ronda_bkm(), _rank_bkm()

### Community 53 - "qu_metrics.py"
Cohesion: 0.16
Nodes (9): Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12), Validation results of QU runs by profile (Oct 2026), align_daily_panel(), annualize_monthly(), estimate_bkm_history_calls(), LP feasibility check (reachable beta band, regional caps) and ETF refill, test_align_daily_panel_uses_spy_and_drops_the_short_name_only(), test_annualize_monthly_uses_twelve_not_horizon() (+1 more)

### Community 54 - "mfis_check_deadline"
Cohesion: 0.22
Nodes (5): mfis_check_deadline(), mfis_deadline(), MfisTiempoAgotado, test_mfis_check_deadline_usa_perf_counter_por_defecto(), test_mfis_deadline_es_reloj_real_y_none_sin_limite()

### Community 55 - "_momentos_sector"
Cohesion: 0.29
Nodes (4): mfiv_vs_atm(), _momentos_sector(), mfik_cap(), test_mfik_cap_rises_with_chain_depth()

### Community 56 - "drop_partial_last_week"
Cohesion: 0.43
Nodes (6): drop_partial_last_week(), _semanal(), test_drop_partial_last_week_empty_and_dataframe(), test_drop_partial_last_week_friday_kept(), test_drop_partial_last_week_thursday_before_holiday_friday(), test_drop_partial_last_week_wednesday_dropped()

### Community 57 - "calcular_bkm_moments"
Cohesion: 0.40
Nodes (5): calcular_bkm_moments(), otm_price_ssvi(), phi_powerlaw(), sigma_desde_ssvi(), ssvi_w()

### Community 58 - "spot_series_for"
Cohesion: 0.33
Nodes (3): spot_series_for(), _spot_series_bkm(), _spot_series_bkm()

### Community 59 - "fetch_option_aggs"
Cohesion: 0.14
Nodes (10): fetch_option_aggs(), close_near_from_bars(), contract_agg_ranges(), bkm_precios_en_rango(), polygon_contract_close_near(), bkm_precios_en_rango(), polygon_contract_close_near(), test_cache_de_disco_evita_llamadas_en_la_reejecucion() (+2 more)

### Community 60 - "parse_horizon_months"
Cohesion: 0.33
Nodes (3): InvalidHorizonError, parse_horizon_months(), test_horizon_accepts_integers_1_to_12()

### Community 61 - "frontier_curve"
Cohesion: 0.25
Nodes (4): frontier_curve(), frontier_lambda_grid(), portfolio_mu_final_metrics(), test_constrained_frontier_passes_through_the_optimum()

### Community 63 - "clip_negligible_weights"
Cohesion: 0.40
Nodes (3): clip_negligible_weights(), markowitz_clasico(), optimizar_mvsk()

### Community 65 - "AM-PM Portfolio Construction Repository"
Cohesion: 0.29
Nodes (8): AM-PM Portfolio Construction Repository, BL_INPUT_FILE universe/views JSON, horizon_months as single source of investment term (mu*h, Sigma*h), Pipeline JSON export (portfolio_latest.json), Pull request merge order (stacked PRs #2 to #4 then this PR), RISK_FREE_RATE env var (resolve_risk_free_rate), Warning: /workspace/pipeline/portfolio read-only, JSON export skipped, run continues, Console outputs of minimum_variance.py and quadratic_utility.py (2026-10-06, agresivo)

### Community 66 - "calcular_metricas_riesgo_cola"
Cohesion: 0.29
Nodes (4): calcular_metricas_riesgo_cola(), _pesos_normalizados(), var_cvar_cornish_fisher(), var_cvar_historico()

### Community 67 - "higher_moments_admissible"
Cohesion: 0.20
Nodes (7): momentos_cola_historicos(), momentos_cola_historicos(), bkm_compute_moments(), bkm_compute_moments(), higher_moments_admissible(), mfik_cap_tenor(), test_higher_moments_admissible_pearson()

### Community 68 - "average_abs_correlation"
Cohesion: 0.33
Nodes (5): average_abs_correlation(), _corr_abc(), test_average_abs_correlation_ignores_sign_and_order(), test_average_abs_correlation_uses_full_row(), test_old_alphabetical_grouping_drops_last_ticker()

### Community 69 - "mfis_tail_decision"
Cohesion: 0.29
Nodes (4): mfis_tail_decision(), test_mfis_tail_decision(), test_mfis_tail_default_upper_matches_old_inequality(), test_mfis_tail_rejects_unknown_mode()

### Community 70 - "resumen_ajuste_iv"
Cohesion: 0.33
Nodes (4): resumen_ajuste_iv(), texto_ajuste_iv(), test_resumen_ajuste_iv_counts_only_queried_chains(), test_texto_ajuste_iv_without_pairs()

### Community 71 - "select_historical_otm"
Cohesion: 0.33
Nodes (5): select_historical_otm(), _contratos(), test_select_historical_otm_empty_without_both_sides(), test_select_historical_otm_prefers_50_dte_over_15(), test_select_historical_otm_real_strikes_and_dte()

### Community 72 - "horizon_from_months"
Cohesion: 0.40
Nodes (3): _add_months(), horizon_from_months(), test_horizon_from_months()

### Community 73 - "quadratic_utility.py run: QUBO + filters to 5-asset portfolio (ANET, AVGO, LLY, ORLY, NTES), lambda 1.5, 2-month horizon"
Cohesion: 0.50
Nodes (5): Historical MFIS time budget (bkm_hist_max_minutes), MFIS_MAX_MINUTES wall-clock budget and queue ordering, QUBO/Ising candidate selection, QU run historical MFIS: 23 z-scored, 0 unprocessed, 215.8 s, key v3, quadratic_utility.py run: QUBO + filters to 5-asset portfolio (ANET, AVGO, LLY, ORLY, NTES), lambda 1.5, 2-month horizon

### Community 74 - "covariance_min_history"
Cohesion: 0.33
Nodes (4): columns_with_min_obs(), covariance_min_history(), test_columns_with_min_obs_keeps_long_history(), test_covariance_min_history_uses_each_series_full_sample()

### Community 76 - "estimar_theta_esscher"
Cohesion: 0.50
Nodes (3): cumulantes_Q_desde_P(), estimar_theta_esscher(), objetivo()

### Community 78 - "resolve_bl_mode"
Cohesion: 0.50
Nodes (3): resolve_bl_mode(), test_bl_mode_default_env_and_flag(), test_bl_mode_rejects_unknown_value()

### Community 79 - "scale_option_deltas"
Cohesion: 0.50
Nodes (3): scale_option_deltas(), test_scale_option_deltas_direct_does_not_stretch_a_tight_range(), test_scale_relative_no_reescala_lambda()

### Community 86 - "portfolio_returns_skipna"
Cohesion: 0.50
Nodes (3): portfolio_returns_skipna(), portfolio_returns_series(), test_portfolio_returns_skipna_does_not_drop_the_month()

### Community 88 - "_evaluar_historia_bkm"
Cohesion: 0.67
Nodes (4): evaluar_historia_bkm(), _evaluar_historia_bkm(), _fila(), _fila_bkm()

### Community 102 - "test_bl_horizonte_previews.py"
Cohesion: 0.14
Nodes (23): _archivo(), _correr(), _correr_previews(), _entorno(), _payload(), test_default_horizon_is_unchanged(), test_env_horizon_propagates_to_every_derived_quantity(), test_full_mode_unchanged_when_bl_mode_full() (+15 more)

## Knowledge Gaps
- **11 isolated node(s):** `pandas>=2.0`, `plotly>=5.18`, `scipy>=1.10`, `statsmodels>=0.14`, `DTE window and tenor scaling` (+6 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 455 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `mfis_tail_decision()` connect `mfis_tail_decision` to `_evaluar_historia_bkm`, `quadratic_utility_(seasonal_version).py`, `numpy`, `qu_metrics.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **What connects `pandas>=2.0`, `plotly>=5.18`, `scipy>=1.10` to the rest of the system?**
  _11 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `bl_metrics.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10384068278805121 - nodes in this community are weakly interconnected._
- **Why does `fetch_otm_chain()` connect `test_polygon_client.py` to `quadratic_utility_(seasonal_version).py`, `polygon_client.py`, `test_ajuste_iv_tasa.py`, `to_years`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Should `test_pipeline_io.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11956521739130435 - nodes in this community are weakly interconnected._
- **Why does `var_cvar_cornish_fisher()` connect `test_portfolio_constraints.py` to `calcular_metricas_riesgo_cola`, `numpy`, `cornish_fisher_tail`, `risk_estimators.py`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Should `numpy` be split into smaller, more focused modules?**
  _Cohesion score 0.07532467532467532 - nodes in this community are weakly interconnected._