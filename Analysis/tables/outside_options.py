"""
Produces: LaTeX/Tables/destinationQualityPost.tex
Destination quality analysis for Big 4 audit leavers.
Tests whether female leavers experience different outcomes post-Form AP.
DV1: Salary % change at next job
DV2: Log gap days between jobs
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import numpy as np
import pandas as pd

from shared.paths import tables_dir
from shared.stata_setup import init_stata
from shared.data_loader import load_b4_stata
from shared.latex_utils import format_latex

stata = init_stata()

print("Creating destinationQualityPost.tex")

# Load data -- destination quality variables already computed in pipeline
df = load_b4_stata()

# Filter to leavers (retained==0 in their last year, with valid exit year)
last_years = df.sort_values(['userid', 'year']).groupby('userid').tail(1)
leavers = last_years[(last_years['retained'] == 0) &
                      (last_years['year'] <= 2023)].copy()
leavers = leavers.rename(columns={'year': 'exit_year', 'auditorkey': 'aud_firm'})

print(f"  Leavers: {len(leavers):,}")
print(f"  with valid salary: {leavers['salary_pct_change'].notna().sum():,}")
print(f"  with valid gap: {leavers['log_gap'].notna().sum():,}")
print(f"  Female: {leavers['female'].sum():,} ({100*leavers['female'].mean():.1f}%)")

# Prepare Stata data
stata_cols = ['userid', 'female', 'exit_year',
              'salary_pct_change', 'log_gap',
              'post_formap', 'female_post',
              'masterorhigher', 'api', 'black', 'other',
              'aud_firm', 'yearfirst']
stata_df = leavers[stata_cols].copy()
for col in stata_df.columns:
    stata_df[col] = pd.to_numeric(stata_df[col], errors='coerce').astype('float64')
stata_df = stata_df.replace([np.inf, -np.inf], np.nan)
stata_df = stata_df.dropna(subset=['userid', 'female', 'exit_year', 'aud_firm',
                                    'yearfirst', 'masterorhigher', 'api', 'black', 'other'])

stata.pdataframe_to_data(stata_df, force=True)

fe_spec_post = 'female_post female post_formap masterorhigher api black other'

print("\nRunning Model 1: DV = Salary % Change...")
stata.run(
    f'reghdfe salary_pct_change {fe_spec_post} if salary_pct_change != ., '
    'absorb(aud_firm ib2000.exit_year yearfirst) vce(robust) version(5)',
    quietly=True
)
stata.run('estadd scalar n_employees = e(N)', quietly=True)
stata.run('estadd local fetypes "F,Y,C"', quietly=True)
stata.run('estadd local controls "Yes"', quietly=True)
stata.run('est store dest_sal_post', quietly=True)

print("Running Model 2: DV = Log Gap Days...")
stata.run(
    f'reghdfe log_gap {fe_spec_post} if log_gap != ., '
    'absorb(aud_firm ib2000.exit_year yearfirst) vce(robust) version(5)',
    quietly=True
)
stata.run('estadd scalar n_employees = e(N)', quietly=True)
stata.run('estadd local fetypes "F,Y,C"', quietly=True)
stata.run('estadd local controls "Yes"', quietly=True)
stata.run('est store dest_gap_post', quietly=True)

print("\nGenerating LaTeX table...")
stata.run(
    rf'''
esttab dest_sal_post dest_gap_post ///
    using "{tables_dir}/destinationQualityPost.tex", ///
    replace ///
    label ///
    b(%9.3f) se(%9.3f) ///
    star(* 0.10 ** 0.05 *** 0.01) ///
    nogaps ///
    order(female_post female) ///
    drop(masterorhigher api black other post_formap) ///
    stats(N n_employees r2_a controls fetypes, fmt(%12.0fc %12.0fc %12.3f) labels("Observations" "Unique employees" "Adjusted R-squared" "Controls" "Fixed effects")) ///
    booktabs ///
    alignment(D{{.}}{{.}}{{-1}}) ///
    nonotes ///
    mtitles("\shortstack{{Leavers w/ Next Job\\ DV = Salary \% Change}}" ///
            "\shortstack{{Leavers w/ Next Job\\ DV = Log Gap Days}}")''',
    quietly=True
)

format_latex(f"{tables_dir}/destinationQualityPost.tex")

print(f"\nSaved {tables_dir}/destinationQualityPost.tex")
