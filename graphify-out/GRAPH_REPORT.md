# Graph Report - AM-PM-Architecture  (2026-10-12)

## Corpus Check
- 35 files · ~132,282 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .ini 1)

## Summary
- 1434 nodes · 3171 edges · 103 communities (72 shown, 31 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 70 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a74042a5`
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
- delta_cushion
- minimum_variance.py
- minimum_variance_(seasonal_version).py
- market_data.py
- test_market_cap_internacional.py
- pipeline_io.py
- test_ajuste_iv_tasa.py
- cache_get
- test_market_data.py
- math
- test_script_smoke.py
- numpy
- fit_ssvi
- pathlib
- test_universo_y_delta_estacional.py
- get_spot_history
- polygon_format_ticker
- ledoit_wolf_constant_correlation
- frames_from_yf_download
- risk_estimators.py
- Workflow architecture (shared modules feed standalone optimizers)
- test_mv_cola_y_delta.py
- _diag_ssvi
- Risk Profile Audit (configuration per investor profile)
- test_cycle2_fixes.py
- test_risk_profile.py
- _GetterFalso
- bkm_reconstruct_mfis_history
- fetch_option_aggs
- test_qu_metrics.py
- set_rate_limit
- mfik_cap_tenor
- test_tail_prune_loop.py
- normalize_currency
- align_prices_to_calendar
- Working with the graphify knowledge graph
- test_etf_floor_estacional.py
- descargar_precio
- _YahooFalso
- calcular_metricas_riesgo_cola
- mfis_tail_decision
- _RespuestaFalsa
- pandas
- black_litterman.py
- cache_set
- load_bl_input
- score_candidate_portfolios
- calls_per_minute_from_env
- average_abs_correlation
- test_polygon_client.py
- estimar_theta_esscher
- mincer_zarnowitz
- max_drawdown
- etfs_necesarios
- bootstrap_estacionario
- media_hac
- utilidad_mvsk_negativa
- covariance_min_history
- restricciones_factibles
- select_optimal_candidates
- gram_charlier_pdf_ratio
- _Limitador
- test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados
- entropy_pooling
- dispersion_weights
- horizon_from_months
- horizon_from_month_list
- qu_metrics.py
- winsorizar
- higher_moments_admissible
- Working with the graphify knowledge graph
- spot_series_for
- test_risk_estimators.py
- test_get_json_exhausts_retries_on_network_error
- estimate_bkm_history_calls
- portfolio_returns_skipna
- candidatos_reposicion
- os
- build_qp_constraints
- bkm_motivo_fallback
- frontier_lambda_grid
- build_qp_constraints
- bkm_motivo_fallback
- max_drawdown_from_returns
- polygon_contracts_asof
- shrink_mu_to_prior
- select_views
- summarize_yearly_mdd
- aplicar_limites_cartera
- _momento_pendiente
- momentos_ponderados
- optimizar_min_cvar
- calc_mdd
- primas_esscher
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
- `Reachable ETF floor and LP feasibility check` --semantically_similar_to--> `Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12)`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `lambda3/lambda4 derived from gamma (CRRA Taylor expansion)` --semantically_similar_to--> `BL lambda3/lambda4 closed form from gamma`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `test_currency_from_suffix()` --calls--> `currency_from_suffix()`  [EXTRACTED]
  tests/test_market_data.py → market_data.py
- `test_expiry_rank_prefers_50_over_15_for_a_30_day_target()` --calls--> `expiry_rank_columns()`  [EXTRACTED]
  tests/test_polygon_client.py → polygon_client.py
- `test_script_mapea_sufijo_y_region()` --calls--> `currency_from_suffix()`  [EXTRACTED]
  tests/test_universo_y_delta_estacional.py → market_data.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared estimation modules feeding the three optimizers** — polygon_client, risk_estimators, market_data, portfolio_constraints, qu_metrics, bl_metrics, pipeline_io, quadratic_utility, minimum_variance, black_litterman [EXTRACTED 1.00]
- **Options-implied tail risk pipeline (BKM, Q to P, Cornish-Fisher)** — readme_bkm, readme_q_to_p, readme_cornish_fisher, readme_co_moments, readme_ssvi_fit [INFERRED 0.85]
- **Risk-profile calibration (gamma ladder, CRRA lambdas, lambda-only aversion, pen_ret)** — docs_risk_profile_audit_gamma_ladder, docs_risk_profile_audit_crra_lambdas, docs_risk_profile_audit_lambda_only_risk_aversion, docs_risk_profile_audit_lambda_calibration [INFERRED 0.85]

## Communities (103 total, 31 thin omitted)

### Community 0 - "pytest"
Cohesion: 0.12
Nodes (27): crra_taylor_lambdas(), integration_strike_bounds(), market_delta(), variance_annual_to_horizon(), test_apply_vol_q_to_p_does_not_haircut_historical_vol(), test_calibrar_superficie_ignora_leaps_y_quotes_rotos(), test_clip_negligible_weights_drops_solver_dust(), test_crra_taylor_lambdas_match_profile_ladder() (+19 more)

### Community 1 - "test_pipeline_io.py"
Cohesion: 0.19
Nodes (6): _leer(), test_atomic_replace(), test_default_dir_and_env(), test_export_writes_latest_and_timestamped_copy(), test_weights_round_to_six_decimals_and_sum_to_one(), test_write_error_warns()

### Community 2 - "quadratic_utility_(seasonal_version).py"
Cohesion: 0.08
Nodes (22): armar_restricciones(), _asegurar_momentos_actuales(), bkm_compute_moments(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_iv_chain_to_prices(), bs_price(), clean_symbol_table() (+14 more)

### Community 3 - "bl_metrics.py"
Cohesion: 0.07
Nodes (21): apply_vol_q_to_p(), calibrar_superficie_ssvi(), _fecha_naive(), forward_por_paridad(), iv_vol_at_horizon(), mfiv_or_horizon_variance(), momentos_fallback(), seleccionar_vencimientos() (+13 more)

### Community 4 - "quadratic_utility.py"
Cohesion: 0.09
Nodes (17): _asegurar_momentos_actuales(), bkm_fetch_otm_chain(), bkm_iv_chain_to_prices(), bkm_seleccion_fecha(), bs_price(), clean_symbol_table(), fila_iv_vs_reciente(), _momento_actual_bkm() (+9 more)

### Community 5 - "polygon_client.py"
Cohesion: 0.11
Nodes (15): _avisar_403(), _avisar_sin_api_key(), _con_api_key(), _espera_reintento(), get_all(), get_json(), print_diagnostics(), _registrar() (+7 more)

### Community 6 - "test_etf_floor_refill.py"
Cohesion: 0.15
Nodes (9): relajar_banda_etf(), siguiente_reposicion(), test_relajar_banda_no_toca_una_banda_alcanzable(), test_relajar_banda_sube_el_techo_si_faltan_acciones(), test_script_chequea_factibilidad_antes_de_quadprog(), test_script_delta_min_es_global_015(), test_siguiente_reposicion_prioriza_etf_cuando_faltan(), test_siguiente_reposicion_sin_etf_coincide_con_el_indice_secuencial() (+1 more)

### Community 7 - "delta_cushion"
Cohesion: 0.11
Nodes (17): bs_call_delta_from_vol(), delta_cushion(), evaluar_delta_candidato(), filtro_delta_otm(), _finito(), otm_log_moneyness(), pasa_filtro_delta(), test_horizonte_cambia_la_moneyness_efectiva() (+9 more)

### Community 8 - "minimum_variance.py"
Cohesion: 0.11
Nodes (15): bkm_annual_vol(), bkm_compute_moments(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), bs_price() (+7 more)

### Community 9 - "minimum_variance_(seasonal_version).py"
Cohesion: 0.10
Nodes (17): bkm_annual_vol(), bkm_compute_moments(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), bs_price() (+9 more)

### Community 10 - "market_data.py"
Cohesion: 0.10
Nodes (17): _campo(), combinar_tickers(), _con_reintentos(), currency_from_suffix(), default_market_cap_cache_path(), es_ticker_formato_us(), _escribir_cache(), _leer_cache() (+9 more)

### Community 11 - "test_market_cap_internacional.py"
Cohesion: 0.11
Nodes (19): _llamar_caps(), _llamar_fx(), tabla_market_cap_texto(), _ordenar(), _proveedores(), cap_provider(), fx_provider(), test_cache_corrupta_no_rompe() (+11 more)

### Community 12 - "pipeline_io.py"
Cohesion: 0.21
Nodes (11): _date_or_none(), export_portfolio(), _export_portfolio(), _int_or_none(), _jsonify(), _metrics(), _normalize_weights(), _num_or_none() (+3 more)

### Community 13 - "test_ajuste_iv_tasa.py"
Cohesion: 0.07
Nodes (38): get_polygon_option_snapshot(), is_non_us_exchange(), get_polygon_option_snapshot(), is_non_us_exchange(), expiry_rank_columns(), is_us_ticker(), pares_call_put(), resumen_ajuste_iv() (+30 more)

### Community 14 - "cache_get"
Cohesion: 0.14
Nodes (11): cache_get(), bkm_clave_historia(), bkm_fechas_pendientes(), bkm_reconstruct_mfis_history(), _datos_con_precios(), evaluar_historia_bkm(), _evaluar_historia_bkm(), _fila() (+3 more)

### Community 15 - "test_market_data.py"
Cohesion: 0.12
Nodes (19): dedupe_share_classes(), drop_partial_last_week(), resolve_currencies(), resolve_execution_months(), _semanal(), test_currency_from_suffix(), test_dedupe_share_classes_keeps_the_configured_class(), test_drop_partial_last_week_empty_and_dataframe() (+11 more)

### Community 16 - "math"
Cohesion: 0.05
Nodes (47): beta_band_columns(), beta_coverage_additions(), _rango(), beta_range_reachable(), bs_call_delta(), build_weight_constraints(), clip_to_band(), prune_order() (+39 more)

### Community 17 - "test_script_smoke.py"
Cohesion: 0.22
Nodes (11): _alias_importados(), _asignaciones_de_modulo(), _correr_bl(), _nombres(), sombras_de_import(), test_bl_input_file_overrides_tickers_and_views(), test_bl_risk_profile_env_and_cli(), test_bl_universe_file_drops_default_views() (+3 more)

### Community 18 - "numpy"
Cohesion: 0.08
Nodes (26): clip_negligible_weights(), log_portfolio_return(), markowitz_clasico(), optimizar_mvsk(), relax_beta_band(), implied_variance_to_horizon(), nearest_psd(), portfolio_log_returns() (+18 more)

### Community 19 - "fit_ssvi"
Cohesion: 0.16
Nodes (14): fit_ssvi(), objetivo(), _params(), _penalty(), _relativos(), _sigmoid(), _grupos_vencimiento(), ssvi_total_variance() (+6 more)

### Community 21 - "test_universo_y_delta_estacional.py"
Cohesion: 0.23
Nodes (11): _descartados(), _formato_us_viejo(), _fuente(), _internacionales_del_script(), _literales(), test_bl_no_manda_internacionales_a_polygon(), test_conteo_de_colchon_separa_umbrales_y_aguanta_el_horizonte(), test_defaults_estacionales_del_colchon() (+3 more)

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

### Community 26 - "risk_estimators.py"
Cohesion: 0.07
Nodes (25): compute_marginal_cvar_contrib(), compute_marginal_cvar_contrib(), cornish_fisher_domain(), cornish_fisher_es_gradient(), cornish_fisher_moments(), cornish_fisher_params(), a_parametros(), residuo() (+17 more)

### Community 27 - "Workflow architecture (shared modules feed standalone optimizers)"
Cohesion: 0.14
Nodes (13): AM-PM Portfolio Construction Repository, Pull request merge order (stacked PRs #2 to #4 then this PR), Test suite (pytest, no network), numpy>=1.24, pandas>=2.0, plotly>=5.18, pytest>=7.0, quadprog>=0.1.11 (+5 more)

### Community 28 - "test_mv_cola_y_delta.py"
Cohesion: 0.20
Nodes (13): _bucle_de_cola(), _descartes(), _fuente(), _funcion(), test_conteo_estable_entre_horizontes(), test_conteos_por_umbral_conservador_moderado_agresivo(), test_defaults_del_filtro_delta_en_mv(), test_fallback_historico_activo_por_defecto() (+5 more)

### Community 30 - "Risk Profile Audit (configuration per investor profile)"
Cohesion: 0.07
Nodes (28): Asset Allocation (FICs) am_pm/profiles.py mandates, Risk Profile Audit (configuration per investor profile), Black-Litterman PERFILES (omega_scale, tau, gamma_ra), COL Portfolio Architecture (proposed profile bands, max Sharpe), QU OTM delta filter as annual IV cap, Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12), International ticker format filter and region caps, Lambda calibration with pen_ret (+20 more)

### Community 31 - "test_cycle2_fixes.py"
Cohesion: 0.08
Nodes (21): resolve_risk_free_rate(), _clave_cap(), mfis_max_minutes_from_env(), orden_prioridad_mfis(), clave(), plan_bkm_history_budget(), texto_delta_shrinkage(), _Resp (+13 more)

### Community 32 - "test_risk_profile.py"
Cohesion: 0.21
Nodes (10): _cli_risk_profile(), resolve_risk_profile(), _literales(), _presets(), test_el_perfil_de_qu_y_mv_es_una_banda_de_beta(), test_preset_agresivo_no_cambia_los_literales(), test_presets_de_mv_y_qu_coinciden_con_la_auditoria(), test_resolve_default_si_no_hay_env_ni_cli() (+2 more)

### Community 33 - "_GetterFalso"
Cohesion: 0.12
Nodes (15): default_ff_cache_dir(), _escribir_atomico(), fetch_fama_french(), parse_fama_french_zip(), _ff(), _GetterFalso, _Resp, test_ff_cache_corrupta_cuenta_como_failed_y_un_zip_invalido_no_pisa_la_cache() (+7 more)

### Community 34 - "bkm_reconstruct_mfis_history"
Cohesion: 0.13
Nodes (10): bkm_clave_historia(), bkm_fechas_pendientes(), bkm_reconstruct_mfis_history(), _datos_con_precios(), evaluar_historia_bkm(), _fila(), _fila_bkm(), _precargar_spots_bkm() (+2 more)

### Community 35 - "fetch_option_aggs"
Cohesion: 0.15
Nodes (9): fetch_option_aggs(), close_near_from_bars(), contract_agg_ranges(), bkm_precios_en_rango(), polygon_contract_close_near(), bkm_precios_en_rango(), polygon_contract_close_near(), _barra() (+1 more)

### Community 36 - "test_qu_metrics.py"
Cohesion: 0.11
Nodes (19): history_window(), pool_sin_no_procesados_mfis(), scale_option_deltas(), select_historical_otm(), _contratos(), _formato_us_viejo(), test_combinar_tickers_conserva_sufijos_que_el_filtro_us_tiraba(), test_history_window_includes_current_year_through_last_full_month() (+11 more)

### Community 37 - "set_rate_limit"
Cohesion: 0.17
Nodes (6): estimate_minutes(), set_rate_limit(), polygon_aislado(), entorno_aislado(), test_limiter_spaces_calls(), test_set_rate_limit_updates_limiter_and_estimate()

### Community 38 - "mfik_cap_tenor"
Cohesion: 0.20
Nodes (6): mfiv_vs_atm(), _momentos_sector(), mfik_cap(), mfik_cap_tenor(), test_mfik_cap_rises_with_chain_depth(), test_mfik_cap_tenor_loosens_a_short_chain()

### Community 39 - "test_tail_prune_loop.py"
Cohesion: 0.26
Nodes (6): _bucle_de_poda(), _correr(), test_block_cut_is_skipped_when_it_leaves_too_few_names(), test_min_weight_keeps_capped_defensives(), test_names_below_threshold_are_cut_in_one_step(), test_prune_loop_survives_floor_weights()

### Community 40 - "normalize_currency"
Cohesion: 0.17
Nodes (8): normalize_currency(), price_scale_factor(), download_period_returns(), get_currency_for_ticker(), download_period_returns(), get_currency_for_ticker(), test_normalize_currency(), test_price_scale_factor()

### Community 41 - "align_prices_to_calendar"
Cohesion: 0.19
Nodes (11): align_prices_to_calendar(), align_daily_panel(), _bdays(), _precios_dos_mercados(), test_align_drops_low_coverage_ticker(), test_align_fills_local_holiday_instead_of_dropping_row(), test_align_long_gap_not_filled_beyond_limit(), test_align_reindexes_to_calendar_and_keeps_offcalendar_level() (+3 more)

### Community 42 - "Working with the graphify knowledge graph"
Cohesion: 0.33
Nodes (5): Freshness check, Git hygiene, Navigating, Verify before asserting, Working with the graphify knowledge graph

### Community 43 - "test_etf_floor_estacional.py"
Cohesion: 0.27
Nodes (6): _bloque_restricciones(), _correr_restricciones(), test_banda_que_ya_cumplia_no_cambia(), test_con_el_cuarto_etf_el_conservador_resuelve_sin_relajar(), test_sin_cuarto_etf_la_banda_se_relaja_y_quadprog_resuelve(), test_sin_relajar_falla_con_mensaje_claro_y_no_con_quadprog()

### Community 44 - "descargar_precio"
Cohesion: 0.22
Nodes (5): asegurar_fx(), descargar_fx_moneda(), descargar_precio(), _par_fx(), convertir_serie_a_usd()

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
Cohesion: 0.10
Nodes (14): elegir_spot_momentos(), calibrar_ssvi_ticker(), momentos_realizados_rolling(), parse_chain(), _spot_bkm(), frontier_curve(), portfolio_mu_final_metrics(), seasonal_vol_ratio() (+6 more)

### Community 50 - "black_litterman.py"
Cohesion: 0.17
Nodes (9): bs_price(), calcular_bkm_moments(), construir_restricciones(), otm_price_ssvi(), phi_powerlaw(), port_ret_row(), _sanear_momento_fisico(), sigma_desde_ssvi() (+1 more)

### Community 51 - "cache_set"
Cohesion: 0.20
Nodes (7): cache_permitida(), cache_set(), es_snapshot(), fechas_en_clave(), _ruta_cache(), test_cache_never_stores_current_date_or_snapshot(), test_get_json_serves_from_cache_without_key_or_network()

### Community 52 - "load_bl_input"
Cohesion: 0.31
Nodes (8): load_bl_input(), _parse_views(), _validate_bl_input(), _escribir(), test_bl_input_invalid_or_missing(), test_bl_input_universe_uses_only_tickers(), test_bl_input_views_shape(), test_empty_views_list_is_explicit()

### Community 53 - "score_candidate_portfolios"
Cohesion: 0.17
Nodes (8): comparison_lambdas(), lambda_monthly_from_annual(), score_candidate_portfolios(), utility_terms(), test_lambda_monthly_from_annual_scales_by_twelve_and_is_opt_in(), test_lambda_scores_use_the_reference_lambda_and_mu_final(), test_pen_ret_is_nan_when_return_is_not_positive(), test_utility_terms_show_when_the_penalty_binds()

### Community 54 - "calls_per_minute_from_env"
Cohesion: 0.22
Nodes (7): calls_per_minute_from_env(), _parse_calls_per_min(), test_calls_per_min_alias_y_sin_tope(), test_calls_per_minute_acepta_el_alias_viejo(), test_calls_per_minute_lee_el_nombre_largo(), test_calls_per_minute_sin_env_usa_el_default(), test_parse_calls_per_min()

### Community 55 - "average_abs_correlation"
Cohesion: 0.33
Nodes (5): average_abs_correlation(), _corr_abc(), test_average_abs_correlation_ignores_sign_and_order(), test_average_abs_correlation_uses_full_row(), test_old_alphabetical_grouping_drops_last_ticker()

### Community 56 - "test_polygon_client.py"
Cohesion: 0.10
Nodes (22): default_cache_dir(), es_transitorio(), fetch_otm_chain(), test_fetch_otm_chain_empty_paths_carry_empty_pairs(), _contrato(), _paginas(), _snapshot_grabado(), test_default_cache_dir_lives_outside_the_repo() (+14 more)

### Community 57 - "estimar_theta_esscher"
Cohesion: 0.50
Nodes (3): cumulantes_Q_desde_P(), estimar_theta_esscher(), objetivo()

### Community 59 - "max_drawdown"
Cohesion: 0.25
Nodes (7): mdd_from_log_returns(), max_drawdown(), test_mdd_log_matches_exp_cumsum_not_simple_compounding(), test_max_drawdown_log_and_simple_differ(), test_max_drawdown_log_returns_known_path(), test_max_drawdown_monotone_is_zero_and_short_series_is_nan(), test_max_drawdown_simple_returns_known_path()

### Community 60 - "etfs_necesarios"
Cohesion: 0.22
Nodes (6): diagnostico_banda_etf(), etfs_necesarios(), test_diagnostico_explica_el_piso_de_etf(), test_diagnostico_vacio_si_los_conteos_alcanzan(), test_etfs_necesarios(), test_etfs_necesarios_rechaza_max_weight_invalido()

### Community 64 - "covariance_min_history"
Cohesion: 0.33
Nodes (4): columns_with_min_obs(), covariance_min_history(), test_columns_with_min_obs_keeps_long_history(), test_covariance_min_history_uses_each_series_full_sample()

### Community 65 - "restricciones_factibles"
Cohesion: 0.36
Nodes (8): restricciones_factibles(), test_caso_conservador_tal_como_llegaba_es_infactible_para_quadprog(), _quadprog(), _restricciones(), test_caso_conservador_es_infactible_y_quadprog_lo_confirma(), test_con_cuatro_etf_el_conservador_es_factible(), test_factibilidad_considera_el_tope_regional(), test_relajar_banda_lleva_el_piso_a_lo_alcanzable_y_queda_factible()

### Community 66 - "select_optimal_candidates"
Cohesion: 0.25
Nodes (5): beta_band_text(), armar_restricciones(), qubo_energy(), select_candidates_qubo(), select_optimal_candidates()

### Community 67 - "gram_charlier_pdf_ratio"
Cohesion: 0.33
Nodes (4): gram_charlier_pdf_ratio(), he3(), he4(), posterior_gram_charlier()

### Community 69 - "test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados"
Cohesion: 0.18
Nodes (9): completar_etfs(), contar_etfs(), reserva_etf(), test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados(), test_completar_etfs_agrega_solo_lo_necesario_y_en_orden(), test_completar_etfs_devuelve_lo_que_haya_si_no_alcanza(), test_contar_etfs_sin_duplicados(), test_reserva_etf_toma_los_que_faltan_en_orden_de_ranking() (+1 more)

### Community 71 - "dispersion_weights"
Cohesion: 0.25
Nodes (6): dispersion_usable(), dispersion_weights(), test_dispersion_cap_share_is_the_basket_over_known_spy_caps(), test_dispersion_weights_cap_weighted_spy_names_with_iv(), test_dispersion_weights_equal_when_a_cap_is_missing(), test_dispersion_weights_insufficient_basket()

### Community 72 - "horizon_from_months"
Cohesion: 0.40
Nodes (3): _add_months(), horizon_from_months(), test_horizon_from_months()

### Community 74 - "qu_metrics.py"
Cohesion: 0.09
Nodes (15): annualize_monthly(), clip_implied_correlation(), mfis_check_deadline(), mfis_deadline(), MfisTiempoAgotado, mfiv_annual_vol(), sector_implied_ready(), stitch_covariance() (+7 more)

### Community 76 - "higher_moments_admissible"
Cohesion: 0.25
Nodes (5): momentos_cola_historicos(), momentos_cola_historicos(), bkm_compute_moments(), higher_moments_admissible(), test_higher_moments_admissible_pearson()

### Community 77 - "Working with the graphify knowledge graph"
Cohesion: 0.33
Nodes (5): Freshness check, Git hygiene, Navigating, Verify before asserting, Working with the graphify knowledge graph

### Community 78 - "spot_series_for"
Cohesion: 0.33
Nodes (3): spot_series_for(), _spot_series_bkm(), _spot_series_bkm()

### Community 79 - "test_risk_estimators.py"
Cohesion: 0.09
Nodes (24): annualize(), market_beta(), scale_moments(), _lw_constant_correlation_referencia(), _mercado_y_activos(), panel(), retornos(), retornos_shock_covid() (+16 more)

### Community 80 - "test_get_json_exhausts_retries_on_network_error"
Cohesion: 0.40
Nodes (3): n_fallos_transitorios(), test_get_json_exhausts_retries_on_network_error(), test_n_fallos_transitorios_excludes_missing_key()

### Community 82 - "portfolio_returns_skipna"
Cohesion: 0.40
Nodes (4): portfolio_returns_skipna(), portfolio_returns_series(), portfolio_returns_series(), test_portfolio_returns_skipna_does_not_drop_the_month()

### Community 83 - "candidatos_reposicion"
Cohesion: 0.40
Nodes (3): candidatos_reposicion(), test_reposicion_aplica_el_filtro_iv_a_quien_nunca_paso_por_el(), test_reposicion_bkm_no_trae_de_vuelta_a_mchi()

## Knowledge Gaps
- **23 isolated node(s):** `Freshness check`, `Git hygiene`, `Navigating`, `Verify before asserting`, `Freshness check` (+18 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 454 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `_YahooFalso` connect `_YahooFalso` to `test_script_smoke.py`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **What connects `Freshness check`, `Git hygiene`, `Navigating` to the rest of the system?**
  _23 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `pytest` be split into smaller, more focused modules?**
  _Cohesion score 0.11931818181818182 - nodes in this community are weakly interconnected._
- **Why does `test_yfinance_single_uses_history_when_download_is_empty()` connect `frames_from_yf_download` to `test_market_data.py`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Should `quadratic_utility_(seasonal_version).py` be split into smaller, more focused modules?**
  _Cohesion score 0.08108108108108109 - nodes in this community are weakly interconnected._
- **Why does `posterior_gram_charlier()` connect `gram_charlier_pdf_ratio` to `black_litterman.py`, `numpy`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Should `bl_metrics.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06685633001422475 - nodes in this community are weakly interconnected._