"""
Extract DEI keyword measures from proxy statements for every Big 4 audit client.

Reads a local mirror of SEC DEF 14A filings (a SQLite index plus markdown files
on disk) rather than fetching from SEC.gov.

Reproducers do NOT need to run this: its output is committed to this repository
as Analysis/Data/public/proxy/proxy_dei_keywords_v2.csv. The script is included
to document how that file was produced.

Three phases:
  1. Query local-edgar DB for all DEF 14A filings with markdown available
  2. Match Audit Analytics Big 4 client-years to filings (merge_asof)
  3. Read markdown from disk, run keyword counts, save to CSV

Usage:
  python 08_fetch_proxy_keywords.py --edgar-archive /path/to/archive
  python 08_fetch_proxy_keywords.py --edgar-archive /path/to/archive --limit 50
"""
import sys
import os
import re
import sqlite3
import argparse
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import pandas as pd

from shared.paths import data_dir
from shared.r2 import upload_to_r2

# Import keyword patterns from existing module
from extract_dei_keywords import compute_measures

# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════
# Path to a local EDGAR archive: a directory holding db/edgar.db (an index of
# filings with a `relative_path` per filing) plus the filing markdown itself.
# Supplied with --edgar-archive or $EDGAR_ARCHIVE; there is no default. See
# DATA_AVAILABILITY.md -- reproducers do not need this, because this script's
# output (proxy_dei_keywords_v2.csv) is committed under Analysis/Data/public/.
EDGAR_ARCHIVE = None
EDGAR_DB = None

PROXY_DIR = os.path.join(data_dir, 'proxy statements')
OUTPUT_PATH = os.path.join(PROXY_DIR, 'proxy_dei_keywords_v2.csv')

AUDITOR_MAP = {
    'PricewaterhouseCoopers LLP': 'pwc',
    'Deloitte & Touche LLP': 'deloitte',
    'Ernst & Young LLP': 'ey',
    'KPMG LLP': 'kpmg',
}


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Query local-edgar for all DEF 14A filings with markdown
# ═══════════════════════════════════════════════════════════════════════════════
def _set_edgar_archive(path):
    """Resolve and validate the local EDGAR archive location."""
    global EDGAR_ARCHIVE, EDGAR_DB
    path = path or os.environ.get('EDGAR_ARCHIVE')
    if not path:
        raise SystemExit(
            "No EDGAR archive provided. Pass --edgar-archive PATH or set "
            "EDGAR_ARCHIVE.\n"
            "You almost certainly do not need to run this script: its output, "
            "proxy_dei_keywords_v2.csv, is committed under "
            "Analysis/Data/public/proxy/. This script documents how that file "
            "was produced from a local mirror of SEC DEF 14A filings."
        )
    EDGAR_ARCHIVE = Path(path)
    EDGAR_DB = EDGAR_ARCHIVE / "db" / "edgar.db"
    if not EDGAR_DB.exists():
        raise SystemExit(f"No EDGAR index database at {EDGAR_DB}")


