"""
Produces: LaTeX/Tables/robustnessModels.tex
Robustness checks: Cox proportional hazards + location fixed effects.
Requires: Stata, revB4AudStata
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import pandas as pd
from shared.paths import tables_dir
from shared.stata_setup import init_stata
from shared.data_loader import load_b4_stata
from shared.latex_utils import format_latex

stata = init_stata()

print("Creating robustnessModels.tex")

revB4AudStata = load_b4_stata()
revB4AudStata['university_id'] = pd.Categorical(revB4AudStata['university_name']).codes + 1

controls = 'top_university masterorhigher api black other'

stata.pdataframe_to_data(revB4AudStata, force=True)

# ── Cox proportional hazards ──────────────────────────────────────────────────
stata.run('stset time, id(userid) failure(termination)', quietly=True)
stata.run(
    f'stcox female_post female post_formap {controls} '
    'i.auditorkey i.year, vce(robust)',
    quietly=True
)
stata.run('estadd scalar n_employees = e(N_clust)', quietly=True)

stata.run('estadd local fetypes "Y,E"', quietly=True)
stata.run('estadd local controls "Yes"', quietly=True)
stata.run('est store model_cox_1', quietly=True)

# ── Location fixed effects ────────────────────────────────────────────────────
stata.run(
    f'reghdfe retained female_post female post_formap {controls}, '
    'absorb(auditorkey yearfirst year##metro_area_code) vce(cluster userid) version(5)',
    quietly=True
)
stata.run('estadd scalar n_employees = e(N_clust)', quietly=True)

stata.run('estadd local fetypes "C,E,Y*M"', quietly=True)
stata.run('estadd local controls "Yes"', quietly=True)
stata.run('est store model_loc_1', quietly=True)

# ── Output LaTeX table ────────────────────────────────────────────────────────
stata.run(
    rf'''
esttab model_cox_1 model_loc_1 ///
    using {f"{tables_dir}/robustnessModels.tex"}, ///
    replace ///
    label ///
    b(%9.3f) se(%9.3f) ///
    star(* 0.10 ** 0.05 *** 0.01) ///
    nogaps ///
    keep(female_post female _cons) ///
    order(female_post female _cons) ///
    stats(N n_employees r2_a controls fetypes, fmt(%12.0fc %12.0fc %12.3f) ///
        labels("Observations" "Unique employees" "Adjusted R-squared" "Controls" "Fixed effects")) ///
    booktabs ///
    alignment(D{{.}}{{.}}{{-1}}) ///
    nonotes ///
    mtitles("\shortstack{{Auditors\\ DV = Hazard}}" ///
            "\shortstack{{Auditors\\ DV = Retained}}")''',
    quietly=True
)

format_latex(f"{tables_dir}/robustnessModels.tex")
print(f"Saved {tables_dir}/robustnessModels.tex")
