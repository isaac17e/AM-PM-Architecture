# Graph Report - AM-PM-Architecture  (2026-10-13)

## Corpus Check
- 33 files · ~130,897 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 3, .ini 1)

## Summary
- 1416 nodes · 3150 edges · 66 communities (55 shown, 11 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 70 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a7e9f26b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- pytest
- test_pipeline_io.py
- quadratic_utility_(seasonal_version).py
- bl_metrics.py
- quadratic_utility.py
- get_json
- bkm_reconstruct_mfis_history
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
- ledoit_wolf_constant_correlation
- frames_from_yf_download
- risk_estimators.py
- fetch_otm_chain
- test_mv_cola_y_delta.py
- align_prices_to_calendar
- Risk Profile Audit (configuration per investor profile)
- test_cycle2_fixes.py
- test_risk_profile.py
- _GetterFalso
- bkm_get_current_moments
- fetch_option_aggs
- test_qu_metrics.py
- drop_partial_last_week
- average_abs_correlation
- test_tail_prune_loop.py
- _precargar_spots_bkm
- sector_implied_ready
- test_single_retries_do_not_overlap
- descargar_precio
- _YahooFalso
- mfis_tail_decision
- test_polygon_client.py
- pandas
- black_litterman.py
- dispersion_weights
- score_candidate_portfolios
- resumen_ajuste_iv
- is_us_ticker
- elegir_spot_momentos
- covariance_min_history
- test_etf_floor_refill.py
- _Limitador
- mfis_check_deadline
- higher_moments_admissible
- test_risk_estimators.py
- estimate_bkm_history_calls
- portfolio_returns_skipna
- frontier_lambda_grid
- dedupe_share_classes
- implied_variance_to_horizon

## God Nodes (most connected - your core abstractions)
1. `get_json()` - 27 edges
2. `to_years()` - 25 edges
3. `calibrate_iv_carry()` - 19 edges
4. `fetch_otm_chain()` - 19 edges
5. `fit_ssvi()` - 18 edges
6. `es_transitorio()` - 18 edges
7. `Risk Profile Audit (configuration per investor profile)` - 18 edges
8. `calibrar_superficie_ssvi()` - 17 edges
9. `get_all()` - 15 edges
10. `polygon_format_ticker()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Reachable ETF floor and LP feasibility check` --semantically_similar_to--> `Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12)`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `lambda3/lambda4 derived from gamma (CRRA Taylor expansion)` --semantically_similar_to--> `BL lambda3/lambda4 closed form from gamma`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `test_bs_price_matches_closed_form_and_parity()` --calls--> `bs_price()`  [EXTRACTED]
  tests/test_ajuste_iv_tasa.py → risk_estimators.py
- `test_expiry_rank_prefers_50_over_15_for_a_30_day_target()` --calls--> `expiry_rank_columns()`  [EXTRACTED]
  tests/test_polygon_client.py → polygon_client.py
- `_mercado()` --calls--> `bs_implied_vol()`  [EXTRACTED]
  tests/test_ajuste_iv_tasa.py → risk_estimators.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared estimation modules feeding the three optimizers** — polygon_client, risk_estimators, market_data, portfolio_constraints, qu_metrics, bl_metrics, pipeline_io, quadratic_utility, minimum_variance, black_litterman [EXTRACTED 1.00]
- **Options-implied tail risk pipeline (BKM, Q to P, Cornish-Fisher)** — readme_bkm, readme_q_to_p, readme_cornish_fisher, readme_co_moments, readme_ssvi_fit [INFERRED 0.85]
- **Risk-profile calibration (gamma ladder, CRRA lambdas, lambda-only aversion, pen_ret)** — docs_risk_profile_audit_gamma_ladder, docs_risk_profile_audit_crra_lambdas, docs_risk_profile_audit_lambda_only_risk_aversion, docs_risk_profile_audit_lambda_calibration [INFERRED 0.85]

## Communities (66 total, 11 thin omitted)

### Community 0 - "pytest"
Cohesion: 0.10
Nodes (30): crra_taylor_lambdas(), integration_strike_bounds(), market_delta(), variance_annual_to_horizon(), _cadena_ssvi(), _precios_con_paridad(), test_apply_vol_q_to_p_does_not_haircut_historical_vol(), test_calibrar_superficie_ignora_leaps_y_quotes_rotos() (+22 more)

### Community 1 - "test_pipeline_io.py"
Cohesion: 0.09
Nodes (18): horizon_from_month_list(), horizon_from_months(), load_bl_input(), select_views(), _escribir(), _leer(), test_atomic_replace(), test_bl_input_invalid_or_missing() (+10 more)

### Community 2 - "quadratic_utility_(seasonal_version).py"
Cohesion: 0.07
Nodes (14): print_diagnostics(), armar_restricciones(), bkm_iv_chain_to_prices(), bs_price(), clean_symbol_table(), download_fx_prices(), _parse_market_cap(), qubo_energy() (+6 more)

### Community 3 - "bl_metrics.py"
Cohesion: 0.06
Nodes (22): apply_vol_q_to_p(), calibrar_superficie_ssvi(), _fecha_naive(), forward_por_paridad(), iv_vol_at_horizon(), mfiv_or_horizon_variance(), mfiv_vs_atm(), momentos_fallback() (+14 more)

### Community 4 - "quadratic_utility.py"
Cohesion: 0.07
Nodes (20): spot_series_for(), bkm_clave_historia(), bkm_fechas_pendientes(), clean_symbol_table(), evaluar_historia_bkm(), _evaluar_historia_bkm(), _fila(), _ff3_betas() (+12 more)

### Community 5 - "get_json"
Cohesion: 0.07
Nodes (30): _avisar_403(), _avisar_sin_api_key(), cache_get(), cache_permitida(), cache_set(), _con_api_key(), es_snapshot(), _espera_reintento() (+22 more)

### Community 6 - "bkm_reconstruct_mfis_history"
Cohesion: 0.14
Nodes (10): bkm_clave_historia(), bkm_fechas_pendientes(), bkm_reconstruct_mfis_history(), bkm_seleccion_fecha(), _datos_con_precios(), evaluar_historia_bkm(), _fila(), _fila_bkm() (+2 more)

### Community 7 - "qu_metrics.py"
Cohesion: 0.13
Nodes (19): bs_call_delta_from_vol(), delta_cushion(), evaluar_delta_candidato(), filtro_delta_otm(), _finito(), mfis_max_minutes_from_env(), otm_log_moneyness(), pasa_filtro_delta() (+11 more)

### Community 8 - "minimum_variance.py"
Cohesion: 0.11
Nodes (10): bkm_motivo_fallback(), bkm_resumen_fallbacks(), build_qp_constraints(), clean_symbol_table(), constraints_feasible(), download_ticker_data(), get_atm_iv_safe(), get_currency_for_ticker() (+2 more)

### Community 9 - "minimum_variance_(seasonal_version).py"
Cohesion: 0.10
Nodes (14): bkm_iv_chain_to_prices(), bkm_motivo_fallback(), bkm_resumen_fallbacks(), bs_price(), build_qp_constraints(), clean_symbol_table(), constraints_feasible(), download_ticker_data() (+6 more)

### Community 10 - "market_data.py"
Cohesion: 0.09
Nodes (15): _campo(), combinar_tickers(), _con_reintentos(), es_ticker_formato_us(), _market_cap_yf(), normalize_currency(), _positivo(), price_scale_factor() (+7 more)

### Community 11 - "test_market_cap_internacional.py"
Cohesion: 0.07
Nodes (29): currency_from_suffix(), default_market_cap_cache_path(), _escribir_cache(), _leer_cache(), market_caps_usd(), _llamar_caps(), _llamar_fx(), ordenar_por_market_cap() (+21 more)

### Community 12 - "pipeline_io.py"
Cohesion: 0.12
Nodes (15): _add_months(), _atomic_write(), _date_or_none(), export_portfolio(), _export_portfolio(), _int_or_none(), _jsonify(), _metrics() (+7 more)

### Community 13 - "to_years"
Cohesion: 0.19
Nodes (13): get_polygon_option_snapshot(), get_polygon_option_snapshot(), expiry_rank_columns(), pares_call_put(), polygon_get_atm_option(), polygon_get_atm_option(), bs_implied_vol(), bs_price() (+5 more)

### Community 14 - "test_qu_horizonte.py"
Cohesion: 0.11
Nodes (19): calcular_metricas_riesgo_cola(), _pesos_normalizados(), var_cvar_cornish_fisher(), var_cvar_historico(), cornish_fisher_at_horizon(), qp_inputs_at_horizon(), var_cvar_cornish_fisher(), _pesos() (+11 more)

### Community 15 - "test_market_data.py"
Cohesion: 0.17
Nodes (12): resolve_currencies(), resolve_execution_months(), test_normalize_currency(), test_price_scale_factor(), test_resolve_currencies_override_applies_without_provider(), test_resolve_currencies_pence_normalized_no_conflict_with_suffix(), test_resolve_currencies_provider_nan_falls_back(), test_resolve_currencies_provider_wins_over_override_hsbc_bp() (+4 more)

### Community 16 - "test_portfolio_constraints.py"
Cohesion: 0.06
Nodes (38): markowitz_clasico(), beta_band_columns(), beta_band_text(), beta_coverage_additions(), _rango(), beta_range_reachable(), bs_call_delta(), build_weight_constraints() (+30 more)

### Community 17 - "test_script_smoke.py"
Cohesion: 0.22
Nodes (11): _alias_importados(), _asignaciones_de_modulo(), _correr_bl(), _nombres(), sombras_de_import(), test_bl_input_file_overrides_tickers_and_views(), test_bl_risk_profile_env_and_cli(), test_bl_universe_file_drops_default_views() (+3 more)

### Community 18 - "numpy"
Cohesion: 0.10
Nodes (20): clip_negligible_weights(), log_portfolio_return(), optimizar_mvsk(), frontier_curve(), portfolio_mu_final_metrics(), nearest_psd(), portfolio_log_returns(), rescale_panel() (+12 more)

### Community 19 - "fit_ssvi"
Cohesion: 0.16
Nodes (14): fit_ssvi(), objetivo(), _params(), _penalty(), _relativos(), _sigmoid(), _grupos_vencimiento(), ssvi_total_variance() (+6 more)

### Community 21 - "test_universo_y_delta_estacional.py"
Cohesion: 0.18
Nodes (12): _descartados(), _formato_us_viejo(), _fuente(), _internacionales_del_script(), _literales(), test_bl_no_manda_internacionales_a_polygon(), test_conteo_de_colchon_separa_umbrales_y_aguanta_el_horizonte(), test_conteo_del_filtro_estacional_sobre_universo_sintetico() (+4 more)

### Community 22 - "get_spot_history"
Cohesion: 0.15
Nodes (14): get_spot_history(), _retry_spot_single(), _usable_spot(), _cierres(), test_get_spot_history_downloads_the_batch_once_and_workers_only_read(), batch(), single(), test_get_spot_history_falls_through_to_the_next_provider() (+6 more)

### Community 23 - "test_ajuste_iv_tasa.py"
Cohesion: 0.19
Nodes (16): _contrato(), _fuente(), _funcion(), _mercado(), _smile(), test_atm_snapshot_fetches_both_sides_and_adjusts_iv(), test_bs_implied_vol_round_trip_and_out_of_bounds(), test_bs_price_matches_closed_form_and_parity() (+8 more)

### Community 24 - "ledoit_wolf_constant_correlation"
Cohesion: 0.15
Nodes (13): average_correlation(), cov_ewma_shrunk(), effective_sample_size(), ewma_cov(), ewma_weights(), ledoit_wolf_constant_correlation(), _lw_ewma_referencia_delta(), test_cov_ewma_shrunk_pipeline() (+5 more)

### Community 25 - "frames_from_yf_download"
Cohesion: 0.11
Nodes (10): default_spot_providers(), _frame_from_close(), frames_from_yf_download(), _naive_dates(), yfinance_spot_batch(), yfinance_spot_single(), test_frames_from_yf_download_reads_both_multiindex_orders(), test_yfinance_batch_is_one_unadjusted_download() (+2 more)

### Community 26 - "risk_estimators.py"
Cohesion: 0.07
Nodes (26): compute_marginal_cvar_contrib(), compute_marginal_cvar_contrib(), cornish_fisher_domain(), cornish_fisher_es_gradient(), cornish_fisher_moments(), cornish_fisher_params(), a_parametros(), residuo() (+18 more)

### Community 27 - "fetch_otm_chain"
Cohesion: 0.15
Nodes (10): polygon_fetch_chain(), bkm_fetch_otm_chain(), bkm_fetch_otm_chain(), fetch_otm_chain(), polygon_format_ticker(), bkm_fetch_otm_chain(), polygon_get_sector_etf(), polygon_get_sic_description() (+2 more)

### Community 28 - "test_mv_cola_y_delta.py"
Cohesion: 0.22
Nodes (13): _bucle_de_cola(), _descartes(), _fuente(), _funcion(), test_conteo_estable_entre_horizontes(), test_conteos_por_umbral_conservador_moderado_agresivo(), test_defaults_del_filtro_delta_en_mv(), test_fallback_historico_activo_por_defecto() (+5 more)

### Community 29 - "align_prices_to_calendar"
Cohesion: 0.19
Nodes (11): align_prices_to_calendar(), align_daily_panel(), _bdays(), _precios_dos_mercados(), test_align_drops_low_coverage_ticker(), test_align_fills_local_holiday_instead_of_dropping_row(), test_align_long_gap_not_filled_beyond_limit(), test_align_reindexes_to_calendar_and_keeps_offcalendar_level() (+3 more)

### Community 30 - "Risk Profile Audit (configuration per investor profile)"
Cohesion: 0.05
Nodes (41): Asset Allocation (FICs) am_pm/profiles.py mandates, Risk Profile Audit (configuration per investor profile), Black-Litterman PERFILES (omega_scale, tau, gamma_ra), COL Portfolio Architecture (proposed profile bands, max Sharpe), QU OTM delta filter as annual IV cap, Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12), International ticker format filter and region caps, Lambda calibration with pen_ret (+33 more)

