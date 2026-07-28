"""
06_build_interim.py — Build interim datasets from raw Revelio data.

Converts raw Revelio position/education files into two analysis-ready
interim datasets.

Data sources:
    - B4 Audit: revelioB4Aud.feather + revelioB4Edu.feather (pre-extracted)
    - Other FS: Per-role files (revelioPosUsr_role_*.feather, original 52 roles
      from the Nov 2025 WRDS download) + revelioEdu_role_combined.feather

Outputs (in Analysis/Data/interim/):
    - revB4Aud.feather    Big 4 auditor positions (cleaned, ranked, education merged)
    - revOtherFs.feather  Other financial services positions (education merged)

Usage:
    python Analysis/pipeline/06_build_interim.py
"""
import sys, os, gc
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import numpy as np
import pandas as pd
from glob import glob

from shared.paths import data_dir
from shared.r2 import ensure_data_file, upload_to_r2
from shared.benchmark_utils import school_mapping

RAW_DIR = os.path.join(data_dir, 'raw', 'revelio')
INTERIM_DIR = os.path.join(data_dir, 'interim')
os.makedirs(INTERIM_DIR, exist_ok=True)

# Big 4 firm identification lives in shared/firm_mappings.py so that the
# appendix table (Analysis/tables/firm_names.py) is generated from the same
# mapping the sample construction applies.
from shared.firm_mappings import AUDIT_FIRM_MAPPING, AUDIT_FIRM_KEY

# Columns to drop before saving (reduce file size)
DROP_COLUMNS = [
    'region', 'remote_suitability', 'weight', 'start_salary', 'end_salary',
    'seniority', 'salary', 'rcid', 'onet_code', 'total_compensation',
    'additional_compensation', 'description', 'profile_title', 'profile_summary',
    'fullname', 'f_prob', 'm_prob', 'white_prob', 'black_prob', 'api_prob',
    'hispanic_prob', 'native_prob', 'multiple_prob', 'prestige', 'numconnections',
]


# ── Step 1: Load position data ───────────────────────────────────────────────

CONSULTING_ROLES = {'consulting', 'consulting analyst', 'strategy consultant', 'business consultant'}

def load_all_positions():
    """Load all Revelio position data from per-role files for the Other FS panel.

    Excludes consulting roles that were added after the original Nov 2025 download.
    """
    print("Loading per-role position files...")
    pattern = os.path.join(RAW_DIR, 'revelioPosUsr_role_*.feather')
    files = sorted(glob(pattern))
    if not files:
        raise FileNotFoundError(f"No role files found at {pattern}")

    dfs = []
    for f in files:
        role = os.path.basename(f).replace('revelioPosUsr_role_', '').replace('.feather', '')
        if role in CONSULTING_ROLES:
            print(f"  {role}: SKIPPED (consulting role)")
            continue
        df = pd.read_feather(f)
        if 'role_k1500_v2' in df.columns and 'role_k1500' not in df.columns:
            df = df.rename(columns={'role_k1500_v2': 'role_k1500'})
        dfs.append(df)
        print(f"  {role}: {len(df):,} rows")

    combined = pd.concat(dfs, ignore_index=True)
    del dfs
    gc.collect()

    # Normalize dtypes from mixed Arrow/pandas types across download batches
    for col in ['startdate', 'enddate', 'updated_dt']:
        if col in combined.columns:
            combined[col] = pd.to_datetime(combined[col], errors='coerce')
    for col in combined.select_dtypes(include=['string']).columns:
        combined[col] = combined[col].astype('object')
    for col in combined.columns:
        if str(combined[col].dtype) == 'Float64':
            combined[col] = combined[col].astype('float64')
        elif str(combined[col].dtype) == 'Int64':
            combined[col] = combined[col].astype('float64')

    print(f"  Total: {len(combined):,} rows, {combined['user_id'].nunique():,} users")
    return combined


# ── Step 2: Load and process education data ──────────────────────────────────

