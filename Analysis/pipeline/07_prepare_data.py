"""
Prepare analysis-ready datasets from interim Revelio data.

Converts interim/revB4Aud.feather and interim/revOtherFs.feather into
processed/revB4AudStata.feather, processed/revB4AudExp.feather,
processed/revOtherFsStata.feather, processed/revOtherFsExp.feather,
and processed/sample_counts.json.

By default this script FAILS if an input needed for a published table is
missing, rather than silently producing a panel with empty columns. Pass
--allow-missing to downgrade those failures to warnings (useful for partial
replications); the affected tables will not reproduce.

Usage:
    python3 Analysis/pipeline/07_prepare_data.py
    python3 Analysis/pipeline/07_prepare_data.py --allow-missing
"""

import argparse
import gc
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from shared.paths import data_dir
from shared.r2 import ensure_data_file, upload_to_r2


def prepare_audit_data(allow_missing=False):
    """Process interim audit data into analysis-ready panel.

    Args:
        allow_missing: if True, inputs required only for the destination-quality
            and mechanism variables may be absent; those columns are set to NaN
            and a warning is printed instead of raising.

    Returns (revB4AudStata, revB4AudExp, sample_counts_dict).
    """
    print("=" * 60)
    print("Working with the audit dataset")
    print("=" * 60)

    revB4Aud = pd.read_feather(ensure_data_file("interim/revB4Aud.feather"))

    ua1 = revB4Aud['user_id'].nunique()
    uap1 = len(revB4Aud)
    print(f"Unique auditors: {ua1:,}")
    print(f"Unique audit positions: {uap1:,}")

    # ── Step 6: Drop positions with missing or incorrect dates ────────────
    revB4Aud = revB4Aud[revB4Aud['startdate'] <= revB4Aud['enddate']]
    revB4Aud = revB4Aud[~revB4Aud['startdate'].isnull()]

    uad1 = abs(ua1 - revB4Aud['user_id'].nunique())
    uapd1 = abs(uap1 - len(revB4Aud))
    print(f"Less {uad1:,} auditors with bad dates")
    print(f"Less {uapd1:,} positions with bad dates")

    # ── Step 7: Drop users missing educational data ────────────────────────
    revB4Aud = revB4Aud[revB4Aud['highest_degree'].notnull()]

    uad2 = abs(ua1 - uad1 - revB4Aud['user_id'].nunique())
    uapd2 = abs(uap1 - uapd1 - len(revB4Aud))
    print(f"Less {uad2:,} auditors without educational data")
    print(f"Less {uapd2:,} positions without educational data")

    # ── Step 9: Tenure variables ──────────────────────────────────────────
    revB4Aud['user_firm_enddate'] = revB4Aud.groupby('user_id')['enddate'].transform('max')
    revB4Aud['user_firm_startdate'] = revB4Aud.groupby('user_id')['startdate'].transform('min')

    # ── Step 10: Rank standardization ─────────────────────────────────────
    revB4Aud['user_firm_enddate'] = pd.to_datetime(revB4Aud['user_firm_enddate'])
    revB4Aud['user_firm_startdate'] = pd.to_datetime(revB4Aud['user_firm_startdate'])

    # Intern
    revB4Aud.loc[
        revB4Aud['title_raw'].str.contains('intern', case=False, na=False),
        'rank'
    ] = 'intern'

    # Staff
    revB4Aud.loc[
        revB4Aud['title_raw'].str.contains('associate|assoc|assistant|staff', case=False, na=False),
        'rank'
    ] = 'staff'

    revB4Aud.loc[
        (revB4Aud['title_raw'].str.lower().isin([
            'auditor', 'audit', 'assurance', 'external auditor', 'external audit',
            'audit & assurance', 'audit assurance', 'audit and assurance'
        ])) &
        (revB4Aud['user_firm_enddate'] - revB4Aud['user_firm_startdate'] < pd.Timedelta(days=3*365)),
        'rank'
    ] = 'staff'

    # Senior
    revB4Aud.loc[
        (revB4Aud['title_raw'].str.contains('sr|senior|in charge|in-charge', case=False, na=False)) &
        (~revB4Aud['title_raw'].str.contains('mgr|manager|partner|assistant|staff', case=False, na=False)),
        'rank'
    ] = 'senior'

    # Manager
    revB4Aud.loc[
        (revB4Aud['title_raw'].str.contains('mgr|manager', case=False, na=False)) &
        (~revB4Aud['title_raw'].str.contains('sr|senior|partner', case=False, na=False)),
        'rank'
    ] = 'manager'

    # Senior manager
    revB4Aud.loc[
        (revB4Aud['title_raw'].str.contains('sr|senior', case=False, na=False)) &
        (revB4Aud['title_raw'].str.contains('mgr|manager', case=False, na=False)) &
        (~revB4Aud['title_raw'].str.contains('partner|director', case=False, na=False)),
        'rank'
    ] = 'senior manager'

    # Director
    revB4Aud.loc[
        (revB4Aud['title_raw'].str.contains('director', case=False, na=False)) &
        (~revB4Aud['title_raw'].str.contains('partner', case=False, na=False)),
        'rank'
    ] = 'director'

    # Partner
    revB4Aud.loc[
        (revB4Aud['title_raw'].str.contains('partner|owner|principal', case=False, na=False)) &
        (~revB4Aud['title_raw'].str.contains('retired', case=False, na=False)),
        'rank'
    ] = 'partner'

    rankMapping = {
        'intern': 0, 'staff': 1, 'senior': 2, 'manager': 3,
        'senior manager': 4, 'director': 5, 'partner': 6
    }
    revB4Aud['rank_num'] = revB4Aud['rank'].map(rankMapping)

    # ── Step 11: Drop interns ─────────────────────────────────────────────
    revB4Aud = revB4Aud[revB4Aud['rank'] != 'intern']

    uad3 = abs(ua1 - uad1 - uad2 - revB4Aud['user_id'].nunique())
    uapd3 = abs(uap1 - uapd1 - uapd2 - len(revB4Aud))
    print(f"Less {uad3:,} auditors who only ever work as interns")
    print(f"Less {uapd3:,} intern positions")

    # ── Step 12: Bad rank detection ───────────────────────────────────────
    revB4Aud['bad_rank'] = False

    user_ids_with_partner = revB4Aud[revB4Aud['rank'] == 'partner']['user_id'].unique()
    user_ids_with_director = revB4Aud[revB4Aud['rank'] == 'director']['user_id'].unique()
    user_ids_with_senior_manager = revB4Aud[revB4Aud['rank'] == 'senior manager']['user_id'].unique()
    user_ids_with_manager = revB4Aud[revB4Aud['rank'] == 'manager']['user_id'].unique()
    user_ids_with_senior = revB4Aud[revB4Aud['rank'] == 'senior']['user_id'].unique()
    user_ids_with_staff = revB4Aud[revB4Aud['rank'] == 'staff']['user_id'].unique()

    revB4Aud['bad_rank'] = revB4Aud['user_id'].isin(
        np.setdiff1d(user_ids_with_senior, user_ids_with_staff)
    )

    revB4Aud.loc[
        revB4Aud['user_id'].isin(np.setdiff1d(
            user_ids_with_manager,
            np.concatenate((user_ids_with_senior, user_ids_with_staff))
        )), 'bad_rank'
    ] = True

    revB4Aud.loc[
        revB4Aud['user_id'].isin(np.setdiff1d(
            user_ids_with_senior_manager,
            np.concatenate((user_ids_with_manager, user_ids_with_senior, user_ids_with_staff))
        )), 'bad_rank'
    ] = True

    revB4Aud.loc[
        revB4Aud['user_id'].isin(np.setdiff1d(
            user_ids_with_director,
            np.concatenate((user_ids_with_senior_manager, user_ids_with_manager,
                            user_ids_with_senior, user_ids_with_staff))
        )), 'bad_rank'
    ] = True

    revB4Aud.loc[
        revB4Aud['user_id'].isin(np.setdiff1d(
            user_ids_with_partner,
            np.concatenate((user_ids_with_director, user_ids_with_senior_manager,
                            user_ids_with_manager, user_ids_with_senior, user_ids_with_staff))
        )), 'bad_rank'
    ] = True

    revB4Aud.loc[revB4Aud['rank'].isnull(), 'bad_rank'] = True
    revB4Aud['bad_rank'] = revB4Aud.groupby('user_id')['bad_rank'].transform('any')

    # ── Step 13: Explode to user-year panel ───────────────────────────────
    revB4Aud['startdate'] = pd.to_datetime(revB4Aud['startdate'])
    revB4Aud['enddate'] = pd.to_datetime(revB4Aud['enddate'])

    revB4Aud['position_year'] = revB4Aud.apply(
        lambda row: list(range(row['startdate'].year, row['enddate'].year + 1)), axis=1
    )

    revB4AudExp = (
        revB4Aud[[
            'user_id', 'position_id', 'state', 'metro_area', 'user_firm_startdate',
            'user_firm_enddate', 'position_year', 'auditor_key', 'aud_firm', 'rank',
            'rank_num', 'bad_rank', 'sex_predicted', 'ethnicity_predicted',
            'profile_linkedin_url', 'university_name', 'degree'
        ]].explode('position_year', ignore_index=True)
    )

    revB4AudExp = revB4AudExp.sort_values(['user_id', 'position_year', 'rank_num'])
    revB4AudExp = revB4AudExp.drop_duplicates(['user_id', 'position_year'], keep='last')

    ua2 = revB4AudExp['user_id'].nunique()
    uay1 = len(revB4AudExp)
    print(f"After explosion — Unique users: {ua2:,}, User-years: {uay1:,}")

    # ── Step 14: Create all analysis variables ────────────────────────────
    revB4AudExp = revB4AudExp.copy()

    revB4AudExp['userid'] = revB4AudExp['user_id'].astype(int)
    revB4AudExp['year'] = revB4AudExp['position_year'].astype(int)
    revB4AudExp['auditorkey'] = revB4AudExp['auditor_key'].astype(int)

    revB4AudExp['retained'] = (
        revB4AudExp['user_firm_enddate'].dt.year > revB4AudExp['year']
    ).fillna(False).astype(int)

    revB4AudExp['female'] = 0
    revB4AudExp.loc[revB4AudExp['sex_predicted'] == 'F', 'female'] = 1

    revB4AudExp['rank_num'] = revB4AudExp['rank_num'].fillna(-1)
    revB4AudExp['positionrank'] = revB4AudExp['rank_num'].astype(int)

    revB4AudExp['badrankdummy'] = 0
    revB4AudExp.loc[revB4AudExp['bad_rank'] == True, 'badrankdummy'] = 1

    revB4AudExp['yearswithfirm'] = revB4AudExp['year'] - revB4AudExp['user_firm_startdate'].dt.year
    revB4AudExp['yearfirst'] = revB4AudExp['user_firm_startdate'].dt.year

    revB4AudExp['white'] = (revB4AudExp['ethnicity_predicted'] == 'White').fillna(False).astype(int)
    revB4AudExp['api'] = (revB4AudExp['ethnicity_predicted'] == 'API').fillna(False).astype(int)
    revB4AudExp['black'] = (revB4AudExp['ethnicity_predicted'] == 'Black').fillna(False).astype(int)
    revB4AudExp['other'] = (~revB4AudExp['ethnicity_predicted'].isin(['White', 'API', 'Black'])).astype(int)

    revB4AudExp['masterorhigher'] = revB4AudExp['degree'].isin(['Master', 'MBA', 'Doctor']).astype(int)
    revB4AudExp['top_university'] = (revB4AudExp['university_name'] != 'other').astype(int)

    # Promotion variable
    revB4AudExp.sort_values(by=['userid', 'year'], inplace=True)
    revB4AudExp['promo'] = (
        revB4AudExp.groupby('userid')['positionrank'].diff().gt(0).astype(int)
    )
    revB4AudExp['promo'] = (
        revB4AudExp.groupby('userid')['promo'].shift(-1).fillna(0).astype(int)
    )

    # Biennial period dummies and interactions
    years = list(range(2010, 2020, 2))
    for start_year in years:
        end_year = start_year + 1
        revB4AudExp[f'year_{start_year}_{end_year}'] = (
            (revB4AudExp['year'] == start_year) | (revB4AudExp['year'] == end_year)
        ).astype(int)

    revB4AudExp['year_pre_2010'] = (revB4AudExp['year'] < 2010).astype(int)
    revB4AudExp['year_post_2019'] = (revB4AudExp['year'] > 2019).astype(int)

    for start_year in years:
        end_year = start_year + 1
        revB4AudExp[f'female_{start_year}_{end_year}'] = (
            revB4AudExp['female'] * revB4AudExp[f'year_{start_year}_{end_year}']
        )

    revB4AudExp['female_pre_2010'] = revB4AudExp['female'] * revB4AudExp['year_pre_2010']
    revB4AudExp['female_post_2019'] = revB4AudExp['female'] * revB4AudExp['year_post_2019']

    # Hazard/survival variables
    revB4AudExp['termination'] = 1 - revB4AudExp['retained']
    revB4AudExp['time'] = revB4AudExp['year'] - revB4AudExp['yearfirst'] + 1

    # Equalized family leave policy variables
    revB4AudExp['post_eq'] = 0
    revB4AudExp.loc[(revB4AudExp['auditorkey'] == 1) & (revB4AudExp['year'] >= 2014), 'post_eq'] = 1
    revB4AudExp.loc[(revB4AudExp['auditorkey'] == 2) & (revB4AudExp['year'] >= 2016), 'post_eq'] = 1
    revB4AudExp.loc[(revB4AudExp['auditorkey'] == 3) & (revB4AudExp['year'] >= 2016), 'post_eq'] = 1

    revB4AudExp['pre_eq_1'] = 0
    revB4AudExp.loc[(revB4AudExp['auditorkey'] == 1) & (revB4AudExp['year'] == 2013), 'pre_eq_1'] = 1
    revB4AudExp.loc[(revB4AudExp['auditorkey'] == 2) & (revB4AudExp['year'] == 2015), 'pre_eq_1'] = 1
    revB4AudExp.loc[(revB4AudExp['auditorkey'] == 3) & (revB4AudExp['year'] == 2015), 'pre_eq_1'] = 1

    revB4AudExp['pre_eq_2'] = 0
    revB4AudExp.loc[(revB4AudExp['auditorkey'] == 1) & (revB4AudExp['year'] == 2012), 'pre_eq_2'] = 1
    revB4AudExp.loc[(revB4AudExp['auditorkey'] == 2) & (revB4AudExp['year'] == 2014), 'pre_eq_2'] = 1
    revB4AudExp.loc[(revB4AudExp['auditorkey'] == 3) & (revB4AudExp['year'] == 2014), 'pre_eq_2'] = 1

    revB4AudExp['pre_eq_3'] = 0
    revB4AudExp.loc[(revB4AudExp['auditorkey'] == 1) & (revB4AudExp['year'] == 2011), 'pre_eq_3'] = 1
    revB4AudExp.loc[(revB4AudExp['auditorkey'] == 2) & (revB4AudExp['year'] == 2013), 'pre_eq_3'] = 1
    revB4AudExp.loc[(revB4AudExp['auditorkey'] == 3) & (revB4AudExp['year'] == 2013), 'pre_eq_3'] = 1

    revB4AudExp['female_post_eq'] = revB4AudExp['female'] * revB4AudExp['post_eq']
    revB4AudExp['female_pre_eq_1'] = revB4AudExp['female'] * revB4AudExp['pre_eq_1']
    revB4AudExp['female_pre_eq_2'] = revB4AudExp['female'] * revB4AudExp['pre_eq_2']
    revB4AudExp['female_pre_eq_3'] = revB4AudExp['female'] * revB4AudExp['pre_eq_3']

    # Post Form AP indicator and interaction
    revB4AudExp['post_formap'] = (revB4AudExp['year'] >= 2015).astype(int)
    revB4AudExp['female_post'] = revB4AudExp['female'] * revB4AudExp['post_formap']
    revB4AudExp['female_post_formap'] = revB4AudExp['female_post']  # alias used by mechanisms table

    # Rank indicators and interactions (for rank interaction table)
    revB4AudExp['staff'] = (revB4AudExp['positionrank'] == 1).astype(int)
    revB4AudExp['senior'] = (revB4AudExp['positionrank'] == 2).astype(int)
    revB4AudExp['mgrplus'] = (revB4AudExp['positionrank'] >= 3).astype(int)
    revB4AudExp['female_staff'] = revB4AudExp['female'] * revB4AudExp['staff']
    revB4AudExp['female_senior'] = revB4AudExp['female'] * revB4AudExp['senior']
    revB4AudExp['female_mgrplus'] = revB4AudExp['female'] * revB4AudExp['mgrplus']
    revB4AudExp['post_senior'] = revB4AudExp['post_formap'] * revB4AudExp['senior']
    revB4AudExp['post_mgrplus'] = revB4AudExp['post_formap'] * revB4AudExp['mgrplus']
    revB4AudExp['female_post_staff'] = revB4AudExp['female'] * revB4AudExp['post_formap'] * revB4AudExp['staff']
    revB4AudExp['female_post_senior'] = revB4AudExp['female'] * revB4AudExp['post_formap'] * revB4AudExp['senior']
    revB4AudExp['female_post_mgrplus'] = revB4AudExp['female'] * revB4AudExp['post_formap'] * revB4AudExp['mgrplus']

    # Time in rank (for rank interaction table -- computed on good-rank obs only)
    good_mask = revB4AudExp['badrankdummy'] == 0
    first_year_at_rank = revB4AudExp.loc[good_mask].groupby(['userid', 'positionrank'])['year'].transform('min')
    revB4AudExp['time_in_rank'] = np.nan
    revB4AudExp.loc[good_mask, 'time_in_rank'] = revB4AudExp.loc[good_mask, 'year'] - first_year_at_rank

    # ── Step 15: Drop post-2023 ───────────────────────────────────────────
    revB4AudExp = revB4AudExp[revB4AudExp['position_year'] <= 2023].copy()

    uad5 = abs(ua2 - revB4AudExp['user_id'].nunique())
    uayd1 = abs(uay1 - len(revB4AudExp))
    print(f"Less {uad5:,} auditors only after 2023")
    print(f"Less {uayd1:,} auditor-years after 2023")

    # ── Step 16: Metro area coding ────────────────────────────────────────
    revB4AudExp['metro_area'] = revB4AudExp['metro_area'].replace("", np.nan)
    revB4AudExp['metro_area_code'] = revB4AudExp['metro_area'].astype('category').cat.codes
    revB4AudExp.loc[revB4AudExp['metro_area'].isna(), 'metro_area_code'] = np.nan

    # ── Step 17: Destination quality variables for leavers ──────────────────
    # For retained==0 observations, look up next non-B4 job from all-positions file
    try:
        all_pos_path = ensure_data_file('raw/revelio/revelio_b4_users_all_positions.feather')
    except FileNotFoundError as e:
        if not allow_missing:
            raise RuntimeError(
                f"{e}\n"
                "  This file holds the complete post-Big 4 career histories that feed "
                "Table 5 (destinationQualityPost.tex). Rerun with --allow-missing to "
                "continue anyway and produce a panel in which the destination-quality "
                "columns are all missing -- note that Table 5 then CANNOT be reproduced."
            ) from e
        all_pos_path = None

    if all_pos_path is not None:
        print("  Computing destination quality variables for leavers...")
        all_pos = pd.read_feather(all_pos_path)
        all_pos = all_pos.loc[:, ~all_pos.columns.duplicated()]
        all_pos['startdate'] = pd.to_datetime(all_pos['startdate'], errors='coerce')
        all_pos['enddate'] = pd.to_datetime(all_pos['enddate'], errors='coerce')

        big4_pat = '|'.join([
            'PricewaterhouseCoopers', 'Deloitte', 'Ernst & Young', 'KPMG',
            'PwC', 'EY', 'Arthur Andersen', 'Coopers & Lybrand', 'Price Waterhouse',
            'KPMG Peat Marwick', 'Deloitte & Touche'
        ])
        all_pos['is_big4'] = all_pos['company_raw'].str.contains(big4_pat, case=False, na=False)

        # Identify leavers: last year for each user where retained==0
        last_years = revB4AudExp.sort_values(['user_id', 'year']).groupby('user_id').tail(1)
        leavers = last_years[last_years['retained'] == 0][['user_id', 'user_firm_enddate']].copy()
        leavers['b4_enddate'] = pd.to_datetime(leavers['user_firm_enddate'])
        leaver_ids = set(leavers['user_id'].unique())

        all_pos_leavers = all_pos[all_pos['user_id'].isin(leaver_ids)].sort_values(['user_id', 'startdate'])

        # For each leaver, find next non-B4 job and B4 end salary
        next_jobs = {}
        b4_end_salaries = {}
        for uid, grp in all_pos_leavers.groupby('user_id'):
            b4_end = leavers.loc[leavers['user_id'] == uid, 'b4_enddate'].iloc[0]
            b4p = grp[grp['is_big4']]
            if len(b4p) > 0:
                b4_end_salaries[uid] = b4p.iloc[-1]['end_salary']
            if pd.isna(b4_end):
                continue
            nonb4_after = grp[(~grp['is_big4']) & (grp['startdate'] >= b4_end)]
            if len(nonb4_after) > 0:
                nxt = nonb4_after.iloc[0]
                next_jobs[uid] = {
                    'next_start_salary': nxt['start_salary'],
                    'gap_days': (nxt['startdate'] - b4_end).days,
                }

        # Map onto the full panel (NaN for retained==1 and leavers with no next job)
        revB4AudExp['b4_end_salary'] = revB4AudExp['user_id'].map(b4_end_salaries)
        revB4AudExp['next_start_salary'] = revB4AudExp['user_id'].map(
            {uid: v['next_start_salary'] for uid, v in next_jobs.items()})
        revB4AudExp['gap_days'] = revB4AudExp['user_id'].map(
            {uid: v['gap_days'] for uid, v in next_jobs.items()})

        # Only populate for the leaver's last year (retained==0)
        not_leaver_year = ~((revB4AudExp['retained'] == 0) &
                            (revB4AudExp['user_id'].isin(leaver_ids)) &
                            (revB4AudExp.groupby('user_id')['year'].transform('max') == revB4AudExp['year']))
        revB4AudExp.loc[not_leaver_year, ['b4_end_salary', 'next_start_salary', 'gap_days']] = np.nan

        revB4AudExp['salary_pct_change'] = (
            (revB4AudExp['next_start_salary'] - revB4AudExp['b4_end_salary'])
            / revB4AudExp['b4_end_salary'] * 100
        )
        revB4AudExp['log_gap'] = np.log(revB4AudExp['gap_days'].clip(lower=1))

        n_leavers = len(leaver_ids)
        n_with_next = len(next_jobs)
        print(f"    Leavers: {n_leavers:,}, with next job: {n_with_next:,} ({100*n_with_next/n_leavers:.0f}%)")
        del all_pos, all_pos_leavers, leavers
        gc.collect()
    else:
        print("  WARNING: all-positions file not found. --allow-missing given: "
              "skipping destination quality variables. Table 5 will NOT reproduce.")
        for col in ['b4_end_salary', 'next_start_salary', 'gap_days', 'salary_pct_change', 'log_gap']:
            revB4AudExp[col] = np.nan

    # ── Step 18: Mechanism variables (AC female %, gender keywords) ─────────
    # Merge audit committee gender composition and proxy statement DEI keywords
    # onto the auditor panel at the CBSA-firm-year level.
    import re
    from shared.metro_crosswalk import add_cbsa_to_companies, add_cbsa_to_auditors

    try:
        print("  Building mechanism variables (AC female %, gender keywords)...")

        # Audit Analytics Big 4 linkage
        aa = pd.read_csv(
            ensure_data_file("raw/audit_analytics/audit_audit_comp_feed34_revised_audit_opinions.csv"),
            usecols=['auditor_name', 'company_fkey', 'fiscal_year_of_op']
        )
        auditor_map = {
            'PricewaterhouseCoopers LLP': 'pwc',
            'Deloitte & Touche LLP': 'deloitte',
            'Ernst & Young LLP': 'ey',
            'KPMG LLP': 'kpmg',
        }
        aa_b4 = aa[aa['auditor_name'].isin(auditor_map)].copy()
        aa_b4['aud_firm'] = aa_b4['auditor_name'].map(auditor_map)
        aa_b4 = aa_b4.rename(columns={'company_fkey': 'cik', 'fiscal_year_of_op': 'fyear'})
        aa_b4 = aa_b4[['cik', 'fyear', 'aud_firm']].dropna(subset=['fyear'])
        aa_b4['fyear'] = aa_b4['fyear'].astype(int)
        aa_b4 = aa_b4.drop_duplicates(subset=['cik', 'fyear'], keep='last')
        del aa

        # AC female % from BoardEx
        boardex = pd.read_feather(ensure_data_file("raw/boardex/na_wrds_org_summary.feather"))
        boardex['annualreportdate'] = pd.to_datetime(boardex['annualreportdate'])
        boardex['fyear'] = boardex['annualreportdate'].dt.year
        boardex['cik'] = pd.to_numeric(boardex['cikcode'], errors='coerce')
        board_cik = boardex[boardex['cik'].notna()].drop_duplicates(subset=['companyid', 'fyear'])[['companyid', 'cik', 'fyear']].copy()
        board_cik['cik'] = board_cik['cik'].astype(int)

        committees = pd.read_feather(ensure_data_file("raw/boardex/na_board_dir_committees.feather"))
        audit_comm = committees[committees['committeename'].str.contains('Audit', case=False, na=False)].copy()
        dir_gender = boardex[['directorid', 'gender']].drop_duplicates(subset=['directorid'])
        audit_comm = audit_comm.merge(dir_gender, on='directorid', how='inner')
        audit_comm['annualreportdate'] = pd.to_datetime(audit_comm['annualreportdate'], errors='coerce')
        audit_comm = audit_comm[audit_comm['annualreportdate'].notna()]
        audit_comm['fyear'] = audit_comm['annualreportdate'].dt.year
        audit_comm['is_female'] = (audit_comm['gender'] == 'F').astype(int)
        audit_comm = audit_comm.rename(columns={'boardid': 'companyid'})
        audit_comm['companyid'] = audit_comm['companyid'].astype(int)

        ac_fem = audit_comm.groupby(['companyid', 'fyear'])['is_female'].mean().reset_index().rename(columns={'is_female': 'ac_fem_pct'})
        ac_fem = ac_fem.merge(board_cik, on=['companyid', 'fyear'], how='inner')

        profile = pd.read_feather(ensure_data_file("raw/boardex/na_wrds_company_profile.feather"))
        profile = profile[profile['hocountryname'] == 'United States'].copy()
        profile['bx_city'] = profile['hoaddress3'].str.upper().str.strip()
        def extract_st(a4):
            if pd.isna(a4): return None
            m_st = re.search(r'\b([A-Z]{2})\s*$', a4.strip())
            return m_st.group(1) if m_st else None
        profile['bx_state'] = profile['hoaddress4'].apply(extract_st)
        prof_loc = profile[profile['hoaddress5'].notna() & profile['bx_state'].notna()].drop_duplicates(subset=['boardid'])[['boardid', 'hoaddress5', 'bx_city', 'bx_state']].rename(columns={'boardid': 'companyid'})
        ac_fem = ac_fem.merge(prof_loc, on='companyid', how='inner')
        ac_fem = add_cbsa_to_companies(ac_fem, zip_col='hoaddress5', city_col='bx_city', state_col='bx_state')

        ac_client = ac_fem[ac_fem['cbsa_code'].notna()].merge(aa_b4, on=['cik', 'fyear'], how='inner')
        ac_client['cbsa_code'] = ac_client['cbsa_code'].astype(int)
        cbsa_firm_ac = ac_client.groupby(['cbsa_code', 'aud_firm', 'fyear'])['ac_fem_pct'].mean().reset_index().rename(columns={'ac_fem_pct': 'ac_fem_pct_sf'})
        state_firm_ac = ac_client.groupby(['bx_state', 'aud_firm', 'fyear'])['ac_fem_pct'].mean().reset_index().rename(columns={'ac_fem_pct': 'ac_fem_pct_state', 'bx_state': 'state_abbrev'})
        print(f"    AC: {len(cbsa_firm_ac):,} CBSA-firm-year cells")
        del boardex, committees, audit_comm, ac_fem, ac_client, profile

        # Gender keywords from proxy statements
        us_state_abbrev = {
            'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
            'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
            'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
            'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
            'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
            'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire',
            'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina',
            'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania',
            'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota', 'TN': 'Tennessee',
            'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington',
            'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia',
        }

        kw = pd.read_csv(ensure_data_file("proxy statements/proxy_dei_keywords_v2.csv"))
        kw = kw[kw['status'] == 'ok'].copy()

        # Registrant business addresses, keyed by CIK. This is the most recent
        # snapshot per filer, extracted from EDGAR company metadata; see
        # DATA_AVAILABILITY.md. Public SEC data, committed under
        # Analysis/Data/public/edgar/.
        locs = pd.read_csv(
            ensure_data_file("edgar/company_locations.csv"),
            dtype={'zip': str, 'state': str, 'city': str},
        )
        locs = locs.dropna(subset=['zip', 'state'])
        locs['cik'] = locs['cik'].astype(int)

        df_us = kw.merge(locs, on='cik', how='inner')
        df_us = df_us[df_us['state'].isin(us_state_abbrev.keys())].copy()
        df_us = add_cbsa_to_companies(df_us, zip_col='zip')

        cbsa_year_firm_dei = df_us[df_us['aud_firm'].notna() & df_us['cbsa_code'].notna()].groupby(['cbsa_code', 'fyear', 'aud_firm'])['gender_word_count'].mean().reset_index().rename(columns={'gender_word_count': 'dei_proportion_firm'})
        cbsa_year_firm_dei['cbsa_code'] = cbsa_year_firm_dei['cbsa_code'].astype(int)

        df_us_with_state = df_us[df_us['aud_firm'].notna() & df_us['state'].notna()].copy()
        state_year_firm_dei = df_us_with_state.groupby(['state', 'fyear', 'aud_firm'])['gender_word_count'].mean().reset_index().rename(columns={'gender_word_count': 'dei_proportion_state', 'state': 'state_abbrev'})
        print(f"    DEI: {len(cbsa_year_firm_dei):,} CBSA-firm-year cells")
        del kw, locs, df_us, df_us_with_state

        # Merge onto auditor panel (CBSA primary, state fallback)
        revB4AudExp = add_cbsa_to_auditors(revB4AudExp)
        revB4AudExp['cbsa_code'] = revB4AudExp['cbsa_code'].astype('Int64')

        _sa = {v: k for k, v in us_state_abbrev.items()}
        _sa['Washington, D.C.'] = 'DC'
        revB4AudExp['state_abbrev'] = revB4AudExp['state'].map(_sa)

        revB4AudExp = revB4AudExp.merge(cbsa_firm_ac, left_on=['cbsa_code', 'aud_firm', 'year'], right_on=['cbsa_code', 'aud_firm', 'fyear'], how='left')
        revB4AudExp.drop(columns=['fyear'], errors='ignore', inplace=True)
        revB4AudExp = revB4AudExp.merge(cbsa_year_firm_dei, left_on=['cbsa_code', 'aud_firm', 'year'], right_on=['cbsa_code', 'aud_firm', 'fyear'], how='left')
        revB4AudExp.drop(columns=['fyear'], errors='ignore', inplace=True)

        # State fallback
        revB4AudExp = revB4AudExp.merge(state_firm_ac, left_on=['state_abbrev', 'aud_firm', 'year'], right_on=['state_abbrev', 'aud_firm', 'fyear'], how='left')
        revB4AudExp.drop(columns=['fyear'], errors='ignore', inplace=True)
        revB4AudExp.loc[revB4AudExp['ac_fem_pct_sf'].isna(), 'ac_fem_pct_sf'] = revB4AudExp.loc[revB4AudExp['ac_fem_pct_sf'].isna(), 'ac_fem_pct_state']
        revB4AudExp.drop(columns=['ac_fem_pct_state'], inplace=True)

        revB4AudExp = revB4AudExp.merge(state_year_firm_dei, left_on=['state_abbrev', 'aud_firm', 'year'], right_on=['state_abbrev', 'aud_firm', 'fyear'], how='left')
        revB4AudExp.drop(columns=['fyear'], errors='ignore', inplace=True)
        revB4AudExp.loc[revB4AudExp['dei_proportion_firm'].isna(), 'dei_proportion_firm'] = revB4AudExp.loc[revB4AudExp['dei_proportion_firm'].isna(), 'dei_proportion_state']
        revB4AudExp.drop(columns=['dei_proportion_state', 'state_abbrev', 'cbsa_code'], errors='ignore', inplace=True)

        # Interactions
        revB4AudExp['female_ac'] = revB4AudExp['female'] * revB4AudExp['ac_fem_pct_sf']
        revB4AudExp['female_dei'] = revB4AudExp['female'] * revB4AudExp['dei_proportion_firm']

        ac_cov = revB4AudExp['ac_fem_pct_sf'].notna().mean()
        dei_cov = revB4AudExp['dei_proportion_firm'].notna().mean()
        print(f"    AC coverage: {ac_cov*100:.1f}%, DEI coverage: {dei_cov*100:.1f}%")
        if ac_cov == 0 or dei_cov == 0:
            raise RuntimeError(
                f"Mechanism variables built but empty (AC coverage {ac_cov:.1%}, "
                f"DEI coverage {dei_cov:.1%}). Table 4 (mechanismsTable) cannot be "
                "reproduced from this panel -- check the BoardEx, Audit Analytics, "
                "and EDGAR location inputs."
            )
        del cbsa_firm_ac, state_firm_ac, cbsa_year_firm_dei, state_year_firm_dei

    except Exception as e:
        if not allow_missing:
            raise RuntimeError(
                f"Could not build mechanism variables: {e}\n"
                "  These feed Table 4 (mechanismsTable.tex) and the metro mechanism "
                "figure. Rerun with --allow-missing to continue anyway and produce a "
                "panel in which the mechanism columns are all missing -- note that "
                "Table 4 then CANNOT be reproduced."
            ) from e
        print(f"  WARNING: Could not build mechanism variables: {e}")
        print("  --allow-missing given: setting ac_fem_pct_sf, dei_proportion_firm, "
              "female_ac, female_dei to NaN. Table 4 will NOT reproduce.")
        for col in ['ac_fem_pct_sf', 'dei_proportion_firm', 'female_ac', 'female_dei']:
            revB4AudExp[col] = np.nan

    # ── Step 19: Winsorize continuous variables at 1%/99% ──────────────────
    print("  Winsorizing continuous variables at 1%/99%...")
    for col in ['salary_pct_change', 'gap_days', 'ac_fem_pct_sf', 'dei_proportion_firm']:
        s = revB4AudExp[col].dropna()
        if len(s) == 0:
            continue
        p01, p99 = s.quantile(0.01), s.quantile(0.99)
        n_before = ((revB4AudExp[col] < p01) | (revB4AudExp[col] > p99)).sum()
        revB4AudExp[col] = revB4AudExp[col].clip(lower=p01, upper=p99)
        print(f"    {col}: clipped {n_before:,} obs to [{p01:.2f}, {p99:.2f}]")

    # Recompute derived variables after winsorization
    revB4AudExp['log_gap'] = np.log(revB4AudExp['gap_days'].clip(lower=1))
    # Set log_gap to 0 for retained observations (not leavers)
    revB4AudExp.loc[revB4AudExp['retained'] == 1, 'log_gap'] = 0
    revB4AudExp['female_ac'] = revB4AudExp['female'] * revB4AudExp['ac_fem_pct_sf']
    revB4AudExp['female_dei'] = revB4AudExp['female'] * revB4AudExp['dei_proportion_firm']

    # ── Create final Stata dataset ────────────────────────────────────────
    revB4AudStata = revB4AudExp[[
        'userid', 'year', 'auditorkey', 'retained', 'promo', 'female', 'ethnicity_predicted',
        'positionrank', 'rank', 'badrankdummy', 'masterorhigher', 'yearswithfirm', 'yearfirst',
        'white', 'api', 'black', 'other', 'metro_area', 'user_firm_startdate', 'user_firm_enddate',
        'female_pre_2010', 'female_2010_2011', 'female_2012_2013', 'female_2014_2015',
        'female_2016_2017', 'female_2018_2019', 'female_post_2019', 'termination', 'time',
        'female_pre_eq_3', 'female_pre_eq_2', 'female_pre_eq_1', 'female_post_eq',
        'pre_eq_1', 'pre_eq_2', 'pre_eq_3', 'post_eq', 'metro_area_code',
        'university_name', 'top_university',
        'post_formap', 'female_post', 'female_post_formap',
        'staff', 'senior', 'mgrplus',
        'female_staff', 'female_senior', 'female_mgrplus',
        'post_senior', 'post_mgrplus',
        'female_post_staff', 'female_post_senior', 'female_post_mgrplus',
        'time_in_rank',
        'b4_end_salary', 'next_start_salary', 'gap_days', 'salary_pct_change', 'log_gap',
        'ac_fem_pct_sf', 'dei_proportion_firm', 'female_ac', 'female_dei',
    ]].copy()

    # Final counts
    ua3 = revB4AudStata['userid'].nunique()
    uay2 = len(revB4AudStata)
    ua4 = revB4AudStata.loc[revB4AudStata['badrankdummy'] == 0, 'userid'].nunique()
    uay3 = len(revB4AudStata.loc[revB4AudStata['badrankdummy'] == 0])
    uad6 = abs(ua3 - ua4)
    uayd2 = abs(uay2 - uay3)

    print(f"\nFinal — Unique users: {ua3:,}, User-years: {uay2:,}")
    print(f"Good ranks — Unique users: {ua4:,}, User-years: {uay3:,}")

    counts = {
        'ua1': ua1, 'uap1': uap1,
        'uad1': uad1, 'uapd1': uapd1,
        'uad2': uad2, 'uapd2': uapd2,
        'uad3': uad3, 'uapd3': uapd3,
        'ua2': ua2, 'uay1': uay1,
        'uad5': uad5, 'uayd1': uayd1,
        'ua3': ua3, 'uay2': uay2,
        'ua4': ua4, 'uay3': uay3,
        'uad6': uad6, 'uayd2': uayd2,
    }

    return revB4AudStata, revB4AudExp, counts