### Community 31 - "test_cycle2_fixes.py"
Cohesion: 0.05
Nodes (29): resolve_risk_free_rate(), estimate_minutes(), set_rate_limit(), _clave_cap(), orden_prioridad_mfis(), clave(), plan_bkm_history_budget(), _plan_ronda_bkm() (+21 more)

### Community 32 - "test_risk_profile.py"
Cohesion: 0.21
Nodes (10): _cli_risk_profile(), resolve_risk_profile(), _literales(), _presets(), test_el_perfil_de_qu_y_mv_es_una_banda_de_beta(), test_preset_agresivo_no_cambia_los_literales(), test_presets_de_mv_y_qu_coinciden_con_la_auditoria(), test_resolve_default_si_no_hay_env_ni_cli() (+2 more)

### Community 33 - "_GetterFalso"
Cohesion: 0.12
Nodes (15): default_ff_cache_dir(), _escribir_atomico(), fetch_fama_french(), parse_fama_french_zip(), _ff(), _GetterFalso, _Resp, test_ff_cache_corrupta_cuenta_como_failed_y_un_zip_invalido_no_pisa_la_cache() (+7 more)

### Community 34 - "bkm_get_current_moments"
Cohesion: 0.22
Nodes (9): _asegurar_momentos_actuales(), bkm_fetch_otm_chain(), bkm_get_current_moments(), get_spot_safe_bkm(), is_us_ticker(), _momento_actual_bkm(), polygon_format_ticker(), polygon_get_sector_etf() (+1 more)

