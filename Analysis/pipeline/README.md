# Data Pipeline

Numbered scripts that download, process, and prepare all data for the paper. Each script is self-contained and documents its data sources, authentication requirements, and outputs.

## Script Sequence

| # | Script | Source | Auth | Description |
|---|--------|--------|------|-------------|
| 01 | `01_download_revelio.py` | WRDS Revelio | Duo 2FA | Position files by role + education data + B4 career histories |
| 02 | `02_download_boardex.py` | WRDS BoardEx | Duo 2FA | Board composition and committee data |
| 03 | `03_download_audit_analytics.py` | WRDS Audit Analytics | Duo 2FA | Auditor-client engagement records (audit opinions) |
| 04 | `04_download_census.py` | Census/OMB | Public | ZIP-to-CBSA crosswalk from Census ZCTA + OMB delineation |
| 05 | `05_download_ipeds.py` | NCES IPEDS | Public | Accounting degree completions by year/institution |
| 06 | `06_build_interim.py` | Local | None | Raw Revelio → interim datasets |
| 07 | `07_prepare_data.py` | Local | None | Interim → processed analysis-ready panels |
| 08 | `08_fetch_proxy_keywords.py` | Local SEC mirror | None | Extract DEI keywords from proxy statements. **Optional** -- its output is committed under `Analysis/Data/public/proxy/`. |

## Data Sources for 06_build_interim.py

Script 06 builds two datasets from two different sources:

- **Big 4 audit panel** from `revelioB4Aud.feather` (Big 4 audit/auditor positions pre-extracted
  from the January 2025 Revelio download) plus `revelioB4Edu.feather` for education. These are the
  data behind the published tables.
- **Other financial services panel** from the per-role files
  (`revelioPosUsr_role_*.feather`, all 58 of them, consulting roles excluded) plus
  `revelioEdu_role_combined.feather`.

Both must be present; there is no fallback between them.

## Dependencies

Scripts 01-05 download raw data and can run in any order (01-03 share WRDS auth).

Scripts 01-03 require a WRDS username: pass `--wrds-username YOUR_ID` or set
`WRDS_USERNAME`. Each connection triggers a Duo two-factor push -- approve it
promptly, and do not retry in a loop, as repeated failures can lock the account.

Scripts 06-08 must run in order:
- `06` requires `revelioB4Aud.feather`, `revelioB4Edu.feather`, the per-role position files
  from `01`, and `revelioEdu_role_combined.feather`
- `07` requires interim files from `06`, plus BoardEx, Audit Analytics, and
  `public/edgar/company_locations.csv` for the mechanism variables. It FAILS if an
  input needed for a published table is missing; `--allow-missing` downgrades that
  to a warning, and the affected tables will not reproduce.
- `08` requires Audit Analytics from `03` and a local SEC filings mirror passed via
  `--edgar-archive`. Not needed for reproduction.

## Usage

```bash
# Rebuild from existing raw data (no WRDS connection needed)
python Analysis/pipeline/06_build_interim.py
python Analysis/pipeline/07_prepare_data.py
python Analysis/run_all.py

# Full pipeline with fresh download (requires WRDS Duo 2FA)
python Analysis/pipeline/01_download_revelio.py --force --wrds-username YOUR_ID
python Analysis/pipeline/02_download_boardex.py --force --wrds-username YOUR_ID
python Analysis/pipeline/03_download_audit_analytics.py --force --wrds-username YOUR_ID
python Analysis/pipeline/04_download_census.py
python Analysis/pipeline/05_download_ipeds.py
python Analysis/pipeline/06_build_interim.py
python Analysis/pipeline/07_prepare_data.py
python Analysis/pipeline/08_fetch_proxy_keywords.py --edgar-archive /path/to/sec/mirror
python Analysis/run_all.py
```

## Data Directory Layout

```
Analysis/Data/
├── raw/
│   ├── revelio/
│   │   ├── revelioB4Aud.feather                  Big 4 audit positions (Jan 2025) -- used by 06
│   │   ├── revelioB4Edu.feather                  Big 4 education (Jan 2025) -- used by 06
│   │   ├── revelioPosUsr_role_*.feather          Per-role position files (from 01) -- used by 06
│   │   ├── revelioEdu_role_combined.feather       Education data
│   │   └── revelio_b4_users_all_positions.feather B4 auditor complete career histories
│   ├── boardex/          3 board composition feather files
│   ├── audit_analytics/  Auditor-client engagement CSV
│   ├── census/           ZIP-CBSA crosswalk + OMB reference
│   └── ipeds/            Accounting degree completions CSVs
├── interim/
│   ├── revB4Aud.feather          Big 4 auditor positions (from 06)
│   └── revOtherFs.feather        Other FS positions (from 06)
└── processed/
    ├── revB4AudStata.feather     Regression-ready B4 panel (from 07)
    ├── revB4AudExp.feather       Exploration B4 panel (from 07)
    ├── revOtherFsStata.feather   Regression-ready Other FS panel (from 07)
    ├── revOtherFsExp.feather     Exploration Other FS panel (from 07)
    └── sample_counts.json        Filtering audit trail (from 07)
```

## A note on writing back to object storage

Scripts 02-04, 06, and 07 call `upload_to_r2()` after producing a dataset, which archives it to
the authors' bucket. That upload is skipped unless **both** object-storage credentials and
`R2_ALLOW_UPLOAD=1` are set, so having read credentials in your environment cannot cause a rerun
to overwrite the archived copies. Reproducers never need it.
