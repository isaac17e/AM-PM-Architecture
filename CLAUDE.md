# Working with the graphify knowledge graph

`graphify-out/` (committed) holds a knowledge graph of this repo: `graph.json`, `GRAPH_REPORT.md` and `manifest.json`. `wiki/` and `graph.html` are gitignored and not available.

Install the CLI with `pip install graphifyy`, or run it without installing via `uvx --from graphifyy graphify <command>`.

## Navigating

- Before searching files by hand, read `graphify-out/GRAPH_REPORT.md` (god nodes, communities, architecture overview).
- Then use `graphify path A B` (how two things connect), `graphify explain <symbol>` (one symbol and its neighbours) and `graphify affected <file>` (what a change to a file touches).
- Do NOT use `graphify query`: its output is too noisy.

## Verify before asserting

The graph is a hint, not ground truth. Confirm every connection with `rg` before stating it.

- Calls made from a script's top-level (module-level) code are not captured as edges, so the graph under-reports usage from scripts.
- Arrows in `graphify explain` output can be inverted. Check direction in the source.
- Verified example here: calls from the black_litterman, minimum variance and QU scripts to `rk.cov_ewma_shrunk` are missing from the graph. Of 47 calls from `black_litterman.py` to shared modules, only 17 appear as edges.

## Freshness check

`graph.json` records the commit it was built from in the top-level key `built_at_commit`. Check whether code changed since then (ignoring `graphify-out/`):

```
git diff --quiet "$(python3 -c "import json;print(json.load(open('graphify-out/graph.json'))['built_at_commit'])")" HEAD -- . ':!graphify-out'
```

(`jq -r .built_at_commit graphify-out/graph.json` also works.) Exit code 0 means the graph is fresh. A non-zero exit means it is stale: run `graphify update .` (AST-only, no API cost) before relying on it.

## Git hygiene

- Do not commit changes under `graphify-out/` unless explicitly asked.
- Do not commit `.claude/` (its hooks use absolute paths).
- Leave pre-existing untracked or modified files (`.DS_Store`, `graphify-out/.Rhistory`, `salidas_*.txt`, ...) alone and never stage them.

# black_litterman.py: horizon and previews mode

- Horizon: `MESES_HORIZONTE` is resolved once in BLOQUE 0 by `pipeline_io.resolve_horizon`: `horizon_months` in `BL_INPUT_FILE` > env `BL_HORIZON_MONTHS` > default 2 (integer 1..12, otherwise `InvalidHorizonError`). Anything derived from it (`MAX_DIAS_VENCIMIENTO`, `BOOTSTRAP_BLOQUE`, `horizonte_dias`, `factor_anualizacion`, `tau_horizonte`, `Rf_h`, export `horizon_days`/`horizon_end`) must stay below that line. `tests/test_bl_horizonte_previews.py` enforces the ordering with an AST check.
- Previews: `BL_MODE=previews` or `--previews` runs to the end of BLOQUE 5 and calls `sys.exit(0)` after writing `previews_<timestamp>.json` (`BL_PREVIEWS_OUT`, default `PORTFOLIO_OUT_DIR`). Returns and vols in it are at the configured horizon, not annualized. Format: README, "Previews JSON". Under `runpy` a test must catch `SystemExit`.