### Community 35 - "fetch_option_aggs"
Cohesion: 0.15
Nodes (9): fetch_option_aggs(), close_near_from_bars(), contract_agg_ranges(), bkm_precios_en_rango(), polygon_contract_close_near(), bkm_precios_en_rango(), polygon_contract_close_near(), _barra() (+1 more)

### Community 36 - "test_qu_metrics.py"
Cohesion: 0.06
Nodes (29): annualize_monthly(), clip_implied_correlation(), history_window(), mfiv_annual_vol(), pool_sin_no_procesados_mfis(), scale_option_deltas(), select_historical_otm(), stitch_covariance() (+21 more)

### Community 37 - "drop_partial_last_week"
Cohesion: 0.43
Nodes (6): drop_partial_last_week(), _semanal(), test_drop_partial_last_week_empty_and_dataframe(), test_drop_partial_last_week_friday_kept(), test_drop_partial_last_week_thursday_before_holiday_friday(), test_drop_partial_last_week_wednesday_dropped()

### Community 38 - "average_abs_correlation"
Cohesion: 0.33
Nodes (5): average_abs_correlation(), _corr_abc(), test_average_abs_correlation_ignores_sign_and_order(), test_average_abs_correlation_uses_full_row(), test_old_alphabetical_grouping_drops_last_ticker()

