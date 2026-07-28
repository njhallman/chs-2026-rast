"""
Produces: LaTeX/Tables/mainB4Table.tex
Table 3 (Main): Big 4 Auditors with 11 biennial female x period interactions
(pre-2004 baseline through 2022-23).
Requires: Stata, processed B4 audit data
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from shared.paths import tables_dir
from shared.stata_setup import init_stata
from shared.data_loader import load_b4_stata
from shared.latex_utils import format_latex
from shared.benchmark_utils import add_period_dummies, PERIOD_STR as PERIOD_STR11

stata = init_stata()
CONTROLS = 'masterorhigher top_university api black other'

print("=" * 80)
print("TABLE 3 (MAIN): Big 4 Auditors — 11 Periods (pre-2004 baseline)")
print("=" * 80)

b4_main = load_b4_stata()
old_periods_main = [c for c in b4_main.columns if c.startswith('female_') and c != 'female']
b4_main = b4_main.drop(columns=old_periods_main)
b4_main = add_period_dummies(b4_main)

stata.pdataframe_to_data(b4_main, force=True)
stata.run(
    f'reghdfe retained {PERIOD_STR11} {CONTROLS}, '
    'absorb(auditorkey ib2000.year yearfirst) vce(cluster userid) version(5)',
    quietly=True
)
stata.run('estadd scalar n_employees = e(N_clust)', quietly=True)
stata.run('estadd local fetypes "C,Y,E"', quietly=True)
stata.run('est store model_main_b4', quietly=True)
print(f"  B4 Audit (11 periods): {len(b4_main):,} obs")
del b4_main

stata.run(
    rf'''
esttab model_main_b4 ///
    using {f"{tables_dir}/mainB4Table.tex"}, ///
    replace ///
    label ///
    b(%9.3f) se(%9.3f) ///
    star(* 0.10 ** 0.05 *** 0.01) ///
    nogaps ///
    stats(N n_employees r2_a fetypes, fmt(%12.0fc %12.0fc %12.3f) labels("Observations" "Unique employees" "Adjusted R-squared" "Fixed effects")) ///
    booktabs ///
    alignment(D{{.}}{{.}}{{-1}}) ///
    nonotes ///
    mtitles("\shortstack{{Big 4 Auditors\\ DV = Retained}}")''',
    quietly=True
)

format_latex(f"{tables_dir}/mainB4Table.tex")

# Widen label column, reduce font size, add shading to 2014-15 row
with open(f"{tables_dir}/mainB4Table.tex", 'r') as f:
    lines = f.readlines()
# Find the FEMALExXIVtoXV line and shade it + the following SE line
for i, line in enumerate(lines):
    if r'\FEMALExXIVtoXV' in line:
        lines[i] = r'\rowcolor{gray!15}' + line
        if i + 1 < len(lines):
            lines[i + 1] = r'\rowcolor{gray!15}' + lines[i + 1]
        break
_t = ''.join(lines)
_t = _t.replace('{l*{', '{p{10cm}*{', 1)
_t = '{\\small\n' + _t + '\n}'
with open(f"{tables_dir}/mainB4Table.tex", 'w') as f:
    f.write(_t)

print(f"\nSaved {tables_dir}/mainB4Table.tex")
print("\nALL DONE")