def prepare_other_fs_data():
    """Process interim other financial services data into analysis-ready panel.

    Returns (revOtherFsStata, revOtherFsExp, sample_counts_dict).
    """
    print("\n" + "=" * 60)
    print("Working with the other financial services dataset")
    print("=" * 60)

    revOtherFs = pd.read_feather(ensure_data_file("interim/revOtherFs.feather"))

    uw1 = revOtherFs['user_id'].nunique()
    uwp1 = len(revOtherFs)
    print(f"Unique fs employees: {uw1:,}")
    print(f"Unique fs positions: {uwp1:,}")

    # Drop bad dates
    revOtherFs = revOtherFs[revOtherFs['startdate'] <= revOtherFs['enddate']]
    revOtherFs = revOtherFs[~revOtherFs['startdate'].isnull()]

    uwd1 = abs(uw1 - revOtherFs['user_id'].nunique())
    uwpd1 = abs(uwp1 - len(revOtherFs))
    print(f"Less {uwd1:,} workers with bad dates")
    print(f"Less {uwpd1:,} positions with bad dates")

    # Limit to valid companies
    revOtherFs = revOtherFs[revOtherFs['ultimate_parent_rcid'].notnull()]
    revOtherFs = revOtherFs[~revOtherFs['company_raw'].str.contains("self-employed", case=False, na=False)]
    revOtherFs = revOtherFs[~revOtherFs['company_raw'].str.contains("self employed", case=False, na=False)]
    revOtherFs = revOtherFs[~revOtherFs['company_raw'].str.contains("h&r block", case=False, na=False)]

    uwd2 = abs(uw1 - uwd1 - revOtherFs['user_id'].nunique())
    uwpd2 = abs(uwp1 - uwpd1 - len(revOtherFs))
    print(f"Less {uwd2:,} workers without valid company ID")
    print(f"Less {uwpd2:,} positions without valid company ID")

    # Exclude accounting firms: Big 4, Arthur Andersen, and AT Top 100 firms
    # (all positions, not just audit roles) to ensure clean separation from
    # auditor benchmarks. See Response Memo R2, comment 2.
    ACCT_FIRM_PATTERNS = [
        'deloitte', 'pricewaterhousecoopers', 'pwc',
        'ernst & young', 'ernst and young', 'ernst & whinney',
        'kpmg', 'arthur andersen',
    ]
    ACCT_FIRM_EXACT = {
        'andersen', 'andersen llp', 'andersen, llp',
        'andersen tax', 'andersen tax llp',
        'andersen consulting', 'andersen business consulting',
    }
    def _is_acct_firm(name):
        if pd.isna(name):
            return False
        nl = name.lower()
        if nl in ('ey', 'e & y') or nl.startswith('ey '):
            return True
        if nl in ACCT_FIRM_EXACT:
            return True
        return any(p in nl for p in ACCT_FIRM_PATTERNS)

    at_mapping_path = ensure_data_file('interim/at_revelio_firm_mapping.json')
    with open(at_mapping_path) as f:
        at_firm_mapping = json.load(f)
    at_company_raws = set()
    for firm, matches in at_firm_mapping.items():
        for company_raw, _count in matches:
            at_company_raws.add(company_raw)

    pre_at = revOtherFs['user_id'].nunique()
    is_at100 = revOtherFs['company_raw'].isin(at_company_raws)
    is_b4_andersen = revOtherFs['company_raw'].apply(_is_acct_firm)
    revOtherFs = revOtherFs[~is_at100 & ~is_b4_andersen]
    uwd_at = abs(pre_at - revOtherFs['user_id'].nunique())
    print(f"Less {uwd_at:,} workers at accounting firms (Big 4, Andersen, AT Top 100)")

    # Drop missing education
    revOtherFs = revOtherFs[revOtherFs['highest_degree'].notnull()]

    uwd3 = abs(uw1 - uwd1 - uwd2 - revOtherFs['user_id'].nunique())
    uwpd3 = abs(uwp1 - uwpd1 - uwpd2 - len(revOtherFs))
    print(f"Less {uwd3:,} workers without education")
    print(f"Less {uwpd3:,} positions without education")

    # Drop interns
    revOtherFs = revOtherFs[~revOtherFs['title_raw'].str.contains('intern', case=False, na=False)]

    uwd4 = abs(uw1 - uwd1 - uwd2 - uwd3 - revOtherFs['user_id'].nunique())
    uwpd4 = abs(uwp1 - uwpd1 - uwpd2 - uwpd3 - len(revOtherFs))
    print(f"Less {uwd4:,} workers who are only interns")
    print(f"Less {uwpd4:,} intern positions")

    # Explode to employee-year
    revOtherFs = revOtherFs.sort_values(['user_id', 'ultimate_parent_rcid', 'startdate'])
    revOtherFs['startdate'] = pd.to_datetime(revOtherFs['startdate'])
    revOtherFs['enddate'] = pd.to_datetime(revOtherFs['enddate'])

    revOtherFs['new_spell'] = (
        (revOtherFs['user_id'] != revOtherFs['user_id'].shift(1)) |
        (revOtherFs['ultimate_parent_rcid'] != revOtherFs['ultimate_parent_rcid'].shift(1))
    ).fillna(True).astype(int)

    revOtherFs['spell_id'] = revOtherFs['new_spell'].cumsum()
    revOtherFs['spell_startdate'] = revOtherFs.groupby('spell_id')['startdate'].transform('min')
    revOtherFs['spell_enddate'] = revOtherFs.groupby('spell_id')['enddate'].transform('max')
    revOtherFs = revOtherFs.drop_duplicates(['user_id', 'spell_id'], keep='last')

    revOtherFs['position_year'] = revOtherFs.apply(
        lambda row: list(range(row['spell_startdate'].year, row['spell_enddate'].year + 1)), axis=1
    )

    revOtherFsExp = (
        revOtherFs[[
            'user_id', 'state', 'metro_area', 'spell_startdate', 'spell_enddate',
            'position_year', 'sex_predicted', 'ethnicity_predicted', 'profile_linkedin_url',
            'ultimate_parent_rcid', 'company_raw', 'role_k1500', 'degree', 'university_name'
        ]].explode('position_year', ignore_index=True)
    )

    revOtherFsExp = revOtherFsExp.sort_values(['user_id', 'position_year', 'spell_enddate'])
    revOtherFsExp = revOtherFsExp.drop_duplicates(['user_id', 'position_year'], keep='last')

    uw2 = revOtherFsExp['user_id'].nunique()
    uwy1 = len(revOtherFsExp)
    print(f"After explosion — Unique workers: {uw2:,}, Worker-years: {uwy1:,}")

    # Drop post-2023
    revOtherFsExp = revOtherFsExp[revOtherFsExp['position_year'] <= 2023]

    uwd5 = abs(uw2 - revOtherFsExp['user_id'].nunique())
    uwyd1 = abs(uwy1 - len(revOtherFsExp))
    print(f"Less {uwd5:,} workers only after 2023")
    print(f"Less {uwyd1:,} worker-years after 2023")

    # Create variables
    revOtherFsExp = revOtherFsExp.copy()

    revOtherFsExp['userid'] = revOtherFsExp['user_id'].astype(int)
    revOtherFsExp['year'] = revOtherFsExp['position_year'].astype(int)
    revOtherFsExp['retained'] = (
        revOtherFsExp['spell_enddate'].dt.year > revOtherFsExp['year']
    ).fillna(False).astype(int)

    revOtherFsExp['female'] = 0
    revOtherFsExp.loc[revOtherFsExp['sex_predicted'] == 'F', 'female'] = 1

    revOtherFsExp['yearswithfirm'] = revOtherFsExp['year'] - revOtherFsExp['spell_startdate'].dt.year
    revOtherFsExp['yearfirst'] = revOtherFsExp['spell_startdate'].dt.year

    revOtherFsExp['white'] = (revOtherFsExp['ethnicity_predicted'] == 'White').fillna(False).astype(int)
    revOtherFsExp['api'] = (revOtherFsExp['ethnicity_predicted'] == 'API').fillna(False).astype(int)
    revOtherFsExp['black'] = (revOtherFsExp['ethnicity_predicted'] == 'Black').fillna(False).astype(int)
    revOtherFsExp['other'] = (~revOtherFsExp['ethnicity_predicted'].isin(['White', 'API', 'Black'])).fillna(False).astype(int)

    revOtherFsExp['masterorhigher'] = revOtherFsExp['degree'].isin(['Master', 'MBA', 'Doctor']).fillna(False).astype(int)
    revOtherFsExp['top_university'] = (revOtherFsExp['university_name'] != 'other').fillna(False).astype(int)

    years = list(range(2010, 2020, 2))
    for start_year in years:
        end_year = start_year + 1
        revOtherFsExp[f'year_{start_year}_{end_year}'] = (
            (revOtherFsExp['year'] == start_year) | (revOtherFsExp['year'] == end_year)
        ).fillna(False).astype(int)

    revOtherFsExp['year_pre_2010'] = (revOtherFsExp['year'] < 2010).fillna(False).astype(int)
    revOtherFsExp['year_post_2019'] = (revOtherFsExp['year'] > 2019).fillna(False).astype(int)

    for start_year in years:
        end_year = start_year + 1
        revOtherFsExp[f'female_{start_year}_{end_year}'] = (
            revOtherFsExp['female'] * revOtherFsExp[f'year_{start_year}_{end_year}']
        )

    revOtherFsExp['female_pre_2010'] = revOtherFsExp['female'] * revOtherFsExp['year_pre_2010']
    revOtherFsExp['female_post_2019'] = revOtherFsExp['female'] * revOtherFsExp['year_post_2019']

    revOtherFsStata = revOtherFsExp[[
        'retained', 'female_pre_2010', 'female_2010_2011', 'female_2012_2013',
        'female_2014_2015', 'female_2016_2017', 'female_2018_2019', 'female_post_2019',
        'masterorhigher', 'female', 'top_university', 'api', 'black', 'other',
        'ultimate_parent_rcid', 'year', 'yearfirst', 'userid', 'role_k1500'
    ]].copy()

    uw3 = revOtherFsStata['userid'].nunique()
    uwy2 = len(revOtherFsStata)
    print(f"\nFinal — Unique workers: {uw3:,}, Worker-years: {uwy2:,}")

    counts = {
        'uw1': uw1, 'uwp1': uwp1,
        'uwd1': uwd1, 'uwpd1': uwpd1,
        'uwd2': uwd2, 'uwpd2': uwpd2,
        'uwd3': uwd3, 'uwpd3': uwpd3,
        'uwd4': uwd4, 'uwpd4': uwpd4,
        'uw2': uw2, 'uwy1': uwy1,
        'uwd5': uwd5, 'uwyd1': uwyd1,
        'uw3': uw3, 'uwy2': uwy2,
    }

    return revOtherFsStata, revOtherFsExp, counts


