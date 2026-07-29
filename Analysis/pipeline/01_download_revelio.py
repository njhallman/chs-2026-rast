"""
01_download_revelio.py — Revelio Labs position and education data.

Data source: WRDS Revelio Labs (revelio schema)
Authentication: WRDS username/password + Duo two-factor authentication

Raw Revelio data files in Analysis/Data/raw/revelio/:

  B4 AUDIT POSITIONS (revelioB4Aud.feather):
    Big 4 audit/auditor positions extracted from the Jan 2025 bulk download.
    Used by 06_build_interim.py to build the main B4 audit panel.

  B4 EDUCATION (revelioB4Edu.feather):
    Education records for B4 auditor user_ids, from the Jan 2025 batch
    education download (same vintage as revelioB4Aud.feather).

  PER-ROLE POSITION DATA (revelioPosUsr_role_{role}.feather, 54 files):
    Individual role files (Nov 2025) for all 52 FS roles. The audit and
    auditor files contain only non-B4 positions (B4 data is in
    revelioB4Aud.feather). Used by 06_build_interim.py for the Other FS
    panel and by benchmark scripts for IB, tax, and non-B4 audit figures.

  EDUCATION DATA (revelioEdu_role_combined.feather, 221 MB):
    Education records for all per-role file user_ids (Nov 2025).

  B4 ALL-POSITIONS DATA (revelio_b4_users_all_positions.feather):
    Complete career histories (all roles, not just audit) for Big 4 auditor
    user_ids. Used by outside_options.py for the destination quality analysis.

All data was queried from WRDS PostgreSQL via the `wrds` Python library,
which requires Duo two-factor authentication. The position data query
joins four Revelio tables:

    SELECT pos.*, pos_raw.*, user_raw.*, usr.*
    FROM revelio.individual_positions AS pos
    JOIN revelio.individual_positions_raw AS pos_raw
        ON pos.position_id = pos_raw.position_id
    JOIN revelio.individual_user_raw AS user_raw
        ON pos.user_id = user_raw.user_id
    JOIN revelio.individual_user AS usr
        ON pos.user_id = usr.user_id
    WHERE pos.role_k1500 = '{role}'
    AND usr.user_country IN ('United States')
    AND pos.country IN ('United States')

The education data query:

    SELECT usr_edu.*
    FROM revelio.individual_user_education AS usr_edu
    WHERE usr_edu.user_id IN ({user_ids})

NOTE: As of 2026, the Revelio schema on WRDS renamed role_k1500 to
role_k1500_v2. The --force re-download uses the updated column name.

All raw files are backed up to Cloudflare R2 via shared/r2.py.

Usage:
    python Analysis/pipeline/01_download_revelio.py          # verify files exist
    python Analysis/pipeline/01_download_revelio.py --force  # re-download from WRDS
"""
import sys, os, gc, argparse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import pandas as pd
from shared.paths import data_dir
from shared.r2 import ensure_data_file
from shared.wrds_conn import add_wrds_argument, connect as wrds_connect

RAW_DIR = os.path.join(data_dir, 'raw', 'revelio')


def verify():
    """Check that all required raw Revelio files are present."""
    print("=" * 60)
    print("  01_download_revelio.py — Revelio Labs data")
    print("=" * 60)

    # Check education file
    print("\nEducation data:")
    edu_path = os.path.join(RAW_DIR, 'revelioEdu_role_combined.feather')
    if os.path.exists(edu_path):
        size = os.path.getsize(edu_path) / 1024 / 1024
        print(f"  revelioEdu_role_combined.feather: {size:.0f} MB")
    else:
        print(f"  revelioEdu_role_combined.feather: MISSING — downloading from R2...")
        ensure_data_file('raw/revelio/revelioEdu_role_combined.feather')

    print("\nAll required files present.")


def download_fresh(wrds_username=None):
    """Re-download all Revelio data from WRDS (requires Duo 2FA)."""
    ROLES = [
        'actuarial', 'actuarial analyst', 'actuary', 'aml analyst',
        'audit', 'auditor', 'banking consultant', 'broker', 'brokerage',
        'business controller', 'capital markets', 'cfo', 'commercial finance',
        'commercial underwriter', 'controller', 'credit analyst',
        'equity analyst', 'equity research', 'equity research analyst',
        'finance controller', 'financial adviser', 'financial analyst fp a',
        'financial consultant', 'financial controller', 'financial officer',
        'financial planner', 'financial planning', 'financial planning analysis',
        'financial planning analyst', 'financial reporting',
        'financial reporting analyst', 'fraud analyst', 'fraud investigator',
        'investment analyst', 'investment banking', 'investment banking analyst',
        'investment consultant', 'investments', 'mergers acquisitions',
        'portfolio analyst', 'pricing analyst', 'project controller',
        'quantitative analyst', 'sap fico consultant', 'stock controller',
        'tax', 'tax accountant', 'tax analyst', 'tax consultant',
        'trade finance', 'trader', 'trading', 'underwriter', 'underwriting',
    ]

    QUERY = """
        SELECT pos.*, pos_raw.*, user_raw.*, usr.*
        FROM revelio.individual_positions AS pos
        JOIN revelio.individual_positions_raw AS pos_raw
            ON pos.position_id = pos_raw.position_id
        JOIN revelio.individual_user_raw AS user_raw
            ON pos.user_id = user_raw.user_id
        JOIN revelio.individual_user AS usr
            ON pos.user_id = usr.user_id
        WHERE pos.role_k1500_v2 = '{role}'
        AND usr.user_country IN ('United States')
        AND pos.country IN ('United States')
    """

    os.makedirs(RAW_DIR, exist_ok=True)

    conn = wrds_connect(wrds_username)

    for role in ROLES:
        path = os.path.join(RAW_DIR, f'revelioPosUsr_role_{role}.feather')
        print(f"  Downloading: {role}...", end='', flush=True)
        result = conn.raw_sql(QUERY.format(role=role))
        result = result.loc[:, ~result.columns.duplicated()]
        result.to_feather(path, compression='zstd')
        print(f" {len(result):,} rows")
        del result
        gc.collect()

    # Education data
    print("\nCollecting user_ids for education download...")
    all_ids = set()
    for f in os.listdir(RAW_DIR):
        if f.startswith('revelioPosUsr_role_') and f.endswith('.feather'):
            df = pd.read_feather(os.path.join(RAW_DIR, f), columns=['user_id'])
            all_ids.update(df['user_id'].unique())
            del df
    print(f"  Total users: {len(all_ids):,}")

    user_list = sorted(all_ids)
    batch_size = 10_000
    edu_dfs = []
    for i in range(0, len(user_list), batch_size):
        batch = user_list[i:i + batch_size]
        user_str = ', '.join(str(int(uid)) for uid in batch)
        result = conn.raw_sql(f"SELECT * FROM revelio.individual_user_education WHERE user_id IN ({user_str})")
        edu_dfs.append(result)
        del result
        gc.collect()

    edu = pd.concat(edu_dfs, ignore_index=True)
    edu.to_feather(os.path.join(RAW_DIR, 'revelioEdu_role_combined.feather'), compression='zstd')
    print(f"  Saved education data: {len(edu):,} rows")

    conn.close()
    print("\nDone.")


def main():
    parser = argparse.ArgumentParser(description='Revelio Labs data')
    parser.add_argument('--force', action='store_true',
                        help='Re-download from WRDS (requires Duo 2FA)')
    add_wrds_argument(parser)
    args = parser.parse_args()

    if args.force:
        download_fresh(args.wrds_username)
    else:
        verify()


if __name__ == '__main__':
    main()
