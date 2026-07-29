"""
Regenerate every table and figure in the paper.

Each entry below names the output(s) it must produce. A script that exits
non-zero, or that leaves an output file untouched, is reported as a failure --
so a silent no-op cannot be mistaken for a successful run.

Prerequisites: the processed panels must already exist (see
Analysis/pipeline/README.md), and Stata with reghdfe/estout must be installed
for the regression tables (see SETUP.md).

Usage:
    python Analysis/run_all.py            # run everything
    python Analysis/run_all.py --tables   # tables only
    python Analysis/run_all.py --figures  # figures only
    python Analysis/run_all.py --in-text  # in-text statistics only

Each script can also be run individually, e.g.:
    python Analysis/tables/extended_period_tables.py

Afterwards, compare against the published outputs with:
    python Analysis/verify_outputs.py
"""
import sys, os, subprocess, argparse, time, json

_dir = os.path.dirname(os.path.abspath(__file__))
_repo = os.path.dirname(_dir)
_tables_dir = os.path.join(_repo, 'LaTeX', 'Tables')
_figures_dir = os.path.join(_repo, 'LaTeX', 'Figures')

# Records which outputs this run actually regenerated, so verify_outputs.py can
# tell "regenerated and identical" from "left over from a previous checkout".
# Without it, a script that fails to run still shows as passing verification.
MANIFEST_PATH = os.path.join(_repo, '.run_manifest.json')


def _outputs_for(names):
    """Resolve output filenames to absolute paths under LaTeX/."""
    paths = []
    for name in names:
        base = _tables_dir if name.endswith('.tex') else _figures_dir
        paths.append(os.path.join(base, name))
    return paths


def run(script_path, outputs):
    """Run one script; return (ok, message).

    A script must exit 0 AND rewrite every file it declares. Outputs are
    stat-ed before and after, so a script that fails to write is caught even
    when it exits cleanly.
    """
    rel = os.path.relpath(script_path, _repo)
    label = ', '.join(outputs) if outputs else '(no file output)'
    print(f"\n{'='*60}")
    print(f"  Running: {rel}")
    print(f"{'='*60}")

    paths = _outputs_for(outputs)
    before = {p: (os.path.getmtime(p) if os.path.exists(p) else None) for p in paths}

    t0 = time.time()
    result = subprocess.run([sys.executable, script_path], cwd=_repo)
    elapsed = time.time() - t0

    if result.returncode != 0:
        print(f"  {label}: FAILED (exit code {result.returncode})  ({elapsed:.0f}s)")
        return False, f"{label}: exit code {result.returncode}"

    stale = []
    for p in paths:
        if not os.path.exists(p):
            stale.append(f"{os.path.basename(p)} not created")
        elif before[p] is not None and os.path.getmtime(p) <= before[p]:
            stale.append(f"{os.path.basename(p)} not rewritten")
    if stale:
        print(f"  {label}: FAILED ({'; '.join(stale)})  ({elapsed:.0f}s)")
        return False, f"{label}: {'; '.join(stale)}"

    print(f"  {label}: OK  ({elapsed:.0f}s)")
    return True, None


# ── The paper's 12 tables ───────────────────────────────────────────────────
TABLE_SCRIPTS = [
    # Descriptive
    (os.path.join(_dir, 'tables', 'sample_design.py'),           ['sampleDesign.tex']),
    (os.path.join(_dir, 'tables', 'summary_stats.py'),           ['summaryStats.tex']),
    # Main results
    (os.path.join(_dir, 'tables', 'extended_period_tables.py'),  ['mainB4Table.tex']),
    (os.path.join(_dir, 'tables', 'mechanisms_table.py'),        ['mechanismsTable.tex']),
    (os.path.join(_dir, 'tables', 'outside_options.py'),         ['destinationQualityPost.tex']),
    (os.path.join(_dir, 'tables', 'rank_interaction.py'),        ['rankInteraction.tex']),
    (os.path.join(_dir, 'tables', 'robustness_models.py'),       ['robustnessModels.tex']),
    # Appendix
    (os.path.join(_dir, 'tables', 'roles_table.py'),             ['rolesTable.tex']),
    (os.path.join(_dir, 'tables', 'firm_names.py'),              ['firmNamesTable.tex']),
    (os.path.join(_dir, 'tables', 'top_companies.py'),           ['topCompanies.tex']),
    (os.path.join(_dir, 'tables', 'nonb4_firms.py'),             ['nonB4FirmsTable.tex']),
    (os.path.join(_dir, 'tables', 'variable_definitions.py'),    ['VariableDefinitions.tex']),
]