def main():
    parser = argparse.ArgumentParser(
        description='Build analysis-ready panels from interim Revelio data.')
    parser.add_argument(
        '--allow-missing', action='store_true',
        help='Continue when an input needed for a published table is missing, '
             'leaving the affected columns empty (those tables will not reproduce)')
    args = parser.parse_args()

    start_time = time.time()

    # ── Audit data ────────────────────────────────────────────────────────
    revB4AudStata, revB4AudExp, aud_counts = prepare_audit_data(args.allow_missing)

    stata_path = "processed/revB4AudStata.feather"
    exp_path = "processed/revB4AudExp.feather"

    revB4AudExp.to_feather(os.path.join(data_dir, exp_path))
    revB4AudStata.to_feather(os.path.join(data_dir, stata_path))
    print(f"\nSaved {stata_path} and {exp_path}")

    upload_to_r2(exp_path)
    upload_to_r2(stata_path)

    del revB4AudStata, revB4AudExp
    gc.collect()

    # ── Other financial services data ─────────────────────────────────────
    revOtherFsStata, revOtherFsExp, fs_counts = prepare_other_fs_data()

    fs_stata_path = "processed/revOtherFsStata.feather"
    fs_exp_path = "processed/revOtherFsExp.feather"

    revOtherFsExp.to_feather(os.path.join(data_dir, fs_exp_path))
    revOtherFsStata.to_feather(os.path.join(data_dir, fs_stata_path))
    print(f"\nSaved {fs_stata_path} and {fs_exp_path}")

    upload_to_r2(fs_exp_path)
    upload_to_r2(fs_stata_path)

    del revOtherFsStata, revOtherFsExp
    gc.collect()

    # ── Save sample counts ────────────────────────────────────────────────
    # These counts are the sole input to Table 1 (sampleDesign.tex), which never
    # reads a panel. Writing them only after the panels are on disk, and checking
    # they describe THOSE panels, keeps Table 1 from silently disagreeing with the
    # N reported by every other table.
    all_counts = {**aud_counts, **fs_counts}

    panel_rows = len(pd.read_feather(os.path.join(data_dir, stata_path),
                                     columns=['female']))
    if all_counts.get('uay2') != panel_rows:
        raise RuntimeError(
            f"Sample counts disagree with the panel just written: counts say "
            f"uay2={all_counts.get('uay2'):,} primary-sample employee-years but "
            f"{stata_path} has {panel_rows:,} rows. Table 1 would contradict the "
            "other tables. This means the counts and the panel came from "
            "different runs -- do not mix vintages."
        )

    counts_path = "processed/sample_counts.json"
    with open(os.path.join(data_dir, counts_path), 'w') as f:
        json.dump(all_counts, f, indent=2)
    print(f"\nSaved {len(all_counts)} sample counts to {counts_path} "
          f"(cross-checked against {panel_rows:,} panel rows)")

    elapsed = (time.time() - start_time) / 60
    print(f"\nDone. Total time: {elapsed:.1f} minutes")


if __name__ == '__main__':
    main()
