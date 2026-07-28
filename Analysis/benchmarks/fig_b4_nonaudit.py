"""
Figure: benchmarkB4NonAudit.png
B4 Audit vs B4 Tax (Big 4 non-audit practice lines).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from shared.stata_setup import init_stata
stata = init_stata()

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from shared.benchmark_utils import (
    PERIODS, PERIOD_LABELS, SHORT_LABELS, CONTROLS, PERIOD_STR,
    AUDIT_FIRM_MAPPING, AUDIT_FIRM_KEYS,
    school_mapping, extract_coefs, add_period_dummies, run_b4_audit_regression,
)
from shared.r2 import ensure_data_file
from shared.paths import data_dir, figures_dir

print("Running B4 Audit regression...")
coef_aud, se_aud, n_aud = run_b4_audit_regression(stata)

print("\nBuilding B4 Tax panel...")
nonaudit_roles = ['tax', 'tax accountant', 'tax analyst', 'tax consultant']
na_dfs = []
for role in nonaudit_roles:
    path = ensure_data_file(f"raw/revelio/revelioPosUsr_role_{role}.feather")
    df_role = pd.read_feather(path)
    df_role['aud_firm'] = df_role['company_raw'].map(AUDIT_FIRM_MAPPING)
    na_dfs.append(df_role[df_role['aud_firm'].notna()].copy())
na_raw = pd.concat(na_dfs, ignore_index=True)
na_raw['female'] = (na_raw['sex_predicted'] == 'F').astype(int)
eth_na = na_raw['ethnicity_predicted'].fillna('')
na_raw['api'] = (eth_na == 'API').astype(int)
na_raw['black'] = (eth_na == 'Black').astype(int)
na_raw['other'] = (~eth_na.isin(['White', 'API', 'Black', 'Hispanic', ''])).astype(int)
na_raw['startdate'] = pd.to_datetime(na_raw['startdate'], errors='coerce')
na_raw['enddate'] = pd.to_datetime(na_raw['enddate'], errors='coerce')
na_raw = na_raw[(na_raw['country'] == 'United States') & (na_raw['startdate'].notna())].copy()
na_raw['start_year'] = na_raw['startdate'].dt.year.clip(lower=1990)
na_raw['end_year'] = na_raw['enddate'].dt.year.fillna(2024).astype(int).clip(upper=2024)
na_raw = na_raw[(na_raw['end_year'] - na_raw['start_year'] + 1) > 0]

na_exp = na_raw[['user_id', 'aud_firm', 'female', 'api', 'black', 'other',
                  'start_year', 'end_year']].copy()
na_exp['position_year'] = [list(range(s, e+1)) for s, e in zip(na_exp['start_year'], na_exp['end_year'])]
na_panel = na_exp.explode('position_year', ignore_index=True)
na_panel['position_year'] = na_panel['position_year'].astype(int)
na_panel = na_panel.sort_values(['user_id', 'position_year', 'start_year']).drop_duplicates(
    subset=['user_id', 'position_year'], keep='last')
yf = na_panel.groupby('user_id')['position_year'].min().reset_index().rename(
    columns={'position_year': 'yearfirst'})
na_panel = na_panel.merge(yf, on='user_id')
nxt = na_panel[['user_id', 'position_year']].copy()
nxt['position_year'] = nxt['position_year'] - 1
nxt['retained'] = 1
na_panel = na_panel.merge(nxt, on=['user_id', 'position_year'], how='left')
na_panel['retained'] = na_panel['retained'].fillna(0).astype(int)
na_panel = na_panel[na_panel['position_year'] <= 2023].copy()

# Education
edu_raw_na = pd.read_feather(ensure_data_file("raw/revelio/revelioEdu_role_combined.feather"))
edu_raw_na = edu_raw_na[edu_raw_na['user_id'].isin(set(na_panel['user_id'].unique()))].copy()
edu_raw_na = edu_raw_na[edu_raw_na['degree'].isin(['Bachelor', 'Master', 'MBA', 'Doctor'])].copy()
edu_raw_na['degree_rank'] = edu_raw_na['degree'].map({'Doctor': 4, 'MBA': 3, 'Master': 2, 'Bachelor': 1})
edu_raw_na['enddate'] = pd.to_datetime(edu_raw_na['enddate'], errors='coerce').fillna(pd.to_datetime('2025-10-01'))
edu_na = (edu_raw_na.sort_values(['user_id', 'degree_rank', 'enddate'], ascending=[False, True, True])
          .groupby('user_id').tail(1)[['user_id', 'university_name', 'degree']])
edu_na['university_name'] = edu_na['university_name'].apply(lambda x: school_mapping.get(x, 'other'))
na_panel = na_panel.merge(edu_na, on='user_id', how='left')
na_panel['masterorhigher'] = na_panel['degree'].isin(['Master', 'MBA', 'Doctor']).fillna(False).astype(int)
na_panel['top_university'] = (na_panel['university_name'] != 'other').fillna(False).astype(int)

na_panel['auditorkey'] = na_panel['aud_firm'].map(AUDIT_FIRM_KEYS)
na_panel['year'] = na_panel['position_year']
na_panel['userid'] = na_panel['user_id'].astype('category').cat.codes + 1
add_period_dummies(na_panel)
n_b4tax = na_panel['user_id'].nunique()
print(f"  B4 Tax: {len(na_panel):,} obs, {n_b4tax:,} users")

stata.pdataframe_to_data(na_panel, force=True)
stata.run(
    f'reghdfe retained {PERIOD_STR} {CONTROLS}, '
    'absorb(auditorkey ib2000.year yearfirst) vce(cluster userid) version(5)',
    quietly=True
)
coef_na, se_na = extract_coefs(stata, PERIODS)

print("\nB4 Tax coefficients:")
for i, p in enumerate(PERIOD_LABELS):
    t = abs(coef_na[i] / se_na[i])
    stars = '***' if t > 2.576 else '**' if t > 1.96 else '*' if t > 1.645 else ''
    print(f"  {p:<12} {coef_na[i]:+.4f}{stars}")

x = np.arange(len(PERIODS))
fig3, ax3 = plt.subplots(figsize=(12, 7))

ax3.errorbar(x, coef_aud, yerr=se_aud,
             color='#2171B5', marker='o', markersize=9, linestyle='-', linewidth=2.5,
             capsize=4, capthick=1.2, label=f'Big 4 Audit (n={n_aud:,})', zorder=5)
ax3.errorbar(x, coef_na, yerr=se_na,
             color='#6BAED6', marker='s', markersize=8, linestyle='--', linewidth=2.5,
             capsize=4, capthick=1.2, label=f'Big 4 Tax (n={n_b4tax:,})', zorder=4)

ax3.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, zorder=1)
post_idx = PERIOD_LABELS.index('2014-15')
ax3.axvspan(post_idx - 0.5, len(PERIODS) - 0.5, alpha=0.10, color='gray', zorder=0)
ax3.text((post_idx - 0.5 + len(PERIODS) - 0.5) / 2, 0.02, 'Post Form AP', ha='center', va='bottom',
         fontsize=10, color='gray', fontstyle='italic', transform=ax3.get_xaxis_transform())
ax3.set_xlabel('Period', fontsize=14, labelpad=28)
ax3.set_ylabel('Female \u00d7 Period coefficient\n(effect on retention probability)', fontsize=14)
ax3.set_xticks(x)
ax3.set_xticklabels(SHORT_LABELS, fontsize=12)
ax3.tick_params(axis='y', labelsize=12)
ax3.legend(fontsize=12)

# Significance test: z-test on difference of two independent estimates
# H0: beta_audit == beta_tax; z = (b_aud - b_tax) / sqrt(se_aud^2 + se_tax^2)
z_diff = [(ca - ct) / np.sqrt(sa**2 + st**2)
          for ca, ct, sa, st in zip(coef_aud, coef_na, se_aud, se_na)]

for xi, z in zip(x, z_diff):
    if abs(z) > 2.576:
        sym = '***'
    elif abs(z) > 1.960:
        sym = '**'
    elif abs(z) > 1.645:
        sym = '*'
    else:
        continue
    ax3.annotate(sym, xy=(xi, 0), xycoords=('data', 'axes fraction'),
                 xytext=(0, -42), textcoords='offset points',
                 ha='center', va='top', fontsize=9, color='#222222',
                 annotation_clip=False)

ax3.annotate('*p\u202f<\u202f0.10\u2003 **p\u202f<\u202f0.05\u2003 ***p\u202f<\u202f0.01\u2003 (audit vs. tax difference)',
             xy=(0.5, 0), xycoords='axes fraction',
             xytext=(0, -78), textcoords='offset points',
             ha='center', va='top', fontsize=8.5, color='#555555',
             annotation_clip=False)

fig3.tight_layout()

out_path = os.path.join(figures_dir, 'benchmarkB4Tax.png')
fig3.savefig(out_path, dpi=300, bbox_inches='tight')
print(f"\nSaved: {out_path}")
plt.close()

print("\nALL DONE")
