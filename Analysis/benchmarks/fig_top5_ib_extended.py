"""
Figure: benchmarkBB5IB.png
BB5 Investment Banking vs Big 4 Audit coefficient plot with FS Professional overlays.
Uses the standard 11-period structure (pre-2004 baseline) matching the main paper.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from shared.stata_setup import init_stata
stata = init_stata()

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from shared.benchmark_utils import (
    CONTROLS, BB5_MAPPING, BB5_KEYS, PERIODS, PERIOD_LABELS, SHORT_LABELS, PERIOD_STR,
    extract_coefs, build_ib_panel, build_top100_fs_panel,
    add_period_dummies, school_mapping,
)
from shared.data_loader import load_b4_stata
from shared.r2 import ensure_data_file
from shared.paths import figures_dir


# ── B4 Audit ─────────────────────────────────────────────────────────────────
print("Running B4 Audit regression...")
b4 = load_b4_stata()
add_period_dummies(b4, year_col='year')
n_aud = b4['userid'].nunique()
print(f"  B4 Audit: {len(b4):,} obs, {n_aud:,} users")
stata.pdataframe_to_data(b4, force=True)
del b4
stata.run(
    f'reghdfe retained {PERIOD_STR} {CONTROLS}, '
    'absorb(auditorkey ib2000.year yearfirst) vce(cluster userid) version(5)',
    quietly=True
)
coef_aud, se_aud = extract_coefs(stata, PERIODS)

print("\nB4 Audit coefficients:")
for i, p in enumerate(PERIOD_LABELS):
    print(f"  {p:<12} {coef_aud[i]:+.4f} (se={se_aud[i]:.4f})")


# ── BB5 Investment Banks ─────────────────────────────────────────────────────
print("\nBuilding BB5 IB panel...")
panel_bb5 = build_ib_panel(stata, BB5_MAPPING, BB5_KEYS, "BB5 (GS, MS, JPM, BofA, Citi)")
add_period_dummies(panel_bb5)
n_bb5 = panel_bb5['userid'].nunique()
stata.run('capture frame change default\ncapture frame drop _t5', quietly=True)
stata.pdataframe_to_frame(panel_bb5, '_t5')
stata.run(f'''
frame change _t5
reghdfe retained {PERIOD_STR} {CONTROLS}, absorb(firmkey ib2000.year yearfirst) vce(cluster userid) version(5)
''', quietly=True)
coef_t5, se_t5 = extract_coefs(stata, PERIODS)
stata.run('capture frame change default\ncapture frame drop _t5', quietly=True)
del panel_bb5

print("\nBB5 IB coefficients:")
for i, p in enumerate(PERIOD_LABELS):
    print(f"  {p:<12} {coef_t5[i]:+.4f} (se={se_t5[i]:.4f})")


# ── FS Professional overlays ────────────────────────────────────────────────
PROFESSIONAL_ROLES = [
    'financial planning analyst', 'financial analyst fp a', 'financial planning analysis',
    'equity research analyst', 'investment banking analyst', 'quantitative analyst',
    'equity analyst', 'equity research', 'financial reporting', 'financial reporting analyst',
    'actuarial', 'actuarial analyst', 'finance controller', 'commercial finance',
    'portfolio analyst', 'financial planning', 'investment analyst',
    'mergers acquisitions', 'capital markets', 'investment banking',
    'actuary', 'business controller', 'pricing analyst',
]
EXCLUDE_PATTERNS = [
    'deloitte', 'pricewaterhousecoopers', 'pwc', 'ernst & young', 'ernst and young',
    'kpmg', 'arthur andersen',
    'rsm ', 'bdo ', 'grant thornton', 'baker tilly', 'cliftonlarsonallen',
    'crowe', 'plante moran', 'moss adams', 'mazars', 'marcum', 'forvis',
    'internal revenue', 'h&r block', 'h & r block',
    'securities and exchange commission', 'sec ', 'fdic',
    'coldwell banker', 'cbre', 're/max', 'keller williams',
    'self-employed', 'self employed', 'freelance',
]

def _exclude(name):
    if pd.isna(name): return True
    nl = name.lower()
    if nl in ('ey', 'e & y') or nl.startswith('ey '): return True
    return any(p in nl for p in EXCLUDE_PATTERNS)

def _build_fs(df, roles, rcids, label):
    raw = df[(df['role_k1500'].isin(roles)) & (df['ultimate_parent_rcid'].isin(rcids))].copy()
    raw = raw.sort_values(['user_id', 'ultimate_parent_rcid', 'startdate'])
    raw['new_spell'] = ((raw['user_id'] != raw['user_id'].shift(1)) |
                        (raw['ultimate_parent_rcid'] != raw['ultimate_parent_rcid'].shift(1))).fillna(True).astype(int)
    raw['spell_id'] = raw['new_spell'].cumsum()
    raw['spell_startdate'] = raw.groupby('spell_id')['startdate'].transform('min')
    raw['spell_enddate'] = raw.groupby('spell_id')['enddate'].transform('max')
    raw = raw.drop_duplicates(['user_id', 'spell_id'], keep='last')
    raw['position_year'] = raw.apply(lambda r: list(range(r['spell_startdate'].year, r['spell_enddate'].year + 1)), axis=1)
    p = raw[['user_id','ultimate_parent_rcid','sex_predicted','ethnicity_predicted',
             'spell_startdate','spell_enddate','position_year','degree','university_name']
           ].explode('position_year', ignore_index=True)
    p['position_year'] = p['position_year'].astype(int)
    p = p.sort_values(['user_id','position_year','spell_enddate']).drop_duplicates(['user_id','position_year'], keep='last')
    p = p[p['position_year'] <= 2023]
    p['userid'] = p['user_id']; p['year'] = p['position_year']
    p['retained'] = (p['spell_enddate'].dt.year > p['year']).fillna(False).astype(int)
    p['female'] = (p['sex_predicted'] == 'F').astype(int)
    p['yearfirst'] = p['spell_startdate'].dt.year
    eth = p['ethnicity_predicted'].fillna('')
    p['api'] = (eth == 'API').astype(int); p['black'] = (eth == 'Black').astype(int)
    p['other'] = (~eth.isin(['White','API','Black','Hispanic',''])).astype(int)
    p['university_name'] = p['university_name'].apply(lambda x: school_mapping.get(x,'other') if pd.notna(x) else 'other')
    p['masterorhigher'] = p['degree'].isin(['Master','MBA','Doctor']).fillna(False).astype(int)
    p['top_university'] = (p['university_name'] != 'other').astype(int)
    add_period_dummies(p)
    rcid_k = {r: i+1 for i, r in enumerate(sorted(p['ultimate_parent_rcid'].unique()))}
    p['firmkey'] = p['ultimate_parent_rcid'].map(rcid_k)
    n = p['userid'].nunique()
    print(f"  {label}: {len(p):,} obs, {n:,} users, {p['firmkey'].nunique()} firms")
    return p, n

print("\nLoading FS data...")
df_fs = pd.read_feather(ensure_data_file('interim/revOtherFs.feather'))
df_fs['startdate'] = pd.to_datetime(df_fs['startdate'], errors='coerce')
df_fs['enddate'] = pd.to_datetime(df_fs['enddate'], errors='coerce')
df_fs = df_fs[df_fs['startdate'].notna() & (df_fs['startdate'] <= df_fs['enddate'])]
df_fs = df_fs[df_fs['highest_degree'].isin(['Bachelor','Master','MBA','Doctor'])]
df_fs = df_fs[~df_fs['title_raw'].str.contains('intern', case=False, na=False)]
df_fs = df_fs[df_fs['ultimate_parent_rcid'].notna()]
df_fs = df_fs[~df_fs['company_raw'].apply(_exclude)]
sub = df_fs[df_fs['role_k1500'].isin(PROFESSIONAL_ROLES)]
firm_ranks = sub.groupby('ultimate_parent_rcid')['user_id'].nunique().sort_values(ascending=False)

fs_results = {}
for label, n_firms in [('Top 50', 50)]:
    print(f"\nBuilding {label} FS Professional panel...")
    rcids = set(firm_ranks.head(n_firms).index)
    panel, n_u = _build_fs(df_fs, PROFESSIONAL_ROLES, rcids, label)
    fname = f'_fs{n_firms}'
    stata.run(f'capture frame change default\ncapture frame drop {fname}', quietly=True)
    stata.pdataframe_to_frame(panel, fname)
    stata.run(f'''
frame change {fname}
reghdfe retained {PERIOD_STR} {CONTROLS}, absorb(firmkey ib2000.year yearfirst) vce(cluster userid) version(5)
''', quietly=True)
    c, s = extract_coefs(stata, PERIODS)
    stata.run(f'capture frame change default\ncapture frame drop {fname}', quietly=True)
    del panel
    fs_results[label] = (c, s, n_u)
    print(f"  {label} coefficients: {[f'{v:+.4f}' for v in c]}")
del df_fs


# ── Helper to draw a single benchmark panel ──────────────────────────────────
x = np.arange(len(PERIODS))
post_idx = PERIOD_LABELS.index('2014-15')

def draw_benchmark(ax, coef_bench, se_bench, bench_label, bench_color, bench_marker,
                   n_bench, diff_label):
    ax.errorbar(x, coef_aud, yerr=se_aud,
                color='#2171B5', marker='o', markersize=9, linestyle='-', linewidth=2.5,
                capsize=4, capthick=1.2, label=f'Big 4 Audit (n={n_aud:,})', zorder=5)
    ax.errorbar(x, coef_bench, yerr=se_bench,
                color=bench_color, marker=bench_marker, markersize=9, linestyle='--', linewidth=2.5,
                capsize=4, capthick=1.2, label=f'{bench_label} (n={n_bench:,})', zorder=4)
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, zorder=1)
    ax.axvspan(post_idx - 0.5, len(PERIODS) - 0.5, alpha=0.10, color='gray', zorder=0)
    ax.text((post_idx - 0.5 + len(PERIODS) - 0.5) / 2, 0.02, 'Post Form AP',
            ha='center', va='bottom', fontsize=10, color='gray', fontstyle='italic',
            transform=ax.get_xaxis_transform())
    ax.set_xlabel('Period', fontsize=14, labelpad=28)
    ax.set_ylabel('Female \u00d7 Period coefficient\n(effect on retention probability)', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(SHORT_LABELS, fontsize=11)
    ax.tick_params(axis='y', labelsize=12)
    ax.legend(fontsize=12)

    # Significance strip
    z_diff = [(ca - cb) / np.sqrt(sa**2 + sb**2)
              for ca, cb, sa, sb in zip(coef_aud, coef_bench, se_aud, se_bench)]
    for xi, z in zip(x, z_diff):
        if abs(z) > 2.576:
            sym = '***'
        elif abs(z) > 1.960:
            sym = '**'
        elif abs(z) > 1.645:
            sym = '*'
        else:
            continue
        ax.annotate(sym, xy=(xi, 0), xycoords=('data', 'axes fraction'),
                    xytext=(0, -42), textcoords='offset points',
                    ha='center', va='top', fontsize=9, color='#222222',
                    annotation_clip=False)
    ax.annotate(f'*p\u202f<\u202f0.10\u2003 **p\u202f<\u202f0.05\u2003 ***p\u202f<\u202f0.01\u2003 ({diff_label})',
                xy=(0.5, 0), xycoords='axes fraction',
                xytext=(0, -78), textcoords='offset points',
                ha='center', va='top', fontsize=8.5, color='#555555',
                annotation_clip=False)


# ── Figure 1: Big 4 Audit vs BB5 Investment Banks ───────────────────────────
fig1, ax1 = plt.subplots(figsize=(13, 7))
draw_benchmark(ax1, coef_t5, se_t5, 'BB5 Investment Banks', '#D62728', '^',
               n_bb5, 'audit vs. IB difference')
fig1.tight_layout()
out1 = os.path.join(figures_dir, 'benchmarkBB5IB.png')
fig1.savefig(out1, dpi=300, bbox_inches='tight')
print(f"\nSaved: {out1}")
plt.close(fig1)

# ── Figure 2: Big 4 Audit vs Top 50 FS Professionals ────────────────────────
for label, (c, s, n_u) in fs_results.items():
    fig2, ax2 = plt.subplots(figsize=(13, 7))
    draw_benchmark(ax2, c, s, f'FS Prof. {label}', '#888888', 's',
                   n_u, 'audit vs. FS difference')
    fig2.tight_layout()
    out2 = os.path.join(figures_dir, 'benchmarkOFS.png')
    fig2.savefig(out2, dpi=300, bbox_inches='tight')
    print(f"Saved: {out2}")
    plt.close(fig2)

print("\nALL DONE")
