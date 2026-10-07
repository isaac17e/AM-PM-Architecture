# Graph Report - AM-PM-Architecture  (2026-10-06)

## Corpus Check
- 32 files · ~122,159 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .ini 1)

## Summary
- 1295 nodes · 2892 edges · 76 communities (53 shown, 23 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 68 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5cd1de19`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_etf_floor_refill.py
- quadratic_utility_(seasonal_version).py
- quadratic_utility.py
- test_bl_metrics.py
- numpy
- polygon_client.py
- implied_variance_to_horizon
- bs_call_delta
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
- pytest
- fit_ssvi
- test_bl_universo.py
- test_universo_y_delta_estacional.py
- get_spot_history
- test_polygon_client.py
- test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados
- frames_from_yf_download
- portfolio_constraints.py
- risk_estimators.py
- test_mv_cola_y_delta.py
- black_litterman.py
- Risk Profile Audit (configuration per investor profile)
- math
- test_risk_profile.py
- higher_moments_admissible
- test_etf_floor_estacional.py
- close_near_from_bars
- pandas
- set_rate_limit
- _momentos_sector
- test_tail_prune_loop.py
- normalize_currency
- etfs_necesarios
- _RespuestaFalsa
- restricciones_factibles
- descargar_precio
- _YahooFalso
- calcular_metricas_riesgo_cola
- candidatos_reposicion
- elegir_spot_momentos
- is_us_ticker
- otm_log_moneyness
- dedupe_share_classes
- _retorno_min_factible
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
- bkm_motivo_fallback
- build_qp_constraints
- bkm_motivo_fallback
- build_qp_constraints
- _Limitador
- construir_restricciones
- entropy_pooling
- _momento_pendiente
- _sanear_momento_fisico
- qu_metrics.py
- winsorizar
- CLAUDE.md

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
- `test_currency_from_suffix()` --calls--> `currency_from_suffix()`  [EXTRACTED]
  tests/test_market_data.py → market_data.py
- `test_expiry_rank_prefers_50_over_15_for_a_30_day_target()` --calls--> `expiry_rank_columns()`  [EXTRACTED]
  tests/test_polygon_client.py → polygon_client.py
- `test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados()` --calls--> `candidatos_reposicion()`  [EXTRACTED]
  tests/test_etf_floor_estacional.py → qu_metrics.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared estimation modules feeding the three optimizers** — polygon_client, risk_estimators, market_data, portfolio_constraints, qu_metrics, bl_metrics, pipeline_io, quadratic_utility, minimum_variance, black_litterman [EXTRACTED 1.00]
- **Options-implied tail risk pipeline (BKM, Q to P, Cornish-Fisher)** — readme_bkm, readme_q_to_p, readme_cornish_fisher, readme_co_moments, readme_ssvi_fit [INFERRED 0.85]
- **Risk-profile calibration (gamma ladder, CRRA lambdas, lambda-only aversion, pen_ret)** — docs_risk_profile_audit_gamma_ladder, docs_risk_profile_audit_crra_lambdas, docs_risk_profile_audit_lambda_only_risk_aversion, docs_risk_profile_audit_lambda_calibration [INFERRED 0.85]

## Communities (76 total, 23 thin omitted)

### Community 0 - "test_etf_floor_refill.py"
Cohesion: 0.14
Nodes (11): relajar_banda_etf(), siguiente_reposicion(), test_relajar_banda_no_toca_una_banda_alcanzable(), test_relajar_banda_sube_el_techo_si_faltan_acciones(), test_script_chequea_factibilidad_antes_de_quadprog(), test_script_delta_min_agresivo_es_015(), test_siguiente_reposicion_prioriza_etf_cuando_faltan(), test_siguiente_reposicion_sin_etf_coincide_con_el_indice_secuencial() (+3 more)

### Community 1 - "quadratic_utility_(seasonal_version).py"
Cohesion: 0.06
Nodes (30): plan_bkm_history_budget(), armar_restricciones(), _asegurar_momentos_actuales(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_iv_chain_to_prices(), bkm_seleccion_fecha(), bs_price() (+22 more)

### Community 2 - "quadratic_utility.py"
Cohesion: 0.05
Nodes (32): spot_series_for(), armar_restricciones(), _asegurar_momentos_actuales(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_iv_chain_to_prices(), bkm_seleccion_fecha(), bs_price() (+24 more)

### Community 3 - "test_bl_metrics.py"
Cohesion: 0.05
Nodes (42): calibrar_superficie_ssvi(), crra_taylor_lambdas(), _fecha_naive(), forward_por_paridad(), integration_strike_bounds(), iv_vol_at_horizon(), market_delta(), momentos_fallback() (+34 more)

### Community 4 - "numpy"
Cohesion: 0.06
Nodes (31): apply_vol_q_to_p(), clip_negligible_weights(), log_portfolio_return(), markowitz_clasico(), scale_option_deltas(), nearest_psd(), portfolio_log_returns(), portfolio_moments() (+23 more)

### Community 5 - "polygon_client.py"
Cohesion: 0.10
Nodes (20): _avisar_403(), _avisar_sin_api_key(), cache_permitida(), cache_set(), _con_api_key(), es_snapshot(), _espera_reintento(), fechas_en_clave() (+12 more)

### Community 6 - "implied_variance_to_horizon"
Cohesion: 0.17
Nodes (8): mfiv_or_horizon_variance(), variance_annual_to_horizon(), mfiv_annual_vol(), implied_variance_to_horizon(), test_mfiv_fallback_uses_horizon_variance_not_annual(), test_variance_annual_matches_implied_variance_helper(), test_mfiv_annual_vol_uses_real_dte(), test_implied_variance_to_horizon_arrays_and_nan()

### Community 7 - "bs_call_delta"
Cohesion: 0.33
Nodes (4): bs_call_delta(), test_atm_call_delta_always_above_half(), test_bs_call_delta_invalid_inputs_are_nan(), test_otm_call_delta_can_fall_below_old_threshold()

### Community 8 - "minimum_variance.py"
Cohesion: 0.10
Nodes (17): bkm_annual_vol(), bkm_compute_moments(), bkm_fetch_otm_chain(), bkm_get_current_moments(), bkm_get_current_moments_cached(), bkm_iv_chain_to_prices(), _bkm_vacio(), bs_price() (+9 more)

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
Cohesion: 0.06
Nodes (35): _add_months(), _atomic_write(), _date_or_none(), export_portfolio(), _export_portfolio(), horizon_from_month_list(), horizon_from_months(), _int_or_none() (+27 more)

### Community 13 - "test_ajuste_iv_tasa.py"
Cohesion: 0.09
Nodes (32): get_polygon_option_snapshot(), get_polygon_option_snapshot(), expiry_rank_columns(), pares_call_put(), resumen_ajuste_iv(), texto_ajuste_iv(), polygon_get_atm_option(), polygon_get_atm_option() (+24 more)

### Community 14 - "bkm_reconstruct_mfis_history"
Cohesion: 0.11
Nodes (14): cache_get(), mfis_tail_decision(), bkm_clave_historia(), bkm_fechas_pendientes(), bkm_reconstruct_mfis_history(), evaluar_historia_bkm(), bkm_clave_historia(), bkm_fechas_pendientes() (+6 more)

### Community 15 - "test_market_data.py"
Cohesion: 0.10
Nodes (27): align_prices_to_calendar(), drop_partial_last_week(), resolve_currencies(), resolve_execution_months(), align_daily_panel(), _bdays(), _precios_dos_mercados(), _semanal() (+19 more)

### Community 16 - "test_portfolio_constraints.py"
Cohesion: 0.35
Nodes (9): _base(), _minvar(), _slack(), test_budget_is_equality_and_box_constraints_hold(), test_etf_and_fx_columns_bind_on_invested_capital(), test_etf_band_skipped_when_subset_has_no_etf(), test_frontier_feasible_target_respects_etf_band_and_fx_cap(), test_frontier_target_below_etf_band_is_infeasible() (+1 more)

### Community 17 - "test_script_smoke.py"
Cohesion: 0.22
Nodes (11): _alias_importados(), _asignaciones_de_modulo(), _correr_bl(), _nombres(), sombras_de_import(), test_bl_input_file_overrides_tickers_and_views(), test_bl_risk_profile_env_and_cli(), test_bl_universe_file_drops_default_views() (+3 more)

### Community 18 - "pytest"
Cohesion: 0.09
Nodes (31): mdd_from_log_returns(), annualize(), max_drawdown(), scale_moments(), test_mdd_log_matches_exp_cumsum_not_simple_compounding(), _lw_constant_correlation_referencia(), panel(), retornos() (+23 more)

### Community 19 - "fit_ssvi"
Cohesion: 0.16
Nodes (14): fit_ssvi(), objetivo(), _params(), _penalty(), _relativos(), _sigmoid(), _grupos_vencimiento(), ssvi_total_variance() (+6 more)

### Community 21 - "test_universo_y_delta_estacional.py"
Cohesion: 0.18
Nodes (13): convertir_serie_a_usd(), _descartados(), _formato_us_viejo(), _fuente(), _internacionales_del_script(), _literales(), test_bl_no_manda_internacionales_a_polygon(), test_conteo_de_colchon_separa_umbrales_y_aguanta_el_horizonte() (+5 more)

### Community 22 - "get_spot_history"
Cohesion: 0.13
Nodes (15): get_spot_history(), _retry_spot_single(), _usable_spot(), _cierres(), test_get_spot_history_downloads_the_batch_once_and_workers_only_read(), batch(), single(), test_get_spot_history_falls_through_to_the_next_provider() (+7 more)

### Community 23 - "test_polygon_client.py"
Cohesion: 0.07
Nodes (31): polygon_fetch_chain(), calls_per_minute_from_env(), default_cache_dir(), es_transitorio(), fetch_otm_chain(), get_all(), polygon_format_ticker(), test_fetch_otm_chain_empty_paths_carry_empty_pairs() (+23 more)

### Community 24 - "test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados"
Cohesion: 0.18
Nodes (9): completar_etfs(), contar_etfs(), reserva_etf(), test_flujo_conservador_completa_cuatro_etf_sin_revivir_descartados(), test_completar_etfs_agrega_solo_lo_necesario_y_en_orden(), test_completar_etfs_devuelve_lo_que_haya_si_no_alcanza(), test_contar_etfs_sin_duplicados(), test_reserva_etf_toma_los_que_faltan_en_orden_de_ranking() (+1 more)

### Community 25 - "frames_from_yf_download"
Cohesion: 0.11
Nodes (10): default_spot_providers(), _frame_from_close(), frames_from_yf_download(), _naive_dates(), yfinance_spot_batch(), yfinance_spot_single(), test_frames_from_yf_download_reads_both_multiindex_orders(), test_yfinance_batch_is_one_unadjusted_download() (+2 more)

### Community 26 - "portfolio_constraints.py"
Cohesion: 0.18
Nodes (6): build_weight_constraints(), prune_order(), relax_group_band(), with_return_target(), test_prune_order_drops_the_small_weight_not_the_capped_defensive(), test_relax_group_band_lowers_an_unreachable_etf_floor()

### Community 27 - "risk_estimators.py"
Cohesion: 0.05
Nodes (39): compute_marginal_cvar_contrib(), compute_marginal_cvar_contrib(), AM-PM Portfolio Construction Repository, Pull request merge order (stacked PRs #2 to #4 then this PR), numpy>=1.24, pandas>=2.0, plotly>=5.18, quadprog>=0.1.11 (+31 more)

### Community 28 - "test_mv_cola_y_delta.py"
Cohesion: 0.20
Nodes (13): _bucle_de_cola(), _descartes(), _fuente(), _funcion(), test_conteo_estable_entre_horizontes(), test_conteos_por_umbral_conservador_moderado_agresivo(), test_defaults_del_filtro_delta_en_mv(), test_fallback_historico_activo_por_defecto() (+5 more)

### Community 29 - "black_litterman.py"
Cohesion: 0.17
Nodes (9): bs_price(), calcular_bkm_moments(), momentos_ponderados(), otm_price_ssvi(), phi_powerlaw(), port_ret_row(), primas_esscher(), sigma_desde_ssvi() (+1 more)

### Community 30 - "Risk Profile Audit (configuration per investor profile)"
Cohesion: 0.07
Nodes (28): Asset Allocation (FICs) am_pm/profiles.py mandates, Risk Profile Audit (configuration per investor profile), Black-Litterman PERFILES (omega_scale, tau, gamma_ra), COL Portfolio Architecture (proposed profile bands, max Sharpe), QU OTM delta filter as annual IV cap, Conservative ETF band floor (0.55 +/- 0.10, max_weight 0.12), International ticker format filter and region caps, Lambda calibration with pen_ret (+20 more)

### Community 31 - "math"
Cohesion: 0.19
Nodes (13): bs_call_delta_from_vol(), delta_cushion(), evaluar_delta_candidato(), filtro_delta_otm(), _finito(), pasa_filtro_delta(), test_nombres_sin_vol_se_conservan_y_polygon_manda_sobre_historica(), _cojines() (+5 more)

### Community 32 - "test_risk_profile.py"
Cohesion: 0.18
Nodes (9): _cli_risk_profile(), resolve_risk_profile(), _literales(), _presets(), test_preset_agresivo_no_cambia_los_literales(), test_presets_de_mv_y_qu_coinciden_con_la_auditoria(), test_resolve_default_si_no_hay_env_ni_cli(), test_resolve_env_y_cli() (+1 more)

### Community 33 - "higher_moments_admissible"
Cohesion: 0.20
Nodes (7): momentos_cola_historicos(), momentos_cola_historicos(), bkm_compute_moments(), bkm_compute_moments(), higher_moments_admissible(), mfik_cap_tenor(), test_higher_moments_admissible_pearson()

### Community 34 - "test_etf_floor_estacional.py"
Cohesion: 0.27
Nodes (6): _bloque_restricciones(), _correr_restricciones(), test_banda_que_ya_cumplia_no_cambia(), test_con_el_cuarto_etf_el_conservador_resuelve_sin_relajar(), test_sin_cuarto_etf_la_banda_se_relaja_y_quadprog_resuelve(), test_sin_relajar_falla_con_mensaje_claro_y_no_con_quadprog()

### Community 35 - "close_near_from_bars"
Cohesion: 0.19
Nodes (7): fetch_option_aggs(), close_near_from_bars(), contract_agg_ranges(), bkm_precios_en_rango(), polygon_contract_close_near(), bkm_precios_en_rango(), polygon_contract_close_near()

### Community 36 - "pandas"
Cohesion: 0.06
Nodes (40): calibrar_ssvi_ticker(), momentos_realizados_rolling(), parse_chain(), average_abs_correlation(), columns_with_min_obs(), covariance_min_history(), dispersion_weights(), history_window() (+32 more)

### Community 37 - "set_rate_limit"
Cohesion: 0.15
Nodes (7): estimate_minutes(), _parse_calls_per_min(), set_rate_limit(), entorno_aislado(), test_limiter_spaces_calls(), test_parse_calls_per_min(), test_set_rate_limit_updates_limiter_and_estimate()

### Community 38 - "_momentos_sector"
Cohesion: 0.29
Nodes (4): mfiv_vs_atm(), _momentos_sector(), mfik_cap(), test_mfiv_far_above_atm_falls_back_to_atm_variance()

### Community 39 - "test_tail_prune_loop.py"
Cohesion: 0.26
Nodes (6): _bucle_de_poda(), _correr(), test_block_cut_is_skipped_when_it_leaves_too_few_names(), test_min_weight_keeps_capped_defensives(), test_names_below_threshold_are_cut_in_one_step(), test_prune_loop_survives_floor_weights()

### Community 40 - "normalize_currency"
Cohesion: 0.17
Nodes (8): normalize_currency(), price_scale_factor(), download_period_returns(), get_currency_for_ticker(), download_period_returns(), get_currency_for_ticker(), test_normalize_currency(), test_price_scale_factor()

### Community 41 - "etfs_necesarios"
Cohesion: 0.22
Nodes (6): diagnostico_banda_etf(), etfs_necesarios(), test_diagnostico_explica_el_piso_de_etf(), test_diagnostico_vacio_si_los_conteos_alcanzan(), test_etfs_necesarios(), test_etfs_necesarios_rechaza_max_weight_invalido()

### Community 42 - "_RespuestaFalsa"
Cohesion: 0.14
Nodes (12): n_fallos_transitorios(), _RespuestaFalsa, test_get_json_403_is_not_retried_and_names_the_plan(), _get(), test_get_json_exhausts_retries_on_network_error(), test_get_json_jitter_on_5xx_and_retry_after_wins(), test_get_json_non_transient_error_is_not_retried_nor_cached(), _get() (+4 more)

### Community 43 - "restricciones_factibles"
Cohesion: 0.36
Nodes (8): restricciones_factibles(), test_caso_conservador_tal_como_llegaba_es_infactible_para_quadprog(), _quadprog(), _restricciones(), test_caso_conservador_es_infactible_y_quadprog_lo_confirma(), test_con_cuatro_etf_el_conservador_es_factible(), test_factibilidad_considera_el_tope_regional(), test_relajar_banda_lleva_el_piso_a_lo_alcanzable_y_queda_factible()

### Community 44 - "descargar_precio"
Cohesion: 0.24
Nodes (4): asegurar_fx(), descargar_fx_moneda(), descargar_precio(), _par_fx()

### Community 46 - "calcular_metricas_riesgo_cola"
Cohesion: 0.29
Nodes (4): calcular_metricas_riesgo_cola(), _pesos_normalizados(), var_cvar_cornish_fisher(), var_cvar_historico()

### Community 47 - "candidatos_reposicion"
Cohesion: 0.40
Nodes (3): candidatos_reposicion(), test_reposicion_aplica_el_filtro_iv_a_quien_nunca_paso_por_el(), test_reposicion_bkm_no_trae_de_vuelta_a_mchi()

### Community 48 - "elegir_spot_momentos"
Cohesion: 0.33
Nodes (3): elegir_spot_momentos(), _spot_bkm(), test_elegir_spot_momentos_usa_el_cierre_del_dia_o_la_cadena()

### Community 49 - "is_us_ticker"
Cohesion: 0.50
Nodes (3): is_non_us_exchange(), is_non_us_exchange(), is_us_ticker()

### Community 50 - "otm_log_moneyness"
Cohesion: 0.50
Nodes (3): otm_log_moneyness(), test_horizonte_cambia_la_moneyness_efectiva(), test_moneyness_escala_con_uno_y_dos_meses_de_rebalanceo()

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
Cohesion: 0.06
Nodes (24): annualize_monthly(), clip_implied_correlation(), comparison_lambdas(), dispersion_usable(), estimate_bkm_history_calls(), frontier_curve(), frontier_lambda_grid(), lambda_monthly_from_annual() (+16 more)

## Knowledge Gaps
- **16 isolated node(s):** `graphify`, `pandas>=2.0`, `plotly>=5.18`, `scipy>=1.10`, `statsmodels>=0.14` (+11 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 410 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Risk Profile Audit (configuration per investor profile)` connect `Risk Profile Audit (configuration per investor profile)` to `risk_estimators.py`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **What connects `graphify`, `pandas>=2.0`, `plotly>=5.18` to the rest of the system?**
  _16 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_etf_floor_refill.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13725490196078433 - nodes in this community are weakly interconnected._
- **Why does `Workflow architecture (shared modules feed standalone optimizers)` connect `risk_estimators.py` to `quadratic_utility.py`, `test_bl_metrics.py`, `polygon_client.py`, `minimum_variance.py`, `market_data.py`, `qu_metrics.py`, `pipeline_io.py`, `portfolio_constraints.py`, `black_litterman.py`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Should `quadratic_utility_(seasonal_version).py` be split into smaller, more focused modules?**
  _Cohesion score 0.0563265306122449 - nodes in this community are weakly interconnected._
- **Why does `fit_ssvi()` connect `fit_ssvi` to `test_bl_metrics.py`, `numpy`, `math`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Should `quadratic_utility.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05429864253393665 - nodes in this community are weakly interconnected._