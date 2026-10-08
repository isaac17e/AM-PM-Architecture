# Graph Report - AM-PM-Architecture  (2026-10-08)

## Corpus Check
- 35 files · ~125,278 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .ini 1)

## Summary
- 1354 nodes · 3026 edges · 91 communities (66 shown, 25 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 70 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `70bceffe`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_bl_metrics.py
- test_pipeline_io.py
- quadratic_utility.py
- bl_metrics.py
- test_risk_estimators.py
- polygon_client.py
- implied_variance_to_horizon
- math
- minimum_variance.py
- minimum_variance_(seasonal_version).py
- market_data.py
- test_market_cap_internacional.py
- pipeline_io.py
- test_ajuste_iv_tasa.py
- _precargar_spots_bkm
- test_market_data.py
- numpy
- test_script_smoke.py
- pytest
- fit_ssvi
- pathlib
- test_universo_y_delta_estacional.py
- get_spot_history
- fetch_otm_chain
- ledoit_wolf_constant_correlation
- frames_from_yf_download
- cornish_fisher_tail
- cornish_fisher_params
- test_mv_cola_y_delta.py
- black_litterman.py
- Risk Profile Audit (configuration per investor profile)
- test_cycle2_fixes.py
- test_risk_profile.py
- iv_vol_at_horizon
- _precargar_spots_bkm
- fetch_option_aggs
- test_qu_metrics.py
- set_rate_limit
- risk_estimators.py
- test_tail_prune_loop.py
- price_scale_factor
- drop_partial_last_week
- Working with the graphify knowledge graph
- _market_cap_yf
- descargar_fx_moneda
- _YahooFalso
- calcular_metricas_riesgo_cola
- mfis_tail_decision
- elegir_spot_momentos
- pandas
- _momentos_sector
- dedupe_share_classes
- momentos_ponderados
- frontier_curve
- _diag_ssvi
- average_abs_correlation
- test_polygon_client.py
- estimar_theta_esscher
- mincer_zarnowitz
- resumen_ajuste_iv
- align_daily_panel
- bootstrap_estacionario
- media_hac
- optimizar_mvsk
- covariance_min_history
- cache_get
- score_candidate_portfolios
- clip_negligible_weights
- _Limitador
- test_etf_floor_refill.py
- entropy_pooling
- descargar_precio
- normalize_currency
- horizon_from_month_list
- qu_metrics.py
- winsorizar
- bkm_reconstruct_mfis_history
- Working with the graphify knowledge graph
- bkm_reconstruct_mfis_history
- scale_moments
- mfiv_vs_atm
- estimate_bkm_history_calls
- sector_implied_ready
- nearest_psd
- primas_esscher
- get_all
- construir_restricciones
- _momento_pendiente
- _sanear_momento_fisico
- _retorno_min_factible

## God Nodes (most connected - your core abstractions)
1. `get_json()` - 27 edges
2. `to_years()` - 25 edges
3. `calibrate_iv_carry()` - 19 edges
4. `fetch_otm_chain()` - 19 edges
5. `fit_ssvi()` - 18 edges
6. `es_transitorio()` - 18 edges
7. `Risk Profile Audit (configuration per investor profile)` - 18 edges
8. `calibrar_superficie_ssvi()` - 17 edges
9. `scale_moments()` - 15 edges
10. `get_all()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `lambda3/lambda4 derived from gamma (CRRA Taylor expansion)` --semantically_similar_to--> `BL lambda3/lambda4 closed form from gamma`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `Reachable ETF floor and LP feasibility check` --semantically_similar_to--> `Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12)`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `test_currency_from_suffix()` --calls--> `currency_from_suffix()`  [EXTRACTED]
  tests/test_market_data.py → market_data.py
- `test_expiry_rank_prefers_50_over_15_for_a_30_day_target()` --calls--> `expiry_rank_columns()`  [EXTRACTED]
  tests/test_polygon_client.py → polygon_client.py
- `test_history_window_includes_current_year_through_last_full_month()` --calls--> `history_window()`  [EXTRACTED]
  tests/test_qu_metrics.py → qu_metrics.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared estimation modules feeding the three optimizers** — polygon_client, risk_estimators, market_data, portfolio_constraints, qu_metrics, bl_metrics, pipeline_io, quadratic_utility, minimum_variance, black_litterman [EXTRACTED 1.00]
- **Options-implied tail risk pipeline (BKM, Q to P, Cornish-Fisher)** — readme_bkm, readme_q_to_p, readme_cornish_fisher, readme_co_moments, readme_ssvi_fit [INFERRED 0.85]
- **Risk-profile calibration (gamma ladder, CRRA lambdas, lambda-only aversion, pen_ret)** — docs_risk_profile_audit_gamma_ladder, docs_risk_profile_audit_crra_lambdas, docs_risk_profile_audit_lambda_only_risk_aversion, docs_risk_profile_audit_lambda_calibration [INFERRED 0.85]

## Communities (91 total, 25 thin omitted)

### Community 0 - "test_bl_metrics.py"
Cohesion: 0.12
Nodes (18): crra_taylor_lambdas(), integration_strike_bounds(), market_delta(), ssvi_degeneracy(), ssvi_surface_decision(), test_crra_taylor_lambdas_match_profile_ladder(), test_crra_taylor_terms_are_the_crra_expansion(), test_delta_fixed_ignores_the_sample() (+10 more)

### Community 1 - "test_pipeline_io.py"
Cohesion: 0.13
Nodes (14): load_bl_input(), select_views(), _escribir(), _leer(), test_atomic_replace(), test_bl_input_invalid_or_missing(), test_bl_input_universe_uses_only_tickers(), test_bl_input_views_shape() (+6 more)

### Community 2 - "quadratic_utility.py"
Cohesion: 0.05
Nodes (25): armar_restricciones(), bkm_iv_chain_to_prices(), bs_price(), clean_symbol_table(), fila_iv_vs_reciente(), _parse_market_cap(), polygon_get_sector_etf(), polygon_get_sic_description() (+17 more)

### Community 3 - "bl_metrics.py"
Cohesion: 0.09
Nodes (16): calibrar_superficie_ssvi(), _fecha_naive(), forward_por_paridad(), momentos_fallback(), seleccionar_vencimientos(), ssvi_monotone_mask(), ssvi_row_mask(), ssvi_weights() (+8 more)

### Community 4 - "test_risk_estimators.py"
Cohesion: 0.15
Nodes (11): portfolio_moments(), _lw_constant_correlation_referencia(), _lw_ewma_referencia_delta(), panel(), retornos(), retornos_shock_covid(), test_cov_ewma_shrunk_pipeline(), test_ledoit_wolf_matches_independent_reference() (+3 more)

### Community 5 - "polygon_client.py"
Cohesion: 0.10
Nodes (16): _avisar_403(), _avisar_sin_api_key(), _con_api_key(), _espera_reintento(), get_json(), n_fallos_transitorios(), print_diagnostics(), _registrar() (+8 more)

### Community 6 - "implied_variance_to_horizon"
Cohesion: 0.15
Nodes (9): mfiv_or_horizon_variance(), variance_annual_to_horizon(), mfiv_annual_vol(), implied_variance_to_horizon(), test_mfiv_fallback_uses_horizon_variance_not_annual(), test_variance_annual_matches_implied_variance_helper(), test_mfiv_annual_vol_uses_real_dte(), test_implied_variance_to_horizon_arrays_and_nan() (+1 more)

### Community 7 - "math"
Cohesion: 0.13
Nodes (15): bs_call_delta(), bs_call_delta_from_vol(), delta_cushion(), mfis_max_minutes_from_env(), otm_log_moneyness(), test_mfis_max_minutes_from_env(), test_horizonte_cambia_la_moneyness_efectiva(), test_atm_call_delta_always_above_half() (+7 more)

### Community 8 - "minimum_variance.py"
Cohesion: 0.08
Nodes (20): bkm_annual_vol(), bkm_compute_moments(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), bkm_motivo_fallback(), bkm_resumen_fallbacks(), _bkm_vacio() (+12 more)

### Community 9 - "minimum_variance_(seasonal_version).py"
Cohesion: 0.07
Nodes (23): is_non_us_exchange(), bkm_annual_vol(), bkm_compute_moments(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), bkm_motivo_fallback(), bkm_resumen_fallbacks() (+15 more)

### Community 10 - "market_data.py"
Cohesion: 0.13
Nodes (13): combinar_tickers(), _con_reintentos(), currency_from_suffix(), default_market_cap_cache_path(), es_ticker_formato_us(), _escribir_cache(), _leer_cache(), market_caps_usd() (+5 more)

### Community 11 - "test_market_cap_internacional.py"
Cohesion: 0.12
Nodes (18): _llamar_caps(), _llamar_fx(), tabla_market_cap_texto(), _ordenar(), _proveedores(), cap_provider(), fx_provider(), test_cache_corrupta_no_rompe() (+10 more)

### Community 12 - "pipeline_io.py"
Cohesion: 0.14
Nodes (17): _add_months(), _atomic_write(), _date_or_none(), export_portfolio(), _export_portfolio(), horizon_from_months(), _int_or_none(), _jsonify() (+9 more)

### Community 13 - "test_ajuste_iv_tasa.py"
Cohesion: 0.11
Nodes (28): get_polygon_option_snapshot(), get_polygon_option_snapshot(), expiry_rank_columns(), pares_call_put(), polygon_get_atm_option(), polygon_get_atm_option(), bs_implied_vol(), bs_price() (+20 more)

### Community 15 - "test_market_data.py"
Cohesion: 0.13
Nodes (20): align_prices_to_calendar(), resolve_currencies(), resolve_execution_months(), _bdays(), _precios_dos_mercados(), test_align_drops_low_coverage_ticker(), test_align_fills_local_holiday_instead_of_dropping_row(), test_align_long_gap_not_filled_beyond_limit() (+12 more)

### Community 16 - "numpy"
Cohesion: 0.16
Nodes (17): apply_vol_q_to_p(), build_weight_constraints(), prune_order(), relax_group_band(), with_return_target(), test_apply_vol_q_to_p_does_not_haircut_historical_vol(), _base(), _minvar() (+9 more)

### Community 17 - "test_script_smoke.py"
Cohesion: 0.22
Nodes (11): _alias_importados(), _asignaciones_de_modulo(), _correr_bl(), _nombres(), sombras_de_import(), test_bl_input_file_overrides_tickers_and_views(), test_bl_risk_profile_env_and_cli(), test_bl_universe_file_drops_default_views() (+3 more)

### Community 18 - "pytest"
Cohesion: 0.10
Nodes (22): mdd_from_log_returns(), scale_option_deltas(), max_drawdown(), portfolio_log_returns(), seasonal_vol_ratio(), test_mdd_log_matches_exp_cumsum_not_simple_compounding(), test_scale_option_deltas_direct_does_not_stretch_a_tight_range(), test_scale_relative_no_reescala_lambda() (+14 more)

### Community 19 - "fit_ssvi"
Cohesion: 0.16
Nodes (14): fit_ssvi(), objetivo(), _params(), _penalty(), _relativos(), _sigmoid(), _grupos_vencimiento(), ssvi_total_variance() (+6 more)

### Community 21 - "test_universo_y_delta_estacional.py"
Cohesion: 0.14
Nodes (14): convertir_serie_a_usd(), _descartados(), _formato_us_viejo(), _fuente(), _internacionales_del_script(), _literales(), test_bl_no_manda_internacionales_a_polygon(), test_conteo_de_colchon_separa_umbrales_y_aguanta_el_horizonte() (+6 more)

### Community 22 - "get_spot_history"
Cohesion: 0.13
Nodes (15): get_spot_history(), _retry_spot_single(), _usable_spot(), _cierres(), test_get_spot_history_downloads_the_batch_once_and_workers_only_read(), batch(), single(), test_get_spot_history_falls_through_to_the_next_provider() (+7 more)

### Community 23 - "fetch_otm_chain"
Cohesion: 0.08
Nodes (19): bkm_fetch_otm_chain(), bkm_fetch_otm_chain(), es_transitorio(), fetch_otm_chain(), polygon_format_ticker(), bkm_fetch_otm_chain(), polygon_contracts_asof(), polygon_format_ticker() (+11 more)

### Community 24 - "ledoit_wolf_constant_correlation"
Cohesion: 0.20
Nodes (10): average_correlation(), cov_ewma_shrunk(), effective_sample_size(), ewma_cov(), ewma_weights(), ledoit_wolf_constant_correlation(), test_ewma_weights_sum_to_one_and_reduce_to_equal(), test_ledoit_wolf_delta_cap_logs_raw_delta() (+2 more)

### Community 25 - "frames_from_yf_download"
Cohesion: 0.11
Nodes (10): default_spot_providers(), _frame_from_close(), frames_from_yf_download(), _naive_dates(), yfinance_spot_batch(), yfinance_spot_single(), test_frames_from_yf_download_reads_both_multiindex_orders(), test_yfinance_batch_is_one_unadjusted_download() (+2 more)

### Community 26 - "cornish_fisher_tail"
Cohesion: 0.16
Nodes (11): compute_marginal_cvar_contrib(), compute_marginal_cvar_contrib(), cornish_fisher_es_gradient(), cornish_fisher_tail(), portfolio_moment_gradients(), var_cvar_cornish_fisher(), test_cornish_fisher_es_gradient_vs_finite_differences(), test_cornish_fisher_es_monotone_in_moments() (+3 more)

### Community 27 - "cornish_fisher_params"
Cohesion: 0.18
Nodes (10): cornish_fisher_domain(), cornish_fisher_moments(), cornish_fisher_params(), a_parametros(), residuo(), cornish_fisher_z(), test_cornish_fisher_es_matches_numerical_integration(), test_cornish_fisher_params_reproduce_target_moments() (+2 more)

### Community 28 - "test_mv_cola_y_delta.py"
Cohesion: 0.22
Nodes (13): _bucle_de_cola(), _descartes(), _fuente(), _funcion(), test_conteo_estable_entre_horizontes(), test_conteos_por_umbral_conservador_moderado_agresivo(), test_defaults_del_filtro_delta_en_mv(), test_fallback_historico_activo_por_defecto() (+5 more)

### Community 29 - "black_litterman.py"
Cohesion: 0.13
Nodes (8): aplicar_limites_cartera(), calc_mdd(), gram_charlier_pdf_ratio(), he3(), he4(), optimizar_min_cvar(), port_ret_row(), posterior_gram_charlier()

### Community 30 - "Risk Profile Audit (configuration per investor profile)"
Cohesion: 0.05
Nodes (41): Asset Allocation (FICs) am_pm/profiles.py mandates, Risk Profile Audit (configuration per investor profile), Black-Litterman PERFILES (omega_scale, tau, gamma_ra), COL Portfolio Architecture (proposed profile bands, max Sharpe), QU OTM delta filter as annual IV cap, Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12), International ticker format filter and region caps, Lambda calibration with pen_ret (+33 more)

### Community 31 - "test_cycle2_fixes.py"
Cohesion: 0.06
Nodes (35): resolve_risk_free_rate(), _clave_cap(), cornish_fisher_at_horizon(), orden_prioridad_mfis(), clave(), plan_bkm_history_budget(), qp_inputs_at_horizon(), _plan_ronda_bkm() (+27 more)

### Community 32 - "test_risk_profile.py"
Cohesion: 0.20
Nodes (9): _cli_risk_profile(), resolve_risk_profile(), _literales(), _presets(), test_preset_agresivo_no_cambia_los_literales(), test_presets_de_mv_y_qu_coinciden_con_la_auditoria(), test_resolve_default_si_no_hay_env_ni_cli(), test_resolve_env_y_cli() (+1 more)

### Community 33 - "iv_vol_at_horizon"
Cohesion: 0.33
Nodes (4): iv_vol_at_horizon(), vol_annual_to_horizon(), test_ssvi_and_hist_fallback_share_horizon_units(), test_vol_annual_scales_with_sqrt_horizon()

### Community 35 - "fetch_option_aggs"
Cohesion: 0.15
Nodes (9): fetch_option_aggs(), close_near_from_bars(), contract_agg_ranges(), bkm_precios_en_rango(), polygon_contract_close_near(), bkm_precios_en_rango(), polygon_contract_close_near(), _barra() (+1 more)

### Community 36 - "test_qu_metrics.py"
Cohesion: 0.12
Nodes (17): dispersion_usable(), dispersion_weights(), history_window(), select_historical_otm(), _contratos(), _formato_us_viejo(), test_combinar_tickers_conserva_sufijos_que_el_filtro_us_tiraba(), test_dispersion_cap_share_is_the_basket_over_known_spy_caps() (+9 more)

### Community 37 - "set_rate_limit"
Cohesion: 0.17
Nodes (6): estimate_minutes(), set_rate_limit(), polygon_aislado(), entorno_aislado(), test_limiter_spaces_calls(), test_set_rate_limit_updates_limiter_and_estimate()

### Community 38 - "risk_estimators.py"
Cohesion: 0.09
Nodes (13): martin_wagner_excess_return(), mfik_cap(), mfik_cap_tenor(), q_to_p_correlation(), q_to_p_vol(), rescale_panel(), scale_cov(), standardized_panel() (+5 more)

### Community 39 - "test_tail_prune_loop.py"
Cohesion: 0.26
Nodes (6): _bucle_de_poda(), _correr(), test_block_cut_is_skipped_when_it_leaves_too_few_names(), test_min_weight_keeps_capped_defensives(), test_names_below_threshold_are_cut_in_one_step(), test_prune_loop_survives_floor_weights()

### Community 40 - "price_scale_factor"
Cohesion: 0.25
Nodes (5): price_scale_factor(), download_period_returns(), download_period_returns(), test_normalize_currency(), test_price_scale_factor()

### Community 41 - "drop_partial_last_week"
Cohesion: 0.43
Nodes (6): drop_partial_last_week(), _semanal(), test_drop_partial_last_week_empty_and_dataframe(), test_drop_partial_last_week_friday_kept(), test_drop_partial_last_week_thursday_before_holiday_friday(), test_drop_partial_last_week_wednesday_dropped()

### Community 42 - "Working with the graphify knowledge graph"
Cohesion: 0.33
Nodes (5): Freshness check, Git hygiene, Navigating, Verify before asserting, Working with the graphify knowledge graph

### Community 43 - "_market_cap_yf"
Cohesion: 0.18
Nodes (6): _campo(), _market_cap_yf(), yfinance_market_caps(), _uno(), test_fast_info_en_peniques_se_lleva_a_libras(), _Ticker

### Community 44 - "descargar_fx_moneda"
Cohesion: 0.40
Nodes (3): asegurar_fx(), descargar_fx_moneda(), _par_fx()

### Community 46 - "calcular_metricas_riesgo_cola"
Cohesion: 0.29
Nodes (4): calcular_metricas_riesgo_cola(), _pesos_normalizados(), var_cvar_cornish_fisher(), var_cvar_historico()

### Community 47 - "mfis_tail_decision"
Cohesion: 0.29
Nodes (4): mfis_tail_decision(), test_mfis_tail_decision(), test_mfis_tail_default_upper_matches_old_inequality(), test_mfis_tail_rejects_unknown_mode()

### Community 48 - "elegir_spot_momentos"
Cohesion: 0.33
Nodes (3): elegir_spot_momentos(), _spot_bkm(), test_elegir_spot_momentos_usa_el_cierre_del_dia_o_la_cadena()

### Community 49 - "pandas"
Cohesion: 0.10
Nodes (18): log_portfolio_return(), calibrar_ssvi_ticker(), momentos_realizados_rolling(), parse_chain(), portfolio_returns_skipna(), shrink_mu_to_prior(), summarize_yearly_mdd(), portfolio_returns_series() (+10 more)

### Community 50 - "_momentos_sector"
Cohesion: 0.29
Nodes (7): bs_price(), calcular_bkm_moments(), _momentos_sector(), otm_price_ssvi(), phi_powerlaw(), sigma_desde_ssvi(), ssvi_w()

### Community 53 - "frontier_curve"
Cohesion: 0.25
Nodes (4): frontier_curve(), frontier_lambda_grid(), portfolio_mu_final_metrics(), test_constrained_frontier_passes_through_the_optimum()

### Community 55 - "average_abs_correlation"
Cohesion: 0.33
Nodes (5): average_abs_correlation(), _corr_abc(), test_average_abs_correlation_ignores_sign_and_order(), test_average_abs_correlation_uses_full_row(), test_old_alphabetical_grouping_drops_last_ticker()

### Community 56 - "test_polygon_client.py"
Cohesion: 0.08
Nodes (27): calls_per_minute_from_env(), default_cache_dir(), _parse_calls_per_min(), test_calls_per_min_alias_y_sin_tope(), _contrato(), _RespuestaFalsa, _snapshot_grabado(), test_calls_per_minute_acepta_el_alias_viejo() (+19 more)

### Community 57 - "estimar_theta_esscher"
Cohesion: 0.50
Nodes (3): cumulantes_Q_desde_P(), estimar_theta_esscher(), objetivo()

### Community 59 - "resumen_ajuste_iv"
Cohesion: 0.33
Nodes (4): resumen_ajuste_iv(), texto_ajuste_iv(), test_resumen_ajuste_iv_counts_only_queried_chains(), test_texto_ajuste_iv_without_pairs()

### Community 60 - "align_daily_panel"
Cohesion: 0.27
Nodes (4): align_daily_panel(), stitch_covariance(), test_align_daily_panel_uses_spy_and_drops_the_short_name_only(), test_stitch_keeps_daily_block_and_monthly_for_the_short_name()

### Community 63 - "optimizar_mvsk"
Cohesion: 0.40
Nodes (3): momentos_portafolio(), optimizar_mvsk(), utilidad_mvsk_negativa()

### Community 64 - "covariance_min_history"
Cohesion: 0.33
Nodes (4): columns_with_min_obs(), covariance_min_history(), test_columns_with_min_obs_keeps_long_history(), test_covariance_min_history_uses_each_series_full_sample()

### Community 65 - "cache_get"
Cohesion: 0.23
Nodes (8): cache_get(), cache_permitida(), cache_set(), es_snapshot(), fechas_en_clave(), _ruta_cache(), test_cache_never_stores_current_date_or_snapshot(), test_get_json_serves_from_cache_without_key_or_network()

### Community 66 - "score_candidate_portfolios"
Cohesion: 0.17
Nodes (8): comparison_lambdas(), lambda_monthly_from_annual(), score_candidate_portfolios(), utility_terms(), test_lambda_monthly_from_annual_scales_by_twelve_and_is_opt_in(), test_lambda_scores_use_the_reference_lambda_and_mu_final(), test_pen_ret_is_nan_when_return_is_not_positive(), test_utility_terms_show_when_the_penalty_binds()

### Community 67 - "clip_negligible_weights"
Cohesion: 0.40
Nodes (3): clip_negligible_weights(), markowitz_clasico(), test_clip_negligible_weights_drops_solver_dust()

### Community 69 - "test_etf_floor_refill.py"
Cohesion: 0.05
Nodes (40): candidatos_reposicion(), completar_etfs(), contar_etfs(), diagnostico_banda_etf(), etfs_necesarios(), relajar_banda_etf(), reserva_etf(), restricciones_factibles() (+32 more)

### Community 72 - "normalize_currency"
Cohesion: 0.50
Nodes (3): normalize_currency(), get_currency_for_ticker(), get_currency_for_ticker()

### Community 74 - "qu_metrics.py"
Cohesion: 0.16
Nodes (11): annualize_monthly(), clip_implied_correlation(), evaluar_delta_candidato(), filtro_delta_otm(), _finito(), pasa_filtro_delta(), test_nombres_sin_vol_se_conservan_y_polygon_manda_sobre_historica(), test_annualize_monthly_uses_twelve_not_horizon() (+3 more)

### Community 76 - "bkm_reconstruct_mfis_history"
Cohesion: 0.10
Nodes (16): _asegurar_momentos_actuales(), bkm_clave_historia(), bkm_compute_moments(), bkm_fechas_pendientes(), bkm_get_current_moments(), bkm_reconstruct_mfis_history(), bkm_seleccion_fecha(), _datos_con_precios() (+8 more)

### Community 77 - "Working with the graphify knowledge graph"
Cohesion: 0.33
Nodes (5): Freshness check, Git hygiene, Navigating, Verify before asserting, Working with the graphify knowledge graph

### Community 78 - "bkm_reconstruct_mfis_history"
Cohesion: 0.10
Nodes (17): spot_series_for(), _asegurar_momentos_actuales(), bkm_clave_historia(), bkm_compute_moments(), bkm_fechas_pendientes(), bkm_get_current_moments(), bkm_reconstruct_mfis_history(), _datos_con_precios() (+9 more)

### Community 79 - "scale_moments"
Cohesion: 0.12
Nodes (11): momentos_cola_historicos(), momentos_cola_historicos(), annualize(), higher_moments_admissible(), scale_moments(), test_annualize_shortcut(), test_higher_moments_admissible_pearson(), test_scale_moments_identity_and_basic_rules() (+3 more)

### Community 87 - "get_all"
Cohesion: 0.24
Nodes (7): polygon_fetch_chain(), get_all(), _sumar(), _paginas(), test_get_all_follows_next_url(), test_get_all_marks_incomplete_when_a_page_fails(), test_get_all_truncated_by_max_pages()

## Knowledge Gaps
- **23 isolated node(s):** `Freshness check`, `Git hygiene`, `Navigating`, `Verify before asserting`, `Freshness check` (+18 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 429 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `fit_ssvi()` connect `fit_ssvi` to `numpy`, `bl_metrics.py`, `math`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **What connects `Freshness check`, `Git hygiene`, `Navigating` to the rest of the system?**
  _23 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_bl_metrics.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11594202898550725 - nodes in this community are weakly interconnected._
- **Why does `Quadratic utility maximization U = mu'w - lambda/2 w'Sigma w` connect `Risk Profile Audit (configuration per investor profile)` to `qu_metrics.py`, `quadratic_utility.py`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Should `test_pipeline_io.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12648221343873517 - nodes in this community are weakly interconnected._
- **Should `quadratic_utility.py` be split into smaller, more focused modules?**
  _Cohesion score 0.050505050505050504 - nodes in this community are weakly interconnected._
- **Should `bl_metrics.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09401709401709402 - nodes in this community are weakly interconnected._