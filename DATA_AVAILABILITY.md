# Data availability

The analysis draws on four kinds of input. Three of them are licensed from commercial vendors
and **cannot be redistributed**, so they are not in this repository. This document says exactly
what each input is, where it comes from, and where it has to sit on disk for the code to find
it.

Everything resolves through `shared.r2.ensure_data_file(subpath)`, which looks for
`Analysis/Data/<subpath>`, then `Analysis/Data/public/<subpath>`, and raises a message naming
the missing file if neither exists. There are no hidden fetches and no credentials in this
repository.

## 1. Licensed data — you must obtain this yourself

All three are available through [WRDS](https://wrds-www.wharton.upenn.edu/) to subscribing
institutions. `Analysis/pipeline/01`–`03` download them directly given a WRDS account with the
relevant subscriptions; each connection triggers a Duo two-factor push.

| Source | Vendor | What it provides | Pipeline script | Lands in |
| --- | --- | --- | --- | --- |
| Revelio Labs | Revelio Labs, via WRDS | Individual employment histories (position spells, titles, employers, locations) and education records. The employee panel is built from these. | `01_download_revelio.py` | `Analysis/Data/raw/revelio/` |
| BoardEx | BoardEx, via WRDS | Board and committee composition, used for the audit-committee gender measure. | `02_download_boardex.py` | `Analysis/Data/raw/boardex/` |
| Audit Analytics | Ideagen Audit Analytics, via WRDS | Auditor–client engagements (audit opinions), used to link Big 4 offices to their clients. | `03_download_audit_analytics.py` | `Analysis/Data/raw/audit_analytics/` |

```bash
python Analysis/pipeline/01_download_revelio.py --force --wrds-username YOUR_ID
```

Pass `--wrds-username`, or set `WRDS_USERNAME`. There is no default.

### A note on the Revelio vintage

The published results were produced from the January 2025 Revelio bulk extract (145,573 users;
713,614 person-years). Revelio revises its underlying profile data over time — job histories are
re-parsed, and profiles are added — so a fresh extract will not reproduce the published tables
exactly. `06_build_interim.py` prefers the bulk partition files
(`revelioFsPosUsr_{1-4}_of_4.feather`) for this reason and falls back to per-role files only if
they are absent. Anyone attempting an exact numerical reproduction should request the January
2025 vintage; a current extract will reproduce the patterns but not the digits.

## 2. Public data — downloaded by the pipeline

No authentication required.

| Source | What it provides | Pipeline script |
| --- | --- | --- |
| US Census 2020 ZCTA-to-county relationship file, plus the OMB 2023 CBSA delineation file | ZIP5 → CBSA crosswalk, for the metro-level analysis | `04_download_census.py` |
| NCES IPEDS Completions (`C{year}_A`) | Accounting bachelor's degree completions by institution and gender, 2000–2023, for the talent-pipeline figure | `05_download_ipeds.py` |

## 3. Public and author-curated inputs — committed to this repository

These live in `Analysis/Data/public/` and are either public-domain or small hand-built mappings.
`tools/fetch_public_inputs.py --list` prints the manifest with provenance for each.

| File | What it is |
| --- | --- |
| `census/zip_cbsa.csv` | ZIP5 → CBSA crosswalk, built by `04_download_census.py` from Census and OMB files. Public domain. |
| `census/cbsa_revelio_metro.csv` | CBSA code → Revelio `metro_area` mapping, hand-reviewed by the authors. Not regenerable by any script. |
| `interim/at_revelio_firm_mapping.json` | *Accounting Today* Top 100 firm → Revelio `company_raw` mapping, with PCAOB annual-inspection status. Hand-curated by the authors. |
| `proxy/proxy_dei_keywords_v2.csv` | DEI and gender keyword counts per DEF 14A filing, computed by `08_fetch_proxy_keywords.py` from public SEC filings. |
| `edgar/company_locations.csv` | Registrant business city, state, and ZIP by CIK, from the SEC submissions API. Public domain. See the caveat below. |
| `geo/us-states.json` | US state boundaries (Census TIGER, public domain), used by the retention-gap map. Vendored here because the figure script previously fetched it from an unpinned GitHub URL at run time, which made the figure depend on a third-party file that could change without notice. |

The last two exist so that no reproducer needs the authors' local mirror of SEC filings.
`08_fetch_proxy_keywords.py` documents how the keyword counts were produced and requires
`--edgar-archive` pointing at such a mirror; you do not need to run it.

**IPEDS is deliberately not committed.** The Completions files are public domain but total
~900 MB. `Analysis/pipeline/05_download_ipeds.py` fetches them straight from NCES with no
authentication, into `Analysis/Data/raw/ipeds/`. Run it before `supply_vs_entry.py`.

### Caveat on `edgar/company_locations.csv`

This file maps each Big 4 audit client CIK to a business address, which is how `07` assigns
clients to CBSAs for the Table 4 mechanism measures. It is built by
`tools/build_company_locations.py` from the SEC submissions API
(`https://data.sec.gov/submissions/CIK##########.json`), which reports each filer's **current**
address rather than its address in the filing year. Companies that have relocated are therefore
assigned to their present CBSA.

The published measure was built from a point-in-time EDGAR snapshot. Table 4 rebuilt from this
file may therefore differ slightly from the published version. For an exact reproduction, use a
point-in-time archive instead:

```bash
python tools/fetch_public_inputs.py --extract-locations /path/to/edgar.db
```

The committed file is the SEC-sourced one, so that the package is reproducible by anyone without
access to a private archive.

Big 4 firm identification is not a data file — the `company_raw` → firm mapping lives in
`Analysis/shared/firm_mappings.py`, and the appendix table listing it is generated from that
same mapping by `Analysis/tables/firm_names.py`.

## 4. Derived panels — produced by the pipeline

Built by `06_build_interim.py` and `07_prepare_data.py` into `Analysis/Data/interim/` and
`Analysis/Data/processed/`. These are derivative works of licensed data and are likewise not
redistributed.

```
Analysis/Data/
├── raw/          licensed + public source data (see above)
├── interim/      revB4Aud.feather, revOtherFs.feather
├── processed/    revB4AudStata.feather, revB4AudExp.feather,
│                 revOtherFsStata.feather, revOtherFsExp.feather,
│                 sample_counts.json
└── public/       the committed inputs from section 3
```

`Analysis/pipeline/README.md` gives the full expected directory layout.

## Partial reproduction

Two published tables depend on inputs beyond the four main panels:

- **Table 5** (`destinationQualityPost.tex`) needs
  `raw/revelio/revelio_b4_users_all_positions.feather`, the complete post-Big 4 career histories.
- **Table 4** (`mechanismsTable.tex`) needs BoardEx, Audit Analytics, and
  `edgar/company_locations.csv` to build the audit-committee and keyword measures.

`07_prepare_data.py` **fails** if either set is missing rather than quietly writing a panel with
empty columns. If you want to proceed without them, pass `--allow-missing`: the affected columns
become missing, the script says which, and those tables will not reproduce.

## Optional object storage

The authors keep the raw and derived files in a private Cloudflare R2 bucket. If
`R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, and `R2_ENDPOINT` (or `R2_ACCOUNT_ID`) are set,
`ensure_data_file` will fetch missing files from it. This is for the authors' own use; the bucket
is not public, because it holds licensed data. Without those variables the code simply reads from
disk.
