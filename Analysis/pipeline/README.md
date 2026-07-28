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

Script 06 prefers the **bulk partition files** (`revelioFsPosUsr_1-4_of_4.feather`) from the original January 2025 Revelio download. These are the data that produced the published tables (145,573 users, 713,614 person-years). If bulk files are not present, it falls back to per-role files from `01_download_revelio.py`.

## Dependencies

Scripts 01-05 download raw data and can run in any order (01-03 share WRDS auth).

Scripts 01-03 require a WRDS username: pass `--wrds-username YOUR_ID` or set
`WRDS_USERNAME`. Each connection triggers a Duo two-factor push -- approve it
promptly, and do not retry in a loop, as repeated failures can lock the account.

Scripts 06-08 must run in order:
- `06` requires raw Revelio files (bulk partitions or per-role files from `01`)
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
│   │   ├── revelioFsPosUsr_{1-4}_of_4.feather   Bulk position data (Jan 2025, preferred by 06)
│   │   ├── revelioPosUsr_role_*.feather          Per-role position files (from 01, fallback)
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
