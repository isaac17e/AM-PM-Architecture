# Graph Report - AM-PM-Architecture  (2026-10-08)

## Corpus Check
- 33 files · ~122,651 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .ini 1)

## Summary
- 1305 nodes · 2901 edges · 69 communities (51 shown, 18 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 68 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `353aa7ac`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_etf_floor_refill.py
- to_years
- quadratic_utility.py
- bl_metrics.py
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
- bkm_reconstruct_mfis_history
- test_market_data.py
- test_portfolio_constraints.py
- test_script_smoke.py
- test_risk_estimators.py
- fit_ssvi
- test_bl_universo.py
- test_universo_y_delta_estacional.py
- get_spot_history
- test_polygon_client.py
- risk_estimators.py
- frames_from_yf_download
- relax_group_band
- cornish_fisher_tail
- test_mv_cola_y_delta.py
- black_litterman.py
- Risk Profile Audit (configuration per investor profile)
- delta_cushion
- test_risk_profile.py
- pytest
- bkm_fechas_pendientes
- close_near_from_bars
- pandas
- calls_per_minute_from_env
- mfik_cap_tenor
- test_tail_prune_loop.py
- normalize_currency
- drop_partial_last_week
- Working with the graphify knowledge graph
- calcular_bkm_moments
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
- aplicar_limites_cartera
- estimar_theta_esscher
- mincer_zarnowitz
- calc_mdd
- optimizar_min_cvar
- bootstrap_estacionario
- media_hac
- optimizar_mvsk
- _Limitador
- entropy_pooling
- qu_metrics.py
- winsorizar
- Working with the graphify knowledge graph

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
- `Reachable ETF floor and LP feasibility check` --semantically_similar_to--> `Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12)`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `lambda3/lambda4 derived from gamma (CRRA Taylor expansion)` --semantically_similar_to--> `BL lambda3/lambda4 closed form from gamma`  [INFERRED] [semantically similar]
  README.md → docs/risk_profile_audit.html
- `test_fetch_otm_chain_empty_paths_carry_empty_pairs()` --calls--> `fetch_otm_chain()`  [EXTRACTED]
  tests/test_ajuste_iv_tasa.py → polygon_client.py
- `test_relajar_banda_no_toca_una_banda_alcanzable()` --calls--> `relajar_banda_etf()`  [EXTRACTED]
  tests/test_etf_floor_refill.py → qu_metrics.py
- `test_siguiente_reposicion_prioriza_etf_cuando_faltan()` --calls--> `siguiente_reposicion()`  [EXTRACTED]
  tests/test_etf_floor_refill.py → qu_metrics.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared estimation modules feeding the three optimizers** — polygon_client, risk_estimators, market_data, portfolio_constraints, qu_metrics, bl_metrics, pipeline_io, quadratic_utility, minimum_variance, black_litterman [EXTRACTED 1.00]
- **Options-implied tail risk pipeline (BKM, Q to P, Cornish-Fisher)** — readme_bkm, readme_q_to_p, readme_cornish_fisher, readme_co_moments, readme_ssvi_fit [INFERRED 0.85]
- **Risk-profile calibration (gamma ladder, CRRA lambdas, lambda-only aversion, pen_ret)** — docs_risk_profile_audit_gamma_ladder, docs_risk_profile_audit_crra_lambdas, docs_risk_profile_audit_lambda_only_risk_aversion, docs_risk_profile_audit_lambda_calibration [INFERRED 0.85]

## Communities (69 total, 18 thin omitted)

### Community 0 - "test_etf_floor_refill.py"
Cohesion: 0.05
Nodes (42): candidatos_reposicion(), completar_etfs(), contar_etfs(), diagnostico_banda_etf(), etfs_necesarios(), relajar_banda_etf(), reserva_etf(), restricciones_factibles() (+34 more)

### Community 1 - "to_years"
Cohesion: 0.09
Nodes (23): get_spot_safe_bkm(), polygon_get_atm_option(), _asegurar_momentos_actuales(), bkm_compute_moments(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_reconstruct_mfis_history(), bkm_seleccion_fecha() (+15 more)

### Community 2 - "quadratic_utility.py"
Cohesion: 0.05
Nodes (34): armar_restricciones(), _asegurar_momentos_actuales(), bkm_compute_moments(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_iv_chain_to_prices(), bs_price(), clean_symbol_table() (+26 more)

### Community 3 - "bl_metrics.py"
Cohesion: 0.07
Nodes (21): apply_vol_q_to_p(), calibrar_superficie_ssvi(), _fecha_naive(), forward_por_paridad(), iv_vol_at_horizon(), mfiv_or_horizon_variance(), momentos_fallback(), seleccionar_vencimientos() (+13 more)

### Community 4 - "numpy"
Cohesion: 0.07
Nodes (28): clip_negligible_weights(), log_portfolio_return(), markowitz_clasico(), momentos_realizados_rolling(), clip_implied_correlation(), comparison_lambdas(), frontier_curve(), frontier_lambda_grid() (+20 more)

### Community 5 - "polygon_client.py"
Cohesion: 0.06
Nodes (34): _avisar_403(), _avisar_sin_api_key(), cache_get(), cache_permitida(), cache_set(), _con_api_key(), es_snapshot(), _espera_reintento() (+26 more)

### Community 6 - "implied_variance_to_horizon"
Cohesion: 0.25
Nodes (5): mfiv_annual_vol(), implied_variance_to_horizon(), test_mfiv_annual_vol_uses_real_dte(), test_implied_variance_to_horizon_arrays_and_nan(), test_implied_variance_to_horizon_uses_real_dte()

### Community 7 - "math"
Cohesion: 0.15
Nodes (11): bs_call_delta(), build_weight_constraints(), bs_call_delta_from_vol(), otm_log_moneyness(), shrink_mu_to_prior(), test_horizonte_cambia_la_moneyness_efectiva(), test_bs_call_delta_invalid_inputs_are_nan(), test_otm_call_delta_can_fall_below_old_threshold() (+3 more)

### Community 8 - "minimum_variance.py"
Cohesion: 0.09
Nodes (21): bkm_annual_vol(), bkm_compute_moments(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), bkm_motivo_fallback(), bkm_resumen_fallbacks(), _bkm_vacio() (+13 more)

### Community 9 - "minimum_variance_(seasonal_version).py"
Cohesion: 0.07
Nodes (24): momentos_cola_historicos(), bkm_annual_vol(), bkm_compute_moments(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), bkm_motivo_fallback(), bkm_resumen_fallbacks() (+16 more)

### Community 10 - "market_data.py"
Cohesion: 0.10
Nodes (18): _campo(), combinar_tickers(), _con_reintentos(), currency_from_suffix(), default_market_cap_cache_path(), es_ticker_formato_us(), _escribir_cache(), _leer_cache() (+10 more)

### Community 11 - "test_market_cap_internacional.py"
Cohesion: 0.10
Nodes (20): _llamar_caps(), _llamar_fx(), tabla_market_cap_texto(), _ordenar(), _proveedores(), cap_provider(), fx_provider(), test_cache_corrupta_no_rompe() (+12 more)

### Community 12 - "pipeline_io.py"
Cohesion: 0.06
Nodes (33): _add_months(), _atomic_write(), _date_or_none(), export_portfolio(), _export_portfolio(), horizon_from_month_list(), horizon_from_months(), _int_or_none() (+25 more)

### Community 13 - "test_ajuste_iv_tasa.py"
Cohesion: 0.12
Nodes (21): resumen_ajuste_iv(), texto_ajuste_iv(), bs_price(), residuo(), _contrato(), _fuente(), _funcion(), _mercado() (+13 more)

### Community 14 - "bkm_reconstruct_mfis_history"
Cohesion: 0.10
Nodes (12): bkm_clave_historia(), bkm_fechas_pendientes(), bkm_reconstruct_mfis_history(), bkm_seleccion_fecha(), _datos_con_precios(), evaluar_historia_bkm(), _fila(), _fila_bkm() (+4 more)

### Community 15 - "test_market_data.py"
Cohesion: 0.12
Nodes (20): align_prices_to_calendar(), resolve_currencies(), resolve_execution_months(), align_daily_panel(), _bdays(), _precios_dos_mercados(), test_align_drops_low_coverage_ticker(), test_align_fills_local_holiday_instead_of_dropping_row() (+12 more)

### Community 16 - "test_portfolio_constraints.py"
Cohesion: 0.23
Nodes (11): with_return_target(), _base(), _minvar(), _slack(), test_atm_call_delta_always_above_half(), test_budget_is_equality_and_box_constraints_hold(), test_etf_and_fx_columns_bind_on_invested_capital(), test_etf_band_skipped_when_subset_has_no_etf() (+3 more)

### Community 17 - "test_script_smoke.py"
Cohesion: 0.22
Nodes (11): _alias_importados(), _asignaciones_de_modulo(), _correr_bl(), _nombres(), sombras_de_import(), test_bl_input_file_overrides_tickers_and_views(), test_bl_risk_profile_env_and_cli(), test_bl_universe_file_drops_default_views() (+3 more)

### Community 18 - "test_risk_estimators.py"
Cohesion: 0.07
Nodes (26): mdd_from_log_returns(), annualize(), max_drawdown(), scale_moments(), var_cvar_cornish_fisher(), _lw_constant_correlation_referencia(), panel(), retornos() (+18 more)

### Community 19 - "fit_ssvi"
Cohesion: 0.16
Nodes (14): fit_ssvi(), objetivo(), _params(), _penalty(), _relativos(), _sigmoid(), _grupos_vencimiento(), ssvi_total_variance() (+6 more)

### Community 21 - "test_universo_y_delta_estacional.py"
Cohesion: 0.20
Nodes (11): convertir_serie_a_usd(), _formato_us_viejo(), _fuente(), _internacionales_del_script(), _literales(), test_bl_no_manda_internacionales_a_polygon(), test_convertir_serie_a_usd_alinea_el_fx(), test_defaults_estacionales_del_colchon() (+3 more)

### Community 22 - "get_spot_history"
Cohesion: 0.13
Nodes (15): get_spot_history(), _retry_spot_single(), _usable_spot(), _cierres(), test_get_spot_history_downloads_the_batch_once_and_workers_only_read(), batch(), single(), test_get_spot_history_falls_through_to_the_next_provider() (+7 more)

### Community 23 - "test_polygon_client.py"
Cohesion: 0.07
Nodes (32): polygon_fetch_chain(), bkm_fetch_otm_chain(), get_polygon_option_snapshot(), bkm_fetch_otm_chain(), get_polygon_option_snapshot(), is_non_us_exchange(), es_transitorio(), expiry_rank_columns() (+24 more)

### Community 24 - "risk_estimators.py"
Cohesion: 0.07
Nodes (24): average_correlation(), cov_ewma_shrunk(), effective_sample_size(), ewma_cov(), ewma_weights(), ledoit_wolf_constant_correlation(), martin_wagner_excess_return(), nearest_psd() (+16 more)

### Community 25 - "frames_from_yf_download"
Cohesion: 0.11
Nodes (10): default_spot_providers(), _frame_from_close(), frames_from_yf_download(), _naive_dates(), yfinance_spot_batch(), yfinance_spot_single(), test_frames_from_yf_download_reads_both_multiindex_orders(), test_yfinance_batch_is_one_unadjusted_download() (+2 more)

### Community 27 - "cornish_fisher_tail"
Cohesion: 0.12
Nodes (16): compute_marginal_cvar_contrib(), compute_marginal_cvar_contrib(), cornish_fisher_domain(), cornish_fisher_es_gradient(), cornish_fisher_moments(), cornish_fisher_params(), a_parametros(), residuo() (+8 more)

### Community 28 - "test_mv_cola_y_delta.py"
Cohesion: 0.20
Nodes (13): _bucle_de_cola(), _descartes(), _fuente(), _funcion(), test_conteo_estable_entre_horizontes(), test_conteos_por_umbral_conservador_moderado_agresivo(), test_defaults_del_filtro_delta_en_mv(), test_fallback_historico_activo_por_defecto() (+5 more)

### Community 29 - "black_litterman.py"
Cohesion: 0.12
Nodes (8): calibrar_ssvi_ticker(), construir_restricciones(), _momento_pendiente(), parse_chain(), port_ret_row(), primas_esscher(), _retorno_min_factible(), _sanear_momento_fisico()

### Community 30 - "Risk Profile Audit (configuration per investor profile)"
Cohesion: 0.05
Nodes (39): Asset Allocation (FICs) am_pm/profiles.py mandates, Risk Profile Audit (configuration per investor profile), Black-Litterman PERFILES (omega_scale, tau, gamma_ra), COL Portfolio Architecture (proposed profile bands, max Sharpe), QU OTM delta filter as annual IV cap, International ticker format filter and region caps, Lambda calibration with pen_ret, Minimum Variance profile parameter tables (normal and seasonal) (+31 more)

### Community 31 - "delta_cushion"
Cohesion: 0.18
Nodes (12): delta_cushion(), evaluar_delta_candidato(), filtro_delta_otm(), _finito(), pasa_filtro_delta(), test_nombres_sin_vol_se_conservan_y_polygon_manda_sobre_historica(), _cojines(), test_colchon_baja_con_la_vol_y_separa_perfiles() (+4 more)

### Community 32 - "test_risk_profile.py"
Cohesion: 0.18
Nodes (9): _cli_risk_profile(), resolve_risk_profile(), _literales(), _presets(), test_preset_agresivo_no_cambia_los_literales(), test_presets_de_mv_y_qu_coinciden_con_la_auditoria(), test_resolve_default_si_no_hay_env_ni_cli(), test_resolve_env_y_cli() (+1 more)

### Community 33 - "pytest"
Cohesion: 0.10
Nodes (31): crra_taylor_lambdas(), integration_strike_bounds(), market_delta(), variance_annual_to_horizon(), _cadena_ssvi(), _precios_con_paridad(), test_apply_vol_q_to_p_does_not_haircut_historical_vol(), test_calibrar_superficie_ignora_leaps_y_quotes_rotos() (+23 more)

### Community 34 - "bkm_fechas_pendientes"
Cohesion: 0.12
Nodes (10): spot_series_for(), bkm_clave_historia(), bkm_fechas_pendientes(), evaluar_historia_bkm(), _fila(), _fila_bkm(), _precargar_spots_bkm(), _spot_series_bkm() (+2 more)

### Community 35 - "close_near_from_bars"
Cohesion: 0.19
Nodes (7): fetch_option_aggs(), close_near_from_bars(), contract_agg_ranges(), bkm_precios_en_rango(), polygon_contract_close_near(), bkm_precios_en_rango(), polygon_contract_close_near()

### Community 36 - "pandas"
Cohesion: 0.06
Nodes (39): average_abs_correlation(), columns_with_min_obs(), covariance_min_history(), dispersion_usable(), dispersion_weights(), history_window(), select_historical_otm(), stitch_covariance() (+31 more)

### Community 37 - "calls_per_minute_from_env"
Cohesion: 0.11
Nodes (11): calls_per_minute_from_env(), estimate_minutes(), _parse_calls_per_min(), set_rate_limit(), entorno_aislado(), test_calls_per_minute_acepta_el_alias_viejo(), test_calls_per_minute_lee_el_nombre_largo(), test_calls_per_minute_sin_env_usa_el_default() (+3 more)

### Community 38 - "mfik_cap_tenor"
Cohesion: 0.20
Nodes (6): mfiv_vs_atm(), _momentos_sector(), mfik_cap(), mfik_cap_tenor(), test_mfik_cap_rises_with_chain_depth(), test_mfik_cap_tenor_loosens_a_short_chain()

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

### Community 43 - "calcular_bkm_moments"
Cohesion: 0.40
Nodes (6): bs_price(), calcular_bkm_moments(), otm_price_ssvi(), phi_powerlaw(), sigma_desde_ssvi(), ssvi_w()

### Community 44 - "descargar_precio"
Cohesion: 0.28
Nodes (4): asegurar_fx(), descargar_fx_moneda(), descargar_precio(), _par_fx()

### Community 46 - "calcular_metricas_riesgo_cola"
Cohesion: 0.29
Nodes (4): calcular_metricas_riesgo_cola(), _pesos_normalizados(), var_cvar_cornish_fisher(), var_cvar_historico()

### Community 47 - "mfis_tail_decision"
Cohesion: 0.33
Nodes (3): mfis_tail_decision(), test_mfis_tail_decision(), test_mfis_tail_default_upper_matches_old_inequality()

### Community 49 - "portfolio_returns_skipna"
Cohesion: 0.50
Nodes (3): portfolio_returns_skipna(), portfolio_returns_series(), portfolio_returns_series()

### Community 53 - "gram_charlier_pdf_ratio"
Cohesion: 0.33
Nodes (4): gram_charlier_pdf_ratio(), he3(), he4(), posterior_gram_charlier()

### Community 57 - "estimar_theta_esscher"
Cohesion: 0.50
Nodes (3): cumulantes_Q_desde_P(), estimar_theta_esscher(), objetivo()

### Community 63 - "optimizar_mvsk"
Cohesion: 0.40
Nodes (3): momentos_portafolio(), optimizar_mvsk(), utilidad_mvsk_negativa()

### Community 74 - "qu_metrics.py"
Cohesion: 0.09
Nodes (14): Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12), prune_order(), annualize_monthly(), estimate_bkm_history_calls(), lambda_monthly_from_annual(), plan_bkm_history_budget(), sector_implied_ready(), utility_terms() (+6 more)

### Community 77 - "Working with the graphify knowledge graph"
Cohesion: 0.33
Nodes (5): Freshness check, Git hygiene, Navigating, Verify before asserting, Working with the graphify knowledge graph

## Knowledge Gaps
- **23 isolated node(s):** `Navigating`, `Verify before asserting`, `Freshness check`, `Git hygiene`, `Navigating` (+18 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 418 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `bkm_reconstruct_mfis_history()` connect `to_years` to `quadratic_utility.py`, `close_near_from_bars`, `bkm_fechas_pendientes`, `polygon_client.py`, `bkm_reconstruct_mfis_history`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **What connects `Navigating`, `Verify before asserting`, `Freshness check` to the rest of the system?**
  _23 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_etf_floor_refill.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05017921146953405 - nodes in this community are weakly interconnected._
- **Why does `ledoit_wolf_constant_correlation()` connect `risk_estimators.py` to `test_risk_estimators.py`, `numpy`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Should `to_years` be split into smaller, more focused modules?**
  _Cohesion score 0.08712121212121213 - nodes in this community are weakly interconnected._
- **Should `quadratic_utility.py` be split into smaller, more focused modules?**
  _Cohesion score 0.047107014848950336 - nodes in this community are weakly interconnected._
- **Should `bl_metrics.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06685633001422475 - nodes in this community are weakly interconnected._