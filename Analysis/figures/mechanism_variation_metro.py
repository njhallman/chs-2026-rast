"""
Show geographic variation in DEI/AC mechanisms at the METRO level,
using keyword-based DEI measures from the local-edgar proxy archive (v2).

Split metros into high-change vs low-change groups and plot the time series.
Uses CBSA-level linkage via Census ZIP-CBSA crosswalk.

Data sources:
  - proxy_dei_keywords_v2.csv: keyword counts from local-edgar markdown proxies
  - local-edgar company_snapshots: business ZIP for CBSA mapping
  - BoardEx: audit committee gender composition

Produces: mechanism_variation_metro.png
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path

from shared.paths import figures_dir
from shared.r2 import ensure_data_file
from shared.metro_crosswalk import add_cbsa_to_companies

EDGAR_DB = Path(os.path.expanduser("~/Documents/Projects/local-edgar/archive/db/edgar.db"))

us_state_abbrev = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC',
}

# ══════════════════════════════════════════════════════════════════════════════
# Load v2 keyword data + company locations from local-edgar
# ══════════════════════════════════════════════════════════════════════════════
print("Loading v2 keyword data...")
kw = pd.read_csv(ensure_data_file("proxy statements/proxy_dei_keywords_v2.csv"))
kw = kw[kw['status'] == 'ok'].copy()
print(f"  {len(kw):,} proxy statements with keyword data")

# Get company business ZIP from local-edgar company_snapshots (latest snapshot per CIK)
print("Loading company locations from local-edgar...")
conn = sqlite3.connect(str(EDGAR_DB))
locs = pd.read_sql_query("""
    SELECT cik, business_zip AS zip, business_state AS state, business_city AS city
    FROM company_snapshots
    WHERE business_zip IS NOT NULL AND business_state IS NOT NULL
    GROUP BY cik
    HAVING snapshot_date = MAX(snapshot_date)