def load_education(user_ids=None, source='combined'):
    """Load education data, keep highest degree per user, standardize universities.

    Args:
        user_ids: optional set of user_ids to filter to after loading
        source: 'b4' to load from revelioB4Edu.feather (Jan 2025, matches B4 data),
                'combined' to load from revelioEdu_role_combined.feather (Nov 2025)
    """
    print(f"\nLoading education data (source={source})...")

    if source == 'b4':
        path = os.path.join(RAW_DIR, 'revelioB4Edu.feather')
        edu = pd.read_feather(path)
        print(f"  Loaded revelioB4Edu.feather: {len(edu):,} rows")
    else:
        combined_path = os.path.join(RAW_DIR, 'revelioEdu_role_combined.feather')
        edu = pd.read_feather(combined_path)
        print(f"  Loaded revelioEdu_role_combined.feather: {len(edu):,} rows")

    if user_ids is not None:
        edu = edu[edu['user_id'].isin(user_ids)]

    # Filter to recognized degree types
    edu = edu[edu['degree'].isin(['Bachelor', 'Master', 'MBA', 'Doctor'])].copy()

    # Degree hierarchy (higher = better)
    degree_rank = {'Bachelor': 1, 'Master': 2, 'MBA': 3, 'Doctor': 4}
    edu['degree_rank'] = edu['degree'].map(degree_rank)

    # Parse dates
    edu['enddate'] = pd.to_datetime(edu['enddate'], errors='coerce')
    edu['enddate'] = edu['enddate'].fillna(pd.Timestamp('2025-10-01'))

    # Keep highest degree per user (by rank, then most recent enddate)
    edu = (edu.sort_values(['user_id', 'degree_rank', 'enddate'], ascending=[True, True, True])
              .groupby('user_id').tail(1))

    # Standardize university names
    edu['university_name'] = edu['university_name'].apply(
        lambda x: school_mapping.get(x, 'other') if pd.notna(x) else 'other'
    )

    edu = edu[['user_id', 'university_name', 'degree']].copy()
    print(f"  After filtering: {len(edu):,} users with recognized degrees")
    return edu


# ── Step 3: Build B4 Audit interim dataset ───────────────────────────────────

def build_b4_audit(edu):
    """Build the Big 4 auditor interim dataset with screens and rank assignment.

    Loads revelioB4Aud.feather (Big 4 audit/auditor positions extracted from
    the bulk partition files), applies data screens (bad dates, inter-firm
    movers, missing education, interns), assigns ranks from title_raw, and
    flags implausible rank progressions.
    """
    print("\n" + "─" * 60)
    print("Building revB4Aud (Big 4 auditor positions)")
    print("─" * 60)

    # Load pre-extracted B4 audit/auditor positions
    b4_path = os.path.join(RAW_DIR, 'revelioB4Aud.feather')
    b4 = pd.read_feather(b4_path)
    b4['aud_firm'] = b4['company_raw'].map(AUDIT_FIRM_MAPPING)
    b4['auditor_key'] = b4['aud_firm'].map(AUDIT_FIRM_KEY)
    # Track screening counts for sample design table
    _sc = {}
    _sc['initial_users'] = b4['user_id'].nunique()
    _sc['initial_positions'] = len(b4)
    print(f"  Loaded: {_sc['initial_users']:,} auditors, {_sc['initial_positions']:,} positions")

    # Drop unnecessary columns
    b4.drop(columns=[c for c in DROP_COLUMNS if c in b4.columns], inplace=True, errors='ignore')

    # Merge education data
    b4 = b4.merge(edu, on='user_id', how='left')

    # Parse dates
    b4['enddate'] = pd.to_datetime(b4['enddate'], errors='coerce')
    b4['enddate'] = b4['enddate'].fillna(pd.Timestamp('2025-10-01'))
    b4['startdate'] = pd.to_datetime(b4['startdate'], errors='coerce')

    # ── Data screens ──

    # Screen 1: Drop invalid dates
    n_before_u, n_before_p = b4['user_id'].nunique(), len(b4)
    b4 = b4[b4['startdate'].notna() & (b4['startdate'] <= b4['enddate'])]
    _sc['date_drop_users'] = n_before_u - b4['user_id'].nunique()
    _sc['date_drop_positions'] = n_before_p - len(b4)
    print(f"  After date screen: {b4['user_id'].nunique():,} auditors (-{_sc['date_drop_users']:,})")

    # Screen 2: Drop users with missing education
    n_before_u, n_before_p = b4['user_id'].nunique(), len(b4)
    b4 = b4[b4['highest_degree'].notna()]
    _sc['edu_drop_users'] = n_before_u - b4['user_id'].nunique()
    _sc['edu_drop_positions'] = n_before_p - len(b4)
    print(f"  After education screen: {b4['user_id'].nunique():,} auditors (-{_sc['edu_drop_users']:,})")

    # ── Compute tenure dates ──
    b4['user_firm_enddate'] = b4.groupby('user_id')['enddate'].transform('max')
    b4['user_firm_startdate'] = b4.groupby('user_id')['startdate'].transform('min')

    # ── Rank assignment from title_raw ──
    assign_ranks(b4)

    # Screen 4: Drop interns
    n_before_u, n_before_p = b4['user_id'].nunique(), len(b4)
    intern_only = b4.groupby('user_id')['rank'].apply(lambda x: (x == 'intern').all())
    b4 = b4[~b4['user_id'].isin(intern_only[intern_only].index)]
    b4 = b4[b4['rank'] != 'intern']
    _sc['intern_drop_users'] = n_before_u - b4['user_id'].nunique()
    _sc['intern_drop_positions'] = n_before_p - len(b4)
    print(f"  After intern screen: {b4['user_id'].nunique():,} auditors (-{_sc['intern_drop_users']:,})")

    # ── Bad rank flag ──
    flag_bad_ranks(b4)

    _sc['final_users'] = b4['user_id'].nunique()
    _sc['final_positions'] = len(b4)
    print(f"  Final: {_sc['final_users']:,} auditors, {_sc['final_positions']:,} positions")
    print(f"  Rank distribution:\n{b4['rank'].value_counts().to_string()}")

    # Save screening counts for sample design table
    import json
    sc_path = os.path.join(INTERIM_DIR, 'interim_screening_counts.json')
    with open(sc_path, 'w') as f:
        json.dump(_sc, f, indent=2)
    print(f"  Saved screening counts to {sc_path}")

    return b4


