"""
Produces: LaTeX/Tables/summaryStats.tex (Big 4 auditors)
Summary statistics with means, SDs, and t-tests by gender.
Requires: Stata, revB4AudStata
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import numpy as np
import pandas as pd
from shared.paths import tables_dir
from shared.stata_setup import init_stata
from shared.data_loader import load_b4_stata
from shared.latex_utils import add_tabular_environment, format_latex

stata = init_stata()

print("Creating summaryStats.tex (Big 4 auditors)")

df = load_b4_stata()
df.loc[df['badrankdummy'] == 1, 'promo'] = np.nan

stata.pdataframe_to_data(df, force=True)

VARS = 'retained promo post_formap top_university masterorhigher api black other ac_fem_pct_sf dei_proportion_firm salary_pct_change log_gap'

stata.run(f'eststo female : estpost sum {VARS} if female == 1', quietly=True)
stata.run('local N_female : display %12.0fc e(N)', quietly=True)
stata.run(f'eststo male : estpost sum {VARS} if female == 0', quietly=True)
stata.run('local N_male : display %12.0fc e(N)', quietly=True)
stata.run(f'eststo tot : estpost sum {VARS}', quietly=True)
stata.run('local N_tot : display %12.0fc e(N)', quietly=True)
stata.run(f'eststo diff : estpost ttest {VARS}, by(female) unequal', quietly=True)

stata.run(
    rf'''
esttab tot female male diff using {f"{tables_dir}/summaryStats.tex"}, replace nostar unstack label nonum f noobs nogaps booktabs ///
    mlabels("\hspace{{1.2mm}} Total (N = `N_tot') \hspace{{1.1mm}}" "\hspace{{1.2mm}} Female (N = `N_female') \hspace{{1.1mm}}" "\hspace{{1.2mm}} Male (N = `N_male') \hspace{{1.1mm}}" " \hspace{{1.1mm}} Difference  \hspace{{1.1mm}}") ///
    cells("mean(fmt(3) pattern(1 1 1 0)) p(fmt(3) pattern(0 0 0 1))" sd(fmt(3)par pattern(1 1 1 0)))
''', quietly=True)

add_tabular_environment(f"{tables_dir}/summaryStats.tex")
format_latex(f"{tables_dir}/summaryStats.tex")

# Fix mechanism-specific labels
_path = f"{tables_dir}/summaryStats.tex"
with open(_path, 'r') as f:
    _tex = f.read()
_tex = _tex.replace(r'ac\_fem\_pct\_sf', r'AC Female \%')
_tex = _tex.replace(r'dei\_proportion\_firm', r'Gender Keywords')
_tex = _tex.replace(r'salary\_pct\_change', r'Salary \% Change')
_tex = _tex.replace(r'log\_gap', r'Log Gap Days')
with open(_path, 'w') as f:
    f.write(_tex)

print(f"Saved {tables_dir}/summaryStats.tex")
