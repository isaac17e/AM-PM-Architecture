# Graph Report - AM-PM-Architecture  (2026-10-06)

## Corpus Check
- 32 files · ~115,747 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .ini 1)

## Summary
- 1293 nodes · 2880 edges · 78 communities (55 shown, 23 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 68 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a6946f5a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_etf_floor_refill.py
- quadratic_utility_(seasonal_version).py
- quadratic_utility.py
- bl_metrics.py
- numpy
- polygon_client.py
- pytest
- math
- minimum_variance.py
- minimum_variance_(seasonal_version).py
- market_data.py
- test_market_cap_internacional.py
- pipeline_io.py
- test_ajuste_iv_tasa.py
- bkm_reconstruct_mfis_history
- test_market_data.py
- test_portfolio_constraints.py
- to_years
- test_risk_estimators.py
- fit_ssvi
- pandas
- test_universo_y_delta_estacional.py
- get_spot_history
- fetch_otm_chain
- ledoit_wolf_constant_correlation
- frames_from_yf_download
- get_all
- risk_estimators.py
- test_mv_cola_y_delta.py
- black_litterman.py
- Risk Profile Audit (configuration per investor profile)
- evaluar_delta_candidato
- test_script_smoke.py
- higher_moments_admissible
- is_us_ticker
- close_near_from_bars
- test_qu_metrics.py
- set_rate_limit
- _momentos_sector
- test_tail_prune_loop.py
- normalize_currency
- dispersion_weights
- test_polygon_client.py
- resumen_ajuste_iv
- descargar_precio
- test_chain_to_prices_uses_calibrated_carry
- calcular_metricas_riesgo_cola
- drop_partial_last_week
- elegir_spot_momentos
- polygon_contracts_asof
- _precargar_spots_bkm
- mfis_tail_decision
- _retorno_min_factible
- gram_charlier_pdf_ratio
- _diag_ssvi
- convertir_serie_a_usd
- aplicar_limites_cartera
- estimar_theta_esscher
- mincer_zarnowitz
- test_get_json_exhausts_retries_on_network_error
- portfolio_returns_skipna
- bootstrap_estacionario
- media_hac
- optimizar_mvsk
- bkm_motivo_fallback
- build_qp_constraints
- bkm_motivo_fallback
- build_qp_constraints
- _Limitador
- construir_restricciones
- entropy_pooling
- _momento_pendiente
- momentos_ponderados
- _sanear_momento_fisico
- qu_metrics.py
- winsorizar
- CLAUDE.md
- primas_esscher

## God Nodes (most connected - your core abstractions)
1. `get_json()` - 27 edges
2. `to_years()` - 21 edges
3. `fetch_otm_chain()` - 19 edges
4. `fit_ssvi()` - 18 edges
5. `es_transitorio()` - 18 edges
6. `Risk Profile Audit (configuration per investor profile)` - 18 edges
7. `calibrar_superficie_ssvi()` - 17 edges
8. `get_all()` - 15 edges
9. `calibrate_iv_carry()` - 15 edges
10. `market_caps_usd()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `lambda3/lambda4 derived from gamma (CRRA Taylor expansion)` --semantically_similar_to--> `BL lambda3/lambda4 closed form from gamma`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `Reachable ETF floor and LP feasibility check` --semantically_similar_to--> `Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12)`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `test_vol_annual_scales_with_sqrt_horizon()` --calls--> `vol_annual_to_horizon()`  [EXTRACTED]
  tests/test_bl_metrics.py → bl_metrics.py
- `test_ssvi_and_hist_fallback_share_horizon_units()` --calls--> `iv_vol_at_horizon()`  [EXTRACTED]
  tests/test_bl_metrics.py → bl_metrics.py
- `test_mfiv_fallback_uses_horizon_variance_not_annual()` --calls--> `mfiv_or_horizon_variance()`  [EXTRACTED]
  tests/test_bl_metrics.py → bl_metrics.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared estimation modules feeding the three optimizers** — polygon_client, risk_estimators, market_data, portfolio_constraints, qu_metrics, bl_metrics, pipeline_io, quadratic_utility, minimum_variance, black_litterman [EXTRACTED 1.00]
- **Options-implied tail risk pipeline (BKM, Q to P, Cornish-Fisher)** — readme_bkm, readme_q_to_p, readme_cornish_fisher, readme_co_moments, readme_ssvi_fit [INFERRED 0.85]
- **Risk-profile calibration (gamma ladder, CRRA lambdas, lambda-only aversion, pen_ret)** — docs_risk_profile_audit_gamma_ladder, docs_risk_profile_audit_crra_lambdas, docs_risk_profile_audit_lambda_only_risk_aversion, docs_risk_profile_audit_lambda_calibration [INFERRED 0.85]

## Communities (78 total, 23 thin omitted)

### Community 0 - "test_etf_floor_refill.py"
Cohesion: 0.05
Nodes (40): candidatos_reposicion(), completar_etfs(), contar_etfs(), diagnostico_banda_etf(), etfs_necesarios(), relajar_banda_etf(), reserva_etf(), restricciones_factibles() (+32 more)

### Community 1 - "quadratic_utility_(seasonal_version).py"
Cohesion: 0.06
Nodes (30): armar_restricciones(), _asegurar_momentos_actuales(), bkm_compute_moments(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_iv_chain_to_prices(), bkm_seleccion_fecha(), bs_price() (+22 more)

### Community 2 - "quadratic_utility.py"
Cohesion: 0.09
Nodes (16): armar_restricciones(), bkm_iv_chain_to_prices(), bs_price(), clean_symbol_table(), _datos_con_precios(), _fila(), _fila_bkm(), fila_iv_vs_reciente() (+8 more)

### Community 3 - "bl_metrics.py"
Cohesion: 0.07
Nodes (21): apply_vol_q_to_p(), calibrar_superficie_ssvi(), _fecha_naive(), forward_por_paridad(), iv_vol_at_horizon(), mfiv_or_horizon_variance(), momentos_fallback(), seleccionar_vencimientos() (+13 more)

### Community 4 - "numpy"
Cohesion: 0.07
Nodes (26): clip_negligible_weights(), markowitz_clasico(), bkm_annual_vol(), clip_implied_correlation(), comparison_lambdas(), frontier_curve(), frontier_lambda_grid(), mfiv_annual_vol() (+18 more)

### Community 5 - "polygon_client.py"
Cohesion: 0.10
Nodes (20): _avisar_403(), _avisar_sin_api_key(), cache_get(), cache_permitida(), cache_set(), _con_api_key(), es_snapshot(), _espera_reintento() (+12 more)

### Community 6 - "pytest"
Cohesion: 0.11
Nodes (29): crra_taylor_lambdas(), market_delta(), variance_annual_to_horizon(), _cadena_ssvi(), _precios_con_paridad(), test_apply_vol_q_to_p_does_not_haircut_historical_vol(), test_calibrar_superficie_ignora_leaps_y_quotes_rotos(), test_clip_negligible_weights_drops_solver_dust() (+21 more)

### Community 7 - "math"
Cohesion: 0.12
Nodes (16): Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12), bs_call_delta(), build_weight_constraints(), bs_call_delta_from_vol(), delta_cushion(), otm_log_moneyness(), shrink_mu_to_prior(), Reachable ETF floor and LP feasibility check (+8 more)

### Community 8 - "minimum_variance.py"
Cohesion: 0.11
Nodes (15): bkm_compute_moments(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), bs_price(), clean_symbol_table(), constraints_feasible() (+7 more)

### Community 9 - "minimum_variance_(seasonal_version).py"
Cohesion: 0.11
Nodes (18): bkm_annual_vol(), bkm_compute_moments(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), bs_price(), clean_symbol_table() (+10 more)

### Community 10 - "market_data.py"
Cohesion: 0.09
Nodes (18): _campo(), combinar_tickers(), _con_reintentos(), currency_from_suffix(), default_market_cap_cache_path(), es_ticker_formato_us(), _escribir_cache(), _leer_cache() (+10 more)

### Community 11 - "test_market_cap_internacional.py"
Cohesion: 0.10
Nodes (20): _llamar_caps(), _llamar_fx(), tabla_market_cap_texto(), _ordenar(), _proveedores(), cap_provider(), fx_provider(), test_cache_corrupta_no_rompe() (+12 more)

### Community 12 - "pipeline_io.py"
Cohesion: 0.06
Nodes (33): _add_months(), _atomic_write(), _date_or_none(), export_portfolio(), _export_portfolio(), horizon_from_month_list(), horizon_from_months(), _int_or_none() (+25 more)

### Community 13 - "test_ajuste_iv_tasa.py"
Cohesion: 0.17
Nodes (16): bs_implied_vol(), bs_price(), calibrate_iv_carry(), residuo(), iv_at_rate(), _contrato(), _mercado(), _smile() (+8 more)

### Community 14 - "bkm_reconstruct_mfis_history"
Cohesion: 0.11
Nodes (12): spot_series_for(), bkm_clave_historia(), bkm_fechas_pendientes(), bkm_reconstruct_mfis_history(), evaluar_historia_bkm(), bkm_clave_historia(), bkm_fechas_pendientes(), bkm_reconstruct_mfis_history() (+4 more)

### Community 15 - "test_market_data.py"
Cohesion: 0.10
Nodes (23): align_prices_to_calendar(), dedupe_share_classes(), resolve_currencies(), resolve_execution_months(), align_daily_panel(), _bdays(), _precios_dos_mercados(), test_align_drops_low_coverage_ticker() (+15 more)

### Community 16 - "test_portfolio_constraints.py"
Cohesion: 0.14
Nodes (15): prune_order(), relax_group_band(), with_return_target(), _base(), _minvar(), _slack(), test_atm_call_delta_always_above_half(), test_budget_is_equality_and_box_constraints_hold() (+7 more)

### Community 17 - "to_years"
Cohesion: 0.19
Nodes (10): get_polygon_option_snapshot(), expiry_rank_columns(), pares_call_put(), bkm_fetch_otm_chain(), bkm_get_current_moments(), get_spot_safe_bkm(), polygon_format_ticker(), polygon_get_atm_option() (+2 more)

### Community 18 - "test_risk_estimators.py"
Cohesion: 0.08
Nodes (23): mdd_from_log_returns(), annualize(), max_drawdown(), scale_moments(), test_mdd_log_matches_exp_cumsum_not_simple_compounding(), _lw_constant_correlation_referencia(), panel(), retornos() (+15 more)

### Community 19 - "fit_ssvi"
Cohesion: 0.16
Nodes (14): fit_ssvi(), objetivo(), _params(), _penalty(), _relativos(), _sigmoid(), _grupos_vencimiento(), ssvi_total_variance() (+6 more)

### Community 20 - "pandas"
Cohesion: 0.09
Nodes (21): log_portfolio_return(), calibrar_ssvi_ticker(), momentos_realizados_rolling(), parse_chain(), covariance_min_history(), stitch_covariance(), summarize_yearly_mdd(), portfolio_log_returns() (+13 more)

### Community 21 - "test_universo_y_delta_estacional.py"
Cohesion: 0.23
Nodes (11): _descartados(), _formato_us_viejo(), _fuente(), _internacionales_del_script(), _literales(), test_bl_no_manda_internacionales_a_polygon(), test_conteo_de_colchon_separa_umbrales_y_aguanta_el_horizonte(), test_defaults_estacionales_del_colchon() (+3 more)

### Community 22 - "get_spot_history"
Cohesion: 0.13
Nodes (15): get_spot_history(), _retry_spot_single(), _usable_spot(), _cierres(), test_get_spot_history_downloads_the_batch_once_and_workers_only_read(), batch(), single(), test_get_spot_history_falls_through_to_the_next_provider() (+7 more)

### Community 23 - "fetch_otm_chain"
Cohesion: 0.09
Nodes (20): polygon_fetch_chain(), bkm_fetch_otm_chain(), is_non_us_exchange(), bkm_fetch_otm_chain(), es_transitorio(), fetch_otm_chain(), is_us_ticker(), polygon_format_ticker() (+12 more)

### Community 24 - "ledoit_wolf_constant_correlation"
Cohesion: 0.15
Nodes (13): average_correlation(), cov_ewma_shrunk(), effective_sample_size(), ewma_cov(), ewma_weights(), ledoit_wolf_constant_correlation(), _lw_ewma_referencia_delta(), test_cov_ewma_shrunk_pipeline() (+5 more)

### Community 25 - "frames_from_yf_download"
Cohesion: 0.11
Nodes (10): default_spot_providers(), _frame_from_close(), frames_from_yf_download(), _naive_dates(), yfinance_spot_batch(), yfinance_spot_single(), test_frames_from_yf_download_reads_both_multiindex_orders(), test_yfinance_batch_is_one_unadjusted_download() (+2 more)

### Community 26 - "get_all"
Cohesion: 0.32
Nodes (6): get_all(), _sumar(), _paginas(), test_get_all_follows_next_url(), test_get_all_marks_incomplete_when_a_page_fails(), test_get_all_truncated_by_max_pages()

### Community 27 - "risk_estimators.py"
Cohesion: 0.07
Nodes (28): compute_marginal_cvar_contrib(), compute_marginal_cvar_contrib(), cornish_fisher_domain(), cornish_fisher_es_gradient(), cornish_fisher_moments(), cornish_fisher_params(), a_parametros(), residuo() (+20 more)

### Community 28 - "test_mv_cola_y_delta.py"
Cohesion: 0.20
Nodes (13): _bucle_de_cola(), _descartes(), _fuente(), _funcion(), test_conteo_estable_entre_horizontes(), test_conteos_por_umbral_conservador_moderado_agresivo(), test_defaults_del_filtro_delta_en_mv(), test_fallback_historico_activo_por_defecto() (+5 more)

### Community 29 - "black_litterman.py"
Cohesion: 0.17
Nodes (8): bs_price(), calc_mdd(), optimizar_min_cvar(), otm_price_ssvi(), phi_powerlaw(), port_ret_row(), sigma_desde_ssvi(), ssvi_w()

### Community 30 - "Risk Profile Audit (configuration per investor profile)"
Cohesion: 0.05
Nodes (39): Asset Allocation (FICs) am_pm/profiles.py mandates, Risk Profile Audit (configuration per investor profile), Black-Litterman PERFILES (omega_scale, tau, gamma_ra), COL Portfolio Architecture (proposed profile bands, max Sharpe), QU OTM delta filter as annual IV cap, International ticker format filter and region caps, Lambda calibration with pen_ret, Minimum Variance profile parameter tables (normal and seasonal) (+31 more)

### Community 31 - "evaluar_delta_candidato"
Cohesion: 0.19
Nodes (8): evaluar_delta_candidato(), filtro_delta_otm(), _finito(), pasa_filtro_delta(), test_nombres_sin_vol_se_conservan_y_polygon_manda_sobre_historica(), test_conteo_del_filtro_estacional_sobre_universo_sintetico(), test_delta_de_polygon_no_salta_el_modo_otm(), test_sin_vol_se_conserva()

### Community 32 - "test_script_smoke.py"
Cohesion: 0.06
Nodes (23): _cli_risk_profile(), resolve_risk_profile(), test_bl_con_internacionales_en_tickers(), _YahooMultimoneda, _literales(), _presets(), test_preset_agresivo_no_cambia_los_literales(), test_presets_de_mv_y_qu_coinciden_con_la_auditoria() (+15 more)

### Community 33 - "higher_moments_admissible"
Cohesion: 0.20
Nodes (6): momentos_cola_historicos(), momentos_cola_historicos(), bkm_compute_moments(), higher_moments_admissible(), mfik_cap_tenor(), test_higher_moments_admissible_pearson()

### Community 34 - "is_us_ticker"
Cohesion: 0.22
Nodes (7): plan_bkm_history_budget(), _asegurar_momentos_actuales(), is_us_ticker(), _momento_actual_bkm(), _plan_ronda_bkm(), _rank_bkm(), test_plan_bkm_history_budget_keeps_a_ranked_prefix()

### Community 35 - "close_near_from_bars"
Cohesion: 0.15
Nodes (9): fetch_option_aggs(), close_near_from_bars(), contract_agg_ranges(), bkm_precios_en_rango(), polygon_contract_close_near(), bkm_precios_en_rango(), polygon_contract_close_near(), _barra() (+1 more)

### Community 36 - "test_qu_metrics.py"
Cohesion: 0.13
Nodes (16): average_abs_correlation(), history_window(), select_historical_otm(), _contratos(), _corr_abc(), _formato_us_viejo(), test_average_abs_correlation_ignores_sign_and_order(), test_average_abs_correlation_uses_full_row() (+8 more)

### Community 37 - "set_rate_limit"
Cohesion: 0.15
Nodes (7): estimate_minutes(), _parse_calls_per_min(), set_rate_limit(), entorno_aislado(), test_limiter_spaces_calls(), test_parse_calls_per_min(), test_set_rate_limit_updates_limiter_and_estimate()

### Community 38 - "_momentos_sector"
Cohesion: 0.20
Nodes (6): integration_strike_bounds(), mfiv_vs_atm(), calcular_bkm_moments(), _momentos_sector(), mfik_cap(), test_mfik_cap_rises_with_chain_depth()

### Community 39 - "test_tail_prune_loop.py"
Cohesion: 0.26
Nodes (6): _bucle_de_poda(), _correr(), test_block_cut_is_skipped_when_it_leaves_too_few_names(), test_min_weight_keeps_capped_defensives(), test_names_below_threshold_are_cut_in_one_step(), test_prune_loop_survives_floor_weights()

### Community 40 - "normalize_currency"
Cohesion: 0.17
Nodes (8): normalize_currency(), price_scale_factor(), download_period_returns(), get_currency_for_ticker(), download_period_returns(), get_currency_for_ticker(), test_normalize_currency(), test_price_scale_factor()

### Community 41 - "dispersion_weights"
Cohesion: 0.25
Nodes (6): dispersion_usable(), dispersion_weights(), test_dispersion_cap_share_is_the_basket_over_known_spy_caps(), test_dispersion_weights_cap_weighted_spy_names_with_iv(), test_dispersion_weights_equal_when_a_cap_is_missing(), test_dispersion_weights_insufficient_basket()

### Community 42 - "test_polygon_client.py"
Cohesion: 0.11
Nodes (19): calls_per_minute_from_env(), default_cache_dir(), _contrato(), _RespuestaFalsa, _snapshot_grabado(), test_cache_never_stores_current_date_or_snapshot(), test_calls_per_minute_acepta_el_alias_viejo(), test_calls_per_minute_lee_el_nombre_largo() (+11 more)

### Community 43 - "resumen_ajuste_iv"
Cohesion: 0.33
Nodes (4): resumen_ajuste_iv(), texto_ajuste_iv(), test_resumen_ajuste_iv_counts_only_queried_chains(), test_texto_ajuste_iv_without_pairs()

### Community 44 - "descargar_precio"
Cohesion: 0.24
Nodes (4): asegurar_fx(), descargar_fx_moneda(), descargar_precio(), _par_fx()

### Community 45 - "test_chain_to_prices_uses_calibrated_carry"
Cohesion: 0.60
Nodes (5): _fuente(), _funcion(), test_atm_snapshot_fetches_both_sides_and_adjusts_iv(), test_chain_to_prices_uses_calibrated_carry(), test_current_moments_calibrate_before_pricing()

### Community 46 - "calcular_metricas_riesgo_cola"
Cohesion: 0.29
Nodes (4): calcular_metricas_riesgo_cola(), _pesos_normalizados(), var_cvar_cornish_fisher(), var_cvar_historico()

### Community 47 - "drop_partial_last_week"
Cohesion: 0.43
Nodes (6): drop_partial_last_week(), _semanal(), test_drop_partial_last_week_empty_and_dataframe(), test_drop_partial_last_week_friday_kept(), test_drop_partial_last_week_thursday_before_holiday_friday(), test_drop_partial_last_week_wednesday_dropped()

### Community 51 - "mfis_tail_decision"
Cohesion: 0.29
Nodes (4): mfis_tail_decision(), test_mfis_tail_decision(), test_mfis_tail_default_upper_matches_old_inequality(), test_mfis_tail_rejects_unknown_mode()

### Community 53 - "gram_charlier_pdf_ratio"
Cohesion: 0.33
Nodes (4): gram_charlier_pdf_ratio(), he3(), he4(), posterior_gram_charlier()

### Community 57 - "estimar_theta_esscher"
Cohesion: 0.50
Nodes (3): cumulantes_Q_desde_P(), estimar_theta_esscher(), objetivo()

### Community 59 - "test_get_json_exhausts_retries_on_network_error"
Cohesion: 0.40
Nodes (3): n_fallos_transitorios(), test_get_json_exhausts_retries_on_network_error(), test_n_fallos_transitorios_excludes_missing_key()

### Community 60 - "portfolio_returns_skipna"
Cohesion: 0.40
Nodes (4): portfolio_returns_skipna(), portfolio_returns_series(), portfolio_returns_series(), test_portfolio_returns_skipna_does_not_drop_the_month()

### Community 63 - "optimizar_mvsk"
Cohesion: 0.40
Nodes (3): momentos_portafolio(), optimizar_mvsk(), utilidad_mvsk_negativa()

### Community 74 - "qu_metrics.py"
Cohesion: 0.09
Nodes (15): annualize_monthly(), columns_with_min_obs(), estimate_bkm_history_calls(), lambda_monthly_from_annual(), portfolio_mu_final_metrics(), score_candidate_portfolios(), sector_implied_ready(), utility_terms() (+7 more)

## Knowledge Gaps
- **16 isolated node(s):** `graphify`, `Historical MFIS time budget (bkm_hist_max_minutes)`, `Entropy pooling posterior views`, `QUBO/Ising candidate selection`, `SSVI smile fit on |k|<=0.5` (+11 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 408 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `to_years()` connect `to_years` to `higher_moments_admissible`, `quadratic_utility_(seasonal_version).py`, `numpy`, `minimum_variance.py`, `minimum_variance_(seasonal_version).py`, `qu_metrics.py`, `bkm_reconstruct_mfis_history`, `test_risk_estimators.py`, `risk_estimators.py`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **What connects `graphify`, `Historical MFIS time budget (bkm_hist_max_minutes)`, `Entropy pooling posterior views` to the rest of the system?**
  _16 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_etf_floor_refill.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05182443151771549 - nodes in this community are weakly interconnected._
- **Why does `market_caps_usd()` connect `market_data.py` to `normalize_currency`, `test_market_cap_internacional.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Should `quadratic_utility_(seasonal_version).py` be split into smaller, more focused modules?**
  _Cohesion score 0.06294326241134751 - nodes in this community are weakly interconnected._
- **Should `quadratic_utility.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09116809116809117 - nodes in this community are weakly interconnected._
- **Should `bl_metrics.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06685633001422475 - nodes in this community are weakly interconnected._