### Community 39 - "test_tail_prune_loop.py"
Cohesion: 0.26
Nodes (6): _bucle_de_poda(), _correr(), test_block_cut_is_skipped_when_it_leaves_too_few_names(), test_min_weight_keeps_capped_defensives(), test_names_below_threshold_are_cut_in_one_step(), test_prune_loop_survives_floor_weights()

### Community 44 - "descargar_precio"
Cohesion: 0.20
Nodes (5): asegurar_fx(), descargar_fx_moneda(), descargar_precio(), _par_fx(), convertir_serie_a_usd()

### Community 47 - "mfis_tail_decision"
Cohesion: 0.29
Nodes (4): mfis_tail_decision(), test_mfis_tail_decision(), test_mfis_tail_default_upper_matches_old_inequality(), test_mfis_tail_rejects_unknown_mode()

### Community 48 - "test_polygon_client.py"
Cohesion: 0.07
Nodes (29): calls_per_minute_from_env(), default_cache_dir(), es_transitorio(), get_all(), _parse_calls_per_min(), polygon_contracts_asof(), test_calls_per_min_alias_y_sin_tope(), _contrato() (+21 more)

### Community 49 - "pandas"
Cohesion: 0.17
Nodes (14): calibrar_ssvi_ticker(), momentos_realizados_rolling(), parse_chain(), market_beta(), seasonal_vol_ratio(), _mercado_y_activos(), test_market_beta_caja_y_commodities_usan_ols_crudo_sin_blume(), test_market_beta_raw_tickers_vacio_aplica_blume_a_todos() (+6 more)

