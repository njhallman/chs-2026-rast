# The reversal of gender disparities in the retention and promotion of Big 4 auditors

Reproducibility package for:

> Chen, J. H., N. Hallman, and J. Sunder. "The reversal of gender disparities in the retention
> and promotion of Big 4 auditors." *Review of Accounting Studies*, forthcoming.

**Abstract.** Popular media and academic research have long characterized the Big 4 audit firms
as "boys clubs" that fail to equitably retain and promote women. Using data on nearly 150,000
rank-and-file auditors, we show that women did face significantly lower rates of retention and
promotion throughout the 1990s and 2000s. These disparities reversed during the mid-2010s,
however, and female auditors now enjoy *higher* rates of retention and promotion than their male
colleagues. We examine three drivers: increasing female representation on client audit
committees, growing client emphasis on diversity in hiring and vendor selection, and the
introduction of Form AP, which made lead audit partner identities public for the first time.
Only Form AP significantly predicts the reversal when controlling for the other two. Consistent
with Form AP's salience, the reversal is absent among professionals with no Form AP exposure,
muted where exposure is partial, and delayed in Big 4 tax practices.

This repository contains every script that produces the paper's **12 tables and 8 figures**,
plus the manuscript source. It does *not* contain the licensed employment and audit microdata
the analysis runs on — see [DATA_AVAILABILITY.md](DATA_AVAILABILITY.md) for what those inputs
are and how to obtain them.

## Layout

```
Analysis/
├── pipeline/       Numbered scripts 01-08: acquire raw data, build analysis panels
├── tables/         One script per table in the paper
├── figures/        Main figures
├── benchmarks/     Comparison-group figures (investment banking, non-Big 4 audit, tax)
├── shared/         Paths, data loading, Stata setup, firm mappings, LaTeX helpers
├── run_all.py      Regenerate every table and figure
├── verify_outputs.py   Compare what you generated against the published outputs
└── Data/           Not committed, except Data/public/ (non-proprietary inputs)
LaTeX/              Manuscript source; Tables/ and Figures/ are the generated outputs
reference/          The 12 tables and 8 figures exactly as published, for comparison
tools/              Maintenance helpers (not needed to reproduce)
```

## Requirements

- **Python 3.13+** with `requirements.txt`
- **Stata SE 18+** with `estout`, `ftools`, `reghdfe`, `outreg2`, `coefplot`, `ppmlhdfe`.
  The regression tables are estimated in Stata through `pystata`; you must supply your own
  Stata licence. See [SETUP.md](SETUP.md).
- **A TeX distribution** if you want to recompile the manuscript (`latexmk`, `biber`).
- The licensed input data — see [DATA_AVAILABILITY.md](DATA_AVAILABILITY.md).

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

## Reproducing the results

The pipeline is numbered and runs in order. Steps 01–05 acquire raw data; 06–08 build the
analysis panels. If you already have the raw data in place, start at 06.

```bash
# 1. Acquire raw data (WRDS subscriptions + Duo 2FA; public sources need no auth)
python Analysis/pipeline/01_download_revelio.py --force --wrds-username YOUR_ID
python Analysis/pipeline/02_download_boardex.py --force --wrds-username YOUR_ID
python Analysis/pipeline/03_download_audit_analytics.py --force --wrds-username YOUR_ID
python Analysis/pipeline/04_download_census.py
python Analysis/pipeline/05_download_ipeds.py

# 2. Build the analysis panels
python Analysis/pipeline/06_build_interim.py     # raw -> interim
python Analysis/pipeline/07_prepare_data.py      # interim -> regression-ready panels

# 3. Regenerate all 12 tables and 8 figures, plus the statistics quoted in the text
python Analysis/run_all.py

# 4. Compare against the published outputs
python Analysis/verify_outputs.py
```

Step 08 (`08_fetch_proxy_keywords.py`) does not need to be run: it documents how the proxy
statement keyword counts were built, and its output is committed under
`Analysis/Data/public/proxy/`.

