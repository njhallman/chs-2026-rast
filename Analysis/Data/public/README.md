# Committed public inputs

The only part of `Analysis/Data/` tracked in git. Everything here is either public-domain or a
small mapping hand-built by the authors, so it is safe to redistribute. Licensed data (Revelio
Labs, BoardEx, Ideagen Audit Analytics) and the panels derived from it are **not** here — see
[../../../DATA_AVAILABILITY.md](../../../DATA_AVAILABILITY.md).

Expected contents:

```
census/zip_cbsa.csv                   ZIP5 -> CBSA crosswalk (Census ZCTA + OMB delineation)
census/cbsa_revelio_metro.csv         CBSA -> Revelio metro_area, hand-reviewed
interim/at_revelio_firm_mapping.json  Accounting Today firm -> company_raw + inspection status
edgar/company_locations.csv           Registrant business city/state/ZIP by CIK (SEC submissions API)
proxy/proxy_dei_keywords_v2.csv       DEI/gender keyword counts per DEF 14A filing
```

`shared.r2.ensure_data_file` falls back to this directory, so a script asking for
`raw/census/zip_cbsa.csv` finds `public/census/zip_cbsa.csv` if the former is absent.

IPEDS Completions files are NOT here: ~900 MB, public domain, and fetched straight from
NCES by `Analysis/pipeline/05_download_ipeds.py` into `Analysis/Data/raw/ipeds/`.

To refresh from the authors' archive, or to see provenance for each file:

```bash
python tools/fetch_public_inputs.py --list
python tools/fetch_public_inputs.py
```