def load_edgar_index():
    """Query local-edgar SQLite DB for all DEF 14A filings with markdown files."""
    print("Phase 1: Querying local-edgar database for DEF 14A filings...")

    conn = sqlite3.connect(str(EDGAR_DB))
    conn.row_factory = sqlite3.Row

    idx = pd.read_sql_query("""
        SELECT f.accession_number, f.cik, f.filing_date, lf.relative_path
        FROM filings f
        JOIN local_files lf ON f.accession_number = lf.accession_number
        WHERE f.form_type = 'DEF 14A'
          AND lf.format = 'md'
          AND lf.file_type = 'primary'
        ORDER BY f.filing_date
    """, conn)

    conn.close()

    idx['filing_date'] = pd.to_datetime(idx['filing_date'])
    idx['cik'] = idx['cik'].astype(int)

    print(f"  {len(idx):,} DEF 14A filings with markdown available")
    print(f"  {idx['cik'].nunique():,} unique CIKs")
    print(f"  Date range: {idx['filing_date'].min().date()} to {idx['filing_date'].max().date()}")

    return idx


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2: Match Audit Analytics Big 4 Clients → DEF 14A Filings
# ═══════════════════════════════════════════════════════════════════════════════
def match_aa_to_filings(edgar_idx):
    """Load AA Big 4 client-years and match to next DEF 14A within 365 days."""
    print("\nPhase 2: Matching Audit Analytics Big 4 clients to DEF 14A filings...")

    aa_path = os.path.join(data_dir, 'raw', 'audit_analytics',
                           'audit_audit_comp_feed34_revised_audit_opinions.csv')
    aa = pd.read_csv(
        aa_path,
        usecols=['auditor_name', 'company_fkey', 'fiscal_year_of_op', 'fiscal_year_end_op'],
        low_memory=False,
    )

    # Filter to Big 4
    aa_b4 = aa[aa['auditor_name'].isin(AUDITOR_MAP)].copy()
    aa_b4['aud_firm'] = aa_b4['auditor_name'].map(AUDITOR_MAP)
    aa_b4['cik'] = pd.to_numeric(aa_b4['company_fkey'], errors='coerce')
    aa_b4['fiscal_year_end'] = pd.to_datetime(aa_b4['fiscal_year_end_op'], errors='coerce')
    aa_b4['fyear'] = aa_b4['fiscal_year_of_op']
    aa_b4 = aa_b4.dropna(subset=['cik', 'fiscal_year_end', 'fyear'])
    aa_b4['cik'] = aa_b4['cik'].astype(int)
    aa_b4['fyear'] = aa_b4['fyear'].astype(int)
    aa_b4 = aa_b4[['cik', 'fyear', 'fiscal_year_end', 'aud_firm']].copy()
    aa_b4 = aa_b4.drop_duplicates(subset=['cik', 'fyear'], keep='last')

    print(f"  AA Big 4 client-years: {len(aa_b4):,} ({aa_b4['cik'].nunique():,} unique CIKs)")

    # Both sides must be sorted by the merge key
    aa_b4 = aa_b4.sort_values('fiscal_year_end')
    idx = edgar_idx.sort_values('filing_date')

    # merge_asof: for each AA row, find next DEF 14A filing within 365 days
    matched = pd.merge_asof(
        aa_b4, idx[['cik', 'filing_date', 'accession_number', 'relative_path']],
        left_on='fiscal_year_end', right_on='filing_date',
        by='cik',
        direction='forward',
        tolerance=pd.Timedelta('365D'),
    )

    n_matched = matched['accession_number'].notna().sum()
    n_total = len(matched)
    print(f"  Matched: {n_matched:,} of {n_total:,} ({100*n_matched/n_total:.1f}%)")

    # Drop unmatched, deduplicate by accession_number (keep first occurrence)
    matched = matched[matched['accession_number'].notna()].copy()
    matched = matched.drop_duplicates(subset=['accession_number'], keep='first')
    print(f"  After dedup: {matched['accession_number'].nunique():,} unique proxies to process")

    return matched


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3: Read markdown from disk, extract keywords
# ═══════════════════════════════════════════════════════════════════════════════
def extract_keywords(matched_df, limit=None):
    """Read proxy markdown files from local-edgar archive and extract keyword measures."""
    print("\nPhase 3: Extracting keywords from proxy statements...")

    work = matched_df.copy()
    if limit:
        work = work.head(limit)
    total = len(work)
    print(f"  Processing {total:,} proxy statements...")

    results = []
    n_ok = 0
    n_err = 0

    for i, (_, row) in enumerate(work.iterrows()):
        acc = row['accession_number']
        filepath = EDGAR_ARCHIVE / row['relative_path']

        rec = {
            'accession_number': acc,
            'cik': int(row['cik']),
            'fyear': int(row['fyear']),
            'fiscal_year_end': str(row['fiscal_year_end'].date()),
            'aud_firm': row['aud_firm'],
            'filing_date': str(row['filing_date'].date()) if pd.notna(row['filing_date']) else '',
        }

        try:
            text = filepath.read_text(errors='replace')
            if len(text.strip()) < 100:
                rec['status'] = 'empty'
                rec.update({k: 0 for k in ['dei_word_count', 'gender_word_count',
                           'workforce_dei_count', 'dei_char_length',
                           'dei_section_count', 'total_doc_length']})
                n_err += 1
            else:
                measures = compute_measures(text)
                rec.update(measures)
                rec['status'] = 'ok'
                n_ok += 1
        except FileNotFoundError:
            rec['status'] = 'file_not_found'
            rec.update({k: 0 for k in ['dei_word_count', 'gender_word_count',
                       'workforce_dei_count', 'dei_char_length',
                       'dei_section_count', 'total_doc_length']})
            n_err += 1
        except Exception as e:
            rec['status'] = f'error: {str(e)[:200]}'
            rec.update({k: 0 for k in ['dei_word_count', 'gender_word_count',
                       'workforce_dei_count', 'dei_char_length',
                       'dei_section_count', 'total_doc_length']})
            n_err += 1

        results.append(rec)

        if (i + 1) % 5000 == 0 or (i + 1) == total:
            print(f"  [{i+1:,}/{total:,}] ok={n_ok:,} err={n_err:,}")

    print(f"\n  Done: {n_ok:,} ok, {n_err:,} errors")
    return pd.DataFrame(results)


def save_and_upload(df):
    """Save results to CSV and upload to R2."""
    os.makedirs(PROXY_DIR, exist_ok=True)

    col_order = [
        'accession_number', 'cik', 'fyear', 'fiscal_year_end', 'aud_firm',
        'filing_date', 'status',
        'dei_word_count', 'gender_word_count', 'workforce_dei_count',
        'dei_char_length', 'dei_section_count', 'total_doc_length',
    ]
    df = df[[c for c in col_order if c in df.columns]]
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved: {OUTPUT_PATH} ({len(df):,} rows)")

    # Summary stats
    ok = df[df['status'] == 'ok']
    print(f"  Status ok: {len(ok):,}")
    print(f"  Year range: {ok['fyear'].min()} – {ok['fyear'].max()}")
    for col in ['dei_word_count', 'gender_word_count', 'workforce_dei_count', 'total_doc_length']:
        print(f"  Mean {col}: {ok[col].mean():.1f}")

    upload_to_r2('proxy statements/proxy_dei_keywords_v2.csv')
    print("Uploaded to R2.")


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description='Extract DEI keywords from local-edgar proxy statements')
    parser.add_argument('--limit', type=int, default=None,
                        help='Process only first N proxies (for testing)')
    parser.add_argument('--skip-extract', action='store_true',
                        help='Skip Phase 3 (just build index and match)')
    parser.add_argument('--edgar-archive', default=None,
                        help='Path to the local EDGAR archive (default: $EDGAR_ARCHIVE)')
    args = parser.parse_args()

    _set_edgar_archive(args.edgar_archive)
    edgar_idx = load_edgar_index()
    matched = match_aa_to_filings(edgar_idx)

    if not args.skip_extract:
        df = extract_keywords(matched, limit=args.limit)
        save_and_upload(df)
    else:
        print("\nSkipping Phase 3 (--skip-extract). Matched DataFrame:")
        print(matched[['cik', 'fyear', 'aud_firm', 'accession_number']].head(20).to_string())


if __name__ == '__main__':
    main()