""", conn)
conn.close()
locs['cik'] = locs['cik'].astype(int)
print(f"  {len(locs):,} companies with location data")

# Merge location onto keyword data
df = kw.merge(locs, on='cik', how='inner')
df = df[df['state'].isin(us_state_abbrev)].copy()
print(f"  {len(df):,} US proxy statements after location merge")

# Add CBSA from ZIP
df = add_cbsa_to_companies(df, zip_col='zip')
cbsa_match = df['cbsa_code'].notna().sum()
print(f"  {cbsa_match:,} of {len(df):,} matched to CBSA ({cbsa_match/len(df)*100:.1f}%)")

# Aggregate to CBSA × year
dei_cbsa_yr = (
    df[df['cbsa_code'].notna()]
    .groupby(['cbsa_code', 'fyear'])[['dei_word_count', 'gender_word_count',
                                       'workforce_dei_count', 'total_doc_length']]
    .mean().reset_index()
)
dei_cbsa_yr['cbsa_code'] = dei_cbsa_yr['cbsa_code'].astype(int)

# ══════════════════════════════════════════════════════════════════════════════
# AC Female % → CBSA-level
# ══════════════════════════════════════════════════════════════════════════════
print("\nLoading AC Female % data and mapping to CBSAs...")
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

# Get company ZIP from BoardEx profile
profile = pd.read_feather(ensure_data_file("raw/boardex/na_wrds_company_profile.feather"))
profile = profile[profile['hocountryname'] == 'United States'].copy()
profile_zip = profile[profile['hoaddress5'].notna()].drop_duplicates(subset=['boardid'])[['boardid', 'hoaddress5']].rename(
    columns={'boardid': 'companyid', 'hoaddress5': 'zip'})
ac_fem = ac_fem.merge(profile_zip, on='companyid', how='inner')

ac_fem = add_cbsa_to_companies(ac_fem, zip_col='zip')

# Restrict AC data to B4 clients using AA
aa = pd.read_csv(
    ensure_data_file("raw/audit_analytics/audit_audit_comp_feed34_revised_audit_opinions.csv"),
    usecols=['auditor_name', 'company_fkey', 'fiscal_year_of_op']
)
auditor_map = {
    'PricewaterhouseCoopers LLP': 'pwc', 'Deloitte & Touche LLP': 'deloitte',
    'Ernst & Young LLP': 'ey', 'KPMG LLP': 'kpmg',
}
aa_b4 = aa[aa['auditor_name'].isin(auditor_map)].copy()
aa_b4 = aa_b4.rename(columns={'company_fkey': 'cik', 'fiscal_year_of_op': 'fyear'})
aa_b4['fyear'] = aa_b4['fyear'].astype(int)
aa_b4 = aa_b4[['cik', 'fyear']].drop_duplicates()
ac_fem = ac_fem.merge(aa_b4, on=['cik', 'fyear'], how='inner')

ac_match = ac_fem['cbsa_code'].notna().sum()
print(f"  AC: {ac_match:,} of {len(ac_fem):,} matched to CBSA ({ac_match/len(ac_fem)*100:.1f}%)")

ac_cbsa_yr = (
    ac_fem[ac_fem['cbsa_code'].notna()]
    .groupby(['cbsa_code', 'fyear'])['ac_fem_pct']
    .mean().reset_index()
)
ac_cbsa_yr['ac_fem_pct'] *= 100
ac_cbsa_yr['cbsa_code'] = ac_cbsa_yr['cbsa_code'].astype(int)

# ══════════════════════════════════════════════════════════════════════════════
# Split CBSAs into high/low change groups
# ══════════════════════════════════════════════════════════════════════════════
print("\nComputing CBSA-level changes...")

# Gender keyword change: pre (2010-2014) vs post (2018-2022)
dei_sub = df[df['cbsa_code'].notna()].copy()
dei_pre = dei_sub[dei_sub['fyear'].between(2010, 2014)].groupby('cbsa_code')['gender_word_count'].mean()
dei_post = dei_sub[dei_sub['fyear'].between(2018, 2022)].groupby('cbsa_code')['gender_word_count'].mean()
dei_change = (dei_post - dei_pre).dropna()
dei_n = dei_sub.groupby('cbsa_code').size()
dei_change = dei_change[dei_change.index.isin(dei_n[dei_n >= 50].index)]

dei_median = dei_change.median()
high_dei = set(dei_change[dei_change >= dei_median].index)
low_dei = set(dei_change[dei_change < dei_median].index)
print(f"  Gender keywords: {len(high_dei)} high-change CBSAs, {len(low_dei)} low-change")
print(f"    High mean change: {dei_change[dei_change >= dei_median].mean():.1f} words")
print(f"    Low mean change:  {dei_change[dei_change < dei_median].mean():.1f} words")

# AC change: pre (2005-2012) vs post (2016-2023)
ac_pre = ac_fem[ac_fem['fyear'].between(2005, 2012) & ac_fem['cbsa_code'].notna()].groupby('cbsa_code')['ac_fem_pct'].mean()
ac_post = ac_fem[ac_fem['fyear'].between(2016, 2023) & ac_fem['cbsa_code'].notna()].groupby('cbsa_code')['ac_fem_pct'].mean()
ac_change = (ac_post - ac_pre).dropna()
ac_n = ac_fem[ac_fem['cbsa_code'].notna()].groupby('cbsa_code').size()
ac_change = ac_change[ac_change.index.isin(ac_n[ac_n >= 50].index)]

ac_median = ac_change.median()
high_ac = set(ac_change[ac_change >= ac_median].index)
low_ac = set(ac_change[ac_change < ac_median].index)
print(f"  AC: {len(high_ac)} high-change CBSAs, {len(low_ac)} low-change")
print(f"    High mean change: {ac_change[ac_change >= ac_median].mean()*100:.1f} pp")
print(f"    Low mean change:  {ac_change[ac_change < ac_median].mean()*100:.1f} pp")

# ══════════════════════════════════════════════════════════════════════════════
# Plot
# ══════════════════════════════════════════════════════════════════════════════
FORM_AP = 2015

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Panel 1: AC Female %
for label, cbsa_set, color, marker, ls in [
    ('High AC-change metros', high_ac, '#2171B5', 'o', '-'),
    ('Low AC-change metros', low_ac, '#D62728', '^', '--'),
]:
    sub = ac_cbsa_yr[ac_cbsa_yr['cbsa_code'].isin(cbsa_set) & ac_cbsa_yr['fyear'].between(2004, 2023)]
    yearly = sub.groupby('fyear')['ac_fem_pct'].mean().reset_index()
    ax1.plot(yearly['fyear'], yearly['ac_fem_pct'],
             color=color, marker=marker, markersize=6, linestyle=ls, linewidth=2.2, label=label)

ax1.axvspan(FORM_AP, 2023.5, alpha=0.10, color='gray', zorder=0)
ax1.text((FORM_AP + 2023.5) / 2, 0.02, 'Post Form AP', ha='center', va='bottom',
         fontsize=10, color='gray', fontstyle='italic', transform=ax1.get_xaxis_transform())
ax1.set_xlabel('Year', fontsize=12)
ax1.set_ylabel('AC Female %', fontsize=12)
ax1.set_title('Audit Committee Female % by Metro Group', fontsize=13)
ax1.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.0f%%'))
ax1.legend(fontsize=10, loc='upper left')
ax1.set_xlim(2003.5, 2023.5)
ax1.xaxis.set_major_locator(ticker.MultipleLocator(4))
ax1.xaxis.set_major_formatter(ticker.FormatStrFormatter('%d'))

# Panel 2: Gender keyword count
for label, cbsa_set, color, marker, ls in [
    ('High gender-keyword-change metros', high_dei, '#2171B5', 'o', '-'),
    ('Low gender-keyword-change metros', low_dei, '#D62728', '^', '--'),
]:
    sub = dei_cbsa_yr[dei_cbsa_yr['cbsa_code'].isin(cbsa_set) & dei_cbsa_yr['fyear'].between(2004, 2023)]
    yearly = sub.groupby('fyear')['gender_word_count'].mean().reset_index()
    ax2.plot(yearly['fyear'], yearly['gender_word_count'],
             color=color, marker=marker, markersize=6, linestyle=ls, linewidth=2.2, label=label)

ax2.axvspan(FORM_AP, 2023.5, alpha=0.10, color='gray', zorder=0)
ax2.text((FORM_AP + 2023.5) / 2, 0.02, 'Post Form AP', ha='center', va='bottom',
         fontsize=10, color='gray', fontstyle='italic', transform=ax2.get_xaxis_transform())
ax2.set_xlabel('Year', fontsize=12)
ax2.set_ylabel('Mean Gender Word Count', fontsize=12)
ax2.set_title('Gender Keyword Count by Metro Group', fontsize=13)
ax2.legend(fontsize=10, loc='upper left')
ax2.set_xlim(2003.5, 2023.5)
ax2.xaxis.set_major_locator(ticker.MultipleLocator(4))
ax2.xaxis.set_major_formatter(ticker.FormatStrFormatter('%d'))

fig.tight_layout()
out = f"{figures_dir}/mechanism_variation_metro.png"
fig.savefig(out, dpi=300, bbox_inches='tight')
plt.close()
print(f"\nSaved: {out}")
print("\nALL DONE")