`run_all.py` requires each script to both exit cleanly *and* rewrite the output it declares, so
a script that silently does nothing is reported as a failure. Individual scripts can be run on
their own:

```bash
python Analysis/tables/extended_period_tables.py   # Table 3 (mainB4Table.tex)
```

### Verifying

`verify_outputs.py` compares `LaTeX/Tables/` and `LaTeX/Figures/` against `reference/`:

- **Tables** must be byte-identical (ignoring trailing whitespace). An identical regression
  produces an identical `.tex`.
- **Figures** pass when byte-identical. PNG bytes shift with matplotlib, freetype, and libpng
  versions even when the data is unchanged, so a figure that differs is reported as `REVIEW`
  with a difference image in `diffs/` for you to inspect, not silently accepted. Once you have
  looked at them, `--accept-review` signs off.

If a table does not reproduce, **fix the script that generates it — never edit the `.tex` by
hand.** Every table in `LaTeX/Tables/` is generated output.

## Recompiling the manuscript

```bash
cd LaTeX && latexmk -pdf manuscript.tex
```

`manuscript.tex` reads the tables from `LaTeX/Tables/` and the figures from `LaTeX/Figures/`, so
recompiling after `run_all.py` produces the paper from freshly generated outputs.

## What the tables and figures are

| Output | Script |
| --- | --- |
| `sampleDesign.tex` | `Analysis/tables/sample_design.py` |
| `summaryStats.tex` | `Analysis/tables/summary_stats.py` |
| `mainB4Table.tex` | `Analysis/tables/extended_period_tables.py` |
| `mechanismsTable.tex` | `Analysis/tables/mechanisms_table.py` |
| `destinationQualityPost.tex` | `Analysis/tables/outside_options.py` |
| `rankInteraction.tex` | `Analysis/tables/rank_interaction.py` |
| `robustnessModels.tex` | `Analysis/tables/robustness_models.py` |
| `rolesTable.tex` | `Analysis/tables/roles_table.py` |
| `firmNamesTable.tex` | `Analysis/tables/firm_names.py` |
| `topCompanies.tex` | `Analysis/tables/top_companies.py` |
| `nonB4FirmsTable.tex` | `Analysis/tables/nonb4_firms.py` |
| `VariableDefinitions.tex` | `Analysis/tables/variable_definitions.py` |
| `stackPlot.png` | `Analysis/figures/stack_plot.py` |
| `mechanism_variation_metro.png` | `Analysis/figures/mechanism_variation_metro.py` |
| `retentionGapMap.png` | `Analysis/figures/retention_gap_map.py` |
| `supplyVsEntry.png` | `Analysis/figures/supply_vs_entry.py` |
| `benchmarkBB5IB.png`, `benchmarkOFS.png` | `Analysis/benchmarks/fig_top5_ib_extended.py` |
| `benchmarkATCombined.png` | `Analysis/benchmarks/fig_at_combined.py` |
| `benchmarkB4Tax.png` | `Analysis/benchmarks/fig_b4_nonaudit.py` |

Two further scripts reproduce statistics quoted in the text rather than a table or figure, and
print their results:

- `Analysis/tables/structural_breaks.py` — Chow and sup-Wald break tests (Section 3.1)
- `Analysis/tables/time_to_rank.py` — median time-to-rank by cohort and gender (Introduction)

## Specification

The primary retention and promotion models are estimated as

```
reghdfe retained [female × period interactions] controls, ///
    absorb(firmkey year yearfirst) vce(cluster userid)
```

that is, employee-year OLS with employer, calendar-year, and entry-cohort fixed effects, and
standard errors clustered by auditor.

## Licence

Code is released under the MIT Licence (see [LICENSE](LICENSE)). The manuscript text and figures
remain © the authors. The input data is licensed from third parties and is not redistributed
here.