# ── The paper's 8 figures ───────────────────────────────────────────────────
FIGURE_SCRIPTS = [
    (os.path.join(_dir, 'figures', 'stack_plot.py'),                ['stackPlot.png']),
    (os.path.join(_dir, 'figures', 'mechanism_variation_metro.py'), ['mechanism_variation_metro.png']),
    (os.path.join(_dir, 'figures', 'retention_gap_map.py'),         ['retentionGapMap.png']),
    (os.path.join(_dir, 'figures', 'supply_vs_entry.py'),           ['supplyVsEntry.png']),
    # Benchmark comparisons
    (os.path.join(_dir, 'benchmarks', 'fig_top5_ib_extended.py'),   ['benchmarkBB5IB.png', 'benchmarkOFS.png']),
    (os.path.join(_dir, 'benchmarks', 'fig_at_combined.py'),        ['benchmarkATCombined.png']),
    (os.path.join(_dir, 'benchmarks', 'fig_b4_nonaudit.py'),        ['benchmarkB4Tax.png']),
]

# ── Statistics quoted in the text, with no table or figure output ───────────
# These reproduce published claims and print their results to stdout.
IN_TEXT_SCRIPTS = [
    (os.path.join(_dir, 'tables', 'structural_breaks.py'), []),   # sup-Wald / Chow, Section 3.1
    (os.path.join(_dir, 'tables', 'time_to_rank.py'),      []),   # median time-to-rank, Introduction
]


def main():
    parser = argparse.ArgumentParser(description='Regenerate all paper outputs.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--tables',  action='store_true', help='Run table scripts only')
    group.add_argument('--figures', action='store_true', help='Run figure scripts only')
    group.add_argument('--in-text', action='store_true', help='Run in-text statistic scripts only')
    args = parser.parse_args()

    if args.tables:
        scripts = TABLE_SCRIPTS
    elif args.figures:
        scripts = FIGURE_SCRIPTS
    elif args.in_text:
        scripts = IN_TEXT_SCRIPTS
    else:
        scripts = TABLE_SCRIPTS + FIGURE_SCRIPTS + IN_TEXT_SCRIPTS

    failures = []
    regenerated = {}
    t_start = time.time()

    for script_path, outputs in scripts:
        ok, message = run(script_path, outputs)
        if not ok:
            failures.append(message)
        for name in outputs:
            regenerated[name] = ok

    # Merge into any existing manifest so partial runs (--tables, --figures)
    # accumulate rather than discarding what the other pass established.
    manifest = {'outputs': {}}
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH) as f:
                manifest = json.load(f)
        except Exception:
            manifest = {'outputs': {}}
    manifest.setdefault('outputs', {})
    for name, ok in regenerated.items():
        manifest['outputs'][name] = {'regenerated': ok, 'at': time.time()}
    manifest['updated'] = time.time()
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    total = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"  Ran {len(scripts)} scripts in {total/60:.1f} min")
    if failures:
        print(f"  {len(failures)} FAILED:")
        for message in failures:
            print(f"    - {message}")
        sys.exit(1)
    print("  All scripts completed successfully.")
    print("  Next: python Analysis/verify_outputs.py")


if __name__ == '__main__':
    main()
