"""
Computes time-to-rank descriptives (RAST cond. accept, editor point 6): how long
it takes staff-entry auditors to reach senior / manager / senior manager /
partner, by five-year entry-cohort window and gender. The medians are disclosed
in the manuscript introduction as an in-text note (the editor asked for tangible
stats, not a table); this script prints them and produces no table output.

Right-censoring: the sample ends in SAMPLE_END (2023). A (cohort, rank) cell is
reported if the cohort's earliest entrants can be observed over the rank's
horizon (cohort_first_year + HORIZONS[rank] <= SAMPLE_END); otherwise it is
suppressed ("--"). Panel B shares are computed only over entrants observed for
the full horizon. This is why the most recent cohort (2015--2019) reports senior
and manager but not senior manager. Partner is omitted from the table (too few
attainers in any one cohort for a cohort-by-gender comparison); its pooled median
(14--15 years, nearly identical by gender) is reported in the manuscript text.
  Panel A: mean (median) years from entry to rank, among attainers.
  Panel B: share reaching the rank within a fixed horizon.
Requires: revB4AudStata (no Stata needed)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import numpy as np
import pandas as pd

from shared.data_loader import load_b4_stata

RANKS = [('Senior', 2), ('Manager', 3), ('Senior Manager', 4), ('Partner', 6)]
HORIZONS = {'Senior': 3, 'Manager': 6, 'Senior Manager': 9, 'Partner': 13}
SAMPLE_END = 2023
# Entry-cohort windows (label, first_year, last_year). The 1990--1999 bucket is
# the pre-2000 partition; the analysis floors at 1990, where LinkedIn-era rank
# coverage becomes reliable.
COHORTS = [('1990--1999', 1990, 1999), ('2000--2004', 2000, 2004),
           ('2005--2009', 2005, 2009), ('2010--2014', 2010, 2014),
           ('2015--2019', 2015, 2019)]


def observable(cohort_last, rank_label):
    """Report a cohort x rank cell only if even the cohort's last entry year is
    observed over the rank's horizon."""
    return cohort_last + HORIZONS[rank_label] <= SAMPLE_END


print("=" * 80)
print("TIME-TO-RANK DESCRIPTIVES (staff-entry auditors)")
print("=" * 80)

df = load_b4_stata()
df = df[df.badrankdummy == 0]

# Staff entrants: first observed B4 year at staff rank
first = df.sort_values('year').groupby('userid').first()
staff_entry = first[first.positionrank == 1]
users = staff_entry.index
sub = df[df.userid.isin(users)]

# First year each user attains each rank threshold
attain = {}
for label, r in RANKS:
    attain[label] = sub[sub.positionrank >= r].groupby('userid')['year'].min()

base = pd.DataFrame({'female': staff_entry['female'],
                     'yearfirst': staff_entry['yearfirst']})
# Assign five-year cohort window; entrants outside 2000--2019 are excluded.
base['cohort'] = np.nan
for clab, a, b in COHORTS:
    base.loc[(base.yearfirst >= a) & (base.yearfirst <= b), 'cohort'] = clab
base = base[base.cohort.notna()]

print(f"\nStaff entrants 1990-2019 with clean ranks: {len(base):,} "
      f"({(base.female == 1).mean() * 100:.1f}% female)")
print(base.groupby(['cohort', 'female']).size().unstack().to_string())

# ---------------------------------------------------------------------------
# Panel A: mean (median) years from entry to rank among attainers, by cohort
# Panel B: share reaching rank within a fixed horizon, by cohort
# ---------------------------------------------------------------------------
attainer, share = {}, {}
for label, r in RANKS:
    a = attain[label].reindex(base.index)
    dur_all = a - base.yearfirst
    within = (a.notna() & (dur_all <= HORIZONS[label])).astype(float)
    for clab, ca, cb in COHORTS:
        for sex in [0, 1]:
            cohort_mask = (base.cohort == clab) & (base.female == sex)
            g = dur_all[cohort_mask & a.notna()]
            attainer[(clab, sex, label)] = (
                (g.mean(), g.median(), len(g)) if len(g) else (np.nan, np.nan, 0))
            # Panel B share is computed only over entrants observed for the full
            # horizon (so partially-observed cohorts use their observable members).
            obs_mask = cohort_mask & (base.yearfirst <= SAMPLE_END - HORIZONS[label])
            share[(clab, sex, label)] = (
                within[obs_mask].mean() * 100 if obs_mask.any() else np.nan)

# Console summary
for label, _ in RANKS:
    print(f"\n  {label}:")
    for clab, ca, cb in COHORTS:
        obs = observable(ca, label)
        a0, a1 = attainer[(clab, 0, label)], attainer[(clab, 1, label)]
        s0, s1 = share[(clab, 0, label)], share[(clab, 1, label)]
        dur = (f"dur M {a0[0]:.1f}({a0[1]:.0f}) W {a1[0]:.1f}({a1[1]:.0f})"
               if obs and a0[2] and a1[2] else "dur --")
        sh = (f"share M {s0:.1f}% W {s1:.1f}%"
              if obs and np.isfinite(s0) else "share --")
        print(f"    {clab}  obs={str(obs):5s}  {dur:34s}  {sh}  "
              f"(n attain {a0[2] + a1[2]:,})")

# Pooled partner timing (reported in the text, not the table)
ap = attain['Partner'].reindex(base.index)
dp = ap - base.yearfirst
pm, pw = dp[(base.female == 0) & ap.notna()], dp[(base.female == 1) & ap.notna()]
print(f"\nPooled partner (1990-2019 entrants): men {pm.mean():.1f} ({pm.median():.0f}) "
      f"n={len(pm)} | women {pw.mean():.1f} ({pw.median():.0f}) n={len(pw)}")

print("\nALL DONE. These statistics are disclosed in the manuscript introduction "
      "(in-text, per editor comment 6); this script produces no table.")
