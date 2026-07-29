# Committed public inputs

The only part of `Analysis/Data/` tracked in git. Everything here is either public-domain or a
small mapping hand-built by the authors, so it is safe to redistribute. Licensed data (Revelio
Labs, BoardEx, Ideagen Audit Analytics) and the panels derived from it are **not** here — see
[../../../DATA_AVAILABILITY.md](../../../DATA_AVAILABILITY.md).

Expected contents:

```
raw/census/zip_cbsa.csv                    ZIP5 -> CBSA crosswalk (Census ZCTA + OMB delineation)
raw/census/cbsa_revelio_metro.csv          CBSA -> Revelio metro_area, hand-reviewed
interim/at_revelio_firm_mapping.json       Accounting Today firm -> company_raw + inspection status
edgar/company_locations.csv                Registrant business city/state/ZIP by CIK (SEC submissions API)
geo/us-states.json                         US state boundaries for the retention-gap map (Census TIGER)
proxy statements/proxy_dei_keywords_v2.csv DEI/gender keyword counts per DEF 14A filing
```

**The path under `public/` must match the subpath the code requests, exactly.**
`ensure_data_file('raw/census/zip_cbsa.csv')` falls back to
`public/raw/census/zip_cbsa.csv` verbatim -- so a file stored under any other name
is invisible to the scripts. That failure is easy to miss if you hold
object-storage credentials, because the lookup then quietly falls through to the
archive and succeeds.

IPEDS Completions files are NOT here: ~900 MB, public domain, and fetched straight from
NCES by `Analysis/pipeline/05_download_ipeds.py` into `Analysis/Data/raw/ipeds/`.

To refresh from the authors' archive, or to see provenance for each file:

```bash
python tools/fetch_public_inputs.py --list
python tools/fetch_public_inputs.py
```
