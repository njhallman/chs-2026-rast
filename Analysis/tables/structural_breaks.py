"""
Structural-break tests for the female retention/promotion gap. The resulting
statistics are quoted in the Section 3.1 narrative; this script produces no
table. It also writes diagnostics/supWaldScan.png, a scan plot that is a
diagnostic only and does not appear in the paper.
  1. Full-model Chow test at the known 2015 (Form AP) break: Post-2015
     interacted with all slopes AND break-spanning fixed effects (strict,
     i.e., the separate-models equivalent) and with slopes only. Robust
     (clustered) Wald versions.
  2. Unknown-date sup-Wald (Andrews 1993, partial structural change in the
     female coefficient, p=1) scan over candidate break years. Headline.
  3. OLS-CUSUM and single-break sup-Wald on the annual adjusted gap series.
  4. Bai-Perron procedure on the same series, by the book: UDmax/WDmax
     (0 vs unknown number of breaks), sequential F to select the number,
     then break-date estimation with confidence intervals.
Also prints baseline retention/promotion rates by gender pre-2010 vs post-2015
(editor point 5).
Requires: Stata, revB4AudStata
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import numpy as np
import pandas as pd

from shared.paths import REPO_DIR
from shared.stata_setup import init_stata
from shared.data_loader import load_b4_stata
from shared.benchmark_utils import extract_coefs

stata = init_stata()

CONTROLS = 'masterorhigher top_university api black other'
FE = 'absorb(auditorkey ib2000.year yearfirst) vce(cluster userid) version(5)'
SERIES_START = 1990          # first year of the annual gap series
SERIES_END = 2023
BREAK_YEAR = 2015            # known candidate break (Form AP, post_formap)
SCAN_START, SCAN_END = 1995, 2018  # ~15% trimming of 1990-2023
PROMO_IF = 'if badrankdummy == 0 & positionrank < 6 & retained == 1'

# Andrews (1993) asymptotic critical values, sup-Wald, 1 restriction, 15% trim
ANDREWS_CV = {'10%': 7.12, '5%': 8.68, '1%': 12.16}

print("=" * 80)
print("STRUCTURAL BREAK TESTS: female retention/promotion gap")
print("=" * 80)

df = load_b4_stata()

# Annual female x year interactions (female_pre absorbs years before the
# series start so the dummies partition the sample and no main effect enters)
years = list(range(SERIES_START, SERIES_END + 1))
df['female_pre'] = df['female'] * (df['year'] < SERIES_START).astype(int)
for y in years:
    df[f'female_y{y}'] = df['female'] * (df['year'] == y).astype(int)
ANNUAL_STR = 'female_pre ' + ' '.join(f'female_y{y}' for y in years)

keep_cols = (['userid', 'year', 'retained', 'promo', 'female', 'auditorkey',
              'yearfirst', 'positionrank', 'badrankdummy', 'time_in_rank',
              'female_pre'] + CONTROLS.split() + [f'female_y{y}' for y in years])
stata.pdataframe_to_data(df[keep_cols], force=True)

results = {}

# ---------------------------------------------------------------------------
# 0. Baseline rates for economic significance (editor point 5)
# ---------------------------------------------------------------------------
print("\n--- Baseline rates (editor point 5) ---")
pre = df[(df.year >= 2000) & (df.year <= 2009)]
post = df[df.year >= BREAK_YEAR]
post16 = df[df.year >= 2016]
promo_mask = (df.badrankdummy == 0) & (df.positionrank < 6) & (df.retained == 1)
for label, sub in [('Retention pre-2010 (2000-09)', pre),
                   ('Retention post-Form AP (2015-23)', post),
                   ('Retention post-reversal (2016-23)', post16)]:
    m = sub[sub.female == 0]['retained'].mean() * 100
    f = sub[sub.female == 1]['retained'].mean() * 100
    print(f"  {label}: men {m:.1f}%, women {f:.1f}%, gap {f - m:+.2f}pp")
for label, yrs in [('Promotion pre-2010 (2000-09)', (2000, 2009)),
                   ('Promotion post-Form AP (2015-23)', (2015, 2023)),
                   ('Promotion post-reversal (2016-23)', (2016, 2023))]:
    sub = df[promo_mask & df.year.between(*yrs)]
    m = sub[sub.female == 0]['promo'].mean() * 100
    f = sub[sub.female == 1]['promo'].mean() * 100
    print(f"  {label}: men {m:.1f}%, women {f:.1f}%, gap {f - m:+.2f}pp")

# ---------------------------------------------------------------------------
# 1. Full-model Chow tests at the known 2015 break (memo only)
#    Strict version = separate-models equivalent: Post interacted with all
#    slopes, firm FE, and break-spanning cohort FE. Year FE are regime-
#    specific by construction (each year lies in one regime), so they have
#    no interaction to add; the intercept break is absorbed by year FE.
#    Robust clustered Wald, so regime variances need not be equal.
# ---------------------------------------------------------------------------
print(f"\n--- 1. Full-model Chow tests at known break ({BREAK_YEAR}) ---")
stata.run(f'capture drop post\ngen post = (year >= {BREAK_YEAR})', quietly=True)
ctrl_int = ' '.join(f'c.post#c.{c}' for c in CONTROLS.split())
for dv, cond, extra, tag in [('retained', '', '', 'ret'),
                             ('promo', PROMO_IF, 'time_in_rank', 'pro')]:
    extra_int = f'c.post#c.{extra}' if extra else ''
    slope_block = f'c.post#c.female {ctrl_int} {extra_int}'
    fe_block = 'i.post#i.auditorkey i.post#i.yearfirst'
    stata.run(
        f'reghdfe {dv} female {CONTROLS} {extra} {slope_block} {fe_block} '
        f'{cond}, {FE}', quietly=True)
    e = stata.get_ereturn()
    n_obs, n_emp = int(e['e(N)']), int(e['e(N_clust)'])
    for label, block in [('strict (slopes + firm/cohort FE)',
                          f'{slope_block} {fe_block}'),
                         ('slopes only', slope_block)]:
        try:
            stata.run(f'testparm {block}', quietly=True)
            r = stata.get_return()
            results[f'chow_{tag}_{label.split()[0]}'] = dict(
                F=float(r['r(F)']), p=float(r['r(p)']),
                df=int(r['r(df)']), N=n_obs, n_emp=n_emp)
            print(f"  {dv} Chow [{label}]: F({int(r['r(df)'])}, ...) = "
                  f"{float(r['r(F)']):.1f}, p = {float(r['r(p)']):.2e}")
        except Exception as ex:
            print(f"  {dv} Chow [{label}] FAILED: {ex}")

# ---------------------------------------------------------------------------
# 2. Sup-Wald (Quandt-Andrews) scan over candidate break years
# ---------------------------------------------------------------------------
print(f"\n--- 2. Sup-Wald scan over candidate breaks {SCAN_START}-{SCAN_END} ---")
scan = {'ret': {}, 'pro': {}}
for tau in range(SCAN_START, SCAN_END + 1):
    for dv, cond, extra, tag in [('retained', '', '', 'ret'),
                                 ('promo', PROMO_IF, 'time_in_rank', 'pro')]:
        stata.run(f'capture drop fpost\ngen fpost = female * (year >= {tau})',
                  quietly=True)
        stata.run(f'reghdfe {dv} female fpost {extra} {CONTROLS} {cond}, {FE}',
                  quietly=True)
        stata.run('test fpost', quietly=True)
        r = stata.get_return()
        scan[tag][tau] = float(r['r(F)'])
    print(f"  tau={tau}: F_ret={scan['ret'][tau]:8.2f}  F_pro={scan['pro'][tau]:8.2f}")

for tag in ['ret', 'pro']:
    best = max(scan[tag], key=scan[tag].get)
    results[f'supwald_{tag}'] = dict(break_year=best, supF=scan[tag][best])
    print(f"  -> {tag}: sup-F = {scan[tag][best]:.1f} at {best} "
          f"(Andrews 1% CV = {ANDREWS_CV['1%']})")

# ---------------------------------------------------------------------------
# 3. Annual adjusted gap series (female x year coefficients, full spec)
# ---------------------------------------------------------------------------
print("\n--- 3. Annual adjusted gap series ---")
series = {}
for dv, cond, extra, tag in [('retained', '', '', 'ret'),
                             ('promo', PROMO_IF, 'time_in_rank', 'pro')]:
    stata.run(f'reghdfe {dv} {ANNUAL_STR} {extra} {CONTROLS} {cond}, {FE}',
              quietly=True)
    coefs, ses = extract_coefs(stata, [f'female_y{y}' for y in years])
    series[tag] = pd.Series(coefs, index=years)
    series[f'{tag}_se'] = pd.Series(ses, index=years)
ann = pd.DataFrame({'year': years,
                    'gap_ret': series['ret'].values,
                    'se_ret': series['ret_se'].values,
                    'gap_pro': series['pro'].values,
                    'se_pro': series['pro_se'].values})
print(ann.round(4).to_string(index=False))

# ---------------------------------------------------------------------------
# 4. Time-series tests on the annual adjusted gap series
# ---------------------------------------------------------------------------
print("\n--- 4. Time-series tests on annual gap series ---")
stata.pdataframe_to_data(ann, force=True)
stata.run('tsset year', quietly=True)
def _clean(rdict):
    out = {}
    for k, v in rdict.items():
        try:
            out[k] = float(v)
        except (TypeError, ValueError):
            out[k] = str(v)
    return out


for tag, col in [('ret', 'gap_ret'), ('pro', 'gap_pro')]:
    # OLS-CUSUM (Ploberger-Kramer)
    stata.run(f'quietly regress {col}\nestat sbcusum, ols', quietly=True)
    r = stata.get_return()
    print(f"  [{tag}] estat sbcusum returns: { {k: v for k, v in r.items()} }")
    results[f'cusum_{tag}'] = _clean(r)
    # Single unknown break, sup-Wald with proper p-value
    stata.run(f'quietly regress {col}\nestat sbsingle, trim(15)', quietly=True)
    r = stata.get_return()
    print(f"  [{tag}] estat sbsingle returns: { {k: v for k, v in r.items()} }")
    results[f'sbsingle_{tag}'] = _clean(r)

# Bai-Perron procedure via xtbreak (install if needed), by the book:
#   (a) UDmax/WDmax: 0 breaks vs unknown number up to 3 (hypothesis(2))
#   (b) sequential F(s+1|s) to select the number of breaks
#   (c) estimate the selected break date(s) with 95% confidence intervals
print("\n--- 5. Bai-Perron procedure (xtbreak) ---")
def _run_xtbreak(cmd):
    """Run an xtbreak command, installing xtbreak + moremata on first failure."""
    try:
        stata.run(cmd)
    except Exception:
        print("  installing xtbreak + moremata from SSC...")
        for pkg in ['moremata', 'xtbreak']:
            try:
                stata.run(f'ssc install {pkg}, replace', quietly=True)
            except Exception as ex:
                print(f"  ssc install {pkg}: {ex}")
        stata.run(cmd)
    return stata.get_return()


for tag, col in [('ret', 'gap_ret'), ('pro', 'gap_pro')]:
    print(f"\n  ===== {tag} ({col}) =====")
    for cmd in [f'xtbreak test {col}, hypothesis(2) breaks(1 3) trimming(0.15) breakconstant',
                f'xtbreak test {col}, hypothesis(2) breaks(3) trimming(0.15) breakconstant']:
        try:
            r = _run_xtbreak(cmd)
            print(f"  [{tag}] UDmax r(): { {k: v for k, v in r.items()} }")
            results[f'bp_udmax_{tag}'] = _clean(r)
            break
        except Exception as ex:
            print(f"  [{tag}] UDmax attempt failed ({cmd}): {ex}")
    # Sequential selection of the number of breaks: supF(1|0), then F(s+1|s).
    # Note: hypothesis(3) breaks(s) tests "H0: s-1 vs H1: s breaks" (each
    # xtbreak printout states its H0/H1 explicitly).
    for lbl, cmd in [
            ('supF(1|0)', f'xtbreak test {col}, hypothesis(1) breaks(1) trimming(0.15) breakconstant'),
            ('F(2|1)', f'xtbreak test {col}, hypothesis(3) breaks(2) trimming(0.15) breakconstant'),
            ('F(3|2)', f'xtbreak test {col}, hypothesis(3) breaks(3) trimming(0.15) breakconstant')]:
        try:
            r = _run_xtbreak(cmd)
            print(f"  [{tag}] {lbl} r(): { {k: v for k, v in r.items()} }")
            results[f'bp_seq_{lbl}_{tag}'] = _clean(r)
        except Exception as ex:
            print(f"  [{tag}] {lbl} failed ({cmd}): {ex}")
    try:
        r = _run_xtbreak(f'xtbreak estimate {col}, breaks(1) trimming(0.15) breakconstant')
        print(f"  [{tag}] estimate r(): { {k: v for k, v in r.items()} }")
        e = stata.get_ereturn()
        print(f"  [{tag}] estimate e() keys: {sorted(e.keys())}")
        for k in sorted(e.keys()):
            v = e[k]
            if not hasattr(v, 'shape') or getattr(v, 'size', 99) < 30:
                print(f"      {k} = {v}")
        results[f'bp_est_{tag}'] = _clean(r)
    except Exception as ex:
        print(f"  [{tag}] estimate failed: {ex}")

# ---------------------------------------------------------------------------
# Figure: sup-Wald scan
# ---------------------------------------------------------------------------
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 4.5))
taus = sorted(scan['ret'])
ax.plot(taus, [scan['ret'][t] for t in taus], 'o-', color='#1f4e79',
        label='Retention')
ax.plot(taus, [scan['pro'][t] for t in taus], 's--', color='#a63603',
        label='Promotion (cond. on retention)')
ax.axhline(ANDREWS_CV['1%'], color='gray', linestyle=':',
           label=f"Andrews 1% critical value ({ANDREWS_CV['1%']})")
best_ret = max(scan['ret'], key=scan['ret'].get)
ax.axvline(best_ret, color='#1f4e79', alpha=0.25)
ax.set_xlabel('Candidate break year')
ax.set_ylabel('Wald F-statistic')
ax.legend(frameon=False)
ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout()
# Diagnostic output, not a paper figure -- kept out of LaTeX/Figures/ so that
# directory holds exactly the eight figures the manuscript includes.
_diag_dir = os.path.join(REPO_DIR, 'diagnostics')
os.makedirs(_diag_dir, exist_ok=True)
fig.savefig(os.path.join(_diag_dir, 'supWaldScan.png'), dpi=300)
print(f"\nSaved {os.path.join(_diag_dir, 'supWaldScan.png')}")

import json
print("\n=== RESULTS SUMMARY (JSON) ===")
print(json.dumps(results, indent=2, default=str))
print("\nALL DONE")
