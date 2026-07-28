#!/usr/bin/env python3
"""
Populate Analysis/Data/public/ from the authors' archive.

This is a maintenance script for the authors, not something reproducers need to
run -- the files it fetches are committed to this repository. It exists to
document exactly where each committed public input came from, and to make the
set easy to refresh if an upstream source is revised.

Every file listed below is either public-domain (US Census, NCES IPEDS, SEC
EDGAR) or hand-curated by the authors. Nothing licensed from Revelio Labs,
BoardEx, or Audit Analytics is fetched here or committed to this repository.

Requires object-storage credentials in the environment (see Analysis/shared/r2.py).

Usage:
    python tools/fetch_public_inputs.py
    python tools/fetch_public_inputs.py --list
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Analysis'))

from shared.paths import data_dir            # noqa: E402
from shared.r2 import _download, _get_s3_client, _R2_BUCKET, remote_configured   # noqa: E402

# (archive subpath, destination under Analysis/Data/public/, provenance note)
PUBLIC_INPUTS = [
    (
        'raw/census/zip_cbsa.csv',
        'census/zip_cbsa.csv',
        'US Census ZCTA-to-county relationship file + OMB CBSA delineation. Public domain.',
    ),
    (
        'raw/census/cbsa_revelio_metro.csv',
        'census/cbsa_revelio_metro.csv',
        'Revelio metro_area -> CBSA code map, hand-reviewed by the authors.',
    ),
    (
        'interim/at_revelio_firm_mapping.json',
        'interim/at_revelio_firm_mapping.json',
        'Accounting Today Top 100 firm -> Revelio company_raw map with PCAOB '
        'annual-inspection status. Hand-curated by the authors.',
    ),
    (
        'proxy statements/proxy_dei_keywords_v2.csv',
        'proxy/proxy_dei_keywords_v2.csv',
        'DEI/gender keyword counts per DEF 14A filing, computed by '
        'Analysis/pipeline/08_fetch_proxy_keywords.py from public SEC filings.',
    ),
    (
        'edgar/company_locations.csv',
        'edgar/company_locations.csv',
        'Registrant business city/state/ZIP by CIK, latest snapshot per filer, '
        'from EDGAR company metadata. Public domain. See --extract-locations if '
        'this is not yet in the archive.',
    ),
]

# IPEDS completions CSVs (one per survey year) are downloaded by pipeline/05.
# Fetched as a prefix because the file set depends on the years covered.
# NCES IPEDS is public domain.
IPEDS_ARCHIVE_PREFIX = 'Data/raw/ipeds/'
IPEDS_DEST_PREFIX = 'ipeds/'


def public_dir():
    return os.path.join(data_dir, 'public')


def do_list():
    print(f"{len(PUBLIC_INPUTS)} public inputs (plus the IPEDS completions CSVs):\n")
    for src, dst, note in PUBLIC_INPUTS:
        present = os.path.exists(os.path.join(public_dir(), dst))
        print(f"  [{'x' if present else ' '}] {dst}")
        print(f"        from archive: {src}")
        print(f"        {note}\n")


def do_fetch():
    if not remote_configured():
        raise SystemExit(
            "Object-storage credentials are not configured. Set R2_ACCESS_KEY_ID, "
            "R2_SECRET_ACCESS_KEY, and R2_ENDPOINT (or R2_ACCOUNT_ID)."
        )

    for src, dst, _note in PUBLIC_INPUTS:
        dest_path = os.path.join(public_dir(), dst)
        if os.path.exists(dest_path):
            print(f"  SKIP (exists): {dst}")
            continue
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        try:
            size_mb = _download(f"Data/{src}", dest_path)
            print(f"  Fetched {dst} ({size_mb:.1f} MB)")
        except Exception as e:
            print(f"  FAILED {dst}: {e}")

    # IPEDS: fetch every object under the archive prefix
    s3 = _get_s3_client()
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=_R2_BUCKET, Prefix=IPEDS_ARCHIVE_PREFIX):
        for obj in page.get('Contents', []):
            name = obj['Key'][len(IPEDS_ARCHIVE_PREFIX):]
            if not name:
                continue
            dest_path = os.path.join(public_dir(), IPEDS_DEST_PREFIX, name)
            if os.path.exists(dest_path):
                print(f"  SKIP (exists): {IPEDS_DEST_PREFIX}{name}")
                continue
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            try:
                size_mb = _download(obj['Key'], dest_path)
                print(f"  Fetched {IPEDS_DEST_PREFIX}{name} ({size_mb:.1f} MB)")
            except Exception as e:
                print(f"  FAILED {IPEDS_DEST_PREFIX}{name}: {e}")

    print("\nDone. Review each file before committing, then:")
    print("  git add Analysis/Data/public && git commit")


def do_extract_locations(edgar_db):
    """Build edgar/company_locations.csv from a local EDGAR index database.

    Replaces the SQLite dependency that pipeline/07 used to carry: the query is
    run once here and its (public, small) result is committed.
    """
    import sqlite3
    import pandas as pd

    if not os.path.exists(edgar_db):
        raise SystemExit(f"No EDGAR index database at {edgar_db}")

    conn = sqlite3.connect(edgar_db)
    locs = pd.read_sql_query("""
        SELECT cik, business_zip AS zip, business_state AS state, business_city AS city
        FROM company_snapshots
        WHERE business_zip IS NOT NULL AND business_state IS NOT NULL
        GROUP BY cik HAVING snapshot_date = MAX(snapshot_date)
    """, conn)
    conn.close()

    dest = os.path.join(public_dir(), 'edgar', 'company_locations.csv')
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    locs.to_csv(dest, index=False)
    print(f"Wrote {dest}: {len(locs):,} filers")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--list', action='store_true',
                        help='Show the manifest and which files are present')
    parser.add_argument('--extract-locations', metavar='EDGAR_DB', default=None,
                        help='Build edgar/company_locations.csv from a local EDGAR '
                             'index database instead of fetching it')
    args = parser.parse_args()

    if args.list:
        do_list()
    elif args.extract_locations:
        do_extract_locations(args.extract_locations)
    else:
        do_fetch()


if __name__ == '__main__':
    main()
