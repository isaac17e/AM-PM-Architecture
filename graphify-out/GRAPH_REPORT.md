# Graph Report - AM-PM-Architecture  (2026-10-11)

## Corpus Check
- 35 files · ~123,666 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .ini 1)

## Summary
- 1384 nodes · 3117 edges · 102 communities (72 shown, 30 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 70 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c4345e79`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- pytest
- test_pipeline_io.py
- quadratic_utility_(seasonal_version).py
- bl_metrics.py
- quadratic_utility.py
- polygon_client.py
- test_etf_floor_refill.py
- qu_metrics.py
- minimum_variance.py
- minimum_variance_(seasonal_version).py
- market_data.py
- test_market_cap_internacional.py
- pipeline_io.py
- calibrate_iv_carry
- bkm_fechas_pendientes
- test_market_data.py
- test_portfolio_constraints.py
- test_script_smoke.py
- numpy
- fit_ssvi
- pathlib
- test_universo_y_delta_estacional.py
- get_spot_history
- polygon_format_ticker
- ledoit_wolf_constant_correlation
- frames_from_yf_download
- test_qu_horizonte.py
- Workflow architecture (shared modules feed standalone optimizers)
- test_mv_cola_y_delta.py
- black_litterman.py
- Risk Profile Audit (configuration per investor profile)
- test_cycle2_fixes.py
- test_risk_profile.py
- bs_price
- test_ajuste_iv_tasa.py
- fetch_option_aggs
- test_qu_metrics.py
- set_rate_limit
- risk_estimators.py
- test_tail_prune_loop.py
- normalize_currency
- drop_partial_last_week
- Working with the graphify knowledge graph
- test_etf_floor_estacional.py
- descargar_precio
- _YahooFalso
- calcular_metricas_riesgo_cola
- mfis_tail_decision
- _RespuestaFalsa
- pandas
- _momentos_sector
- dedupe_share_classes
- load_bl_input
- score_candidate_portfolios
- calls_per_minute_from_env
- average_abs_correlation
- test_polygon_client.py
- estimar_theta_esscher
- mincer_zarnowitz
- resumen_ajuste_iv
- etfs_necesarios
- bootstrap_estacionario
- media_hac
- utilidad_mvsk_negativa
- covariance_min_history
- restricciones_factibles
- utility_terms
- gram_charlier_pdf_ratio
- _Limitador
- test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados
- entropy_pooling
- bkm_reconstruct_mfis_history
- horizon_from_months
- horizon_from_month_list
- clip_implied_correlation
- winsorizar
- bkm_get_current_moments
- Working with the graphify knowledge graph
- evaluar_historia_bkm
- to_years
- test_get_json_exhausts_retries_on_network_error
- estimate_bkm_history_calls
- sector_implied_ready
- candidatos_reposicion
- os
- polygon_contracts_asof
- bkm_motivo_fallback
- get_all
- build_qp_constraints
- bkm_motivo_fallback
- max_drawdown_from_returns
- is_us_ticker
- max_drawdown_from_returns
- select_views
- default_cache_dir
- plan_bkm_history_budget
- construir_restricciones
- bkm_iv_chain_to_prices
- _sanear_momento_fisico
- calc_mdd
- download_ticker_data
- download_ticker_data

## God Nodes (most connected - your core abstractions)
1. `get_json()` - 27 edges
2. `to_years()` - 25 edges
3. `fetch_otm_chain()` - 19 edges
4. `calibrate_iv_carry()` - 19 edges
5. `fit_ssvi()` - 18 edges
6. `es_transitorio()` - 18 edges
7. `Risk Profile Audit (configuration per investor profile)` - 18 edges
8. `calibrar_superficie_ssvi()` - 17 edges
9. `get_all()` - 15 edges
10. `scale_moments()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Reachable ETF floor and LP feasibility check` --semantically_similar_to--> `Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12)`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `lambda3/lambda4 derived from gamma (CRRA Taylor expansion)` --semantically_similar_to--> `BL lambda3/lambda4 closed form from gamma`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `test_currency_from_suffix()` --calls--> `currency_from_suffix()`  [EXTRACTED]
  tests/test_market_data.py → market_data.py
- `test_expiry_rank_prefers_50_over_15_for_a_30_day_target()` --calls--> `expiry_rank_columns()`  [EXTRACTED]
  tests/test_polygon_client.py → polygon_client.py
- `test_vol_annual_scales_with_sqrt_horizon()` --calls--> `vol_annual_to_horizon()`  [EXTRACTED]
  tests/test_bl_metrics.py → bl_metrics.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared estimation modules feeding the three optimizers** — polygon_client, risk_estimators, market_data, portfolio_constraints, qu_metrics, bl_metrics, pipeline_io, quadratic_utility, minimum_variance, black_litterman [EXTRACTED 1.00]
- **Options-implied tail risk pipeline (BKM, Q to P, Cornish-Fisher)** — readme_bkm, readme_q_to_p, readme_cornish_fisher, readme_co_moments, readme_ssvi_fit [INFERRED 0.85]
- **Risk-profile calibration (gamma ladder, CRRA lambdas, lambda-only aversion, pen_ret)** — docs_risk_profile_audit_gamma_ladder, docs_risk_profile_audit_crra_lambdas, docs_risk_profile_audit_lambda_only_risk_aversion, docs_risk_profile_audit_lambda_calibration [INFERRED 0.85]

## Communities (102 total, 30 thin omitted)

### Community 0 - "pytest"
Cohesion: 0.10
Nodes (30): crra_taylor_lambdas(), integration_strike_bounds(), market_delta(), variance_annual_to_horizon(), _cadena_ssvi(), _precios_con_paridad(), test_apply_vol_q_to_p_does_not_haircut_historical_vol(), test_calibrar_superficie_ignora_leaps_y_quotes_rotos() (+22 more)

### Community 1 - "test_pipeline_io.py"
Cohesion: 0.19
Nodes (6): _leer(), test_atomic_replace(), test_default_dir_and_env(), test_export_writes_latest_and_timestamped_copy(), test_weights_round_to_six_decimals_and_sum_to_one(), test_write_error_warns()

### Community 2 - "quadratic_utility_(seasonal_version).py"
Cohesion: 0.06
Nodes (36): cache_get(), armar_restricciones(), _asegurar_momentos_actuales(), bkm_clave_historia(), bkm_compute_moments(), bkm_fechas_pendientes(), bkm_fetch_otm_chain(), bkm_get_current_moments() (+28 more)

### Community 3 - "bl_metrics.py"
Cohesion: 0.06
Nodes (22): apply_vol_q_to_p(), calibrar_superficie_ssvi(), _fecha_naive(), forward_por_paridad(), iv_vol_at_horizon(), mfiv_or_horizon_variance(), mfiv_vs_atm(), momentos_fallback() (+14 more)

### Community 4 - "quadratic_utility.py"
Cohesion: 0.12
Nodes (7): clean_symbol_table(), fila_iv_vs_reciente(), _parse_market_cap(), qubo_energy(), rechaza_iv_vs_reciente(), select_candidates_qubo(), tabla_ratio_vol_reciente()

### Community 5 - "polygon_client.py"
Cohesion: 0.09
Nodes (20): _avisar_403(), _avisar_sin_api_key(), cache_permitida(), cache_set(), _con_api_key(), es_snapshot(), _espera_reintento(), fechas_en_clave() (+12 more)

### Community 6 - "test_etf_floor_refill.py"
Cohesion: 0.15
Nodes (9): relajar_banda_etf(), siguiente_reposicion(), test_relajar_banda_no_toca_una_banda_alcanzable(), test_relajar_banda_sube_el_techo_si_faltan_acciones(), test_script_chequea_factibilidad_antes_de_quadprog(), test_script_delta_min_es_global_015(), test_siguiente_reposicion_prioriza_etf_cuando_faltan(), test_siguiente_reposicion_sin_etf_coincide_con_el_indice_secuencial() (+1 more)

### Community 7 - "qu_metrics.py"
Cohesion: 0.10
Nodes (23): align_daily_panel(), bs_call_delta_from_vol(), delta_cushion(), evaluar_delta_candidato(), filtro_delta_otm(), _finito(), mfis_max_minutes_from_env(), otm_log_moneyness() (+15 more)

### Community 8 - "minimum_variance.py"
Cohesion: 0.11
Nodes (14): bkm_annual_vol(), bkm_compute_moments(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), bs_price() (+6 more)

### Community 9 - "minimum_variance_(seasonal_version).py"
Cohesion: 0.12
Nodes (17): bkm_annual_vol(), bkm_compute_moments(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), bs_price() (+9 more)

### Community 10 - "market_data.py"
Cohesion: 0.11
Nodes (17): _campo(), combinar_tickers(), _con_reintentos(), currency_from_suffix(), default_market_cap_cache_path(), es_ticker_formato_us(), _escribir_cache(), _leer_cache() (+9 more)

### Community 11 - "test_market_cap_internacional.py"
Cohesion: 0.11
Nodes (19): _llamar_caps(), _llamar_fx(), tabla_market_cap_texto(), _ordenar(), _proveedores(), cap_provider(), fx_provider(), test_cache_corrupta_no_rompe() (+11 more)

### Community 12 - "pipeline_io.py"
Cohesion: 0.21
Nodes (11): _date_or_none(), export_portfolio(), _export_portfolio(), _int_or_none(), _jsonify(), _metrics(), _normalize_weights(), _num_or_none() (+3 more)

### Community 13 - "calibrate_iv_carry"
Cohesion: 0.26
Nodes (10): get_polygon_option_snapshot(), get_polygon_option_snapshot(), expiry_rank_columns(), pares_call_put(), polygon_get_atm_option(), polygon_get_atm_option(), calibrate_iv_carry(), iv_at_rate() (+2 more)

### Community 14 - "bkm_fechas_pendientes"
Cohesion: 0.20
Nodes (6): bkm_clave_historia(), bkm_fechas_pendientes(), _plan_ronda_bkm(), _precargar_spots_bkm(), _rank_bkm(), _ventana_spot_bkm()

### Community 15 - "test_market_data.py"
Cohesion: 0.13
Nodes (20): align_prices_to_calendar(), resolve_currencies(), resolve_execution_months(), _bdays(), _precios_dos_mercados(), test_align_drops_low_coverage_ticker(), test_align_fills_local_holiday_instead_of_dropping_row(), test_align_long_gap_not_filled_beyond_limit() (+12 more)

### Community 16 - "test_portfolio_constraints.py"
Cohesion: 0.07
Nodes (35): beta_band_columns(), beta_band_text(), beta_coverage_additions(), _rango(), beta_range_reachable(), bs_call_delta(), build_weight_constraints(), prune_order() (+27 more)

### Community 17 - "test_script_smoke.py"
Cohesion: 0.22
Nodes (11): _alias_importados(), _asignaciones_de_modulo(), _correr_bl(), _nombres(), sombras_de_import(), test_bl_input_file_overrides_tickers_and_views(), test_bl_risk_profile_env_and_cli(), test_bl_universe_file_drops_default_views() (+3 more)

### Community 18 - "numpy"
Cohesion: 0.05
Nodes (47): clip_negligible_weights(), log_portfolio_return(), mdd_from_log_returns(), markowitz_clasico(), optimizar_mvsk(), mfiv_annual_vol(), implied_variance_to_horizon(), market_beta() (+39 more)

### Community 19 - "fit_ssvi"
Cohesion: 0.16
Nodes (14): fit_ssvi(), objetivo(), _params(), _penalty(), _relativos(), _sigmoid(), _grupos_vencimiento(), ssvi_total_variance() (+6 more)

### Community 21 - "test_universo_y_delta_estacional.py"
Cohesion: 0.18
Nodes (12): _descartados(), _formato_us_viejo(), _fuente(), _internacionales_del_script(), _literales(), test_bl_no_manda_internacionales_a_polygon(), test_conteo_de_colchon_separa_umbrales_y_aguanta_el_horizonte(), test_conteo_del_filtro_estacional_sobre_universo_sintetico() (+4 more)

### Community 22 - "get_spot_history"
Cohesion: 0.13
Nodes (15): get_spot_history(), _retry_spot_single(), _usable_spot(), _cierres(), test_get_spot_history_downloads_the_batch_once_and_workers_only_read(), batch(), single(), test_get_spot_history_falls_through_to_the_next_provider() (+7 more)

### Community 23 - "polygon_format_ticker"
Cohesion: 0.33
Nodes (4): polygon_fetch_chain(), polygon_format_ticker(), test_polygon_format_ticker(), test_polygon_format_ticker_none()

### Community 24 - "ledoit_wolf_constant_correlation"
Cohesion: 0.15
Nodes (13): average_correlation(), cov_ewma_shrunk(), effective_sample_size(), ewma_cov(), ewma_weights(), ledoit_wolf_constant_correlation(), _lw_ewma_referencia_delta(), test_cov_ewma_shrunk_pipeline() (+5 more)

### Community 25 - "frames_from_yf_download"
Cohesion: 0.11
Nodes (10): default_spot_providers(), _frame_from_close(), frames_from_yf_download(), _naive_dates(), yfinance_spot_batch(), yfinance_spot_single(), test_frames_from_yf_download_reads_both_multiindex_orders(), test_yfinance_batch_is_one_unadjusted_download() (+2 more)

### Community 26 - "test_qu_horizonte.py"
Cohesion: 0.06
Nodes (35): compute_marginal_cvar_contrib(), compute_marginal_cvar_contrib(), cornish_fisher_at_horizon(), qp_inputs_at_horizon(), cornish_fisher_domain(), cornish_fisher_es_gradient(), cornish_fisher_moments(), cornish_fisher_params() (+27 more)

### Community 27 - "Workflow architecture (shared modules feed standalone optimizers)"
Cohesion: 0.14
Nodes (13): AM-PM Portfolio Construction Repository, Pull request merge order (stacked PRs #2 to #4 then this PR), Test suite (pytest, no network), numpy>=1.24, pandas>=2.0, plotly>=5.18, pytest>=7.0, quadprog>=0.1.11 (+5 more)

### Community 28 - "test_mv_cola_y_delta.py"
Cohesion: 0.22
Nodes (13): _bucle_de_cola(), _descartes(), _fuente(), _funcion(), test_conteo_estable_entre_horizontes(), test_conteos_por_umbral_conservador_moderado_agresivo(), test_defaults_del_filtro_delta_en_mv(), test_fallback_historico_activo_por_defecto() (+5 more)

### Community 29 - "black_litterman.py"
Cohesion: 0.10
Nodes (10): aplicar_limites_cartera(), _diag_ssvi(), _fmt_num(), _momento_pendiente(), momentos_ponderados(), momentos_realizados_rolling(), optimizar_min_cvar(), port_ret_row() (+2 more)

### Community 30 - "Risk Profile Audit (configuration per investor profile)"
Cohesion: 0.07
Nodes (28): Asset Allocation (FICs) am_pm/profiles.py mandates, Risk Profile Audit (configuration per investor profile), Black-Litterman PERFILES (omega_scale, tau, gamma_ra), COL Portfolio Architecture (proposed profile bands, max Sharpe), QU OTM delta filter as annual IV cap, Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12), International ticker format filter and region caps, Lambda calibration with pen_ret (+20 more)

### Community 31 - "test_cycle2_fixes.py"
Cohesion: 0.10
Nodes (18): resolve_risk_free_rate(), _clave_cap(), orden_prioridad_mfis(), clave(), texto_delta_shrinkage(), _Resp, test_cache_de_disco_evita_llamadas_en_la_reejecucion(), _get() (+10 more)

### Community 32 - "test_risk_profile.py"
Cohesion: 0.21
Nodes (10): _cli_risk_profile(), resolve_risk_profile(), _literales(), _presets(), test_el_perfil_de_qu_y_mv_es_una_banda_de_beta(), test_preset_agresivo_no_cambia_los_literales(), test_presets_de_mv_y_qu_coinciden_con_la_auditoria(), test_resolve_default_si_no_hay_env_ni_cli() (+2 more)

### Community 33 - "bs_price"
Cohesion: 0.21
Nodes (9): bs_implied_vol(), bs_price(), residuo(), _mercado(), _smile(), test_bs_implied_vol_round_trip_and_out_of_bounds(), test_bs_price_matches_closed_form_and_parity(), test_calibrate_iv_carry_at_bound_keeps_script_rate() (+1 more)

### Community 34 - "test_ajuste_iv_tasa.py"
Cohesion: 0.36
Nodes (8): _contrato(), _fuente(), _funcion(), test_atm_snapshot_fetches_both_sides_and_adjusts_iv(), test_calibrate_iv_carry_without_pairs_keeps_script_rate(), test_chain_to_prices_uses_calibrated_carry(), test_current_moments_calibrate_before_pricing(), test_fetch_otm_chain_returns_call_put_pairs_of_chosen_expiry()

### Community 35 - "fetch_option_aggs"
Cohesion: 0.24
Nodes (5): fetch_option_aggs(), close_near_from_bars(), bkm_precios_en_rango(), polygon_contract_close_near(), polygon_contract_close_near()

### Community 36 - "test_qu_metrics.py"
Cohesion: 0.10
Nodes (21): dispersion_usable(), dispersion_weights(), history_window(), scale_option_deltas(), select_historical_otm(), _contratos(), _formato_us_viejo(), test_combinar_tickers_conserva_sufijos_que_el_filtro_us_tiraba() (+13 more)

### Community 37 - "set_rate_limit"
Cohesion: 0.17
Nodes (6): estimate_minutes(), set_rate_limit(), polygon_aislado(), entorno_aislado(), test_limiter_spaces_calls(), test_set_rate_limit_updates_limiter_and_estimate()

### Community 38 - "risk_estimators.py"
Cohesion: 0.14
Nodes (8): higher_moments_admissible(), martin_wagner_excess_return(), mfik_cap(), mfik_cap_tenor(), scale_cov(), test_higher_moments_admissible_pearson(), test_mfik_cap_rises_with_chain_depth(), test_mfik_cap_tenor_loosens_a_short_chain()

### Community 39 - "test_tail_prune_loop.py"
Cohesion: 0.26
Nodes (6): _bucle_de_poda(), _correr(), test_block_cut_is_skipped_when_it_leaves_too_few_names(), test_min_weight_keeps_capped_defensives(), test_names_below_threshold_are_cut_in_one_step(), test_prune_loop_survives_floor_weights()

### Community 40 - "normalize_currency"
Cohesion: 0.17
Nodes (8): normalize_currency(), price_scale_factor(), download_period_returns(), get_currency_for_ticker(), download_period_returns(), get_currency_for_ticker(), test_normalize_currency(), test_price_scale_factor()

### Community 41 - "drop_partial_last_week"
Cohesion: 0.43
Nodes (6): drop_partial_last_week(), _semanal(), test_drop_partial_last_week_empty_and_dataframe(), test_drop_partial_last_week_friday_kept(), test_drop_partial_last_week_thursday_before_holiday_friday(), test_drop_partial_last_week_wednesday_dropped()

### Community 42 - "Working with the graphify knowledge graph"
Cohesion: 0.33
Nodes (5): Freshness check, Git hygiene, Navigating, Verify before asserting, Working with the graphify knowledge graph

### Community 43 - "test_etf_floor_estacional.py"
Cohesion: 0.27
Nodes (6): _bloque_restricciones(), _correr_restricciones(), test_banda_que_ya_cumplia_no_cambia(), test_con_el_cuarto_etf_el_conservador_resuelve_sin_relajar(), test_sin_cuarto_etf_la_banda_se_relaja_y_quadprog_resuelve(), test_sin_relajar_falla_con_mensaje_claro_y_no_con_quadprog()

### Community 44 - "descargar_precio"
Cohesion: 0.24
Nodes (4): asegurar_fx(), descargar_fx_moneda(), descargar_precio(), _par_fx()

### Community 46 - "calcular_metricas_riesgo_cola"
Cohesion: 0.29
Nodes (4): calcular_metricas_riesgo_cola(), _pesos_normalizados(), var_cvar_cornish_fisher(), var_cvar_historico()

### Community 47 - "mfis_tail_decision"
Cohesion: 0.29
Nodes (4): mfis_tail_decision(), test_mfis_tail_decision(), test_mfis_tail_default_upper_matches_old_inequality(), test_mfis_tail_rejects_unknown_mode()

### Community 48 - "_RespuestaFalsa"
Cohesion: 0.22
Nodes (9): _RespuestaFalsa, test_get_json_403_is_not_retried_and_names_the_plan(), _get(), test_get_json_jitter_on_5xx_and_retry_after_wins(), test_get_json_non_transient_error_is_not_retried_nor_cached(), _get(), test_get_json_retries_on_429_respecting_retry_after(), test_get_json_strips_key_from_cache_key_and_sends_it() (+1 more)

### Community 49 - "pandas"
Cohesion: 0.09
Nodes (18): elegir_spot_momentos(), calibrar_ssvi_ticker(), parse_chain(), _spot_bkm(), convertir_serie_a_usd(), contract_agg_ranges(), portfolio_returns_skipna(), summarize_yearly_mdd() (+10 more)

### Community 50 - "_momentos_sector"
Cohesion: 0.29
Nodes (7): bs_price(), calcular_bkm_moments(), _momentos_sector(), otm_price_ssvi(), phi_powerlaw(), sigma_desde_ssvi(), ssvi_w()

### Community 52 - "load_bl_input"
Cohesion: 0.31
Nodes (8): load_bl_input(), _parse_views(), _validate_bl_input(), _escribir(), test_bl_input_invalid_or_missing(), test_bl_input_universe_uses_only_tickers(), test_bl_input_views_shape(), test_empty_views_list_is_explicit()

### Community 53 - "score_candidate_portfolios"
Cohesion: 0.14
Nodes (8): comparison_lambdas(), frontier_curve(), frontier_lambda_grid(), portfolio_mu_final_metrics(), score_candidate_portfolios(), test_constrained_frontier_passes_through_the_optimum(), test_lambda_scores_use_the_reference_lambda_and_mu_final(), test_pen_ret_is_nan_when_return_is_not_positive()

### Community 54 - "calls_per_minute_from_env"
Cohesion: 0.22
Nodes (7): calls_per_minute_from_env(), _parse_calls_per_min(), test_calls_per_min_alias_y_sin_tope(), test_calls_per_minute_acepta_el_alias_viejo(), test_calls_per_minute_lee_el_nombre_largo(), test_calls_per_minute_sin_env_usa_el_default(), test_parse_calls_per_min()

### Community 55 - "average_abs_correlation"
Cohesion: 0.33
Nodes (5): average_abs_correlation(), _corr_abc(), test_average_abs_correlation_ignores_sign_and_order(), test_average_abs_correlation_uses_full_row(), test_old_alphabetical_grouping_drops_last_ticker()

### Community 56 - "test_polygon_client.py"
Cohesion: 0.14
Nodes (16): es_transitorio(), fetch_otm_chain(), test_fetch_otm_chain_empty_paths_carry_empty_pairs(), _contrato(), _snapshot_grabado(), test_es_transitorio_false(), test_es_transitorio_true(), test_expiry_rank_prefers_50_over_15_for_a_30_day_target() (+8 more)

### Community 57 - "estimar_theta_esscher"
Cohesion: 0.50
Nodes (3): cumulantes_Q_desde_P(), estimar_theta_esscher(), objetivo()

### Community 59 - "resumen_ajuste_iv"
Cohesion: 0.33
Nodes (4): resumen_ajuste_iv(), texto_ajuste_iv(), test_resumen_ajuste_iv_counts_only_queried_chains(), test_texto_ajuste_iv_without_pairs()

### Community 60 - "etfs_necesarios"
Cohesion: 0.22
Nodes (6): diagnostico_banda_etf(), etfs_necesarios(), test_diagnostico_explica_el_piso_de_etf(), test_diagnostico_vacio_si_los_conteos_alcanzan(), test_etfs_necesarios(), test_etfs_necesarios_rechaza_max_weight_invalido()

### Community 64 - "covariance_min_history"
Cohesion: 0.33
Nodes (4): columns_with_min_obs(), covariance_min_history(), test_columns_with_min_obs_keeps_long_history(), test_covariance_min_history_uses_each_series_full_sample()

### Community 65 - "restricciones_factibles"
Cohesion: 0.36
Nodes (8): restricciones_factibles(), test_caso_conservador_tal_como_llegaba_es_infactible_para_quadprog(), _quadprog(), _restricciones(), test_caso_conservador_es_infactible_y_quadprog_lo_confirma(), test_con_cuatro_etf_el_conservador_es_factible(), test_factibilidad_considera_el_tope_regional(), test_relajar_banda_lleva_el_piso_a_lo_alcanzable_y_queda_factible()

### Community 66 - "utility_terms"
Cohesion: 0.33
Nodes (4): lambda_monthly_from_annual(), utility_terms(), test_lambda_monthly_from_annual_scales_by_twelve_and_is_opt_in(), test_utility_terms_show_when_the_penalty_binds()

### Community 67 - "gram_charlier_pdf_ratio"
Cohesion: 0.33
Nodes (4): gram_charlier_pdf_ratio(), he3(), he4(), posterior_gram_charlier()

### Community 69 - "test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados"
Cohesion: 0.18
Nodes (9): completar_etfs(), contar_etfs(), reserva_etf(), test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados(), test_completar_etfs_agrega_solo_lo_necesario_y_en_orden(), test_completar_etfs_devuelve_lo_que_haya_si_no_alcanza(), test_contar_etfs_sin_duplicados(), test_reserva_etf_toma_los_que_faltan_en_orden_de_ranking() (+1 more)

### Community 71 - "bkm_reconstruct_mfis_history"
Cohesion: 0.33
Nodes (3): bkm_reconstruct_mfis_history(), bkm_seleccion_fecha(), _datos_con_precios()

### Community 72 - "horizon_from_months"
Cohesion: 0.40
Nodes (3): _add_months(), horizon_from_months(), test_horizon_from_months()

### Community 76 - "bkm_get_current_moments"
Cohesion: 0.25
Nodes (8): _asegurar_momentos_actuales(), bkm_compute_moments(), bkm_get_current_moments(), get_spot_safe_bkm(), is_us_ticker(), _momento_actual_bkm(), polygon_get_sector_etf(), polygon_get_sic_description()

### Community 77 - "Working with the graphify knowledge graph"
Cohesion: 0.33
Nodes (5): Freshness check, Git hygiene, Navigating, Verify before asserting, Working with the graphify knowledge graph

### Community 78 - "evaluar_historia_bkm"
Cohesion: 0.29
Nodes (5): spot_series_for(), evaluar_historia_bkm(), _fila(), _fila_bkm(), _spot_series_bkm()

### Community 79 - "to_years"
Cohesion: 0.11
Nodes (14): momentos_cola_historicos(), momentos_cola_historicos(), annualize_monthly(), annualize(), scale_bkm_moments(), scale_moments(), to_years(), test_annualize_monthly_uses_twelve_not_horizon() (+6 more)

### Community 80 - "test_get_json_exhausts_retries_on_network_error"
Cohesion: 0.40
Nodes (3): n_fallos_transitorios(), test_get_json_exhausts_retries_on_network_error(), test_n_fallos_transitorios_excludes_missing_key()

### Community 83 - "candidatos_reposicion"
Cohesion: 0.40
Nodes (3): candidatos_reposicion(), test_reposicion_aplica_el_filtro_iv_a_quien_nunca_paso_por_el(), test_reposicion_bkm_no_trae_de_vuelta_a_mchi()

### Community 85 - "polygon_contracts_asof"
Cohesion: 0.40
Nodes (3): bkm_fetch_otm_chain(), polygon_contracts_asof(), polygon_format_ticker()

### Community 87 - "get_all"
Cohesion: 0.32
Nodes (6): get_all(), _sumar(), _paginas(), test_get_all_follows_next_url(), test_get_all_marks_incomplete_when_a_page_fails(), test_get_all_truncated_by_max_pages()

## Knowledge Gaps
- **15 isolated node(s):** `pandas>=2.0`, `plotly>=5.18`, `scipy>=1.10`, `statsmodels>=0.14`, `Pull request merge order (stacked PRs #2 to #4 then this PR)` (+10 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 436 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **30 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Risk Profile Audit (configuration per investor profile)` connect `Risk Profile Audit (configuration per investor profile)` to `Workflow architecture (shared modules feed standalone optimizers)`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **What connects `pandas>=2.0`, `plotly>=5.18`, `scipy>=1.10` to the rest of the system?**
  _15 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `pytest` be split into smaller, more focused modules?**
  _Cohesion score 0.10384068278805121 - nodes in this community are weakly interconnected._
- **Why does `test_yfinance_batch_is_one_unadjusted_download()` connect `frames_from_yf_download` to `test_market_data.py`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Should `quadratic_utility_(seasonal_version).py` be split into smaller, more focused modules?**
  _Cohesion score 0.05701754385964912 - nodes in this community are weakly interconnected._
- **Why does `mfis_tail_decision()` connect `mfis_tail_decision` to `numpy`, `quadratic_utility_(seasonal_version).py`, `evaluar_historia_bkm`, `qu_metrics.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Should `bl_metrics.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06282051282051282 - nodes in this community are weakly interconnected._