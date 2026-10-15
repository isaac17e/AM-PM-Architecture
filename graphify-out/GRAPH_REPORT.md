# Graph Report - AM-PM-Architecture  (2026-10-15)

## Corpus Check
- 35 files · ~135,627 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 3, .ini 1)

## Summary
- 1533 nodes · 3444 edges · 94 communities (67 shown, 27 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 89 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f1a0e8df`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- pytest
- test_pipeline_io.py
- test_risk_estimators.py
- polygon_client.py
- risk_estimators.py
- portfolio_constraints.py
- test_polygon_client.py
- market_data.py
- test_portfolio_constraints.py
- test_market_data.py
- test_cycle2_fixes.py
- test_qu_metrics.py
- math
- test_ajuste_iv_tasa.py
- minimum_variance.py
- test_previews_hist_vol_moment_source.py
- test_market_cap_internacional.py
- _GetterFalso
- pipeline_io.py
- get_spot_history
- pandas
- bl_metrics.py
- black_litterman.py
- ledoit_wolf_constant_correlation
- frames_from_yf_download
- quadratic_utility_(seasonal_version).py
- test_mv_cola_y_delta.py
- test_universo_y_delta_estacional.py
- quadratic_utility.py
- fit_ssvi
- test_etf_floor_refill.py
- test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados
- test_risk_profile.py
- Risk Profile Audit (configuration per investor profile)
- numpy
- pathlib
- test_script_smoke.py
- test_etf_floor_estacional.py
- resolve_horizon
- test_tail_prune_loop.py
- descargar_precio
- etfs_necesarios
- normalize_currency
- set_rate_limit
- dispersion_weights
- score_candidate_portfolios
- Workflow architecture (shared modules feed standalone optimizers)
- load_bl_input
- candidatos_reposicion
- mincer_zarnowitz
- history_window
- media_hac
- siguiente_reposicion
- qu_metrics.py
- mfis_deadline
- mfik_cap_tenor
- drop_partial_last_week
- calcular_bkm_moments
- dedupe_share_classes
- time
- parse_horizon_months
- frontier_lambda_grid
- estimate_bkm_history_calls
- construir_restricciones
- elegir_spot_momentos
- test_qu_horizonte.py
- calcular_metricas_riesgo_cola
- to_years
- average_abs_correlation
- mfis_tail_decision
- _sanear_momento_fisico
- horizon_from_months
- covariance_min_history
- _YahooFalso
- estimar_theta_esscher
- horizon_from_month_list
- resolve_bl_mode
- bootstrap_estacionario
- posterior_gram_charlier
- utilidad_mvsk_negativa
- _Limitador
- portfolio_returns_skipna
- entropy_pooling
- clip_implied_correlation
- mfiv_annual_vol
- sector_implied_ready
- stitch_covariance
- _diag_ssvi
- default_ff_cache_dir
- shrink_mu_to_prior
- test_bl_horizonte_previews.py

## God Nodes (most connected - your core abstractions)
1. `get_json()` - 27 edges
2. `to_years()` - 25 edges
3. `calibrate_iv_carry()` - 20 edges
4. `Risk Profile Audit (configuration per investor profile)` - 20 edges
5. `calibrar_superficie_ssvi()` - 19 edges
6. `fetch_otm_chain()` - 19 edges
7. `fit_ssvi()` - 18 edges
8. `es_transitorio()` - 18 edges
9. `_fuente()` - 15 edges
10. `_cadena_ssvi()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `QU run lambda sweep and frontier (pen_ret 0.141 at lambda 1.5)` --semantically_similar_to--> `Lambda calibration with pen_ret`  [INFERRED] [semantically similar]
  salidas_minimum_variance_y_quadratic_utility.txt → docs/risk_profile_audit.html
- `mu = historical mean shrunk toward Fama-French (mu_shrink_k = 140)` --semantically_similar_to--> `Expected return shrunk toward Fama-French 3-factor (mu_shrink_k)`  [INFERRED] [semantically similar]
  docs/risk_profile_audit.html → README.md
- `lambda3/lambda4 derived from gamma (CRRA Taylor expansion)` --semantically_similar_to--> `BL lambda3/lambda4 closed form from gamma`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `QU/MV normal: profile is a portfolio beta band (0.60-0.80 / 0.80-0.95 / >=0.95), 2026-10-11` --semantically_similar_to--> `Portfolio beta band (beta_port_lo/hi, beta_asset_min/max, Blume shrink) replaces vol/corr percentiles and ETF quota`  [INFERRED] [semantically similar]
  docs/risk_profile_audit.html → README.md
- `LP feasibility check (reachable beta band, regional caps) and ETF refill` --semantically_similar_to--> `Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12)`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared estimation modules feeding the three optimizers** — polygon_client, risk_estimators, market_data, portfolio_constraints, qu_metrics, bl_metrics, pipeline_io, quadratic_utility, minimum_variance, black_litterman [EXTRACTED 1.00]
- **Beta-band risk profile (README, audit, constraints, optimizers)** — readme_beta_band, docs_risk_profile_audit_beta_band, portfolio_constraints, quadratic_utility, minimum_variance [INFERRED 0.85]
- **Options-implied tail risk pipeline (BKM, Q to P, Cornish-Fisher)** — readme_bkm, readme_q_to_p, readme_cornish_fisher, readme_co_moments, readme_ssvi_fit [INFERRED 0.85]
- **Risk-profile calibration (gamma ladder, CRRA lambdas, lambda-only aversion, pen_ret)** — docs_risk_profile_audit_gamma_ladder, docs_risk_profile_audit_crra_lambdas, docs_risk_profile_audit_lambda_only_risk_aversion, docs_risk_profile_audit_lambda_calibration [INFERRED 0.85]

## Communities (94 total, 27 thin omitted)

### Community 0 - "pytest"
Cohesion: 0.12
Nodes (28): crra_taylor_lambdas(), integration_strike_bounds(), market_delta(), variance_annual_to_horizon(), test_apply_vol_q_to_p_does_not_haircut_historical_vol(), test_calibrar_superficie_ignora_leaps_y_quotes_rotos(), test_crra_taylor_lambdas_match_profile_ladder(), test_crra_taylor_terms_are_the_crra_expansion() (+20 more)

### Community 1 - "test_pipeline_io.py"
Cohesion: 0.13
Nodes (13): select_views(), _escribir(), _leer(), test_atomic_replace(), test_bl_input_invalid_or_missing(), test_bl_input_universe_uses_only_tickers(), test_bl_input_views_shape(), test_default_dir_and_env() (+5 more)

### Community 2 - "test_risk_estimators.py"
Cohesion: 0.07
Nodes (28): mdd_from_log_returns(), extract_metrics(), annualize(), max_drawdown(), portfolio_log_returns(), scale_moments(), test_mdd_log_matches_exp_cumsum_not_simple_compounding(), _lw_constant_correlation_referencia() (+20 more)

### Community 3 - "polygon_client.py"
Cohesion: 0.06
Nodes (37): _avisar_403(), _avisar_sin_api_key(), cache_get(), cache_permitida(), cache_set(), _con_api_key(), default_cache_dir(), es_snapshot() (+29 more)

### Community 4 - "risk_estimators.py"
Cohesion: 0.08
Nodes (25): compute_marginal_cvar_contrib(), compute_marginal_cvar_contrib(), cornish_fisher_domain(), cornish_fisher_es_gradient(), cornish_fisher_moments(), cornish_fisher_params(), a_parametros(), residuo() (+17 more)

### Community 5 - "portfolio_constraints.py"
Cohesion: 0.09
Nodes (14): beta_band_text(), beta_coverage_additions(), _rango(), beta_range_reachable(), build_weight_constraints(), prune_order(), relax_group_band(), with_return_target() (+6 more)

### Community 6 - "test_polygon_client.py"
Cohesion: 0.06
Nodes (36): polygon_fetch_chain(), bkm_fetch_otm_chain(), bkm_fetch_otm_chain(), calls_per_minute_from_env(), es_transitorio(), expiry_rank_columns(), fetch_otm_chain(), get_all() (+28 more)

### Community 7 - "market_data.py"
Cohesion: 0.09
Nodes (18): _campo(), combinar_tickers(), _con_reintentos(), currency_from_suffix(), default_market_cap_cache_path(), es_ticker_formato_us(), _escribir_cache(), _leer_cache() (+10 more)

### Community 8 - "test_portfolio_constraints.py"
Cohesion: 0.15
Nodes (20): bs_call_delta(), clip_to_band(), _base(), _minvar(), _minvar_banda(), _slack(), test_atm_call_delta_always_above_half(), test_banda_de_beta_con_inversion_parcial_es_por_capital_invertido() (+12 more)

### Community 9 - "test_market_data.py"
Cohesion: 0.13
Nodes (20): align_prices_to_calendar(), resolve_currencies(), resolve_execution_months(), _bdays(), _precios_dos_mercados(), test_align_drops_low_coverage_ticker(), test_align_fills_local_holiday_instead_of_dropping_row(), test_align_long_gap_not_filled_beyond_limit() (+12 more)

### Community 10 - "test_cycle2_fixes.py"
Cohesion: 0.12
Nodes (14): resolve_risk_free_rate(), mfis_max_minutes_from_env(), texto_delta_shrinkage(), _Resp, _get(), test_mfis_max_minutes_from_env(), test_optimizadores_leen_la_tasa_del_env_y_la_exportan(), test_orden_prioridad_mfis_por_market_cap_y_ranking() (+6 more)

### Community 11 - "test_qu_metrics.py"
Cohesion: 0.11
Nodes (18): pool_sin_no_procesados_mfis(), scale_option_deltas(), select_historical_otm(), _barra(), _contratos(), _formato_us_viejo(), test_combinar_tickers_conserva_sufijos_que_el_filtro_us_tiraba(), test_mfis_check_deadline_usa_perf_counter_por_defecto() (+10 more)

### Community 12 - "math"
Cohesion: 0.15
Nodes (16): bs_call_delta_from_vol(), delta_cushion(), evaluar_delta_candidato(), filtro_delta_otm(), _finito(), otm_log_moneyness(), pasa_filtro_delta(), test_horizonte_cambia_la_moneyness_efectiva() (+8 more)

### Community 13 - "test_ajuste_iv_tasa.py"
Cohesion: 0.10
Nodes (27): resumen_ajuste_iv(), texto_ajuste_iv(), bs_implied_vol(), bs_price(), calibrate_iv_carry(), residuo(), iv_at_rate(), _contrato() (+19 more)

### Community 14 - "minimum_variance.py"
Cohesion: 0.04
Nodes (41): bkm_annual_vol(), bkm_compute_moments(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), bkm_motivo_fallback(), bkm_resumen_fallbacks(), _bkm_vacio() (+33 more)

### Community 15 - "test_previews_hist_vol_moment_source.py"
Cohesion: 0.11
Nodes (24): SSVICalibrationError, _fuente(), _fuente_de_cadena(), _payload(), test_applied_fallback_is_appended_to_reason(), test_bkm_stage_failures(), test_chain_incomplete_is_reported_as_unavailable(), test_degenerate_smile_is_not_called_a_fit_error() (+16 more)

### Community 16 - "test_market_cap_internacional.py"
Cohesion: 0.11
Nodes (16): tabla_market_cap_texto(), _ordenar(), _proveedores(), test_cache_corrupta_no_rompe(), test_cache_evita_repetir_llamadas_y_vence_con_el_ttl(), test_convierte_a_usd_con_la_moneda_del_sufijo(), test_fast_info_en_peniques_se_lleva_a_libras(), test_n_top_mayor_que_la_lista_devuelve_todo() (+8 more)

### Community 17 - "_GetterFalso"
Cohesion: 0.14
Nodes (13): _escribir_atomico(), fetch_fama_french(), parse_fama_french_zip(), _ff(), _GetterFalso, _Resp, test_ff_cache_corrupta_cuenta_como_failed_y_un_zip_invalido_no_pisa_la_cache(), test_ff_descarga_ok_usa_https_timeout_y_guarda_cache() (+5 more)

### Community 18 - "pipeline_io.py"
Cohesion: 0.20
Nodes (13): _atomic_write(), build_previews_payload(), _date_or_none(), export_portfolio(), _export_portfolio(), _int_or_none(), _jsonify(), _metrics() (+5 more)

### Community 19 - "get_spot_history"
Cohesion: 0.13
Nodes (15): get_spot_history(), _retry_spot_single(), _usable_spot(), _cierres(), test_get_spot_history_downloads_the_batch_once_and_workers_only_read(), batch(), single(), test_get_spot_history_falls_through_to_the_next_provider() (+7 more)

### Community 20 - "pandas"
Cohesion: 0.14
Nodes (17): log_portfolio_return(), calibrar_ssvi_ticker(), momentos_realizados_rolling(), parse_chain(), market_beta(), seasonal_vol_ratio(), test_log_portfolio_return_is_not_the_weighted_sum_of_logs(), test_log_portfolio_return_renormalizes_missing_names() (+9 more)

### Community 21 - "bl_metrics.py"
Cohesion: 0.06
Nodes (24): apply_vol_q_to_p(), calibrar_superficie_ssvi(), _fecha_naive(), _fit_rejection_text(), forward_por_paridad(), iv_vol_at_horizon(), mfiv_or_horizon_variance(), mfiv_vs_atm() (+16 more)

### Community 22 - "black_litterman.py"
Cohesion: 0.10
Nodes (8): aplicar_limites_cartera(), _momento_pendiente(), momentos_ponderados(), optimizar_min_cvar(), port_ret_row(), primas_esscher(), _retorno_min_factible(), winsorizar()

### Community 23 - "ledoit_wolf_constant_correlation"
Cohesion: 0.15
Nodes (13): average_correlation(), cov_ewma_shrunk(), effective_sample_size(), ewma_cov(), ewma_weights(), ledoit_wolf_constant_correlation(), _lw_ewma_referencia_delta(), test_cov_ewma_shrunk_pipeline() (+5 more)

### Community 24 - "frames_from_yf_download"
Cohesion: 0.11
Nodes (10): default_spot_providers(), _frame_from_close(), frames_from_yf_download(), _naive_dates(), yfinance_spot_batch(), yfinance_spot_single(), test_frames_from_yf_download_reads_both_multiindex_orders(), test_yfinance_batch_is_one_unadjusted_download() (+2 more)

### Community 25 - "quadratic_utility_(seasonal_version).py"
Cohesion: 0.05
Nodes (36): armar_restricciones(), _asegurar_momentos_actuales(), bkm_clave_historia(), bkm_compute_moments(), bkm_fechas_pendientes(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_iv_chain_to_prices() (+28 more)

### Community 26 - "test_mv_cola_y_delta.py"
Cohesion: 0.22
Nodes (13): _bucle_de_cola(), _descartes(), _fuente(), _funcion(), test_conteo_estable_entre_horizontes(), test_conteos_por_umbral_conservador_moderado_agresivo(), test_defaults_del_filtro_delta_en_mv(), test_fallback_historico_activo_por_defecto() (+5 more)

### Community 27 - "test_universo_y_delta_estacional.py"
Cohesion: 0.18
Nodes (12): _descartados(), _formato_us_viejo(), _fuente(), _internacionales_del_script(), _literales(), test_bl_no_manda_internacionales_a_polygon(), test_conteo_de_colchon_separa_umbrales_y_aguanta_el_horizonte(), test_conteo_del_filtro_estacional_sobre_universo_sintetico() (+4 more)

### Community 28 - "quadratic_utility.py"
Cohesion: 0.05
Nodes (34): spot_series_for(), is_us_ticker(), _asegurar_momentos_actuales(), bkm_clave_historia(), bkm_fechas_pendientes(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_iv_chain_to_prices() (+26 more)

### Community 29 - "fit_ssvi"
Cohesion: 0.11
Nodes (19): fit_ssvi(), objetivo(), _params(), _penalty(), _relativos(), _sigmoid(), _grupos_vencimiento(), ssvi_total_variance() (+11 more)

### Community 30 - "test_etf_floor_refill.py"
Cohesion: 0.17
Nodes (13): relajar_banda_etf(), restricciones_factibles(), test_caso_conservador_tal_como_llegaba_es_infactible_para_quadprog(), _quadprog(), _restricciones(), test_caso_conservador_es_infactible_y_quadprog_lo_confirma(), test_con_cuatro_etf_el_conservador_es_factible(), test_factibilidad_considera_el_tope_regional() (+5 more)

### Community 31 - "test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados"
Cohesion: 0.18
Nodes (9): completar_etfs(), contar_etfs(), reserva_etf(), test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados(), test_completar_etfs_agrega_solo_lo_necesario_y_en_orden(), test_completar_etfs_devuelve_lo_que_haya_si_no_alcanza(), test_contar_etfs_sin_duplicados(), test_reserva_etf_toma_los_que_faltan_en_orden_de_ranking() (+1 more)

### Community 32 - "test_risk_profile.py"
Cohesion: 0.21
Nodes (10): _cli_risk_profile(), resolve_risk_profile(), _literales(), _presets(), test_el_perfil_de_qu_y_mv_es_una_banda_de_beta(), test_preset_agresivo_no_cambia_los_literales(), test_presets_de_mv_y_qu_coinciden_con_la_auditoria(), test_resolve_default_si_no_hay_env_ni_cli() (+2 more)

### Community 33 - "Risk Profile Audit (configuration per investor profile)"
Cohesion: 0.06
Nodes (41): Asset Allocation (FICs) am_pm/profiles.py mandates, Risk Profile Audit (configuration per investor profile), Black-Litterman PERFILES (omega_scale, tau, gamma_ra), COL Portfolio Architecture (proposed profile bands, max Sharpe), QU OTM delta filter as annual IV cap, Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12), International ticker format filter and region caps, Lambda calibration with pen_ret (+33 more)

### Community 34 - "numpy"
Cohesion: 0.07
Nodes (25): clip_negligible_weights(), markowitz_clasico(), optimizar_mvsk(), beta_band_columns(), relax_beta_band(), frontier_curve(), portfolio_mu_final_metrics(), implied_variance_to_horizon() (+17 more)

### Community 36 - "test_script_smoke.py"
Cohesion: 0.22
Nodes (11): _alias_importados(), _asignaciones_de_modulo(), _correr_bl(), _nombres(), sombras_de_import(), test_bl_input_file_overrides_tickers_and_views(), test_bl_risk_profile_env_and_cli(), test_bl_universe_file_drops_default_views() (+3 more)

### Community 37 - "test_etf_floor_estacional.py"
Cohesion: 0.27
Nodes (6): _bloque_restricciones(), _correr_restricciones(), test_banda_que_ya_cumplia_no_cambia(), test_con_el_cuarto_etf_el_conservador_resuelve_sin_relajar(), test_sin_cuarto_etf_la_banda_se_relaja_y_quadprog_resuelve(), test_sin_relajar_falla_con_mensaje_claro_y_no_con_quadprog()

### Community 38 - "resolve_horizon"
Cohesion: 0.20
Nodes (9): resolve_horizon(), resolve_horizon_months(), test_horizon_blank_env_is_unset(), test_horizon_default_when_nothing_set(), test_horizon_env_beats_default(), test_horizon_input_file_beats_env(), test_horizon_input_without_key_falls_back_to_env(), test_horizon_invalid_env_is_clear_error() (+1 more)

### Community 39 - "test_tail_prune_loop.py"
Cohesion: 0.26
Nodes (6): _bucle_de_poda(), _correr(), test_block_cut_is_skipped_when_it_leaves_too_few_names(), test_min_weight_keeps_capped_defensives(), test_names_below_threshold_are_cut_in_one_step(), test_prune_loop_survives_floor_weights()

### Community 40 - "descargar_precio"
Cohesion: 0.18
Nodes (6): asegurar_fx(), descargar_fx_moneda(), descargar_precio(), _momentos_sector(), _par_fx(), convertir_serie_a_usd()

### Community 41 - "etfs_necesarios"
Cohesion: 0.22
Nodes (6): diagnostico_banda_etf(), etfs_necesarios(), test_diagnostico_explica_el_piso_de_etf(), test_diagnostico_vacio_si_los_conteos_alcanzan(), test_etfs_necesarios(), test_etfs_necesarios_rechaza_max_weight_invalido()

### Community 42 - "normalize_currency"
Cohesion: 0.17
Nodes (8): normalize_currency(), price_scale_factor(), download_period_returns(), get_currency_for_ticker(), download_period_returns(), get_currency_for_ticker(), test_normalize_currency(), test_price_scale_factor()

### Community 43 - "set_rate_limit"
Cohesion: 0.17
Nodes (6): estimate_minutes(), set_rate_limit(), polygon_aislado(), entorno_aislado(), test_limiter_spaces_calls(), test_set_rate_limit_updates_limiter_and_estimate()

### Community 44 - "dispersion_weights"
Cohesion: 0.25
Nodes (6): dispersion_usable(), dispersion_weights(), test_dispersion_cap_share_is_the_basket_over_known_spy_caps(), test_dispersion_weights_cap_weighted_spy_names_with_iv(), test_dispersion_weights_equal_when_a_cap_is_missing(), test_dispersion_weights_insufficient_basket()

### Community 45 - "score_candidate_portfolios"
Cohesion: 0.17
Nodes (8): comparison_lambdas(), lambda_monthly_from_annual(), score_candidate_portfolios(), utility_terms(), test_lambda_monthly_from_annual_scales_by_twelve_and_is_opt_in(), test_lambda_scores_use_the_reference_lambda_and_mu_final(), test_pen_ret_is_nan_when_return_is_not_positive(), test_utility_terms_show_when_the_penalty_binds()

### Community 46 - "Workflow architecture (shared modules feed standalone optimizers)"
Cohesion: 0.12
Nodes (18): AM-PM Portfolio Construction Repository, BL_INPUT_FILE universe/views JSON, Pipeline JSON export (portfolio_latest.json), Pull request merge order (stacked PRs #2 to #4 then this PR), RISK_FREE_RATE env var (resolve_risk_free_rate), Test suite (pytest, no network), numpy>=1.24, pandas>=2.0 (+10 more)

### Community 47 - "load_bl_input"
Cohesion: 0.43
Nodes (6): load_bl_input(), _archivo(), test_load_bl_input_invalid_horizon_not_masked_by_bad_tickers(), test_load_bl_input_invalid_horizon_raises_not_warns(), test_load_bl_input_returns_horizon_months(), test_load_bl_input_without_horizon_is_none()

### Community 48 - "candidatos_reposicion"
Cohesion: 0.40
Nodes (3): candidatos_reposicion(), test_reposicion_aplica_el_filtro_iv_a_quien_nunca_paso_por_el(), test_reposicion_bkm_no_trae_de_vuelta_a_mchi()

### Community 50 - "history_window"
Cohesion: 0.40
Nodes (4): history_window(), test_history_window_includes_current_year_through_last_full_month(), test_history_window_january_stops_at_previous_year(), test_history_window_rejects_start_after_sample()

### Community 52 - "siguiente_reposicion"
Cohesion: 0.50
Nodes (3): siguiente_reposicion(), test_siguiente_reposicion_prioriza_etf_cuando_faltan(), test_siguiente_reposicion_sin_etf_coincide_con_el_indice_secuencial()

### Community 53 - "qu_metrics.py"
Cohesion: 0.10
Nodes (13): align_daily_panel(), annualize_monthly(), _clave_cap(), MfisTiempoAgotado, orden_prioridad_mfis(), clave(), plan_bkm_history_budget(), summarize_yearly_mdd() (+5 more)

### Community 55 - "mfik_cap_tenor"
Cohesion: 0.33
Nodes (4): mfik_cap(), mfik_cap_tenor(), test_mfik_cap_rises_with_chain_depth(), test_mfik_cap_tenor_loosens_a_short_chain()

### Community 56 - "drop_partial_last_week"
Cohesion: 0.43
Nodes (6): drop_partial_last_week(), _semanal(), test_drop_partial_last_week_empty_and_dataframe(), test_drop_partial_last_week_friday_kept(), test_drop_partial_last_week_thursday_before_holiday_friday(), test_drop_partial_last_week_wednesday_dropped()

### Community 57 - "calcular_bkm_moments"
Cohesion: 0.40
Nodes (5): calcular_bkm_moments(), otm_price_ssvi(), phi_powerlaw(), sigma_desde_ssvi(), ssvi_w()

### Community 59 - "time"
Cohesion: 0.14
Nodes (7): close_near_from_bars(), contract_agg_ranges(), mfis_check_deadline(), bkm_precios_en_rango(), polygon_contract_close_near(), bkm_precios_en_rango(), polygon_contract_close_near()

### Community 60 - "parse_horizon_months"
Cohesion: 0.22
Nodes (6): InvalidHorizonError, parse_horizon_months(), _parse_views(), _validate_bl_input(), test_horizon_accepts_integers_1_to_12(), test_horizon_rejects_invalid_values()

### Community 65 - "test_qu_horizonte.py"
Cohesion: 0.16
Nodes (15): cornish_fisher_at_horizon(), qp_inputs_at_horizon(), horizon_months as single source of investment term (mu*h, Sigma*h), _pesos(), _restricciones(), test_cf_gaussiano_escala_con_raiz_de_h(), test_cf_h1_es_el_var_mensual_de_antes(), test_cf_h2_usa_scale_moments() (+7 more)

### Community 66 - "calcular_metricas_riesgo_cola"
Cohesion: 0.29
Nodes (4): calcular_metricas_riesgo_cola(), _pesos_normalizados(), var_cvar_cornish_fisher(), var_cvar_historico()

### Community 67 - "to_years"
Cohesion: 0.22
Nodes (6): momentos_cola_historicos(), momentos_cola_historicos(), bkm_compute_moments(), higher_moments_admissible(), to_years(), test_higher_moments_admissible_pearson()

### Community 68 - "average_abs_correlation"
Cohesion: 0.33
Nodes (5): average_abs_correlation(), _corr_abc(), test_average_abs_correlation_ignores_sign_and_order(), test_average_abs_correlation_uses_full_row(), test_old_alphabetical_grouping_drops_last_ticker()

### Community 69 - "mfis_tail_decision"
Cohesion: 0.29
Nodes (4): mfis_tail_decision(), test_mfis_tail_decision(), test_mfis_tail_default_upper_matches_old_inequality(), test_mfis_tail_rejects_unknown_mode()

### Community 72 - "horizon_from_months"
Cohesion: 0.33
Nodes (4): _add_months(), horizon_from_months(), test_default_horizon_is_unchanged(), test_horizon_from_months()

### Community 74 - "covariance_min_history"
Cohesion: 0.33
Nodes (4): columns_with_min_obs(), covariance_min_history(), test_columns_with_min_obs_keeps_long_history(), test_covariance_min_history_uses_each_series_full_sample()

### Community 76 - "estimar_theta_esscher"
Cohesion: 0.50
Nodes (3): cumulantes_Q_desde_P(), estimar_theta_esscher(), objetivo()

### Community 78 - "resolve_bl_mode"
Cohesion: 0.50
Nodes (3): resolve_bl_mode(), test_bl_mode_default_env_and_flag(), test_bl_mode_rejects_unknown_value()

### Community 86 - "portfolio_returns_skipna"
Cohesion: 0.50
Nodes (3): portfolio_returns_skipna(), portfolio_returns_series(), test_portfolio_returns_skipna_does_not_drop_the_month()

### Community 102 - "test_bl_horizonte_previews.py"
Cohesion: 0.15
Nodes (19): _correr(), _correr_previews(), _entorno(), _payload(), test_env_horizon_propagates_to_every_derived_quantity(), test_full_mode_unchanged_when_bl_mode_full(), test_horizon_is_resolved_before_any_use(), test_input_file_horizon_beats_env() (+11 more)

## Knowledge Gaps
- **11 isolated node(s):** `DTE window and tenor scaling`, `Polygon entitlements (options and reference only)`, `Polygon rate limiting, retry and cache configuration`, `Entropy pooling posterior views`, `SSVI smile fit on |k|<=0.5` (+6 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 464 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `InvalidHorizonError` connect `parse_horizon_months` to `pipeline_io.py`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **What connects `DTE window and tenor scaling`, `Polygon entitlements (options and reference only)`, `Polygon rate limiting, retry and cache configuration` to the rest of the system?**
  _11 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `pytest` be split into smaller, more focused modules?**
  _Cohesion score 0.11586452762923351 - nodes in this community are weakly interconnected._
- **Should `test_pipeline_io.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12857142857142856 - nodes in this community are weakly interconnected._
- **Should `test_risk_estimators.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06923076923076923 - nodes in this community are weakly interconnected._
- **Should `polygon_client.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05974025974025974 - nodes in this community are weakly interconnected._
- **Should `risk_estimators.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07557354925775979 - nodes in this community are weakly interconnected._