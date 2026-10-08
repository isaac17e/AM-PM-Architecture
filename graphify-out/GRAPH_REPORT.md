# Graph Report - AM-PM-Architecture  (2026-10-08)

## Corpus Check
- 34 files · ~124,146 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .ini 1)

## Summary
- 1336 nodes · 2966 edges · 101 communities (75 shown, 26 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 70 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `66949e78`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_etf_floor_refill.py
- bkm_get_current_moments
- quadratic_utility_(seasonal_version).py
- pandas
- numpy
- polygon_client.py
- implied_variance_to_horizon
- math
- minimum_variance.py
- minimum_variance_(seasonal_version).py
- market_data.py
- test_market_cap_internacional.py
- pipeline_io.py
- test_ajuste_iv_tasa.py
- bkm_fechas_pendientes
- test_market_data.py
- test_portfolio_constraints.py
- test_script_smoke.py
- pytest
- fit_ssvi
- test_bl_universo.py
- test_universo_y_delta_estacional.py
- get_spot_history
- fetch_otm_chain
- risk_estimators.py
- frames_from_yf_download
- relax_group_band
- cornish_fisher_tail
- test_mv_cola_y_delta.py
- black_litterman.py
- Risk Profile Audit (configuration per investor profile)
- test_cycle2_fixes.py
- test_risk_profile.py
- iv_vol_at_horizon
- bkm_fechas_pendientes
- fetch_option_aggs
- test_qu_metrics.py
- set_rate_limit
- _momentos_sector
- test_tail_prune_loop.py
- normalize_currency
- drop_partial_last_week
- Working with the graphify knowledge graph
- portfolio_constraints.py
- descargar_precio
- _YahooFalso
- calcular_metricas_riesgo_cola
- mfis_tail_decision
- elegir_spot_momentos
- portfolio_returns_skipna
- default_cache_dir
- dedupe_share_classes
- momentos_ponderados
- gram_charlier_pdf_ratio
- _diag_ssvi
- test_conteo_del_filtro_estacional_sobre_universo_sintetico
- test_polygon_client.py
- estimar_theta_esscher
- mincer_zarnowitz
- Quadratic utility maximization U = mu'w - lambda/2 w'Sigma w
- optimizar_min_cvar
- bootstrap_estacionario
- media_hac
- optimizar_mvsk
- quadratic_utility.py
- cache_get
- score_candidate_portfolios
- test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados
- _Limitador
- test_etf_floor_estacional.py
- entropy_pooling
- _RespuestaFalsa
- etfs_necesarios
- restricciones_factibles
- qu_metrics.py
- winsorizar
- bkm_get_current_moments
- Working with the graphify knowledge graph
- evaluar_historia_bkm
- higher_moments_admissible
- bkm_reconstruct_mfis_history
- polygon_contracts_asof
- bs_call_delta
- bkm_reconstruct_mfis_history
- test_get_json_exhausts_retries_on_network_error
- candidatos_reposicion
- polygon_contracts_asof
- calibrar_ssvi_ticker
- bkm_motivo_fallback
- build_qp_constraints
- is_us_ticker
- bkm_motivo_fallback
- build_qp_constraints
- siguiente_reposicion
- prune_order
- bkm_iv_chain_to_prices
- construir_restricciones
- _momento_pendiente
- _sanear_momento_fisico
- _retorno_min_factible
- tabla_ratio_vol_reciente

## God Nodes (most connected - your core abstractions)
1. `get_json()` - 27 edges
2. `to_years()` - 23 edges
3. `calibrate_iv_carry()` - 19 edges
4. `fetch_otm_chain()` - 19 edges
5. `fit_ssvi()` - 18 edges
6. `es_transitorio()` - 18 edges
7. `Risk Profile Audit (configuration per investor profile)` - 18 edges
8. `calibrar_superficie_ssvi()` - 17 edges
9. `get_all()` - 15 edges
10. `market_caps_usd()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `lambda3/lambda4 derived from gamma (CRRA Taylor expansion)` --semantically_similar_to--> `BL lambda3/lambda4 closed form from gamma`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `Reachable ETF floor and LP feasibility check` --semantically_similar_to--> `Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12)`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `test_calls_per_min_alias_y_sin_tope()` --calls--> `calls_per_minute_from_env()`  [EXTRACTED]
  tests/test_cycle2_fixes.py → polygon_client.py
- `test_currency_from_suffix()` --calls--> `currency_from_suffix()`  [EXTRACTED]
  tests/test_market_data.py → market_data.py
- `test_expiry_rank_prefers_50_over_15_for_a_30_day_target()` --calls--> `expiry_rank_columns()`  [EXTRACTED]
  tests/test_polygon_client.py → polygon_client.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared estimation modules feeding the three optimizers** — polygon_client, risk_estimators, market_data, portfolio_constraints, qu_metrics, bl_metrics, pipeline_io, quadratic_utility, minimum_variance, black_litterman [EXTRACTED 1.00]
- **Options-implied tail risk pipeline (BKM, Q to P, Cornish-Fisher)** — readme_bkm, readme_q_to_p, readme_cornish_fisher, readme_co_moments, readme_ssvi_fit [INFERRED 0.85]
- **Risk-profile calibration (gamma ladder, CRRA lambdas, lambda-only aversion, pen_ret)** — docs_risk_profile_audit_gamma_ladder, docs_risk_profile_audit_crra_lambdas, docs_risk_profile_audit_lambda_only_risk_aversion, docs_risk_profile_audit_lambda_calibration [INFERRED 0.85]

## Communities (101 total, 26 thin omitted)

### Community 0 - "test_etf_floor_refill.py"
Cohesion: 0.18
Nodes (8): relajar_banda_etf(), test_relajar_banda_no_toca_una_banda_alcanzable(), test_relajar_banda_sube_el_techo_si_faltan_acciones(), test_script_chequea_factibilidad_antes_de_quadprog(), test_script_delta_min_agresivo_es_015(), test_scripts_ordenan_por_market_cap_antes_del_top(), _formato_us_viejo(), test_combinar_tickers_conserva_sufijos_que_el_filtro_us_tiraba()

### Community 1 - "bkm_get_current_moments"
Cohesion: 0.20
Nodes (9): _asegurar_momentos_actuales(), bkm_get_current_moments(), bkm_iv_chain_to_prices(), bs_price(), get_spot_safe_bkm(), is_us_ticker(), _momento_actual_bkm(), polygon_get_sector_etf() (+1 more)

### Community 2 - "quadratic_utility_(seasonal_version).py"
Cohesion: 0.12
Nodes (8): armar_restricciones(), clean_symbol_table(), download_fx_prices(), _parse_market_cap(), qubo_energy(), select_candidates_qubo(), select_optimal_candidates(), tabla_ratio_estacional()

### Community 3 - "pandas"
Cohesion: 0.07
Nodes (34): calibrar_superficie_ssvi(), crra_taylor_lambdas(), _fecha_naive(), forward_por_paridad(), log_portfolio_return(), mdd_from_log_returns(), momentos_fallback(), seleccionar_vencimientos() (+26 more)

### Community 4 - "numpy"
Cohesion: 0.07
Nodes (27): apply_vol_q_to_p(), clip_negligible_weights(), integration_strike_bounds(), momentos_realizados_rolling(), clip_implied_correlation(), scale_option_deltas(), nearest_psd(), portfolio_log_returns() (+19 more)

### Community 5 - "polygon_client.py"
Cohesion: 0.11
Nodes (14): _avisar_403(), _avisar_sin_api_key(), _con_api_key(), _espera_reintento(), get_json(), print_diagnostics(), _registrar(), _retry_after() (+6 more)

### Community 6 - "implied_variance_to_horizon"
Cohesion: 0.11
Nodes (12): mfiv_or_horizon_variance(), variance_annual_to_horizon(), bkm_annual_vol(), mfiv_annual_vol(), implied_variance_to_horizon(), q_to_p_vol(), test_mfiv_fallback_uses_horizon_variance_not_annual(), test_variance_annual_matches_implied_variance_helper() (+4 more)

### Community 7 - "math"
Cohesion: 0.19
Nodes (12): bs_call_delta_from_vol(), delta_cushion(), evaluar_delta_candidato(), otm_log_moneyness(), test_horizonte_cambia_la_moneyness_efectiva(), _cojines(), test_colchon_baja_con_la_vol_y_separa_perfiles(), test_delta_atm_no_separa_los_umbrales_de_perfil() (+4 more)

### Community 8 - "minimum_variance.py"
Cohesion: 0.11
Nodes (16): bkm_annual_vol(), bkm_compute_moments(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), bs_price(), clean_symbol_table() (+8 more)

### Community 9 - "minimum_variance_(seasonal_version).py"
Cohesion: 0.12
Nodes (15): bkm_compute_moments(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), bs_price(), clean_symbol_table(), constraints_feasible() (+7 more)

### Community 10 - "market_data.py"
Cohesion: 0.11
Nodes (17): _campo(), combinar_tickers(), _con_reintentos(), currency_from_suffix(), default_market_cap_cache_path(), es_ticker_formato_us(), _escribir_cache(), _leer_cache() (+9 more)

### Community 11 - "test_market_cap_internacional.py"
Cohesion: 0.11
Nodes (19): _llamar_caps(), _llamar_fx(), tabla_market_cap_texto(), _ordenar(), _proveedores(), cap_provider(), fx_provider(), test_cache_corrupta_no_rompe() (+11 more)

### Community 12 - "pipeline_io.py"
Cohesion: 0.06
Nodes (35): _add_months(), _atomic_write(), _date_or_none(), export_portfolio(), _export_portfolio(), horizon_from_month_list(), horizon_from_months(), _int_or_none() (+27 more)

### Community 13 - "test_ajuste_iv_tasa.py"
Cohesion: 0.09
Nodes (31): get_polygon_option_snapshot(), get_polygon_option_snapshot(), expiry_rank_columns(), pares_call_put(), resumen_ajuste_iv(), texto_ajuste_iv(), polygon_get_atm_option(), polygon_get_atm_option() (+23 more)

### Community 14 - "bkm_fechas_pendientes"
Cohesion: 0.20
Nodes (6): bkm_clave_historia(), bkm_fechas_pendientes(), _plan_ronda_bkm(), _precargar_spots_bkm(), _rank_bkm(), _ventana_spot_bkm()

### Community 15 - "test_market_data.py"
Cohesion: 0.12
Nodes (21): align_prices_to_calendar(), resolve_currencies(), resolve_execution_months(), align_daily_panel(), _bdays(), _precios_dos_mercados(), test_align_drops_low_coverage_ticker(), test_align_fills_local_holiday_instead_of_dropping_row() (+13 more)

### Community 16 - "test_portfolio_constraints.py"
Cohesion: 0.27
Nodes (10): markowitz_clasico(), _base(), _minvar(), _slack(), test_budget_is_equality_and_box_constraints_hold(), test_etf_and_fx_columns_bind_on_invested_capital(), test_etf_band_skipped_when_subset_has_no_etf(), test_frontier_feasible_target_respects_etf_band_and_fx_cap() (+2 more)

### Community 17 - "test_script_smoke.py"
Cohesion: 0.22
Nodes (11): _alias_importados(), _asignaciones_de_modulo(), _correr_bl(), _nombres(), sombras_de_import(), test_bl_input_file_overrides_tickers_and_views(), test_bl_risk_profile_env_and_cli(), test_bl_universe_file_drops_default_views() (+3 more)

### Community 18 - "pytest"
Cohesion: 0.07
Nodes (40): market_delta(), annualize_monthly(), annualize(), max_drawdown(), q_to_p_correlation(), scale_bkm_moments(), scale_moments(), seasonal_vol_ratio() (+32 more)

### Community 19 - "fit_ssvi"
Cohesion: 0.17
Nodes (13): fit_ssvi(), objetivo(), _params(), _penalty(), _relativos(), _sigmoid(), _grupos_vencimiento(), ssvi_total_variance() (+5 more)

### Community 21 - "test_universo_y_delta_estacional.py"
Cohesion: 0.18
Nodes (13): convertir_serie_a_usd(), _descartados(), _formato_us_viejo(), _fuente(), _internacionales_del_script(), _literales(), test_bl_no_manda_internacionales_a_polygon(), test_conteo_de_colchon_separa_umbrales_y_aguanta_el_horizonte() (+5 more)

### Community 22 - "get_spot_history"
Cohesion: 0.13
Nodes (15): get_spot_history(), _retry_spot_single(), _usable_spot(), _cierres(), test_get_spot_history_downloads_the_batch_once_and_workers_only_read(), batch(), single(), test_get_spot_history_falls_through_to_the_next_provider() (+7 more)

### Community 23 - "fetch_otm_chain"
Cohesion: 0.11
Nodes (17): bkm_fetch_otm_chain(), bkm_fetch_otm_chain(), es_transitorio(), fetch_otm_chain(), polygon_format_ticker(), test_fetch_otm_chain_empty_paths_carry_empty_pairs(), test_es_transitorio_false(), test_es_transitorio_true() (+9 more)

### Community 24 - "risk_estimators.py"
Cohesion: 0.10
Nodes (18): average_correlation(), cov_ewma_shrunk(), effective_sample_size(), ewma_cov(), ewma_weights(), ledoit_wolf_constant_correlation(), martin_wagner_excess_return(), rescale_panel() (+10 more)

### Community 25 - "frames_from_yf_download"
Cohesion: 0.11
Nodes (10): default_spot_providers(), _frame_from_close(), frames_from_yf_download(), _naive_dates(), yfinance_spot_batch(), yfinance_spot_single(), test_frames_from_yf_download_reads_both_multiindex_orders(), test_yfinance_batch_is_one_unadjusted_download() (+2 more)

### Community 27 - "cornish_fisher_tail"
Cohesion: 0.13
Nodes (15): compute_marginal_cvar_contrib(), compute_marginal_cvar_contrib(), cornish_fisher_domain(), cornish_fisher_es_gradient(), cornish_fisher_moments(), cornish_fisher_params(), a_parametros(), residuo() (+7 more)

### Community 28 - "test_mv_cola_y_delta.py"
Cohesion: 0.22
Nodes (13): _bucle_de_cola(), _descartes(), _fuente(), _funcion(), test_conteo_estable_entre_horizontes(), test_conteos_por_umbral_conservador_moderado_agresivo(), test_defaults_del_filtro_delta_en_mv(), test_fallback_historico_activo_por_defecto() (+5 more)

### Community 29 - "black_litterman.py"
Cohesion: 0.15
Nodes (10): aplicar_limites_cartera(), bs_price(), calc_mdd(), calcular_bkm_moments(), otm_price_ssvi(), phi_powerlaw(), port_ret_row(), primas_esscher() (+2 more)

### Community 30 - "Risk Profile Audit (configuration per investor profile)"
Cohesion: 0.14
Nodes (16): Asset Allocation (FICs) am_pm/profiles.py mandates, Risk Profile Audit (configuration per investor profile), Black-Litterman PERFILES (omega_scale, tau, gamma_ra), COL Portfolio Architecture (proposed profile bands, max Sharpe), QU OTM delta filter as annual IV cap, International ticker format filter and region caps, Lambda calibration with pen_ret, Minimum Variance profile parameter tables (normal and seasonal) (+8 more)

### Community 31 - "test_cycle2_fixes.py"
Cohesion: 0.10
Nodes (18): resolve_risk_free_rate(), _clave_cap(), orden_prioridad_mfis(), clave(), plan_bkm_history_budget(), texto_delta_shrinkage(), test_calls_per_min_alias_y_sin_tope(), test_corte_de_presupuesto_deja_fuera_a_los_menos_relevantes() (+10 more)

### Community 32 - "test_risk_profile.py"
Cohesion: 0.18
Nodes (9): _cli_risk_profile(), resolve_risk_profile(), _literales(), _presets(), test_preset_agresivo_no_cambia_los_literales(), test_presets_de_mv_y_qu_coinciden_con_la_auditoria(), test_resolve_default_si_no_hay_env_ni_cli(), test_resolve_env_y_cli() (+1 more)

### Community 33 - "iv_vol_at_horizon"
Cohesion: 0.33
Nodes (4): iv_vol_at_horizon(), vol_annual_to_horizon(), test_ssvi_and_hist_fallback_share_horizon_units(), test_vol_annual_scales_with_sqrt_horizon()

### Community 34 - "bkm_fechas_pendientes"
Cohesion: 0.20
Nodes (6): bkm_clave_historia(), bkm_fechas_pendientes(), _plan_ronda_bkm(), _precargar_spots_bkm(), _rank_bkm(), _ventana_spot_bkm()

### Community 35 - "fetch_option_aggs"
Cohesion: 0.19
Nodes (7): fetch_option_aggs(), close_near_from_bars(), contract_agg_ranges(), bkm_precios_en_rango(), polygon_contract_close_near(), bkm_precios_en_rango(), polygon_contract_close_near()

### Community 36 - "test_qu_metrics.py"
Cohesion: 0.06
Nodes (34): average_abs_correlation(), columns_with_min_obs(), covariance_min_history(), dispersion_weights(), history_window(), select_historical_otm(), stitch_covariance(), summarize_yearly_mdd() (+26 more)

### Community 37 - "set_rate_limit"
Cohesion: 0.13
Nodes (8): estimate_minutes(), _parse_calls_per_min(), set_rate_limit(), polygon_aislado(), entorno_aislado(), test_limiter_spaces_calls(), test_parse_calls_per_min(), test_set_rate_limit_updates_limiter_and_estimate()

### Community 38 - "_momentos_sector"
Cohesion: 0.25
Nodes (5): mfiv_vs_atm(), _momentos_sector(), mfik_cap(), test_mfiv_far_above_atm_falls_back_to_atm_variance(), test_mfik_cap_rises_with_chain_depth()

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

### Community 43 - "portfolio_constraints.py"
Cohesion: 0.11
Nodes (15): Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12), build_weight_constraints(), with_return_target(), AM-PM Portfolio Construction Repository, Reachable ETF floor and LP feasibility check, Pull request merge order (stacked PRs #2 to #4 then this PR), numpy>=1.24, pandas>=2.0 (+7 more)

### Community 44 - "descargar_precio"
Cohesion: 0.24
Nodes (4): asegurar_fx(), descargar_fx_moneda(), descargar_precio(), _par_fx()

### Community 46 - "calcular_metricas_riesgo_cola"
Cohesion: 0.29
Nodes (4): calcular_metricas_riesgo_cola(), _pesos_normalizados(), var_cvar_cornish_fisher(), var_cvar_historico()

### Community 47 - "mfis_tail_decision"
Cohesion: 0.18
Nodes (7): mfis_tail_decision(), evaluar_historia_bkm(), _fila(), _fila_bkm(), _spot_series_bkm(), test_mfis_tail_decision(), test_mfis_tail_default_upper_matches_old_inequality()

### Community 48 - "elegir_spot_momentos"
Cohesion: 0.33
Nodes (3): elegir_spot_momentos(), _spot_bkm(), test_elegir_spot_momentos_usa_el_cierre_del_dia_o_la_cadena()

### Community 49 - "portfolio_returns_skipna"
Cohesion: 0.50
Nodes (3): portfolio_returns_skipna(), portfolio_returns_series(), portfolio_returns_series()

### Community 53 - "gram_charlier_pdf_ratio"
Cohesion: 0.33
Nodes (4): gram_charlier_pdf_ratio(), he3(), he4(), posterior_gram_charlier()

### Community 56 - "test_polygon_client.py"
Cohesion: 0.16
Nodes (13): calls_per_minute_from_env(), get_all(), _contrato(), _paginas(), _snapshot_grabado(), test_calls_per_minute_acepta_el_alias_viejo(), test_calls_per_minute_lee_el_nombre_largo(), test_calls_per_minute_sin_env_usa_el_default() (+5 more)

### Community 57 - "estimar_theta_esscher"
Cohesion: 0.50
Nodes (3): cumulantes_Q_desde_P(), estimar_theta_esscher(), objetivo()

### Community 59 - "Quadratic utility maximization U = mu'w - lambda/2 w'Sigma w"
Cohesion: 0.17
Nodes (10): BKM risk-neutral moments (MFIV, MFIS, MFIK), Historical MFIS time budget (bkm_hist_max_minutes), Cornish-Fisher VaR/ES (Maillard 2012), Market delta modes (historical, fixed, implied via SVIX), Entropy pooling posterior views, include_etfs_in_portfolio switch, Methodology knobs (lambda_annual, bkm_tail_mode, DELTA_MKT_MODO), QUBO/Ising candidate selection (+2 more)

### Community 63 - "optimizar_mvsk"
Cohesion: 0.40
Nodes (3): momentos_portafolio(), optimizar_mvsk(), utilidad_mvsk_negativa()

### Community 64 - "quadratic_utility.py"
Cohesion: 0.15
Nodes (8): armar_restricciones(), clean_symbol_table(), fila_iv_vs_reciente(), _parse_market_cap(), qubo_energy(), rechaza_iv_vs_reciente(), select_candidates_qubo(), select_optimal_candidates()

### Community 65 - "cache_get"
Cohesion: 0.15
Nodes (11): cache_get(), cache_permitida(), cache_set(), es_snapshot(), fechas_en_clave(), _ruta_cache(), _Resp, test_cache_de_disco_evita_llamadas_en_la_reejecucion() (+3 more)

### Community 66 - "score_candidate_portfolios"
Cohesion: 0.12
Nodes (10): comparison_lambdas(), frontier_curve(), frontier_lambda_grid(), portfolio_mu_final_metrics(), score_candidate_portfolios(), utility_terms(), test_constrained_frontier_passes_through_the_optimum(), test_lambda_scores_use_the_reference_lambda_and_mu_final() (+2 more)

### Community 67 - "test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados"
Cohesion: 0.18
Nodes (9): completar_etfs(), contar_etfs(), reserva_etf(), test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados(), test_completar_etfs_agrega_solo_lo_necesario_y_en_orden(), test_completar_etfs_devuelve_lo_que_haya_si_no_alcanza(), test_contar_etfs_sin_duplicados(), test_reserva_etf_toma_los_que_faltan_en_orden_de_ranking() (+1 more)

### Community 69 - "test_etf_floor_estacional.py"
Cohesion: 0.27
Nodes (6): _bloque_restricciones(), _correr_restricciones(), test_banda_que_ya_cumplia_no_cambia(), test_con_el_cuarto_etf_el_conservador_resuelve_sin_relajar(), test_sin_cuarto_etf_la_banda_se_relaja_y_quadprog_resuelve(), test_sin_relajar_falla_con_mensaje_claro_y_no_con_quadprog()

### Community 71 - "_RespuestaFalsa"
Cohesion: 0.22
Nodes (9): _RespuestaFalsa, test_get_json_403_is_not_retried_and_names_the_plan(), _get(), test_get_json_jitter_on_5xx_and_retry_after_wins(), test_get_json_non_transient_error_is_not_retried_nor_cached(), _get(), test_get_json_retries_on_429_respecting_retry_after(), test_get_json_strips_key_from_cache_key_and_sends_it() (+1 more)

### Community 72 - "etfs_necesarios"
Cohesion: 0.22
Nodes (6): diagnostico_banda_etf(), etfs_necesarios(), test_diagnostico_explica_el_piso_de_etf(), test_diagnostico_vacio_si_los_conteos_alcanzan(), test_etfs_necesarios(), test_etfs_necesarios_rechaza_max_weight_invalido()

### Community 73 - "restricciones_factibles"
Cohesion: 0.36
Nodes (8): restricciones_factibles(), test_caso_conservador_tal_como_llegaba_es_infactible_para_quadprog(), _quadprog(), _restricciones(), test_caso_conservador_es_infactible_y_quadprog_lo_confirma(), test_con_cuatro_etf_el_conservador_es_factible(), test_factibilidad_considera_el_tope_regional(), test_relajar_banda_lleva_el_piso_a_lo_alcanzable_y_queda_factible()

### Community 74 - "qu_metrics.py"
Cohesion: 0.10
Nodes (12): dispersion_usable(), estimate_bkm_history_calls(), filtro_delta_otm(), _finito(), lambda_monthly_from_annual(), mfis_max_minutes_from_env(), pasa_filtro_delta(), sector_implied_ready() (+4 more)

### Community 76 - "bkm_get_current_moments"
Cohesion: 0.25
Nodes (8): _asegurar_momentos_actuales(), bkm_compute_moments(), bkm_get_current_moments(), get_spot_safe_bkm(), is_us_ticker(), _momento_actual_bkm(), polygon_get_sector_etf(), polygon_get_sic_description()

### Community 77 - "Working with the graphify knowledge graph"
Cohesion: 0.33
Nodes (5): Freshness check, Git hygiene, Navigating, Verify before asserting, Working with the graphify knowledge graph

### Community 78 - "evaluar_historia_bkm"
Cohesion: 0.29
Nodes (5): spot_series_for(), evaluar_historia_bkm(), _fila(), _fila_bkm(), _spot_series_bkm()

### Community 79 - "higher_moments_admissible"
Cohesion: 0.29
Nodes (4): momentos_cola_historicos(), momentos_cola_historicos(), higher_moments_admissible(), test_higher_moments_admissible_pearson()

### Community 80 - "bkm_reconstruct_mfis_history"
Cohesion: 0.29
Nodes (4): bkm_compute_moments(), bkm_reconstruct_mfis_history(), _datos_con_precios(), mfik_cap_tenor()

### Community 81 - "polygon_contracts_asof"
Cohesion: 0.29
Nodes (4): bkm_fetch_otm_chain(), bkm_seleccion_fecha(), polygon_contracts_asof(), polygon_format_ticker()

### Community 82 - "bs_call_delta"
Cohesion: 0.33
Nodes (4): bs_call_delta(), test_atm_call_delta_always_above_half(), test_bs_call_delta_invalid_inputs_are_nan(), test_otm_call_delta_can_fall_below_old_threshold()

### Community 83 - "bkm_reconstruct_mfis_history"
Cohesion: 0.33
Nodes (3): bkm_reconstruct_mfis_history(), bkm_seleccion_fecha(), _datos_con_precios()

### Community 84 - "test_get_json_exhausts_retries_on_network_error"
Cohesion: 0.40
Nodes (3): n_fallos_transitorios(), test_get_json_exhausts_retries_on_network_error(), test_n_fallos_transitorios_excludes_missing_key()

### Community 85 - "candidatos_reposicion"
Cohesion: 0.40
Nodes (3): candidatos_reposicion(), test_reposicion_aplica_el_filtro_iv_a_quien_nunca_paso_por_el(), test_reposicion_bkm_no_trae_de_vuelta_a_mchi()

### Community 86 - "polygon_contracts_asof"
Cohesion: 0.40
Nodes (3): bkm_fetch_otm_chain(), polygon_contracts_asof(), polygon_format_ticker()

### Community 87 - "calibrar_ssvi_ticker"
Cohesion: 0.50
Nodes (3): calibrar_ssvi_ticker(), parse_chain(), polygon_fetch_chain()

### Community 90 - "is_us_ticker"
Cohesion: 0.50
Nodes (3): is_non_us_exchange(), is_non_us_exchange(), is_us_ticker()

### Community 93 - "siguiente_reposicion"
Cohesion: 0.50
Nodes (3): siguiente_reposicion(), test_siguiente_reposicion_prioriza_etf_cuando_faltan(), test_siguiente_reposicion_sin_etf_coincide_con_el_indice_secuencial()

## Knowledge Gaps
- **23 isolated node(s):** `Freshness check`, `Git hygiene`, `Navigating`, `Verify before asserting`, `Freshness check` (+18 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 426 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `max_drawdown()` connect `pytest` to `pandas`, `numpy`, `minimum_variance.py`, `minimum_variance_(seasonal_version).py`, `risk_estimators.py`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **What connects `Freshness check`, `Git hygiene`, `Navigating` to the rest of the system?**
  _23 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `quadratic_utility_(seasonal_version).py` be split into smaller, more focused modules?**
  _Cohesion score 0.12280701754385964 - nodes in this community are weakly interconnected._
- **Why does `Risk Profile Audit (configuration per investor profile)` connect `Risk Profile Audit (configuration per investor profile)` to `portfolio_constraints.py`, `Quadratic utility maximization U = mu'w - lambda/2 w'Sigma w`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Should `pandas` be split into smaller, more focused modules?**
  _Cohesion score 0.06568832983927324 - nodes in this community are weakly interconnected._
- **Why does `Workflow architecture (shared modules feed standalone optimizers)` connect `portfolio_constraints.py` to `quadratic_utility.py`, `pandas`, `polygon_client.py`, `minimum_variance.py`, `market_data.py`, `qu_metrics.py`, `pipeline_io.py`, `risk_estimators.py`, `black_litterman.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Should `numpy` be split into smaller, more focused modules?**
  _Cohesion score 0.07422402159244265 - nodes in this community are weakly interconnected._