#!/usr/bin/env python3
"""
Build Analysis/Data/public/edgar/company_locations.csv from SEC EDGAR.

`07_prepare_data.py` needs each Big 4 audit client's business address to assign
it to a CBSA, which is how the audit-committee and proxy-keyword mechanism
measures are aggregated (Table 4). This script fetches those addresses from the
SEC's public submissions API, so reproducing Table 4 requires no private archive.

    https://data.sec.gov/submissions/CIK##########.json  ->  addresses.business

The CIK list comes from proxy_dei_keywords_v2.csv, i.e. exactly the filers whose
proxy statements enter the keyword measure.

IMPORTANT CAVEAT: the submissions API reports each filer's *current* business
address, not its address as of the filing year. Companies that have relocated
will therefore be assigned to their present CBSA. The published measure was built
from a point-in-time EDGAR snapshot, so Table 4 rebuilt from this file may differ
slightly. For the exact as-published measure, use
`tools/fetch_public_inputs.py --extract-locations <edgar.db>` against a
point-in-time archive instead.

SEC fair access: a descriptive User-Agent identifying the requester is required,
and the rate limit is 10 requests/second. Responses are cached under
Analysis/Data/.cache/sec_submissions/ so reruns are cheap and re-fetching is
avoided.

Usage:
    python tools/build_company_locations.py
    python tools/build_company_locations.py --limit 50          # smoke test
    python tools/build_company_locations.py --user-agent "Name email@host"
"""
import argparse
import csv
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Analysis'))

from shared.paths import data_dir            # noqa: E402
from shared.r2 import ensure_data_file       # noqa: E402

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

# SEC requires a User-Agent that identifies the requester with a contact address.
# The corresponding author's address is already public in the paper itself.
DEFAULT_USER_AGENT = (
    "chs-2026-rast reproducibility package (nicholashallman@utexas.edu)"
)

RATE_LIMIT_PER_SEC = 8          # SEC allows 10/s; stay under it
MAX_RETRIES = 4

CACHE_DIR = os.path.join(data_dir, '.cache', 'sec_submissions')
OUT_PATH = os.path.join(data_dir, 'public', 'edgar', 'company_locations.csv')


def load_ciks(limit=None):
    """Distinct CIKs appearing in the proxy keyword file."""
    import pandas as pd

    path = ensure_data_file("proxy statements/proxy_dei_keywords_v2.csv")
    kw = pd.read_csv(path, usecols=['cik'])
    ciks = sorted(int(c) for c in kw['cik'].dropna().unique())
    if limit:
        ciks = ciks[:limit]
    return ciks


def _cache_path(cik):
    # Shard by the last two digits so no single directory holds 10k+ entries
    return os.path.join(CACHE_DIR, f"{cik % 100:02d}", f"CIK{cik:010d}.json.gz")


def fetch_submission(cik, user_agent, session_state):
    """Return the parsed submissions JSON for one CIK, or None if unavailable.

    Cached on disk. Honours the rate limit and retries on 429/5xx.
    """
    cache = _cache_path(cik)
    if os.path.exists(cache):
        try:
            with gzip.open(cache, 'rt', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            os.remove(cache)   # corrupt cache entry; refetch

    url = SUBMISSIONS_URL.format(cik=cik)
    req = urllib.request.Request(url, headers={
        'User-Agent': user_agent,
        'Accept-Encoding': 'gzip, deflate',
        'Host': 'data.sec.gov',
    })

    for attempt in range(MAX_RETRIES):
        # Rate limit across all requests, cache hits excluded
        elapsed = time.monotonic() - session_state['last_request']
        min_gap = 1.0 / RATE_LIMIT_PER_SEC
        if elapsed < min_gap:
            time.sleep(min_gap - elapsed)
        session_state['last_request'] = time.monotonic()

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                if resp.headers.get('Content-Encoding') == 'gzip':
                    raw = gzip.decompress(raw)
                data = json.loads(raw.decode('utf-8'))
            os.makedirs(os.path.dirname(cache), exist_ok=True)
            with gzip.open(cache, 'wt', encoding='utf-8') as f:
                json.dump(data, f)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None                      # filer has no submissions file
            if e.code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            print(f"    CIK {cik}: HTTP {e.code}")
            return None
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            print(f"    CIK {cik}: {type(e).__name__}: {e}")
            return None
    return None


def extract_address(data):
    """Pull (zip, state, city) out of a submissions payload.

    Falls back to the mailing address when no business address is recorded.
    Returns None when neither yields a usable ZIP and state.
    """
    if not data:
        return None
    addresses = data.get('addresses') or {}
    for kind in ('business', 'mailing'):
        addr = addresses.get(kind) or {}
        zipcode = (addr.get('zipCode') or '').strip()
        state = (addr.get('stateOrCountry') or '').strip()
        city = (addr.get('city') or '').strip()
        if zipcode and state:
            return zipcode, state, city
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--limit', type=int, default=None,
                        help='Only process the first N CIKs (smoke test)')
    parser.add_argument('--user-agent', default=DEFAULT_USER_AGENT,
                        help='User-Agent header; SEC requires a contact address')
    args = parser.parse_args()

    ciks = load_ciks(args.limit)
    print(f"Fetching business addresses for {len(ciks):,} CIKs from SEC")
    print(f"  User-Agent: {args.user_agent}")
    print(f"  Cache:      {CACHE_DIR}")
    print(f"  Rate limit: {RATE_LIMIT_PER_SEC}/s\n")

    session_state = {'last_request': 0.0}
    rows = []
    n_missing_file = 0
    n_missing_addr = 0
    t0 = time.time()

    for i, cik in enumerate(ciks, 1):
        data = fetch_submission(cik, args.user_agent, session_state)
        if data is None:
            n_missing_file += 1
        else:
            addr = extract_address(data)
            if addr is None:
                n_missing_addr += 1
            else:
                zipcode, state, city = addr
                rows.append({'cik': cik, 'zip': zipcode, 'state': state, 'city': city})

        if i % 500 == 0 or i == len(ciks):
            rate = i / max(time.time() - t0, 1e-9)
            eta = (len(ciks) - i) / max(rate, 1e-9) / 60
            print(f"  {i:>6,}/{len(ciks):,}  resolved {len(rows):,}  "
                  f"({rate:.1f}/s, ~{eta:.0f} min left)")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['cik', 'zip', 'state', 'city'])
        writer.writeheader()
        writer.writerows(rows)

    elapsed = (time.time() - t0) / 60
    print(f"\nWrote {OUT_PATH}")
    print(f"  {len(rows):,} of {len(ciks):,} CIKs resolved "
          f"({100*len(rows)/max(len(ciks),1):.1f}%)")
    print(f"  {n_missing_file:,} with no submissions file, "
          f"{n_missing_addr:,} with no usable address")
    print(f"  Elapsed: {elapsed:.1f} min")
    if rows:
        states = {r['state'] for r in rows}
        print(f"  {len(states)} distinct state/country codes")


if __name__ == '__main__':
    main()
