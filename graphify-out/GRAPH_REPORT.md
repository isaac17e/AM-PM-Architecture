# Graph Report - AM-PM-Architecture  (2026-10-13)

## Corpus Check
- 33 files · ~130,897 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 3, .ini 1)

## Summary
- 1415 nodes · 3150 edges · 92 communities (67 shown, 25 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 70 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `544a3636`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- iv_vol_at_horizon
- test_pipeline_io.py
- quadratic_utility_(seasonal_version).py
- test_bl_metrics.py
- quadratic_utility.py
- polygon_client.py
- cache_get
- qu_metrics.py
- minimum_variance.py
- minimum_variance_(seasonal_version).py
- market_data.py
- test_market_cap_internacional.py
- pipeline_io.py
- to_years
- test_qu_horizonte.py
- test_market_data.py
- test_portfolio_constraints.py
- test_script_smoke.py
- numpy
- fit_ssvi
- pathlib
- test_universo_y_delta_estacional.py
- get_spot_history
- test_ajuste_iv_tasa.py
- risk_estimators.py
- frames_from_yf_download
- cornish_fisher_tail
- Workflow architecture (shared modules feed standalone optimizers)
- test_mv_cola_y_delta.py
- cache_set
- Risk Profile Audit (configuration per investor profile)
- test_cycle2_fixes.py
- test_risk_profile.py
- _GetterFalso
- _RespuestaFalsa
- fetch_option_aggs
- test_qu_metrics.py
- set_rate_limit
- _momentos_sector
- test_tail_prune_loop.py
- normalize_currency
- bkm_get_current_moments
- load_bl_input
- calls_per_minute_from_env
- descargar_precio
- _YahooFalso
- calcular_metricas_riesgo_cola
- mfis_tail_decision
- test_polygon_client.py
- pandas
- black_litterman.py
- _market_cap_yf
- dispersion_weights
- score_candidate_portfolios
- horizon_from_months
- resumen_ajuste_iv
- fetch_otm_chain
- estimar_theta_esscher
- mincer_zarnowitz
- os
- select_historical_otm
- bootstrap_estacionario
- elegir_spot_momentos
- utilidad_mvsk_negativa
- covariance_min_history
- test_etf_floor_refill.py
- test_get_json_exhausts_retries_on_network_error
- posterior_gram_charlier
- _Limitador
- annualize_monthly
- entropy_pooling
- clip_implied_correlation
- _diag_ssvi
- horizon_from_month_list
- mfis_check_deadline
- summarize_yearly_mdd
- higher_moments_admissible
- optimizar_min_cvar
- default_cache_dir
- pytest
- _sanear_momento_fisico
- estimate_bkm_history_calls
- portfolio_returns_skipna
- bkm_motivo_fallback
- frontier_lambda_grid
- build_qp_constraints
- bkm_motivo_fallback
- dedupe_share_classes
- download_ticker_data
- select_views
- mfiv_annual_vol
- implied_variance_to_horizon

## God Nodes (most connected - your core abstractions)
1. `get_json()` - 27 edges
2. `to_years()` - 25 edges
3. `fetch_otm_chain()` - 19 edges
4. `calibrate_iv_carry()` - 19 edges
5. `fit_ssvi()` - 18 edges
6. `es_transitorio()` - 18 edges
7. `Risk Profile Audit (configuration per investor profile)` - 18 edges
8. `calibrar_superficie_ssvi()` - 17 edges
9. `polygon_format_ticker()` - 15 edges
10. `get_all()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Reachable ETF floor and LP feasibility check` --semantically_similar_to--> `Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12)`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `lambda3/lambda4 derived from gamma (CRRA Taylor expansion)` --semantically_similar_to--> `BL lambda3/lambda4 closed form from gamma`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `test_polygon_format_ticker_none()` --calls--> `polygon_format_ticker()`  [EXTRACTED]
  tests/test_polygon_client.py → polygon_client.py
- `test_expiry_rank_prefers_50_over_15_for_a_30_day_target()` --calls--> `expiry_rank_columns()`  [EXTRACTED]
  tests/test_polygon_client.py → polygon_client.py
- `test_bs_price_matches_closed_form_and_parity()` --calls--> `bs_price()`  [EXTRACTED]
  tests/test_ajuste_iv_tasa.py → risk_estimators.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared estimation modules feeding the three optimizers** — polygon_client, risk_estimators, market_data, portfolio_constraints, qu_metrics, bl_metrics, pipeline_io, quadratic_utility, minimum_variance, black_litterman [EXTRACTED 1.00]
- **Options-implied tail risk pipeline (BKM, Q to P, Cornish-Fisher)** — readme_bkm, readme_q_to_p, readme_cornish_fisher, readme_co_moments, readme_ssvi_fit [INFERRED 0.85]
- **Risk-profile calibration (gamma ladder, CRRA lambdas, lambda-only aversion, pen_ret)** — docs_risk_profile_audit_gamma_ladder, docs_risk_profile_audit_crra_lambdas, docs_risk_profile_audit_lambda_only_risk_aversion, docs_risk_profile_audit_lambda_calibration [INFERRED 0.85]

## Communities (92 total, 25 thin omitted)

### Community 0 - "iv_vol_at_horizon"
Cohesion: 0.33
Nodes (4): iv_vol_at_horizon(), vol_annual_to_horizon(), test_ssvi_and_hist_fallback_share_horizon_units(), test_vol_annual_scales_with_sqrt_horizon()

### Community 1 - "test_pipeline_io.py"
Cohesion: 0.19
Nodes (6): _leer(), test_atomic_replace(), test_default_dir_and_env(), test_export_writes_latest_and_timestamped_copy(), test_weights_round_to_six_decimals_and_sum_to_one(), test_write_error_warns()

### Community 2 - "quadratic_utility_(seasonal_version).py"
Cohesion: 0.07
Nodes (25): armar_restricciones(), _asegurar_momentos_actuales(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_iv_chain_to_prices(), bkm_seleccion_fecha(), bs_price(), clean_symbol_table() (+17 more)

### Community 3 - "test_bl_metrics.py"
Cohesion: 0.06
Nodes (37): calibrar_superficie_ssvi(), crra_taylor_lambdas(), _fecha_naive(), forward_por_paridad(), market_delta(), mfiv_vs_atm(), momentos_fallback(), seleccionar_vencimientos() (+29 more)

### Community 4 - "quadratic_utility.py"
Cohesion: 0.06
Nodes (26): bkm_clave_historia(), bkm_fechas_pendientes(), bkm_reconstruct_mfis_history(), bkm_seleccion_fecha(), clean_symbol_table(), _datos_con_precios(), evaluar_historia_bkm(), _evaluar_historia_bkm() (+18 more)

### Community 5 - "polygon_client.py"
Cohesion: 0.11
Nodes (14): _avisar_403(), _avisar_sin_api_key(), _con_api_key(), _espera_reintento(), get_json(), print_diagnostics(), _registrar(), _retry_after() (+6 more)

### Community 6 - "cache_get"
Cohesion: 0.12
Nodes (12): spot_series_for(), cache_get(), bkm_clave_historia(), bkm_fechas_pendientes(), bkm_reconstruct_mfis_history(), _datos_con_precios(), evaluar_historia_bkm(), _fila() (+4 more)

### Community 7 - "qu_metrics.py"
Cohesion: 0.13
Nodes (19): bs_call_delta_from_vol(), delta_cushion(), evaluar_delta_candidato(), filtro_delta_otm(), _finito(), mfis_max_minutes_from_env(), otm_log_moneyness(), pasa_filtro_delta() (+11 more)

### Community 8 - "minimum_variance.py"
Cohesion: 0.13
Nodes (12): bkm_annual_vol(), bkm_compute_moments(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), clean_symbol_table(), constraints_feasible() (+4 more)

### Community 9 - "minimum_variance_(seasonal_version).py"
Cohesion: 0.12
Nodes (10): build_qp_constraints(), clean_symbol_table(), constraints_feasible(), download_ticker_data(), extract_metrics(), get_atm_iv_safe(), get_currency_for_ticker(), max_drawdown_from_returns() (+2 more)

### Community 10 - "market_data.py"
Cohesion: 0.07
Nodes (23): combinar_tickers(), _con_reintentos(), convertir_serie_a_usd(), currency_from_suffix(), default_ff_cache_dir(), default_market_cap_cache_path(), es_ticker_formato_us(), _escribir_atomico() (+15 more)

### Community 11 - "test_market_cap_internacional.py"
Cohesion: 0.12
Nodes (18): _llamar_caps(), _llamar_fx(), tabla_market_cap_texto(), _ordenar(), _proveedores(), cap_provider(), fx_provider(), test_cache_corrupta_no_rompe() (+10 more)

### Community 12 - "pipeline_io.py"
Cohesion: 0.21
Nodes (11): _date_or_none(), export_portfolio(), _export_portfolio(), _int_or_none(), _jsonify(), _metrics(), _normalize_weights(), _num_or_none() (+3 more)

### Community 13 - "to_years"
Cohesion: 0.12
Nodes (22): polygon_fetch_chain(), get_polygon_option_snapshot(), get_polygon_option_snapshot(), expiry_rank_columns(), get_all(), pares_call_put(), polygon_format_ticker(), polygon_get_atm_option() (+14 more)

### Community 14 - "test_qu_horizonte.py"
Cohesion: 0.16
Nodes (15): cornish_fisher_at_horizon(), qp_inputs_at_horizon(), var_cvar_cornish_fisher(), _pesos(), _restricciones(), test_cf_gaussiano_escala_con_raiz_de_h(), test_cf_h1_es_el_var_mensual_de_antes(), test_cf_h2_usa_scale_moments() (+7 more)

### Community 15 - "test_market_data.py"
Cohesion: 0.10
Nodes (27): align_prices_to_calendar(), drop_partial_last_week(), resolve_currencies(), resolve_execution_months(), align_daily_panel(), _bdays(), _precios_dos_mercados(), _semanal() (+19 more)

### Community 16 - "test_portfolio_constraints.py"
Cohesion: 0.06
Nodes (40): markowitz_clasico(), beta_band_columns(), beta_band_text(), beta_coverage_additions(), _rango(), beta_range_reachable(), bs_call_delta(), build_weight_constraints() (+32 more)

### Community 17 - "test_script_smoke.py"
Cohesion: 0.22
Nodes (11): _alias_importados(), _asignaciones_de_modulo(), _correr_bl(), _nombres(), sombras_de_import(), test_bl_input_file_overrides_tickers_and_views(), test_bl_risk_profile_env_and_cli(), test_bl_universe_file_drops_default_views() (+3 more)

### Community 18 - "numpy"
Cohesion: 0.08
Nodes (26): apply_vol_q_to_p(), clip_negligible_weights(), integration_strike_bounds(), optimizar_mvsk(), nearest_psd(), portfolio_log_returns(), portfolio_moments(), q_to_p_vol() (+18 more)

### Community 19 - "fit_ssvi"
Cohesion: 0.16
Nodes (14): fit_ssvi(), objetivo(), _params(), _penalty(), _relativos(), _sigmoid(), _grupos_vencimiento(), ssvi_total_variance() (+6 more)

### Community 21 - "test_universo_y_delta_estacional.py"
Cohesion: 0.18
Nodes (12): _descartados(), _formato_us_viejo(), _fuente(), _internacionales_del_script(), _literales(), test_bl_no_manda_internacionales_a_polygon(), test_conteo_de_colchon_separa_umbrales_y_aguanta_el_horizonte(), test_conteo_del_filtro_estacional_sobre_universo_sintetico() (+4 more)

### Community 22 - "get_spot_history"
Cohesion: 0.13
Nodes (15): get_spot_history(), _retry_spot_single(), _usable_spot(), _cierres(), test_get_spot_history_downloads_the_batch_once_and_workers_only_read(), batch(), single(), test_get_spot_history_falls_through_to_the_next_provider() (+7 more)

### Community 23 - "test_ajuste_iv_tasa.py"
Cohesion: 0.32
Nodes (10): _contrato(), _fuente(), _funcion(), test_atm_snapshot_fetches_both_sides_and_adjusts_iv(), test_bs_price_matches_closed_form_and_parity(), test_calibrate_iv_carry_without_pairs_keeps_script_rate(), test_chain_to_prices_uses_calibrated_carry(), test_current_moments_calibrate_before_pricing() (+2 more)

### Community 24 - "risk_estimators.py"
Cohesion: 0.12
Nodes (15): average_correlation(), cov_ewma_shrunk(), effective_sample_size(), ewma_cov(), ewma_weights(), ledoit_wolf_constant_correlation(), martin_wagner_excess_return(), scale_cov() (+7 more)

### Community 25 - "frames_from_yf_download"
Cohesion: 0.13
Nodes (8): default_spot_providers(), frames_from_yf_download(), yfinance_spot_batch(), yfinance_spot_single(), test_frames_from_yf_download_reads_both_multiindex_orders(), test_yfinance_batch_is_one_unadjusted_download(), download(), test_yfinance_single_uses_history_when_download_is_empty()

### Community 26 - "cornish_fisher_tail"
Cohesion: 0.10
Nodes (19): compute_marginal_cvar_contrib(), compute_marginal_cvar_contrib(), cornish_fisher_domain(), cornish_fisher_es_gradient(), cornish_fisher_moments(), cornish_fisher_params(), a_parametros(), residuo() (+11 more)

### Community 27 - "Workflow architecture (shared modules feed standalone optimizers)"
Cohesion: 0.14
Nodes (13): AM-PM Portfolio Construction Repository, Pull request merge order (stacked PRs #2 to #4 then this PR), Test suite (pytest, no network), numpy>=1.24, pandas>=2.0, plotly>=5.18, pytest>=7.0, quadprog>=0.1.11 (+5 more)

### Community 28 - "test_mv_cola_y_delta.py"
Cohesion: 0.22
Nodes (13): _bucle_de_cola(), _descartes(), _fuente(), _funcion(), test_conteo_estable_entre_horizontes(), test_conteos_por_umbral_conservador_moderado_agresivo(), test_defaults_del_filtro_delta_en_mv(), test_fallback_historico_activo_por_defecto() (+5 more)

### Community 29 - "cache_set"
Cohesion: 0.20
Nodes (7): cache_permitida(), cache_set(), es_snapshot(), fechas_en_clave(), _ruta_cache(), test_cache_never_stores_current_date_or_snapshot(), test_get_json_serves_from_cache_without_key_or_network()

### Community 30 - "Risk Profile Audit (configuration per investor profile)"
Cohesion: 0.07
Nodes (28): Asset Allocation (FICs) am_pm/profiles.py mandates, Risk Profile Audit (configuration per investor profile), Black-Litterman PERFILES (omega_scale, tau, gamma_ra), COL Portfolio Architecture (proposed profile bands, max Sharpe), QU OTM delta filter as annual IV cap, Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12), International ticker format filter and region caps, Lambda calibration with pen_ret (+20 more)

### Community 31 - "test_cycle2_fixes.py"
Cohesion: 0.08
Nodes (20): resolve_risk_free_rate(), _clave_cap(), orden_prioridad_mfis(), clave(), plan_bkm_history_budget(), texto_delta_shrinkage(), polygon_aislado(), _Resp (+12 more)

### Community 32 - "test_risk_profile.py"
Cohesion: 0.21
Nodes (10): _cli_risk_profile(), resolve_risk_profile(), _literales(), _presets(), test_el_perfil_de_qu_y_mv_es_una_banda_de_beta(), test_preset_agresivo_no_cambia_los_literales(), test_presets_de_mv_y_qu_coinciden_con_la_auditoria(), test_resolve_default_si_no_hay_env_ni_cli() (+2 more)

### Community 33 - "_GetterFalso"
Cohesion: 0.23
Nodes (9): _ff(), _GetterFalso, _Resp, test_ff_cache_corrupta_cuenta_como_failed_y_un_zip_invalido_no_pisa_la_cache(), test_ff_descarga_ok_usa_https_timeout_y_guarda_cache(), test_ff_reintenta_con_backoff_y_luego_baja(), test_ff_si_falla_usa_la_cache_con_su_edad(), test_ff_sin_red_ni_cache_es_failed_con_aviso_fuerte() (+1 more)

### Community 34 - "_RespuestaFalsa"
Cohesion: 0.22
Nodes (9): _RespuestaFalsa, test_get_json_403_is_not_retried_and_names_the_plan(), _get(), test_get_json_jitter_on_5xx_and_retry_after_wins(), test_get_json_non_transient_error_is_not_retried_nor_cached(), _get(), test_get_json_retries_on_429_respecting_retry_after(), test_get_json_strips_key_from_cache_key_and_sends_it() (+1 more)

### Community 35 - "fetch_option_aggs"
Cohesion: 0.19
Nodes (7): fetch_option_aggs(), close_near_from_bars(), contract_agg_ranges(), bkm_precios_en_rango(), polygon_contract_close_near(), bkm_precios_en_rango(), polygon_contract_close_near()

### Community 36 - "test_qu_metrics.py"
Cohesion: 0.08
Nodes (25): average_abs_correlation(), history_window(), pool_sin_no_procesados_mfis(), scale_option_deltas(), sector_implied_ready(), stitch_covariance(), _barra(), _corr_abc() (+17 more)

### Community 37 - "set_rate_limit"
Cohesion: 0.20
Nodes (5): estimate_minutes(), set_rate_limit(), entorno_aislado(), test_limiter_spaces_calls(), test_set_rate_limit_updates_limiter_and_estimate()

### Community 38 - "_momentos_sector"
Cohesion: 0.29
Nodes (6): calcular_bkm_moments(), _momentos_sector(), otm_price_ssvi(), phi_powerlaw(), sigma_desde_ssvi(), ssvi_w()

### Community 39 - "test_tail_prune_loop.py"
Cohesion: 0.26
Nodes (6): _bucle_de_poda(), _correr(), test_block_cut_is_skipped_when_it_leaves_too_few_names(), test_min_weight_keeps_capped_defensives(), test_names_below_threshold_are_cut_in_one_step(), test_prune_loop_survives_floor_weights()

### Community 40 - "normalize_currency"
Cohesion: 0.17
Nodes (8): normalize_currency(), price_scale_factor(), download_period_returns(), get_currency_for_ticker(), download_period_returns(), get_currency_for_ticker(), test_normalize_currency(), test_price_scale_factor()

### Community 41 - "bkm_get_current_moments"
Cohesion: 0.24
Nodes (8): bkm_annual_vol(), bkm_compute_moments(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), bs_price(), get_spot_safe()

### Community 42 - "load_bl_input"
Cohesion: 0.31
Nodes (8): load_bl_input(), _parse_views(), _validate_bl_input(), _escribir(), test_bl_input_invalid_or_missing(), test_bl_input_universe_uses_only_tickers(), test_bl_input_views_shape(), test_empty_views_list_is_explicit()

### Community 43 - "calls_per_minute_from_env"
Cohesion: 0.22
Nodes (7): calls_per_minute_from_env(), _parse_calls_per_min(), test_calls_per_min_alias_y_sin_tope(), test_calls_per_minute_acepta_el_alias_viejo(), test_calls_per_minute_lee_el_nombre_largo(), test_calls_per_minute_sin_env_usa_el_default(), test_parse_calls_per_min()

### Community 44 - "descargar_precio"
Cohesion: 0.24
Nodes (4): asegurar_fx(), descargar_fx_moneda(), descargar_precio(), _par_fx()

### Community 46 - "calcular_metricas_riesgo_cola"
Cohesion: 0.29
Nodes (4): calcular_metricas_riesgo_cola(), _pesos_normalizados(), var_cvar_cornish_fisher(), var_cvar_historico()

### Community 47 - "mfis_tail_decision"
Cohesion: 0.29
Nodes (4): mfis_tail_decision(), test_mfis_tail_decision(), test_mfis_tail_default_upper_matches_old_inequality(), test_mfis_tail_rejects_unknown_mode()

### Community 48 - "test_polygon_client.py"
Cohesion: 0.12
Nodes (17): _contrato(), _paginas(), _snapshot_grabado(), test_es_transitorio_false(), test_es_transitorio_true(), test_expiry_rank_prefers_50_over_15_for_a_30_day_target(), test_fetch_otm_chain_falls_back_when_nothing_reaches_min_dte(), test_fetch_otm_chain_formats_class_share_and_skips_non_us() (+9 more)

### Community 49 - "pandas"
Cohesion: 0.14
Nodes (12): log_portfolio_return(), calibrar_ssvi_ticker(), momentos_realizados_rolling(), parse_chain(), frontier_curve(), portfolio_mu_final_metrics(), seasonal_vol_ratio(), test_log_portfolio_return_is_not_the_weighted_sum_of_logs() (+4 more)

### Community 50 - "black_litterman.py"
Cohesion: 0.10
Nodes (8): aplicar_limites_cartera(), construir_restricciones(), _momento_pendiente(), momentos_ponderados(), port_ret_row(), primas_esscher(), _retorno_min_factible(), winsorizar()

### Community 51 - "_market_cap_yf"
Cohesion: 0.18
Nodes (6): _campo(), _market_cap_yf(), yfinance_market_caps(), _uno(), test_fast_info_en_peniques_se_lleva_a_libras(), _Ticker

### Community 52 - "dispersion_weights"
Cohesion: 0.25
Nodes (6): dispersion_usable(), dispersion_weights(), test_dispersion_cap_share_is_the_basket_over_known_spy_caps(), test_dispersion_weights_cap_weighted_spy_names_with_iv(), test_dispersion_weights_equal_when_a_cap_is_missing(), test_dispersion_weights_insufficient_basket()

### Community 53 - "score_candidate_portfolios"
Cohesion: 0.17
Nodes (8): comparison_lambdas(), lambda_monthly_from_annual(), score_candidate_portfolios(), utility_terms(), test_lambda_monthly_from_annual_scales_by_twelve_and_is_opt_in(), test_lambda_scores_use_the_reference_lambda_and_mu_final(), test_pen_ret_is_nan_when_return_is_not_positive(), test_utility_terms_show_when_the_penalty_binds()

### Community 54 - "horizon_from_months"
Cohesion: 0.40
Nodes (3): _add_months(), horizon_from_months(), test_horizon_from_months()

### Community 55 - "resumen_ajuste_iv"
Cohesion: 0.33
Nodes (4): resumen_ajuste_iv(), texto_ajuste_iv(), test_resumen_ajuste_iv_counts_only_queried_chains(), test_texto_ajuste_iv_without_pairs()

### Community 56 - "fetch_otm_chain"
Cohesion: 0.10
Nodes (15): bkm_fetch_otm_chain(), bkm_fetch_otm_chain(), is_non_us_exchange(), es_transitorio(), fetch_otm_chain(), is_us_ticker(), _asegurar_momentos_actuales(), bkm_fetch_otm_chain() (+7 more)

### Community 57 - "estimar_theta_esscher"
Cohesion: 0.50
Nodes (3): cumulantes_Q_desde_P(), estimar_theta_esscher(), objetivo()

### Community 58 - "mincer_zarnowitz"
Cohesion: 0.20
Nodes (4): media_hac(), mincer_zarnowitz(), _nw_lags(), pronostico_con_sonrisa()

### Community 60 - "select_historical_otm"
Cohesion: 0.33
Nodes (5): select_historical_otm(), _contratos(), test_select_historical_otm_empty_without_both_sides(), test_select_historical_otm_prefers_50_dte_over_15(), test_select_historical_otm_real_strikes_and_dte()

### Community 62 - "elegir_spot_momentos"
Cohesion: 0.33
Nodes (3): elegir_spot_momentos(), _spot_bkm(), test_elegir_spot_momentos_usa_el_cierre_del_dia_o_la_cadena()

### Community 64 - "covariance_min_history"
Cohesion: 0.33
Nodes (4): columns_with_min_obs(), covariance_min_history(), test_columns_with_min_obs_keeps_long_history(), test_covariance_min_history_uses_each_series_full_sample()

### Community 65 - "test_etf_floor_refill.py"
Cohesion: 0.05
Nodes (40): candidatos_reposicion(), completar_etfs(), contar_etfs(), diagnostico_banda_etf(), etfs_necesarios(), relajar_banda_etf(), reserva_etf(), restricciones_factibles() (+32 more)

### Community 66 - "test_get_json_exhausts_retries_on_network_error"
Cohesion: 0.40
Nodes (3): n_fallos_transitorios(), test_get_json_exhausts_retries_on_network_error(), test_n_fallos_transitorios_excludes_missing_key()

### Community 74 - "mfis_check_deadline"
Cohesion: 0.22
Nodes (5): mfis_check_deadline(), mfis_deadline(), MfisTiempoAgotado, test_mfis_check_deadline_usa_perf_counter_por_defecto(), test_mfis_deadline_es_reloj_real_y_none_sin_limite()

### Community 76 - "higher_moments_admissible"
Cohesion: 0.16
Nodes (9): momentos_cola_historicos(), momentos_cola_historicos(), bkm_compute_moments(), bkm_compute_moments(), higher_moments_admissible(), mfik_cap(), mfik_cap_tenor(), test_higher_moments_admissible_pearson() (+1 more)

### Community 79 - "pytest"
Cohesion: 0.08
Nodes (32): mdd_from_log_returns(), extract_metrics(), annualize(), market_beta(), max_drawdown(), q_to_p_correlation(), scale_moments(), test_mdd_log_matches_exp_cumsum_not_simple_compounding() (+24 more)

### Community 82 - "portfolio_returns_skipna"
Cohesion: 0.50
Nodes (3): portfolio_returns_skipna(), portfolio_returns_series(), test_portfolio_returns_skipna_does_not_drop_the_month()

### Community 103 - "implied_variance_to_horizon"
Cohesion: 0.20
Nodes (7): mfiv_or_horizon_variance(), variance_annual_to_horizon(), implied_variance_to_horizon(), test_mfiv_fallback_uses_horizon_variance_not_annual(), test_variance_annual_matches_implied_variance_helper(), test_implied_variance_to_horizon_arrays_and_nan(), test_implied_variance_to_horizon_uses_real_dte()

## Knowledge Gaps
- **15 isolated node(s):** `pandas>=2.0`, `plotly>=5.18`, `scipy>=1.10`, `statsmodels>=0.14`, `Pull request merge order (stacked PRs #2 to #4 then this PR)` (+10 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 444 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `calibrate_iv_carry()` connect `to_years` to `quadratic_utility_(seasonal_version).py`, `minimum_variance.py`, `bkm_get_current_moments`, `numpy`, `test_ajuste_iv_tasa.py`, `fetch_otm_chain`, `risk_estimators.py`, `cornish_fisher_tail`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **What connects `pandas>=2.0`, `plotly>=5.18`, `scipy>=1.10` to the rest of the system?**
  _15 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `quadratic_utility_(seasonal_version).py` be split into smaller, more focused modules?**
  _Cohesion score 0.07317073170731707 - nodes in this community are weakly interconnected._
- **Why does `_YahooFalso` connect `_YahooFalso` to `test_script_smoke.py`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Should `test_bl_metrics.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05779220779220779 - nodes in this community are weakly interconnected._
- **Why does `beta_range_reachable()` connect `test_portfolio_constraints.py` to `minimum_variance.py`, `numpy`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Should `quadratic_utility.py` be split into smaller, more focused modules?**
  _Cohesion score 0.060129509713228495 - nodes in this community are weakly interconnected._