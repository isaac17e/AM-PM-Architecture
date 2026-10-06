# Graph Report - AM-PM-Architecture  (2026-10-06)

## Corpus Check
- 32 files · ~113,125 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .ini 1)

## Summary
- 1252 nodes · 2773 edges · 81 communities (61 shown, 20 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 67 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a57808c6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_etf_floor_refill.py
- quadratic_utility_(seasonal_version).py
- quadratic_utility.py
- bl_metrics.py
- numpy
- polygon_client.py
- test_bl_metrics.py
- math
- minimum_variance.py
- minimum_variance_(seasonal_version).py
- market_data.py
- test_market_cap_internacional.py
- pipeline_io.py
- test_pipeline_io.py
- test_risk_estimators.py
- test_market_data.py
- portfolio_constraints.py
- risk_estimators.py
- to_years
- fit_ssvi
- pandas
- test_universo_y_delta_estacional.py
- get_spot_history
- test_polygon_client.py
- ledoit_wolf_constant_correlation
- frames_from_yf_download
- get_all
- cornish_fisher_tail
- test_mv_cola_y_delta.py
- black_litterman.py
- Risk Profile Audit (configuration per investor profile)
- test_risk_profile.py
- test_script_smoke.py
- higher_moments_admissible
- pytest
- close_near_from_bars
- test_qu_metrics.py
- set_rate_limit
- _momentos_sector
- test_tail_prune_loop.py
- normalize_currency
- lambda_monthly_from_annual
- get_json
- implied_variance_to_horizon
- descargar_precio
- calls_per_minute_from_env
- calcular_metricas_riesgo_cola
- drop_partial_last_week
- polygon_format_ticker
- cornish_fisher_es_gradient
- average_abs_correlation
- mfis_tail_decision
- _retorno_min_factible
- gram_charlier_pdf_ratio
- covariance_min_history
- ssvi_surface_decision
- iv_vol_at_horizon
- estimar_theta_esscher
- mincer_zarnowitz
- n_fallos_transitorios
- portfolio_returns_skipna
- bootstrap_estacionario
- media_hac
- clip_negligible_weights
- bkm_motivo_fallback
- build_qp_constraints
- bkm_motivo_fallback
- build_qp_constraints
- _Limitador
- momentos_fallback
- entropy_pooling
- dedupe_share_classes
- is_us_ticker
- align_daily_panel
- qu_metrics.py
- horizon_from_month_list
- stitch_covariance
- CLAUDE.md
- download_ticker_data
- optimizar_min_cvar
- primas_esscher

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
- `test_get_json_without_api_key_is_definitive_and_warns_once()` --calls--> `get_json()`  [EXTRACTED]
  tests/test_polygon_client.py → polygon_client.py
- `Profiles scale preferences only; estimators global` --conceptually_related_to--> `Risk-neutral to physical (Q to P) correction`  [INFERRED]
  docs/risk_profile_audit.html → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared estimation modules feeding the three optimizers** — polygon_client, risk_estimators, market_data, portfolio_constraints, qu_metrics, bl_metrics, pipeline_io, quadratic_utility, minimum_variance, black_litterman [EXTRACTED 1.00]
- **Options-implied tail risk pipeline (BKM, Q to P, Cornish-Fisher)** — readme_bkm, readme_q_to_p, readme_cornish_fisher, readme_co_moments, readme_ssvi_fit [INFERRED 0.85]
- **Risk-profile calibration (gamma ladder, CRRA lambdas, lambda-only aversion, pen_ret)** — docs_risk_profile_audit_gamma_ladder, docs_risk_profile_audit_crra_lambdas, docs_risk_profile_audit_lambda_only_risk_aversion, docs_risk_profile_audit_lambda_calibration [INFERRED 0.85]

## Communities (81 total, 20 thin omitted)

### Community 0 - "test_etf_floor_refill.py"
Cohesion: 0.05
Nodes (40): candidatos_reposicion(), completar_etfs(), contar_etfs(), diagnostico_banda_etf(), etfs_necesarios(), relajar_banda_etf(), reserva_etf(), restricciones_factibles() (+32 more)

### Community 1 - "quadratic_utility_(seasonal_version).py"
Cohesion: 0.06
Nodes (35): armar_restricciones(), _asegurar_momentos_actuales(), bkm_clave_historia(), bkm_compute_moments(), bkm_fechas_pendientes(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_iv_chain_to_prices() (+27 more)

### Community 2 - "quadratic_utility.py"
Cohesion: 0.06
Nodes (36): armar_restricciones(), _asegurar_momentos_actuales(), bkm_clave_historia(), bkm_compute_moments(), bkm_fechas_pendientes(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_iv_chain_to_prices() (+28 more)

### Community 3 - "bl_metrics.py"
Cohesion: 0.10
Nodes (16): calibrar_superficie_ssvi(), _fecha_naive(), forward_por_paridad(), mfiv_vs_atm(), seleccionar_vencimientos(), ssvi_monotone_mask(), ssvi_row_mask(), ssvi_weights() (+8 more)

### Community 4 - "numpy"
Cohesion: 0.07
Nodes (28): apply_vol_q_to_p(), integration_strike_bounds(), log_portfolio_return(), port_ret_row(), comparison_lambdas(), frontier_curve(), frontier_lambda_grid(), portfolio_mu_final_metrics() (+20 more)

### Community 5 - "polygon_client.py"
Cohesion: 0.09
Nodes (13): _avisar_403(), _avisar_sin_api_key(), _con_api_key(), default_cache_dir(), _espera_reintento(), print_diagnostics(), _registrar(), _retry_after() (+5 more)

### Community 6 - "test_bl_metrics.py"
Cohesion: 0.16
Nodes (13): elegir_spot_momentos(), market_delta(), _cadena_ssvi(), _precios_con_paridad(), test_calibrar_superficie_ignora_leaps_y_quotes_rotos(), test_delta_fixed_ignores_the_sample(), test_delta_historical_can_be_negative(), test_delta_historical_is_excess_over_variance() (+5 more)

### Community 7 - "math"
Cohesion: 0.13
Nodes (17): bs_call_delta_from_vol(), delta_cushion(), evaluar_delta_candidato(), filtro_delta_otm(), _finito(), otm_log_moneyness(), pasa_filtro_delta(), test_horizonte_cambia_la_moneyness_efectiva() (+9 more)

### Community 8 - "minimum_variance.py"
Cohesion: 0.11
Nodes (18): bkm_annual_vol(), bkm_compute_moments(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), bs_price() (+10 more)

### Community 9 - "minimum_variance_(seasonal_version).py"
Cohesion: 0.12
Nodes (17): bkm_annual_vol(), bkm_compute_moments(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), bs_price() (+9 more)

### Community 10 - "market_data.py"
Cohesion: 0.09
Nodes (18): _campo(), combinar_tickers(), _con_reintentos(), currency_from_suffix(), default_market_cap_cache_path(), es_ticker_formato_us(), _escribir_cache(), _leer_cache() (+10 more)

### Community 11 - "test_market_cap_internacional.py"
Cohesion: 0.10
Nodes (20): _llamar_caps(), _llamar_fx(), tabla_market_cap_texto(), _ordenar(), _proveedores(), cap_provider(), fx_provider(), test_cache_corrupta_no_rompe() (+12 more)

### Community 12 - "pipeline_io.py"
Cohesion: 0.12
Nodes (17): _add_months(), _atomic_write(), _date_or_none(), export_portfolio(), _export_portfolio(), horizon_from_months(), _int_or_none(), _jsonify() (+9 more)

### Community 13 - "test_pipeline_io.py"
Cohesion: 0.12
Nodes (14): load_bl_input(), select_views(), _escribir(), _leer(), test_atomic_replace(), test_bl_input_invalid_or_missing(), test_bl_input_universe_uses_only_tickers(), test_bl_input_views_shape() (+6 more)

### Community 14 - "test_risk_estimators.py"
Cohesion: 0.15
Nodes (10): q_to_p_correlation(), q_to_p_vol(), _lw_constant_correlation_referencia(), panel(), retornos(), retornos_shock_covid(), test_ledoit_wolf_matches_independent_reference(), test_q_to_p_correlation_clips() (+2 more)

### Community 15 - "test_market_data.py"
Cohesion: 0.13
Nodes (20): align_prices_to_calendar(), resolve_currencies(), resolve_execution_months(), _bdays(), _precios_dos_mercados(), test_align_drops_low_coverage_ticker(), test_align_fills_local_holiday_instead_of_dropping_row(), test_align_long_gap_not_filled_beyond_limit() (+12 more)

### Community 16 - "portfolio_constraints.py"
Cohesion: 0.12
Nodes (19): bs_call_delta(), build_weight_constraints(), prune_order(), relax_group_band(), with_return_target(), _base(), _minvar(), _slack() (+11 more)

### Community 17 - "risk_estimators.py"
Cohesion: 0.16
Nodes (11): BKM risk-neutral moments (MFIV, MFIS, MFIK), Historical MFIS time budget (bkm_hist_max_minutes), Cornish-Fisher VaR/ES (Maillard 2012), Market delta modes (historical, fixed, implied via SVIX), Entropy pooling posterior views, include_etfs_in_portfolio switch, Methodology knobs (lambda_annual, bkm_tail_mode, DELTA_MKT_MODO), QUBO/Ising candidate selection (+3 more)

### Community 18 - "to_years"
Cohesion: 0.12
Nodes (13): momentos_cola_historicos(), momentos_cola_historicos(), annualize(), scale_bkm_moments(), scale_moments(), to_years(), test_annualize_shortcut(), test_scale_bkm_moments_from_15_to_30_days() (+5 more)

### Community 19 - "fit_ssvi"
Cohesion: 0.16
Nodes (14): fit_ssvi(), objetivo(), _params(), _penalty(), _relativos(), _sigmoid(), _grupos_vencimiento(), ssvi_total_variance() (+6 more)

### Community 20 - "pandas"
Cohesion: 0.15
Nodes (11): calibrar_ssvi_ticker(), momentos_realizados_rolling(), parse_chain(), _spot_bkm(), shrink_mu_to_prior(), summarize_yearly_mdd(), seasonal_vol_ratio(), test_shrink_mu_to_prior_weights_by_history_length() (+3 more)

### Community 21 - "test_universo_y_delta_estacional.py"
Cohesion: 0.18
Nodes (13): convertir_serie_a_usd(), _descartados(), _formato_us_viejo(), _fuente(), _internacionales_del_script(), _literales(), test_bl_no_manda_internacionales_a_polygon(), test_conteo_de_colchon_separa_umbrales_y_aguanta_el_horizonte() (+5 more)

### Community 22 - "get_spot_history"
Cohesion: 0.13
Nodes (15): get_spot_history(), _retry_spot_single(), _usable_spot(), _cierres(), test_get_spot_history_downloads_the_batch_once_and_workers_only_read(), batch(), single(), test_get_spot_history_falls_through_to_the_next_provider() (+7 more)

### Community 23 - "test_polygon_client.py"
Cohesion: 0.13
Nodes (17): es_transitorio(), expiry_rank_columns(), fetch_otm_chain(), _contrato(), _snapshot_grabado(), test_es_transitorio_false(), test_es_transitorio_true(), test_expiry_rank_prefers_50_over_15_for_a_30_day_target() (+9 more)

### Community 24 - "ledoit_wolf_constant_correlation"
Cohesion: 0.15
Nodes (13): average_correlation(), cov_ewma_shrunk(), effective_sample_size(), ewma_cov(), ewma_weights(), ledoit_wolf_constant_correlation(), _lw_ewma_referencia_delta(), test_cov_ewma_shrunk_pipeline() (+5 more)

### Community 25 - "frames_from_yf_download"
Cohesion: 0.11
Nodes (10): default_spot_providers(), _frame_from_close(), frames_from_yf_download(), _naive_dates(), yfinance_spot_batch(), yfinance_spot_single(), test_frames_from_yf_download_reads_both_multiindex_orders(), test_yfinance_batch_is_one_unadjusted_download() (+2 more)

### Community 26 - "get_all"
Cohesion: 0.32
Nodes (6): get_all(), _sumar(), _paginas(), test_get_all_follows_next_url(), test_get_all_marks_incomplete_when_a_page_fails(), test_get_all_truncated_by_max_pages()

### Community 27 - "cornish_fisher_tail"
Cohesion: 0.12
Nodes (16): cornish_fisher_domain(), cornish_fisher_moments(), cornish_fisher_params(), a_parametros(), residuo(), cornish_fisher_tail(), cornish_fisher_z(), var_cvar_cornish_fisher() (+8 more)

### Community 28 - "test_mv_cola_y_delta.py"
Cohesion: 0.20
Nodes (13): _bucle_de_cola(), _descartes(), _fuente(), _funcion(), test_conteo_estable_entre_horizontes(), test_conteos_por_umbral_conservador_moderado_agresivo(), test_defaults_del_filtro_delta_en_mv(), test_fallback_historico_activo_por_defecto() (+5 more)

### Community 29 - "black_litterman.py"
Cohesion: 0.10
Nodes (9): aplicar_limites_cartera(), calc_mdd(), construir_restricciones(), _diag_ssvi(), _fmt_num(), _momento_pendiente(), momentos_ponderados(), _sanear_momento_fisico() (+1 more)

### Community 30 - "Risk Profile Audit (configuration per investor profile)"
Cohesion: 0.07
Nodes (28): Asset Allocation (FICs) am_pm/profiles.py mandates, Risk Profile Audit (configuration per investor profile), Black-Litterman PERFILES (omega_scale, tau, gamma_ra), COL Portfolio Architecture (proposed profile bands, max Sharpe), QU OTM delta filter as annual IV cap, International ticker format filter and region caps, Lambda calibration with pen_ret, Minimum Variance profile parameter tables (normal and seasonal) (+20 more)

### Community 31 - "test_risk_profile.py"
Cohesion: 0.18
Nodes (9): _cli_risk_profile(), resolve_risk_profile(), _literales(), _presets(), test_preset_agresivo_no_cambia_los_literales(), test_presets_de_mv_y_qu_coinciden_con_la_auditoria(), test_resolve_default_si_no_hay_env_ni_cli(), test_resolve_env_y_cli() (+1 more)

### Community 32 - "test_script_smoke.py"
Cohesion: 0.08
Nodes (14): test_bl_con_internacionales_en_tickers(), _YahooMultimoneda, _alias_importados(), _asignaciones_de_modulo(), _correr_bl(), _nombres(), sombras_de_import(), test_bl_input_file_overrides_tickers_and_views() (+6 more)

### Community 33 - "higher_moments_admissible"
Cohesion: 0.22
Nodes (6): higher_moments_admissible(), mfik_cap(), mfik_cap_tenor(), test_higher_moments_admissible_pearson(), test_mfik_cap_rises_with_chain_depth(), test_mfik_cap_tenor_loosens_a_short_chain()

### Community 34 - "pytest"
Cohesion: 0.14
Nodes (15): crra_taylor_lambdas(), mdd_from_log_returns(), scale_option_deltas(), max_drawdown(), test_clip_negligible_weights_drops_solver_dust(), test_crra_taylor_lambdas_match_profile_ladder(), test_crra_taylor_terms_are_the_crra_expansion(), test_mdd_log_matches_exp_cumsum_not_simple_compounding() (+7 more)

### Community 35 - "close_near_from_bars"
Cohesion: 0.15
Nodes (9): fetch_option_aggs(), close_near_from_bars(), contract_agg_ranges(), bkm_precios_en_rango(), polygon_contract_close_near(), bkm_precios_en_rango(), polygon_contract_close_near(), _barra() (+1 more)

### Community 36 - "test_qu_metrics.py"
Cohesion: 0.12
Nodes (17): dispersion_usable(), dispersion_weights(), history_window(), select_historical_otm(), _contratos(), _formato_us_viejo(), test_combinar_tickers_conserva_sufijos_que_el_filtro_us_tiraba(), test_dispersion_cap_share_is_the_basket_over_known_spy_caps() (+9 more)

### Community 37 - "set_rate_limit"
Cohesion: 0.20
Nodes (5): estimate_minutes(), set_rate_limit(), entorno_aislado(), test_limiter_spaces_calls(), test_set_rate_limit_updates_limiter_and_estimate()

### Community 38 - "_momentos_sector"
Cohesion: 0.29
Nodes (7): bs_price(), calcular_bkm_moments(), _momentos_sector(), otm_price_ssvi(), phi_powerlaw(), sigma_desde_ssvi(), ssvi_w()

### Community 39 - "test_tail_prune_loop.py"
Cohesion: 0.26
Nodes (6): _bucle_de_poda(), _correr(), test_block_cut_is_skipped_when_it_leaves_too_few_names(), test_min_weight_keeps_capped_defensives(), test_names_below_threshold_are_cut_in_one_step(), test_prune_loop_survives_floor_weights()

### Community 40 - "normalize_currency"
Cohesion: 0.17
Nodes (8): normalize_currency(), price_scale_factor(), download_period_returns(), get_currency_for_ticker(), download_period_returns(), get_currency_for_ticker(), test_normalize_currency(), test_price_scale_factor()

### Community 41 - "lambda_monthly_from_annual"
Cohesion: 0.33
Nodes (4): lambda_monthly_from_annual(), utility_terms(), test_lambda_monthly_from_annual_scales_by_twelve_and_is_opt_in(), test_utility_terms_show_when_the_penalty_binds()

### Community 42 - "get_json"
Cohesion: 0.13
Nodes (19): cache_get(), cache_permitida(), cache_set(), es_snapshot(), fechas_en_clave(), get_json(), _ruta_cache(), _RespuestaFalsa (+11 more)

### Community 43 - "implied_variance_to_horizon"
Cohesion: 0.15
Nodes (9): mfiv_or_horizon_variance(), variance_annual_to_horizon(), mfiv_annual_vol(), implied_variance_to_horizon(), test_mfiv_fallback_uses_horizon_variance_not_annual(), test_variance_annual_matches_implied_variance_helper(), test_mfiv_annual_vol_uses_real_dte(), test_implied_variance_to_horizon_arrays_and_nan() (+1 more)

### Community 44 - "descargar_precio"
Cohesion: 0.24
Nodes (4): asegurar_fx(), descargar_fx_moneda(), descargar_precio(), _par_fx()

### Community 45 - "calls_per_minute_from_env"
Cohesion: 0.25
Nodes (6): calls_per_minute_from_env(), _parse_calls_per_min(), test_calls_per_minute_acepta_el_alias_viejo(), test_calls_per_minute_lee_el_nombre_largo(), test_calls_per_minute_sin_env_usa_el_default(), test_parse_calls_per_min()

### Community 46 - "calcular_metricas_riesgo_cola"
Cohesion: 0.29
Nodes (4): calcular_metricas_riesgo_cola(), _pesos_normalizados(), var_cvar_cornish_fisher(), var_cvar_historico()

### Community 47 - "drop_partial_last_week"
Cohesion: 0.43
Nodes (6): drop_partial_last_week(), _semanal(), test_drop_partial_last_week_empty_and_dataframe(), test_drop_partial_last_week_friday_kept(), test_drop_partial_last_week_thursday_before_holiday_friday(), test_drop_partial_last_week_wednesday_dropped()

### Community 48 - "polygon_format_ticker"
Cohesion: 0.33
Nodes (4): polygon_fetch_chain(), polygon_format_ticker(), test_polygon_format_ticker(), test_polygon_format_ticker_none()

### Community 49 - "cornish_fisher_es_gradient"
Cohesion: 0.20
Nodes (8): compute_marginal_cvar_contrib(), compute_marginal_cvar_contrib(), cornish_fisher_es_gradient(), portfolio_moment_gradients(), portfolio_moments(), test_cornish_fisher_es_gradient_vs_finite_differences(), test_portfolio_moment_gradients_vs_finite_differences(), test_portfolio_moments_match_direct_computation()

### Community 50 - "average_abs_correlation"
Cohesion: 0.33
Nodes (5): average_abs_correlation(), _corr_abc(), test_average_abs_correlation_ignores_sign_and_order(), test_average_abs_correlation_uses_full_row(), test_old_alphabetical_grouping_drops_last_ticker()

### Community 51 - "mfis_tail_decision"
Cohesion: 0.29
Nodes (4): mfis_tail_decision(), test_mfis_tail_decision(), test_mfis_tail_default_upper_matches_old_inequality(), test_mfis_tail_rejects_unknown_mode()

### Community 53 - "gram_charlier_pdf_ratio"
Cohesion: 0.33
Nodes (4): gram_charlier_pdf_ratio(), he3(), he4(), posterior_gram_charlier()

### Community 54 - "covariance_min_history"
Cohesion: 0.33
Nodes (4): columns_with_min_obs(), covariance_min_history(), test_columns_with_min_obs_keeps_long_history(), test_covariance_min_history_uses_each_series_full_sample()

### Community 55 - "ssvi_surface_decision"
Cohesion: 0.29
Nodes (5): ssvi_degeneracy(), ssvi_surface_decision(), test_ssvi_one_sided_coverage_falls_back_to_atm(), test_ssvi_rho_at_the_bound_falls_back_to_atm(), test_ssvi_surface_keeps_atm_when_the_smile_is_rejected()

### Community 56 - "iv_vol_at_horizon"
Cohesion: 0.33
Nodes (4): iv_vol_at_horizon(), vol_annual_to_horizon(), test_ssvi_and_hist_fallback_share_horizon_units(), test_vol_annual_scales_with_sqrt_horizon()

### Community 57 - "estimar_theta_esscher"
Cohesion: 0.50
Nodes (3): cumulantes_Q_desde_P(), estimar_theta_esscher(), objetivo()

### Community 60 - "portfolio_returns_skipna"
Cohesion: 0.40
Nodes (4): portfolio_returns_skipna(), portfolio_returns_series(), portfolio_returns_series(), test_portfolio_returns_skipna_does_not_drop_the_month()

### Community 63 - "clip_negligible_weights"
Cohesion: 0.22
Nodes (5): clip_negligible_weights(), markowitz_clasico(), momentos_portafolio(), optimizar_mvsk(), utilidad_mvsk_negativa()

### Community 72 - "is_us_ticker"
Cohesion: 0.50
Nodes (3): is_non_us_exchange(), is_non_us_exchange(), is_us_ticker()

### Community 74 - "qu_metrics.py"
Cohesion: 0.11
Nodes (13): Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12), Validation results of QU runs by profile (Oct 2026), annualize_monthly(), clip_implied_correlation(), estimate_bkm_history_calls(), plan_bkm_history_budget(), sector_implied_ready(), Reachable ETF floor and LP feasibility check (+5 more)

## Knowledge Gaps
- **16 isolated node(s):** `graphify`, `Historical MFIS time budget (bkm_hist_max_minutes)`, `Entropy pooling posterior views`, `QUBO/Ising candidate selection`, `SSVI smile fit on |k|<=0.5` (+11 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 396 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `test_get_spot_history_downloads_the_batch_once_and_workers_only_read()` connect `get_spot_history` to `test_market_data.py`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **What connects `graphify`, `Historical MFIS time budget (bkm_hist_max_minutes)`, `Entropy pooling posterior views` to the rest of the system?**
  _16 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_etf_floor_refill.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0523532522474881 - nodes in this community are weakly interconnected._
- **Why does `Workflow architecture (shared modules feed standalone optimizers)` connect `Risk Profile Audit (configuration per investor profile)` to `quadratic_utility.py`, `bl_metrics.py`, `polygon_client.py`, `minimum_variance.py`, `market_data.py`, `qu_metrics.py`, `pipeline_io.py`, `portfolio_constraints.py`, `risk_estimators.py`, `black_litterman.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Should `quadratic_utility_(seasonal_version).py` be split into smaller, more focused modules?**
  _Cohesion score 0.05764411027568922 - nodes in this community are weakly interconnected._
- **Why does `fit_ssvi()` connect `fit_ssvi` to `bl_metrics.py`, `numpy`, `math`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Should `quadratic_utility.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05974025974025974 - nodes in this community are weakly interconnected._