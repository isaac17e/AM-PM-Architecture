# Graph Report - AM-PM-Architecture  (2026-10-06)

## Corpus Check
- 32 files · ~112,977 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 1, .ini 1)

## Summary
- 1250 nodes · 2772 edges · 82 communities (58 shown, 24 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 67 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- ETF Band & Feasibility (seasonal)
- Polygon Options Chain (seasonal)
- Polygon Options Chain
- SSVI Fit & Vol Q-to-P
- Portfolio Moments & Rescaling
- Polygon Client & Cache
- CRRA Lambdas & Delta Tests
- OTM Delta Filter & Constraints
- BKM Moments & Drawdown
- BKM Moments & Drawdown (seasonal)
- Market Data: Tickers & Caps
- FX & Market Cap Lookups
- Pipeline JSON Export
- BL Input & Pipeline IO
- Cornish-Fisher & Ledoit-Wolf
- Calendar Alignment & Currency
- Return Target & Tail Pruning
- README: BL Architecture & BKM
- Moment Horizon Scaling
- SSVI Calibration
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81

## God Nodes (most connected - your core abstractions)
1. `get_json()` - 27 edges
2. `to_years()` - 19 edges
3. `fit_ssvi()` - 18 edges
4. `es_transitorio()` - 18 edges
5. `Risk Profile Audit (configuration per investor profile)` - 18 edges
6. `calibrar_superficie_ssvi()` - 17 edges
7. `fetch_otm_chain()` - 16 edges
8. `get_all()` - 15 edges
9. `market_caps_usd()` - 14 edges
10. `resolve_currencies()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `lambda3/lambda4 derived from gamma (CRRA Taylor expansion)` --semantically_similar_to--> `BL lambda3/lambda4 closed form from gamma`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `Reachable ETF floor and LP feasibility check` --semantically_similar_to--> `Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12)`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `test_currency_from_suffix()` --calls--> `currency_from_suffix()`  [EXTRACTED]
  tests/test_market_data.py → market_data.py
- `test_vol_annual_scales_with_sqrt_horizon()` --calls--> `vol_annual_to_horizon()`  [EXTRACTED]
  tests/test_bl_metrics.py → bl_metrics.py
- `test_mfiv_fallback_uses_horizon_variance_not_annual()` --calls--> `variance_annual_to_horizon()`  [EXTRACTED]
  tests/test_bl_metrics.py → bl_metrics.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared estimation modules feeding the three optimizers** — polygon_client, risk_estimators, market_data, portfolio_constraints, qu_metrics, bl_metrics, pipeline_io, quadratic_utility, minimum_variance, black_litterman [EXTRACTED 1.00]
- **Options-implied tail risk pipeline (BKM, Q to P, Cornish-Fisher)** — readme_bkm, readme_q_to_p, readme_cornish_fisher, readme_co_moments, readme_ssvi_fit [INFERRED 0.85]
- **Risk-profile calibration (gamma ladder, CRRA lambdas, lambda-only aversion, pen_ret)** — docs_risk_profile_audit_gamma_ladder, docs_risk_profile_audit_crra_lambdas, docs_risk_profile_audit_lambda_only_risk_aversion, docs_risk_profile_audit_lambda_calibration [INFERRED 0.85]

## Communities (82 total, 24 thin omitted)

### Community 0 - "ETF Band & Feasibility (seasonal)"
Cohesion: 0.05
Nodes (41): candidatos_reposicion(), completar_etfs(), contar_etfs(), diagnostico_banda_etf(), etfs_necesarios(), relajar_banda_etf(), reserva_etf(), restricciones_factibles() (+33 more)

### Community 1 - "Polygon Options Chain (seasonal)"
Cohesion: 0.05
Nodes (35): spot_series_for(), armar_restricciones(), _asegurar_momentos_actuales(), bkm_clave_historia(), bkm_compute_moments(), bkm_fechas_pendientes(), bkm_fetch_otm_chain(), bkm_get_current_moments() (+27 more)

### Community 2 - "Polygon Options Chain"
Cohesion: 0.06
Nodes (34): armar_restricciones(), _asegurar_momentos_actuales(), bkm_clave_historia(), bkm_fechas_pendientes(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_iv_chain_to_prices(), bkm_seleccion_fecha() (+26 more)

### Community 3 - "SSVI Fit & Vol Q-to-P"
Cohesion: 0.06
Nodes (22): apply_vol_q_to_p(), calibrar_superficie_ssvi(), elegir_spot_momentos(), _fecha_naive(), forward_por_paridad(), iv_vol_at_horizon(), mfiv_or_horizon_variance(), momentos_fallback() (+14 more)

### Community 4 - "Portfolio Moments & Rescaling"
Cohesion: 0.07
Nodes (28): clip_negligible_weights(), log_portfolio_return(), markowitz_clasico(), optimizar_mvsk(), port_ret_row(), clip_implied_correlation(), comparison_lambdas(), scale_option_deltas() (+20 more)

### Community 5 - "Polygon Client & Cache"
Cohesion: 0.09
Nodes (24): _avisar_403(), _avisar_sin_api_key(), cache_get(), cache_permitida(), cache_set(), _con_api_key(), es_snapshot(), _espera_reintento() (+16 more)

### Community 6 - "CRRA Lambdas & Delta Tests"
Cohesion: 0.12
Nodes (29): crra_taylor_lambdas(), integration_strike_bounds(), market_delta(), test_apply_vol_q_to_p_does_not_haircut_historical_vol(), test_calibrar_superficie_ignora_leaps_y_quotes_rotos(), test_clip_negligible_weights_drops_solver_dust(), test_crra_taylor_lambdas_match_profile_ladder(), test_crra_taylor_terms_are_the_crra_expansion() (+21 more)

### Community 7 - "OTM Delta Filter & Constraints"
Cohesion: 0.12
Nodes (20): Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12), Validation results of QU runs by profile (Oct 2026), build_weight_constraints(), bs_call_delta_from_vol(), delta_cushion(), evaluar_delta_candidato(), filtro_delta_otm(), _finito() (+12 more)

### Community 8 - "BKM Moments & Drawdown"
Cohesion: 0.11
Nodes (18): bkm_annual_vol(), bkm_compute_moments(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), bs_price(), clean_symbol_table() (+10 more)

### Community 9 - "BKM Moments & Drawdown (seasonal)"
Cohesion: 0.11
Nodes (18): bkm_annual_vol(), bkm_compute_moments(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), bs_price(), clean_symbol_table() (+10 more)

### Community 10 - "Market Data: Tickers & Caps"
Cohesion: 0.11
Nodes (17): _campo(), combinar_tickers(), _con_reintentos(), currency_from_suffix(), default_market_cap_cache_path(), es_ticker_formato_us(), _escribir_cache(), _leer_cache() (+9 more)

### Community 11 - "FX & Market Cap Lookups"
Cohesion: 0.11
Nodes (19): _llamar_caps(), _llamar_fx(), tabla_market_cap_texto(), _ordenar(), _proveedores(), cap_provider(), fx_provider(), test_cache_corrupta_no_rompe() (+11 more)

### Community 12 - "Pipeline JSON Export"
Cohesion: 0.12
Nodes (17): _add_months(), _atomic_write(), _date_or_none(), export_portfolio(), _export_portfolio(), horizon_from_months(), _int_or_none(), _jsonify() (+9 more)

### Community 13 - "BL Input & Pipeline IO"
Cohesion: 0.10
Nodes (16): horizon_from_month_list(), load_bl_input(), select_views(), _escribir(), _leer(), test_atomic_replace(), test_bl_input_invalid_or_missing(), test_bl_input_universe_uses_only_tickers() (+8 more)

### Community 14 - "Cornish-Fisher & Ledoit-Wolf"
Cohesion: 0.10
Nodes (17): mdd_from_log_returns(), max_drawdown(), q_to_p_correlation(), var_cvar_cornish_fisher(), _lw_constant_correlation_referencia(), panel(), retornos(), retornos_shock_covid() (+9 more)

### Community 15 - "Calendar Alignment & Currency"
Cohesion: 0.13
Nodes (20): align_prices_to_calendar(), resolve_currencies(), resolve_execution_months(), _bdays(), _precios_dos_mercados(), test_align_drops_low_coverage_ticker(), test_align_fills_local_holiday_instead_of_dropping_row(), test_align_long_gap_not_filled_beyond_limit() (+12 more)

### Community 16 - "Return Target & Tail Pruning"
Cohesion: 0.12
Nodes (18): bs_call_delta(), prune_order(), relax_group_band(), with_return_target(), _base(), _minvar(), _slack(), test_atm_call_delta_always_above_half() (+10 more)

### Community 17 - "README: BL Architecture & BKM"
Cohesion: 0.12
Nodes (12): BKM risk-neutral moments (MFIV, MFIS, MFIK), Historical MFIS time budget (bkm_hist_max_minutes), Cornish-Fisher VaR/ES (Maillard 2012), Market delta modes (historical, fixed, implied via SVIX), Entropy pooling posterior views, include_etfs_in_portfolio switch, Methodology knobs (lambda_annual, bkm_tail_mode, DELTA_MKT_MODO), QUBO/Ising candidate selection (+4 more)

### Community 18 - "Moment Horizon Scaling"
Cohesion: 0.11
Nodes (15): momentos_cola_historicos(), momentos_cola_historicos(), annualize_monthly(), annualize(), scale_bkm_moments(), scale_moments(), to_years(), test_annualize_monthly_uses_twelve_not_horizon() (+7 more)

### Community 19 - "SSVI Calibration"
Cohesion: 0.13
Nodes (17): fit_ssvi(), objetivo(), _params(), _penalty(), _relativos(), _sigmoid(), _grupos_vencimiento(), ssvi_total_variance() (+9 more)

### Community 20 - "Community 20"
Cohesion: 0.11
Nodes (15): momentos_realizados_rolling(), _spot_bkm(), portfolio_returns_skipna(), shrink_mu_to_prior(), stitch_covariance(), summarize_yearly_mdd(), portfolio_returns_series(), portfolio_returns_series() (+7 more)

### Community 21 - "Community 21"
Cohesion: 0.14
Nodes (14): convertir_serie_a_usd(), _descartados(), _formato_us_viejo(), _fuente(), _internacionales_del_script(), _literales(), test_bl_no_manda_internacionales_a_polygon(), test_conteo_de_colchon_separa_umbrales_y_aguanta_el_horizonte() (+6 more)

### Community 22 - "Community 22"
Cohesion: 0.13
Nodes (15): get_spot_history(), _retry_spot_single(), _usable_spot(), _cierres(), test_get_spot_history_downloads_the_batch_once_and_workers_only_read(), batch(), single(), test_get_spot_history_falls_through_to_the_next_provider() (+7 more)

### Community 23 - "Community 23"
Cohesion: 0.12
Nodes (15): es_transitorio(), expiry_rank_columns(), fetch_otm_chain(), is_us_ticker(), test_es_transitorio_false(), test_es_transitorio_true(), test_expiry_rank_prefers_50_over_15_for_a_30_day_target(), test_fetch_otm_chain_formats_class_share_and_skips_non_us() (+7 more)

### Community 24 - "Community 24"
Cohesion: 0.15
Nodes (13): average_correlation(), cov_ewma_shrunk(), effective_sample_size(), ewma_cov(), ewma_weights(), ledoit_wolf_constant_correlation(), _lw_ewma_referencia_delta(), test_cov_ewma_shrunk_pipeline() (+5 more)

### Community 25 - "Community 25"
Cohesion: 0.11
Nodes (10): default_spot_providers(), _frame_from_close(), frames_from_yf_download(), _naive_dates(), yfinance_spot_batch(), yfinance_spot_single(), test_frames_from_yf_download_reads_both_multiindex_orders(), test_yfinance_batch_is_one_unadjusted_download() (+2 more)

### Community 26 - "Community 26"
Cohesion: 0.16
Nodes (12): calls_per_minute_from_env(), get_all(), _contrato(), _paginas(), _snapshot_grabado(), test_calls_per_minute_acepta_el_alias_viejo(), test_calls_per_minute_lee_el_nombre_largo(), test_calls_per_minute_sin_env_usa_el_default() (+4 more)

### Community 27 - "Community 27"
Cohesion: 0.15
Nodes (13): cornish_fisher_domain(), cornish_fisher_moments(), cornish_fisher_params(), a_parametros(), residuo(), cornish_fisher_tail(), cornish_fisher_z(), test_cornish_fisher_es_matches_numerical_integration() (+5 more)

### Community 28 - "Community 28"
Cohesion: 0.20
Nodes (13): _bucle_de_cola(), _descartes(), _fuente(), _funcion(), test_conteo_estable_entre_horizontes(), test_conteos_por_umbral_conservador_moderado_agresivo(), test_defaults_del_filtro_delta_en_mv(), test_fallback_historico_activo_por_defecto() (+5 more)

### Community 29 - "Community 29"
Cohesion: 0.16
Nodes (11): aplicar_limites_cartera(), bs_price(), calcular_bkm_moments(), calibrar_ssvi_ticker(), otm_price_ssvi(), parse_chain(), phi_powerlaw(), polygon_fetch_chain() (+3 more)

### Community 30 - "Community 30"
Cohesion: 0.15
Nodes (15): Asset Allocation (FICs) am_pm/profiles.py mandates, Risk Profile Audit (configuration per investor profile), Black-Litterman PERFILES (omega_scale, tau, gamma_ra), COL Portfolio Architecture (proposed profile bands, max Sharpe), QU OTM delta filter as annual IV cap, International ticker format filter and region caps, Lambda calibration with pen_ret, Minimum Variance profile parameter tables (normal and seasonal) (+7 more)

### Community 31 - "Community 31"
Cohesion: 0.18
Nodes (9): _cli_risk_profile(), resolve_risk_profile(), _literales(), _presets(), test_preset_agresivo_no_cambia_los_literales(), test_presets_de_mv_y_qu_coinciden_con_la_auditoria(), test_resolve_default_si_no_hay_env_ni_cli(), test_resolve_env_y_cli() (+1 more)

### Community 32 - "Community 32"
Cohesion: 0.22
Nodes (11): _alias_importados(), _asignaciones_de_modulo(), _correr_bl(), _nombres(), sombras_de_import(), test_bl_input_file_overrides_tickers_and_views(), test_bl_risk_profile_env_and_cli(), test_bl_universe_file_drops_default_views() (+3 more)

### Community 33 - "Community 33"
Cohesion: 0.16
Nodes (9): mfiv_vs_atm(), _momentos_sector(), bkm_compute_moments(), higher_moments_admissible(), mfik_cap(), mfik_cap_tenor(), test_higher_moments_admissible_pearson(), test_mfik_cap_rises_with_chain_depth() (+1 more)

### Community 35 - "Community 35"
Cohesion: 0.19
Nodes (7): fetch_option_aggs(), close_near_from_bars(), contract_agg_ranges(), bkm_precios_en_rango(), polygon_contract_close_near(), bkm_precios_en_rango(), polygon_contract_close_near()

### Community 36 - "Community 36"
Cohesion: 0.21
Nodes (9): select_historical_otm(), _barra(), _contratos(), _formato_us_viejo(), test_combinar_tickers_conserva_sufijos_que_el_filtro_us_tiraba(), test_range_fetch_matches_per_date_close(), test_select_historical_otm_empty_without_both_sides(), test_select_historical_otm_prefers_50_dte_over_15() (+1 more)

### Community 37 - "Community 37"
Cohesion: 0.15
Nodes (7): estimate_minutes(), _parse_calls_per_min(), set_rate_limit(), entorno_aislado(), test_limiter_spaces_calls(), test_parse_calls_per_min(), test_set_rate_limit_updates_limiter_and_estimate()

### Community 38 - "Community 38"
Cohesion: 0.15
Nodes (13): AM-PM Portfolio Construction Repository, Pull request merge order (stacked PRs #2 to #4 then this PR), Test suite (pytest, no network), numpy>=1.24, pandas>=2.0, plotly>=5.18, pytest>=7.0, quadprog>=0.1.11 (+5 more)

### Community 39 - "Community 39"
Cohesion: 0.26
Nodes (6): _bucle_de_poda(), _correr(), test_block_cut_is_skipped_when_it_leaves_too_few_names(), test_min_weight_keeps_capped_defensives(), test_names_below_threshold_are_cut_in_one_step(), test_prune_loop_survives_floor_weights()

### Community 40 - "Community 40"
Cohesion: 0.17
Nodes (8): normalize_currency(), price_scale_factor(), download_period_returns(), get_currency_for_ticker(), download_period_returns(), get_currency_for_ticker(), test_normalize_currency(), test_price_scale_factor()

### Community 41 - "Community 41"
Cohesion: 0.18
Nodes (7): lambda_monthly_from_annual(), portfolio_mu_final_metrics(), score_candidate_portfolios(), utility_terms(), test_lambda_monthly_from_annual_scales_by_twelve_and_is_opt_in(), test_pen_ret_is_nan_when_return_is_not_positive(), test_utility_terms_show_when_the_penalty_binds()

### Community 42 - "Community 42"
Cohesion: 0.22
Nodes (9): _RespuestaFalsa, test_get_json_403_is_not_retried_and_names_the_plan(), _get(), test_get_json_jitter_on_5xx_and_retry_after_wins(), test_get_json_non_transient_error_is_not_retried_nor_cached(), _get(), test_get_json_retries_on_429_respecting_retry_after(), test_get_json_strips_key_from_cache_key_and_sends_it() (+1 more)

### Community 43 - "Community 43"
Cohesion: 0.20
Nodes (6): variance_annual_to_horizon(), mfiv_annual_vol(), implied_variance_to_horizon(), test_mfiv_annual_vol_uses_real_dte(), test_implied_variance_to_horizon_arrays_and_nan(), test_implied_variance_to_horizon_uses_real_dte()

### Community 44 - "Community 44"
Cohesion: 0.24
Nodes (4): asegurar_fx(), descargar_fx_moneda(), descargar_precio(), _par_fx()

### Community 45 - "Community 45"
Cohesion: 0.25
Nodes (6): dispersion_usable(), dispersion_weights(), test_dispersion_cap_share_is_the_basket_over_known_spy_caps(), test_dispersion_weights_cap_weighted_spy_names_with_iv(), test_dispersion_weights_equal_when_a_cap_is_missing(), test_dispersion_weights_insufficient_basket()

### Community 46 - "Community 46"
Cohesion: 0.29
Nodes (4): calcular_metricas_riesgo_cola(), _pesos_normalizados(), var_cvar_cornish_fisher(), var_cvar_historico()

### Community 47 - "Community 47"
Cohesion: 0.43
Nodes (6): drop_partial_last_week(), _semanal(), test_drop_partial_last_week_empty_and_dataframe(), test_drop_partial_last_week_friday_kept(), test_drop_partial_last_week_thursday_before_holiday_friday(), test_drop_partial_last_week_wednesday_dropped()

### Community 48 - "Community 48"
Cohesion: 0.29
Nodes (4): bkm_fetch_otm_chain(), bkm_fetch_otm_chain(), polygon_format_ticker(), test_polygon_format_ticker_none()

### Community 49 - "Community 49"
Cohesion: 0.33
Nodes (5): compute_marginal_cvar_contrib(), compute_marginal_cvar_contrib(), cornish_fisher_es_gradient(), portfolio_moment_gradients(), test_cornish_fisher_es_gradient_vs_finite_differences()

### Community 50 - "Community 50"
Cohesion: 0.33
Nodes (5): average_abs_correlation(), _corr_abc(), test_average_abs_correlation_ignores_sign_and_order(), test_average_abs_correlation_uses_full_row(), test_old_alphabetical_grouping_drops_last_ticker()

### Community 51 - "Community 51"
Cohesion: 0.29
Nodes (4): mfis_tail_decision(), test_mfis_tail_decision(), test_mfis_tail_default_upper_matches_old_inequality(), test_mfis_tail_rejects_unknown_mode()

### Community 52 - "Community 52"
Cohesion: 0.20
Nodes (3): construir_restricciones(), _momento_pendiente(), _retorno_min_factible()

### Community 53 - "Community 53"
Cohesion: 0.33
Nodes (4): gram_charlier_pdf_ratio(), he3(), he4(), posterior_gram_charlier()

### Community 54 - "Community 54"
Cohesion: 0.33
Nodes (4): columns_with_min_obs(), covariance_min_history(), test_columns_with_min_obs_keeps_long_history(), test_covariance_min_history_uses_each_series_full_sample()

### Community 55 - "Community 55"
Cohesion: 0.33
Nodes (3): frontier_curve(), frontier_lambda_grid(), test_constrained_frontier_passes_through_the_optimum()

### Community 57 - "Community 57"
Cohesion: 0.50
Nodes (3): cumulantes_Q_desde_P(), estimar_theta_esscher(), objetivo()

### Community 59 - "Community 59"
Cohesion: 0.40
Nodes (3): n_fallos_transitorios(), test_get_json_exhausts_retries_on_network_error(), test_n_fallos_transitorios_excludes_missing_key()

### Community 60 - "Community 60"
Cohesion: 0.40
Nodes (4): history_window(), test_history_window_includes_current_year_through_last_full_month(), test_history_window_january_stops_at_previous_year(), test_history_window_rejects_start_after_sample()

## Knowledge Gaps
- **15 isolated node(s):** `Pull request merge order (stacked PRs #2 to #4 then this PR)`, `QUBO/Ising candidate selection`, `SSVI smile fit on |k|<=0.5`, `Entropy pooling posterior views`, `RISK_PROFILE env var and --risk-profile flag (RISK_PRESETS / PERFILES)` (+10 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 394 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Risk Profile Audit (configuration per investor profile)` connect `Community 30` to `README: BL Architecture & BKM`, `Community 38`, `OTM Delta Filter & Constraints`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **What connects `Pull request merge order (stacked PRs #2 to #4 then this PR)`, `QUBO/Ising candidate selection`, `SSVI smile fit on |k|<=0.5` to the rest of the system?**
  _15 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `ETF Band & Feasibility (seasonal)` be split into smaller, more focused modules?**
  _Cohesion score 0.05017921146953405 - nodes in this community are weakly interconnected._
- **Why does `_Limitador` connect `Community 68` to `Polygon Client & Cache`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Should `Polygon Options Chain (seasonal)` be split into smaller, more focused modules?**
  _Cohesion score 0.05388471177944862 - nodes in this community are weakly interconnected._
- **Why does `_YahooFalso` connect `Community 56` to `Community 32`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Should `Polygon Options Chain` be split into smaller, more focused modules?**
  _Cohesion score 0.05656565656565657 - nodes in this community are weakly interconnected._