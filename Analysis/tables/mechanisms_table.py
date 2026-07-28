"""
Produces: LaTeX/Tables/mechanismsTable.tex
Mechanisms analysis: 4 columns (3 individual + 1 three-way horse race).
All variables pre-computed in 07_prepare_data.py.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from shared.paths import tables_dir
from shared.stata_setup import init_stata
from shared.data_loader import load_b4_stata
from shared.latex_utils import format_latex

stata = init_stata()

print("Creating mechanismsTable.tex")

df = load_b4_stata()
df['year'] = df['year'].astype(int)

n = len(df)
n_ac = df['ac_fem_pct_sf'].notna().sum()
n_dei = df['dei_proportion_firm'].notna().sum()
n_both = (df['ac_fem_pct_sf'].notna() & df['dei_proportion_firm'].notna()).sum()
print(f"  Panel: {n:,} person-years")
print(f"  AC coverage: {n_ac:,} ({100*n_ac/n:.1f}%)")
print(f"  DEI coverage: {n_dei:,} ({100*n_dei/n:.1f}%)")
print(f"  Horse race (both + Form AP): {n_both:,} ({100*n_both/n:.1f}%)")

controls = 'masterorhigher top_university api black other'
fe = 'absorb(auditorkey ib2000.year yearfirst) vce(cluster userid) version(5)'
sample_both = 'if ac_fem_pct_sf != . & dei_proportion_firm != .'

stata.pdataframe_to_data(df, force=True)

# ── Col 1: AC Female % only ────────────────────────────────────────────
stata.run(
    f'reghdfe retained female_ac female ac_fem_pct_sf {controls} '
    f'if ac_fem_pct_sf != ., {fe}',
    quietly=True
)
stata.run('estadd scalar n_employees = e(N_clust)', quietly=True)
stata.run('estadd local fetypes "C,Y,E"', quietly=True)
stata.run('estadd local controls "Yes"', quietly=True)
stata.run('est store m1', quietly=True)

# ── Col 2: Gender Keywords only ────────────────────────────────────────
stata.run(
    f'reghdfe retained female_dei female dei_proportion_firm {controls} '
    f'if dei_proportion_firm != ., {fe}',
    quietly=True
)
stata.run('estadd scalar n_employees = e(N_clust)', quietly=True)
stata.run('estadd local fetypes "C,Y,E"', quietly=True)
stata.run('estadd local controls "Yes"', quietly=True)
stata.run('est store m2', quietly=True)

# ── Col 3: Post Form AP only ──────────────────────────────────────────
stata.run(
    f'reghdfe retained female_post_formap female post_formap {controls}, {fe}',
    quietly=True
)
stata.run('estadd scalar n_employees = e(N_clust)', quietly=True)
stata.run('estadd local fetypes "C,Y,E"', quietly=True)
stata.run('estadd local controls "Yes"', quietly=True)
stata.run('est store m3', quietly=True)

# ── Col 4: Three-way horse race ───────────────────────────────────────
stata.run(
    f'reghdfe retained female_ac female_dei female_post_formap '
    f'female ac_fem_pct_sf dei_proportion_firm post_formap {controls} '
    f'{sample_both}, {fe}',
    quietly=True
)
stata.run('estadd scalar n_employees = e(N_clust)', quietly=True)
stata.run('estadd local fetypes "C,Y,E"', quietly=True)
stata.run('estadd local controls "Yes"', quietly=True)
stata.run('est store m4', quietly=True)

# ── Output ─────────────────────────────────────────────────────────────
stata.run(
    rf'''
esttab m1 m2 m3 m4 ///
    using "{tables_dir}/mechanismsTable.tex", ///
    replace ///
    label ///
    b(%9.3f) se(%9.3f) ///
    star(* 0.10 ** 0.05 *** 0.01) ///
    nogaps ///
    order(female_ac ac_fem_pct_sf female_dei dei_proportion_firm ///
          female_post_formap post_formap female) ///
    drop({controls} post_formap _cons) ///
    stats(N n_employees r2_a controls fetypes, fmt(%12.0fc %12.0fc %12.3f) ///
        labels("Observations" "Unique employees" "Adjusted R-squared" "Controls" "Fixed effects")) ///
    booktabs ///
    alignment(D{{.}}{{.}}{{-1}}) ///
    nonotes ///
    nomtitles''',
    quietly=True
)

format_latex(f"{tables_dir}/mechanismsTable.tex")

# Fix mechanism-specific variable labels
_path = f"{tables_dir}/mechanismsTable.tex"
with open(_path, 'r') as f:
    _tex = f.read()
_tex = _tex.replace(r'\FEMALE\_ac', r'\FEMALE\ $\times$ AC Female \%')
_tex = _tex.replace(r'\FEMALE\_dei', r'\FEMALE\ $\times$ Gender Keywords')
_tex = _tex.replace(r'ac\_fem\_pct\_sf', r'AC Female \%')
_tex = _tex.replace(r'dei\_proportion\_firm', r'Gender Keywords')
with open(_path, 'w') as f:
    f.write(_tex)

print(f"\nSaved {_path}")