def assign_ranks(df):
    """Assign canonical ranks from title_raw using regex patterns."""
    df['rank'] = np.nan

    df.loc[df['title_raw'].str.contains('intern', case=False, na=False), 'rank'] = 'intern'

    df.loc[df['title_raw'].str.contains('associate|assoc|assistant|staff', case=False, na=False), 'rank'] = 'staff'

    # Generic auditor titles with short tenure -> staff
    df['user_firm_enddate'] = pd.to_datetime(df['user_firm_enddate'])
    df['user_firm_startdate'] = pd.to_datetime(df['user_firm_startdate'])
    generic_titles = ['auditor', 'audit', 'assurance', 'external auditor', 'external audit',
                      'audit & assurance', 'audit assurance', 'audit and assurance']
    df.loc[
        (df['title_raw'].str.lower().isin(generic_titles)) &
        (df['user_firm_enddate'] - df['user_firm_startdate'] < pd.Timedelta(days=3*365)),
        'rank'
    ] = 'staff'

    df.loc[
        (df['title_raw'].str.contains('sr|senior|in charge|in-charge', case=False, na=False)) &
        (~df['title_raw'].str.contains('mgr|manager|partner|assistant|staff', case=False, na=False)),
        'rank'
    ] = 'senior'

    df.loc[
        (df['title_raw'].str.contains('mgr|manager', case=False, na=False)) &
        (~df['title_raw'].str.contains('sr|senior|partner', case=False, na=False)),
        'rank'
    ] = 'manager'

    df.loc[
        (df['title_raw'].str.contains('sr|senior', case=False, na=False)) &
        (df['title_raw'].str.contains('mgr|manager', case=False, na=False)) &
        (~df['title_raw'].str.contains('partner|director', case=False, na=False)),
        'rank'
    ] = 'senior manager'

    df.loc[
        (df['title_raw'].str.contains('director', case=False, na=False)) &
        (~df['title_raw'].str.contains('partner', case=False, na=False)),
        'rank'
    ] = 'director'

    df.loc[
        (df['title_raw'].str.contains('partner|owner|principal', case=False, na=False)) &
        (~df['title_raw'].str.contains('retired', case=False, na=False)),
        'rank'
    ] = 'partner'

    rank_num = {'intern': 0, 'staff': 1, 'senior': 2, 'manager': 3,
                'senior manager': 4, 'director': 5, 'partner': 6}
    df['rank_num'] = df['rank'].map(rank_num)


