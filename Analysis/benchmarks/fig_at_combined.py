"""
Figure: benchmarkATCombined.png
Two-panel figure: B4 Audit vs Annually Inspected AT (left) and vs Other AT (right).
Uses the 9-period NB4 structure to accommodate smaller early-period samples.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from shared.stata_setup import init_stata
stata = init_stata()

import numpy as np
import matplotlib.pyplot as plt

from shared.benchmark_utils import (
    NB4_PERIODS, NB4_PERIOD_LABELS, NB4_SHORT_LABELS, CONTROLS, NB4_PERIOD_STR,
    extract_coefs, run_b4_audit_regression, build_nonb4_audit_panel,
)
from shared.paths import figures_dir

# ── Shared regressions ──────────────────────────────────────────────────────
print("Running B4 Audit regression (NB4 period structure)...")
coef_aud_nb, se_aud_nb, n_aud = run_b4_audit_regression(stata, nb4=True)

print("\nBuilding Non-B4 Audit panel...")
nonb4_panel_all, ANNUAL_AT, OTHER_AT = build_nonb4_audit_panel()

# ── Annually inspected AT ───────────────────────────────────────────────────
sub_ann = nonb4_panel_all[nonb4_panel_all['at_firm'].isin(ANNUAL_AT)].copy()
sub_ann['auditorkey'] = sub_ann['at_firm'].astype('category').cat.codes + 1
n_ann = sub_ann['user_id'].nunique()
print(f"\n  Annually Inspected AT: {len(sub_ann):,} obs, {n_ann:,} users")

stata.pdataframe_to_data(sub_ann, force=True)
stata.run(
    f'reghdfe retained {NB4_PERIOD_STR} {CONTROLS}, '
    'absorb(auditorkey ib2000.year yearfirst) vce(cluster userid) version(5)',
    quietly=True
)
coefs_ann, ses_ann = extract_coefs(stata, NB4_PERIODS)

# ── Other AT ────────────────────────────────────────────────────────────────
sub_oth = nonb4_panel_all[nonb4_panel_all['at_firm'].isin(OTHER_AT)].copy()
sub_oth['auditorkey'] = sub_oth['at_firm'].astype('category').cat.codes + 1
n_oth = sub_oth['user_id'].nunique()
print(f"  Other AT Firms: {len(sub_oth):,} obs, {n_oth:,} users")

stata.pdataframe_to_data(sub_oth, force=True)
stata.run(
    f'reghdfe retained {NB4_PERIOD_STR} {CONTROLS}, '
    'absorb(auditorkey ib2000.year yearfirst) vce(cluster userid) version(5)',
    quietly=True
)
coefs_oth, ses_oth = extract_coefs(stata, NB4_PERIODS)

# ── Combined two-panel figure ───────────────────────────────────────────────
x_nb = np.arange(len(NB4_PERIODS))
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

# Helper to draw one panel
def draw_panel(ax, coefs_bench, ses_bench, bench_label, bench_color, bench_marker, n_bench):
    ax.errorbar(x_nb, coef_aud_nb, yerr=se_aud_nb,
                color='#2171B5', marker='o', markersize=7, linestyle='-', linewidth=2.2,
                capsize=3, capthick=1, label=f'Big 4 Audit (n={n_aud:,})', zorder=5)
    ax.errorbar(x_nb, coefs_bench, yerr=ses_bench,
                color=bench_color, marker=bench_marker, markersize=7, linestyle='--', linewidth=2.2,
                capsize=3, capthick=1, label=f'{bench_label} (n={n_bench:,})', zorder=4)
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, zorder=1)
    post_idx = NB4_PERIOD_LABELS.index('2014-15')
    ax.axvspan(post_idx - 0.5, len(NB4_PERIOD_LABELS) - 0.5, alpha=0.10, color='gray', zorder=0)
    ax.text((post_idx - 0.5 + len(NB4_PERIOD_LABELS) - 0.5) / 2, 0.02, 'Post Form AP', ha='center', va='bottom',
            fontsize=9, color='gray', fontstyle='italic', transform=ax.get_xaxis_transform())
    ax.set_xlabel('Period', fontsize=12)
    ax.set_xticks(x_nb)
    ax.set_xticklabels(NB4_SHORT_LABELS, fontsize=9, rotation=45, ha='right')
    ax.tick_params(axis='y', labelsize=10)
    ax.legend(fontsize=9, loc='upper left')

    # Significance stars for difference
    z_diff = [(ca - cb) / np.sqrt(sa**2 + sb**2)
              for ca, cb, sa, sb in zip(coef_aud_nb, coefs_bench, se_aud_nb, ses_bench)]
    for xi, z in zip(x_nb, z_diff):
        if abs(z) > 2.576:
            sym = '***'
        elif abs(z) > 1.960:
            sym = '**'
        elif abs(z) > 1.645:
            sym = '*'
        else:
            continue
        ax.annotate(sym, xy=(xi, 0), xycoords=('data', 'axes fraction'),
                    xytext=(0, -36), textcoords='offset points',
                    ha='center', va='top', fontsize=8, color='#222222',
                    annotation_clip=False)

# Left panel: Annually Inspected AT
draw_panel(ax1, coefs_ann, ses_ann, 'Annually Inspected AT', '#FF7F0E', '^', n_ann)
ax1.set_ylabel('Female \u00d7 Period coefficient\n(effect on retention probability)', fontsize=11)
ax1.set_title('Big 4 Audit vs. Annually Inspected AT', fontsize=12)

# Right panel: Other AT
draw_panel(ax2, coefs_oth, ses_oth, 'Other AT Firms', '#2CA02C', 's', n_oth)
ax2.set_title('Big 4 Audit vs. Other AT Firms', fontsize=12)

fig.tight_layout()
out_path = os.path.join(figures_dir, 'benchmarkATCombined.png')
fig.savefig(out_path, dpi=300, bbox_inches='tight')
print(f"\nSaved: {out_path}")
plt.close()

print("\nALL DONE")
