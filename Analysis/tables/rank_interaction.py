"""
Produces: LaTeX/Tables/rankInteraction.tex
Rank-level retention & promotion analysis: Female × Post Form AP × Rank interactions.
Columns: (1) DV = Retained, (2) DV = Promoted
Includes post-period net female gap (lincom of 3-way + 2-way) with significance stars.
Requires: Stata, revB4AudStata
"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import pandas as pd

from shared.paths import tables_dir
from shared.stata_setup import init_stata
from shared.data_loader import load_b4_stata
from shared.latex_utils import format_latex

stata = init_stata()

print("Creating rankInteraction.tex")

df = load_b4_stata()

# Drop observations with bad rank data
df_ranked = df[df['badrankdummy'] == 0].copy()

controls = 'masterorhigher top_university api black other'
fe = 'absorb(auditorkey ib2000.year yearfirst) vce(cluster userid) version(5)'
regressors = ('female_post_staff female_post_senior female_post_mgrplus '
              'female_staff female_senior female_mgrplus '
              'post_senior post_mgrplus female senior mgrplus post_formap time_in_rank')
keep = ('female_post_staff female_post_senior female_post_mgrplus '
        'female_staff female_senior female_mgrplus _cons')


def star(p):
    if p < 0.01:
        return r'\sym{***}'
    elif p < 0.05:
        return r'\sym{**}'
    elif p < 0.10:
        return r'\sym{*}'
    return '         '


def get_lincom(rank):
    """Run lincom and return (coef, se, p) from Stata's r() values."""
    stata.run(f'lincom female_post_{rank} + female_{rank}', quietly=True)
    r = stata.get_return()
    return float(r['r(estimate)']), float(r['r(se)']), float(r['r(p)'])


# --- Column 1: Retention ---
print("  Running retention model...")
stata.pdataframe_to_data(df_ranked, force=True)
stata.run(f'reghdfe retained {regressors} {controls}, {fe}', quietly=True)

ret_sums = {}
for rank in ['staff', 'senior', 'mgrplus']:
    ret_sums[rank] = get_lincom(rank)

stata.run('estadd scalar n_employees = e(N_clust)', quietly=True)
stata.run('estadd local fetypes "C,Y,E"', quietly=True)
stata.run('estadd local controls "Yes"', quietly=True)
stata.run('est store m_ret', quietly=True)

# --- Column 2: Promotion ---
print("  Running promotion model...")
df_pro = df_ranked[(df_ranked['positionrank'] < 6) & (df_ranked['retained'] == 1)].copy()
stata.pdataframe_to_data(df_pro, force=True)
stata.run(f'reghdfe promo {regressors} {controls}, {fe}', quietly=True)

pro_sums = {}
for rank in ['staff', 'senior', 'mgrplus']:
    pro_sums[rank] = get_lincom(rank)

stata.run('estadd scalar n_employees = e(N_clust)', quietly=True)
stata.run('estadd local fetypes "C,Y,E"', quietly=True)
stata.run('estadd local controls "Yes"', quietly=True)
stata.run('est store m_pro', quietly=True)

# --- Generate base table via esttab ---
print("  Writing table...")
outpath = f"{tables_dir}/rankInteraction.tex"
stata.run(
    rf'''
esttab m_ret m_pro ///
    using {outpath}, ///
    replace ///
    label ///
    b(%9.3f) se(%9.3f) ///
    star(* 0.10 ** 0.05 *** 0.01) ///
    nogaps ///
    keep({keep}) ///
    order(female_post_staff female_post_senior female_post_mgrplus female_staff female_senior female_mgrplus _cons) ///
    stats(N n_employees r2_a controls fetypes, fmt(%12.0fc %12.0fc %12.3f) ///
        labels("Observations" "Unique employees" "Adjusted R-squared" "Controls" "Fixed effects")) ///
    booktabs ///
    alignment(D{{.}}{{.}}{{-1}}) ///
    nonotes ///
    mtitles("\shortstack{{DV = Retained}}" ///
            "\shortstack{{DV = Promoted}}")''',
    quietly=True
)

# Apply standard formatting (variable names)
format_latex(outpath)

# --- Post-process: variable names + lincom panel ---
with open(outpath, 'rt') as f:
    tex = f.read()

# Variable name substitutions (format_latex handles 'female' → \FEMALE but not
# the compound interaction names)
tex = tex.replace(r'\FEMALExPOST\_staff', r'\FEMALE\ $\times$ Post Form AP $\times$ Staff')
tex = tex.replace(r'\FEMALExPOST\_senior', r'\FEMALE\ $\times$ Post Form AP $\times$ Senior')
tex = tex.replace(r'\FEMALExPOST\_mgrplus', r'\FEMALE\ $\times$ Post Form AP $\times$ Manager+')
tex = tex.replace(r'\FEMALE\_staff', r'\FEMALE\ $\times$ Staff')
tex = tex.replace(r'\FEMALE\_senior', r'\FEMALE\ $\times$ Senior')
tex = tex.replace(r'\FEMALE\_mgrplus', r'\FEMALE\ $\times$ Manager+')

# Build lincom panel in D{.}{.}{-1} stacked format (coeff row, then SE row)
def fmt_coef(coef, p):
    """Format a coefficient for D-column layout."""
    return f"      {coef:.3f}{star(p)}"

def fmt_se(se):
    """Format an SE for D-column layout."""
    return f"     ({se:.3f})         "

lincom_lines = []
ncols = 2 + 1  # 2 models × 1 D-col + label col = 3
lincom_lines.append(rf"\multicolumn{{{ncols}}}{{l}}{{\textit{{Post-period net female gap (sum of 3-way + 2-way):}}}}\\[4pt]")
for label, rank in [('Staff', 'staff'), ('Senior', 'senior'), ('Manager+', 'mgrplus')]:
    rc, rse, rp = ret_sums[rank]
    pc, pse, pp_ = pro_sums[rank]
    lincom_lines.append(
        rf"\quad {label}         &{fmt_coef(rc, rp)}&{fmt_coef(pc, pp_)}\\"
    )
    lincom_lines.append(
        rf"                    &{fmt_se(rse)}&{fmt_se(pse)}\\"
    )
lincom_panel = "\n".join(lincom_lines)

# Insert lincom panel before the stats midrule (the last \midrule before Observations)
obs_idx = tex.index('Observations')
midrule_idx = tex.rindex(r'\midrule', 0, obs_idx)
tex = tex[:midrule_idx] + r'\midrule' + '\n' + lincom_panel + '\n' + tex[midrule_idx:]

with open(outpath, 'wt') as f:
    f.write(tex)

print(f"Saved {outpath}")