### Community 50 - "black_litterman.py"
Cohesion: 0.04
Nodes (32): aplicar_limites_cartera(), bootstrap_estacionario(), calcular_bkm_moments(), construir_restricciones(), cumulantes_Q_desde_P(), _diag_ssvi(), entropy_pooling(), estimar_theta_esscher() (+24 more)

### Community 52 - "dispersion_weights"
Cohesion: 0.25
Nodes (6): dispersion_usable(), dispersion_weights(), test_dispersion_cap_share_is_the_basket_over_known_spy_caps(), test_dispersion_weights_cap_weighted_spy_names_with_iv(), test_dispersion_weights_equal_when_a_cap_is_missing(), test_dispersion_weights_insufficient_basket()

### Community 53 - "score_candidate_portfolios"
Cohesion: 0.17
Nodes (8): comparison_lambdas(), lambda_monthly_from_annual(), score_candidate_portfolios(), utility_terms(), test_lambda_monthly_from_annual_scales_by_twelve_and_is_opt_in(), test_lambda_scores_use_the_reference_lambda_and_mu_final(), test_pen_ret_is_nan_when_return_is_not_positive(), test_utility_terms_show_when_the_penalty_binds()

### Community 55 - "resumen_ajuste_iv"
Cohesion: 0.33
Nodes (4): resumen_ajuste_iv(), texto_ajuste_iv(), test_resumen_ajuste_iv_counts_only_queried_chains(), test_texto_ajuste_iv_without_pairs()

