"""
Figure: supplyVsEntry.png
Overlays IPEDS accounting bachelor's graduate % female (US News top accounting programs)
with Big 4 new hire % female, showing that supply-side gender composition does not explain
the decline in female entry to Big 4 audit.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from shared.data_loader import load_b4_stata
from shared.paths import figures_dir, data_dir

IPEDS_CACHE = os.path.join(data_dir, 'raw', 'ipeds')
YEARS = range(2000, 2024)


def load_ipeds_csv(path):
    """Load an IPEDS CSV, fixing the BOM on the first column."""
    df = pd.read_csv(path, encoding='latin-1', low_memory=False)
    df = df.rename(columns={df.columns[0]: df.columns[0].replace('\xc3\xaf\xc2\xbb\xc2\xbf', '').replace('\ufeff', '').strip()})
    return df


# ── Top University set (24 schools, matches top_university variable in regressions)
TOP_UNIV_UNITIDS = {
    230038, 211440, 190150, 190415, 198419, 166027, 151351, 166683,
    193900, 147767, 204796, 186131, 243744, 110635, 144050, 145637,
    170976, 199120, 152080, 215062, 123961, 228778, 234076, 130794,
}

# ── US News Top 10 Accounting Programs (Francis, Golshan, and Hallman 2023)
USNEWS_ACCT_UNITIDS = {
    228778,  # University of Texas at Austin
    230038,  # Brigham Young University-Provo
    145637,  # University of Illinois Urbana-Champaign
    151351,  # Indiana University-Bloomington
    152080,  # University of Notre Dame
    170976,  # University of Michigan-Ann Arbor
    215062,  # University of Pennsylvania
    123961,  # University of Southern California
    193900,  # New York University
    204796,  # Ohio State University-Main Campus
}

# ── Parse IPEDS completions: Bachelor's accounting from top programs ────────
print("Parsing IPEDS completions (bachelor's, US News top accounting)...")
ipeds_results = []
for year in YEARS:
    cache_path = os.path.join(IPEDS_CACHE, f'C{year}_A.csv')
    if not os.path.exists(cache_path):
        continue
    df = load_ipeds_csv(cache_path)
    df.columns = [c.upper().strip() for c in df.columns]

    cip_mask = df['CIPCODE'].astype(str).str.strip() == '52.0301'
    level_mask = df['AWLEVEL'].astype(int) == 5  # Bachelor's only
    if 'MAJORNUM' in df.columns:
        major_mask = df['MAJORNUM'] == 1
    else:
        major_mask = pd.Series(True, index=df.index)
    acct = df[cip_mask & major_mask & level_mask]
    for tier_name, tier_unitids in [('TopUniv', TOP_UNIV_UNITIDS), ('USNews', USNEWS_ACCT_UNITIDS), ('AllSchools', None)]:
        tier_acct = acct if tier_unitids is None else acct[acct['UNITID'].isin(tier_unitids)]
        if 'CTOTALM' in tier_acct.columns:
            m = pd.to_numeric(tier_acct['CTOTALM'], errors='coerce').fillna(0).sum()
            w = pd.to_numeric(tier_acct['CTOTALW'], errors='coerce').fillna(0).sum()
        elif 'CRACE15' in tier_acct.columns:
            m = pd.to_numeric(tier_acct['CRACE15'], errors='coerce').fillna(0).sum()
            w = pd.to_numeric(tier_acct['CRACE16'], errors='coerce').fillna(0).sum()
        else:
            continue
        if (m + w) > 0:
            ipeds_results.append({
                'year': year, 'tier': tier_name,
                'men': int(m), 'women': int(w), 'total': int(m + w),
                'pct_female': w / (m + w) * 100,
            })
    continue  # skip the old single-tier code below

    if 'CTOTALM' in acct.columns:
        acct = acct.copy()
        acct['men'] = pd.to_numeric(acct['CTOTALM'], errors='coerce').fillna(0)
        acct['women'] = pd.to_numeric(acct['CTOTALW'], errors='coerce').fillna(0)
    elif 'CRACE15' in acct.columns:
        acct = acct.copy()
        acct['men'] = pd.to_numeric(acct['CRACE15'], errors='coerce').fillna(0)
        acct['women'] = pd.to_numeric(acct['CRACE16'], errors='coerce').fillna(0)
    else:
        continue

    m = acct['men'].sum()
    w = acct['women'].sum()
    if (m + w) > 0:
        ipeds_results.append({
            'year': year,
            'men': int(m),
            'women': int(w),
            'total': int(m + w),
            'pct_female': w / (m + w) * 100,
        })

ipeds_panel = pd.DataFrame(ipeds_results)
print(f"  Years: {ipeds_panel['year'].min()}-{ipeds_panel['year'].max()}, avg {ipeds_panel['total'].mean():.0f} grads/year")

# ── Big 4 entry data ────────────────────────────────────────────────────────
print("Loading Big 4 entry data (fresh WRDS pull)...")
fresh_path = os.path.join(data_dir, 'raw', 'revelio', 'fresh_b4_auditor_entry.csv')
if os.path.exists(fresh_path):
    fresh = pd.read_csv(fresh_path)
    fresh['entry_year'] = pd.to_numeric(fresh['entry_year'], errors='coerce')
    fresh = fresh[(fresh['entry_year'] >= 2000) & (fresh['entry_year'] <= 2025)]
    b4_yr = fresh.groupby('entry_year').agg(
        n_total=('user_id', 'count'),
        n_female=('female', 'sum'),
    ).reset_index().rename(columns={'entry_year': 'yearfirst'})
    b4_yr['pct_female'] = b4_yr['n_female'] / b4_yr['n_total'] * 100
    print(f"  Fresh data: {len(fresh):,} users, {fresh['entry_year'].min()}-{fresh['entry_year'].max()}")
else:
    print("  Fresh data not found, falling back to processed data")
    b4 = load_b4_stata()
    entry = b4.drop_duplicates('userid', keep='first')[['userid', 'yearfirst', 'female']].copy()
    entry = entry[(entry['yearfirst'] >= 2000) & (entry['yearfirst'] <= 2023)]
    b4_yr = entry.groupby('yearfirst').agg(
        n_total=('userid', 'count'),
        n_female=('female', 'sum'),
    ).reset_index()
    b4_yr['pct_female'] = b4_yr['n_female'] / b4_yr['n_total'] * 100
b4_yr['se'] = np.sqrt(b4_yr['pct_female'] * (100 - b4_yr['pct_female']) / b4_yr['n_total'])

# ── Print comparison ─────────────────────────────────────────────────────────
print("\n% Female comparison:")
print(f"{'Year':>6} {'IPEDS':>10} {'B4 Hires':>10} {'Gap':>8}")
for year in range(2000, 2024):
    ip = ipeds_panel[ipeds_panel['year'] == year]
    b4r = b4_yr[b4_yr['yearfirst'] == year]
    ip_pf = f"{ip['pct_female'].iloc[0]:.1f}" if len(ip) else "n/a"
    b4_pf = f"{b4r['pct_female'].iloc[0]:.1f}" if len(b4r) else "n/a"
    if len(ip) and len(b4r):
        gap = f"{ip['pct_female'].iloc[0] - b4r['pct_female'].iloc[0]:+.1f}"
    else:
        gap = "n/a"
    print(f"{year:>6} {ip_pf:>9}% {b4_pf:>9}% {gap:>7}")

# ── Plot ─────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 6))

b4_yr_plot = b4_yr[b4_yr['yearfirst'] >= 2000].copy()
ax.errorbar(b4_yr_plot['yearfirst'], b4_yr_plot['pct_female'],
            yerr=b4_yr_plot['se'],
            color='#2171B5', marker='o', markersize=7, linewidth=2.5,
            capsize=3, capthick=1.2, elinewidth=1.2,
            label='Big 4 Audit New Hires')

ipeds_topuniv = ipeds_panel[(ipeds_panel['tier'] == 'TopUniv') & (ipeds_panel['year'] >= 2000)]
ax.plot(ipeds_topuniv['year'], ipeds_topuniv['pct_female'],
        color='#333333', marker='s', markersize=6, linewidth=2.0, linestyle='--',
        label="IPEDS: Top University Acct. Graduates")

ipeds_all = ipeds_panel[(ipeds_panel['tier'] == 'AllSchools') & (ipeds_panel['year'] >= 2000)]
ax.plot(ipeds_all['year'], ipeds_all['pct_female'],
        color='#999999', marker='^', markersize=5, linewidth=1.5, linestyle=':',
        label="IPEDS: All U.S. Acct. Graduates")

ax.axhline(y=50, color='gray', linestyle=':', linewidth=0.8, alpha=0.5)

ax.set_xlabel('Year', fontsize=13)
ax.set_ylabel('% Female', fontsize=13)
ax.set_ylim(30, 65)
ax.set_xticks(range(2000, 2024, 2))
ax.set_xticklabels([str(y) for y in range(2000, 2024, 2)], rotation=45, fontsize=10)
ax.set_xlim(1999.5, 2023.5)
ax.tick_params(axis='y', labelsize=11)
ax.legend(fontsize=10.5, loc='upper right')

fig.tight_layout()
out_path = os.path.join(figures_dir, 'supplyVsEntry.png')
fig.savefig(out_path, dpi=300, bbox_inches='tight')
print(f"\nSaved: {out_path}")
plt.close()