def flag_bad_ranks(df):
    """Flag users with implausible rank progressions."""
    df['bad_rank'] = False

    users_by_rank = {}
    for rank in ['staff', 'senior', 'manager', 'senior manager', 'director', 'partner']:
        users_by_rank[rank] = set(df[df['rank'] == rank]['user_id'].unique())

    bad = users_by_rank['senior'] - users_by_rank['staff']
    df.loc[df['user_id'].isin(bad), 'bad_rank'] = True

    bad = users_by_rank['manager'] - (users_by_rank['senior'] | users_by_rank['staff'])
    df.loc[df['user_id'].isin(bad), 'bad_rank'] = True

    bad = users_by_rank['senior manager'] - (users_by_rank['manager'] | users_by_rank['senior'] | users_by_rank['staff'])
    df.loc[df['user_id'].isin(bad), 'bad_rank'] = True

    lower = users_by_rank['senior manager'] | users_by_rank['manager'] | users_by_rank['senior'] | users_by_rank['staff']
    bad = users_by_rank['director'] - lower
    df.loc[df['user_id'].isin(bad), 'bad_rank'] = True

    bad = users_by_rank['partner'] - lower
    df.loc[df['user_id'].isin(bad), 'bad_rank'] = True

    n_bad = df[df['bad_rank']]['user_id'].nunique()
    print(f"  Bad rank users: {n_bad:,}")


# ── Step 4: Build Other FS interim dataset ───────────────────────────────────

def build_other_fs(revFs, edu):
    """Build the Other Financial Services interim dataset."""
    print("\n" + "─" * 60)
    print("Building revOtherFs (non-B4 audit positions)")
    print("─" * 60)

    # Everything except Big 4 audit positions
    ofs = revFs[(revFs['auditor_key'].isna()) &
                (~revFs['role_k1500'].isin(['audit', 'auditor']))].copy()
    print(f"  Initial: {ofs['user_id'].nunique():,} workers, {len(ofs):,} positions")

    # Drop unnecessary columns
    ofs.drop(columns=[c for c in DROP_COLUMNS if c in ofs.columns], inplace=True, errors='ignore')

    # Merge education data
    ofs = ofs.merge(edu, on='user_id', how='left')

    print(f"  Final: {ofs['user_id'].nunique():,} workers, {len(ofs):,} positions")
    return ofs


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  06_build_interim.py — Build interim datasets from raw Revelio")
    print("=" * 60)

    # Build B4 Audit dataset (from revelioB4Aud.feather + B4-vintage education)
    b4_edu = load_education(source='b4')
    b4 = build_b4_audit(b4_edu)
    del b4_edu
    b4_path = os.path.join(INTERIM_DIR, 'revB4Aud.feather')
    b4.to_feather(b4_path)
    print(f"\n  Saved: {b4_path} ({os.path.getsize(b4_path) / 1024 / 1024:.1f} MB)")
    upload_to_r2('interim/revB4Aud.feather')
    del b4
    gc.collect()

    # Build Other FS dataset (from per-role files)
    revFs = load_all_positions()
    revFs['aud_firm'] = revFs['company_raw'].map(AUDIT_FIRM_MAPPING)
    revFs['auditor_key'] = revFs['aud_firm'].map(AUDIT_FIRM_KEY)
    ofs_edu = load_education(source='combined')
    ofs = build_other_fs(revFs, ofs_edu)
    del ofs_edu
    ofs_path = os.path.join(INTERIM_DIR, 'revOtherFs.feather')
    ofs.to_feather(ofs_path)
    print(f"\n  Saved: {ofs_path} ({os.path.getsize(ofs_path) / 1024 / 1024:.1f} MB)")
    upload_to_r2('interim/revOtherFs.feather')
    del ofs, revFs
    gc.collect()

    print("\n" + "=" * 60)
    print("  Interim datasets built successfully.")
    print("=" * 60)


if __name__ == '__main__':
    main()