### Community 56 - "is_us_ticker"
Cohesion: 0.11
Nodes (13): is_non_us_exchange(), is_us_ticker(), _asegurar_momentos_actuales(), bkm_compute_moments(), bkm_get_current_moments(), bkm_iv_chain_to_prices(), bkm_reconstruct_mfis_history(), bkm_seleccion_fecha() (+5 more)

### Community 64 - "covariance_min_history"
Cohesion: 0.33
Nodes (4): columns_with_min_obs(), covariance_min_history(), test_columns_with_min_obs_keeps_long_history(), test_covariance_min_history_uses_each_series_full_sample()

### Community 65 - "test_etf_floor_refill.py"
Cohesion: 0.05
Nodes (40): candidatos_reposicion(), completar_etfs(), contar_etfs(), diagnostico_banda_etf(), etfs_necesarios(), relajar_banda_etf(), reserva_etf(), restricciones_factibles() (+32 more)

### Community 74 - "mfis_check_deadline"
Cohesion: 0.22
Nodes (5): mfis_check_deadline(), mfis_deadline(), MfisTiempoAgotado, test_mfis_check_deadline_usa_perf_counter_por_defecto(), test_mfis_deadline_es_reloj_real_y_none_sin_limite()

### Community 76 - "higher_moments_admissible"
Cohesion: 0.10
Nodes (19): bkm_compute_moments(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), get_spot_safe(), momentos_cola_historicos(), bkm_compute_moments() (+11 more)

### Community 79 - "test_risk_estimators.py"
Cohesion: 0.07
Nodes (25): mdd_from_log_returns(), extract_metrics(), annualize(), max_drawdown(), scale_moments(), test_mdd_log_matches_exp_cumsum_not_simple_compounding(), _lw_constant_correlation_referencia(), panel() (+17 more)

### Community 82 - "portfolio_returns_skipna"
Cohesion: 0.50
Nodes (3): portfolio_returns_skipna(), portfolio_returns_series(), test_portfolio_returns_skipna_does_not_drop_the_month()

### Community 103 - "implied_variance_to_horizon"
Cohesion: 0.18
Nodes (7): bkm_annual_vol(), bkm_annual_vol(), implied_variance_to_horizon(), q_to_p_vol(), test_implied_variance_to_horizon_arrays_and_nan(), test_implied_variance_to_horizon_uses_real_dte(), test_q_to_p_vol_bounds_and_fallback()

## Knowledge Gaps
- **15 isolated node(s):** `pandas>=2.0`, `plotly>=5.18`, `scipy>=1.10`, `statsmodels>=0.14`, `Pull request merge order (stacked PRs #2 to #4 then this PR)` (+10 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 445 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `fit_ssvi()` connect `fit_ssvi` to `numpy`, `bl_metrics.py`, `qu_metrics.py`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **What connects `pandas>=2.0`, `plotly>=5.18`, `scipy>=1.10` to the rest of the system?**
  _15 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `pytest` be split into smaller, more focused modules?**
  _Cohesion score 0.10384068278805121 - nodes in this community are weakly interconnected._
- **Why does `Workflow architecture (shared modules feed standalone optimizers)` connect `pipeline_io.py` to `quadratic_utility_(seasonal_version).py`, `bl_metrics.py`, `quadratic_utility.py`, `qu_metrics.py`, `minimum_variance.py`, `market_data.py`, `test_portfolio_constraints.py`, `black_litterman.py`, `risk_estimators.py`, `Risk Profile Audit (configuration per investor profile)`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Should `test_pipeline_io.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08817204301075268 - nodes in this community are weakly interconnected._
- **Should `quadratic_utility_(seasonal_version).py` be split into smaller, more focused modules?**
  _Cohesion score 0.06606606606606606 - nodes in this community are weakly interconnected._
- **Should `bl_metrics.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06282051282051282 - nodes in this community are weakly interconnected._