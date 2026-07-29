"""
Compare regenerated outputs against the published ones.

`reference/` holds the 12 tables and 8 figures exactly as they appear in the
accepted manuscript. This script re-checks what is currently in `LaTeX/Tables/`
and `LaTeX/Figures/` against them and prints a per-output verdict.

Tables are compared byte-for-byte after normalising trailing whitespace: an
identical regression produces an identical .tex.

Figures cannot be held to that standard: PNG output varies with the matplotlib,
freetype, and libpng versions in use even when the underlying data is identical,
so a byte difference does not imply a substantive one. But small automated
tolerances are not trustworthy either -- a visible line drawn clear across a
figure moves the mean per-pixel difference by only ~0.25 on a 0-255 scale, well
under any threshold loose enough to absorb font-rendering drift.

So figures are reported in three states rather than forced into pass/fail:

    PASS    byte-identical to the published figure
    REVIEW  differs; metrics and a diff image are produced for visual sign-off
    FAIL    differs grossly (different size, or a large share of pixels changed)

A fourth state applies to both tables and figures:

    STALE   the file matches, but run_all.py did not regenerate it in the last
            run -- so what is being compared is a leftover copy, not output. A
            failed script leaves the previous file in place, which would
            otherwise compare as identical and read as a pass.

REVIEW is not a pass. The run exits non-zero so that any figure which is not
byte-identical gets looked at, and `diffs/` shows exactly where the two
renderings disagree.

Usage:
    python Analysis/verify_outputs.py
    python Analysis/verify_outputs.py --tables
    python Analysis/verify_outputs.py --figures
    python Analysis/verify_outputs.py --diff-dir out/   # where diff images go
    python Analysis/verify_outputs.py --accept-review   # treat REVIEW as passing,
                                                        # once inspected

Exit status is 0 only if every table is identical and every figure is either
identical or an inspected-and-accepted REVIEW.
"""
import argparse
import json
import os
import sys

_dir = os.path.dirname(os.path.abspath(__file__))
_repo = os.path.dirname(_dir)
MANIFEST_PATH = os.path.join(_repo, '.run_manifest.json')

REFERENCE_TABLES = os.path.join(_repo, 'reference', 'tables')
REFERENCE_FIGURES = os.path.join(_repo, 'reference', 'figures')
CURRENT_TABLES = os.path.join(_repo, 'LaTeX', 'Tables')
CURRENT_FIGURES = os.path.join(_repo, 'LaTeX', 'Figures')

# A pixel counts as changed when any channel moves by more than this (0-255).
# Above 8, antialiasing jitter is excluded but a moved glyph or line is not.
PIXEL_CHANGE_THRESHOLD = 8

# Share of changed pixels above which a figure is a hard FAIL rather than a
# REVIEW. Font-rendering drift across library versions perturbs text pixels
# only; a redrawn series, axis, or panel changes far more of the canvas.
GROSS_CHANGE_PCT = 8.0

# Different matplotlib versions round figure dimensions slightly differently, so
# the same figure can come out a few pixels wider or shorter. Within this
# relative tolerance the current image is resampled to the reference size and
# compared on content, which is more informative than refusing to compare.
# Beyond it the layout genuinely changed and the figure is a FAIL.
SIZE_TOLERANCE = 0.02

PASS, FAIL, REVIEW, MISSING, STALE = 'PASS', 'FAIL', 'REVIEW', 'MISSING', 'STALE'


def load_manifest():
    """Return run_all.py's record of what it regenerated, or None if absent.

    Comparing files on disk is not enough on its own: a script that failed to
    run leaves the previous copy in place, which then compares as identical.
    """
    if not os.path.exists(MANIFEST_PATH):
        return None
    try:
        with open(MANIFEST_PATH) as f:
            return (json.load(f) or {}).get('outputs') or {}
    except Exception:
        return None


def _normalise(text):
    """Strip trailing whitespace per line and normalise the final newline."""
    return '\n'.join(line.rstrip() for line in text.splitlines()).strip() + '\n'


def compare_table(name, manifest=None):
    """Compare one .tex file. Returns (status, detail)."""
    stale = _staleness(name, manifest)
    if stale:
        return stale
    ref_path = os.path.join(REFERENCE_TABLES, name)
    cur_path = os.path.join(CURRENT_TABLES, name)

    if not os.path.exists(cur_path):
        return MISSING, 'not generated'

    with open(ref_path) as f:
        ref = f.read()
    with open(cur_path) as f:
        cur = f.read()

    if ref == cur:
        return PASS, 'byte-identical'
    if _normalise(ref) == _normalise(cur):
        return PASS, 'identical (whitespace only)'

    ref_lines = _normalise(ref).splitlines()
    cur_lines = _normalise(cur).splitlines()
    n_diff = sum(1 for a, b in zip(ref_lines, cur_lines) if a != b)
    n_diff += abs(len(ref_lines) - len(cur_lines))
    first = next(
        (i + 1 for i, (a, b) in enumerate(zip(ref_lines, cur_lines)) if a != b),
        min(len(ref_lines), len(cur_lines)) + 1,
    )
    return FAIL, f'{n_diff} line(s) differ, first at line {first}'


def _staleness(name, manifest):
    """Return a STALE verdict when the last run did not regenerate this output."""
    if manifest is None:
        return None
    entry = manifest.get(name)
    if entry is None:
        return STALE, 'not regenerated in the last run_all.py run'
    if not entry.get('regenerated'):
        return STALE, 'its script FAILED in the last run_all.py run'
    return None


def compare_figure(name, diff_dir=None, manifest=None):
    """Compare one .png file. Returns (status, detail).

    PASS only when byte-identical. Anything else is REVIEW (with a diff image
    written) or, if a large share of the canvas changed, FAIL.
    """
    stale = _staleness(name, manifest)
    if stale:
        return stale
    ref_path = os.path.join(REFERENCE_FIGURES, name)
    cur_path = os.path.join(CURRENT_FIGURES, name)

    if not os.path.exists(cur_path):
        return MISSING, 'not generated'

    with open(ref_path, 'rb') as f:
        ref_bytes = f.read()
    with open(cur_path, 'rb') as f:
        cur_bytes = f.read()
    if ref_bytes == cur_bytes:
        return PASS, 'byte-identical'

    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        return REVIEW, 'differs; install numpy + pillow to quantify'

    ref_img = Image.open(ref_path).convert('RGB')
    cur_img = Image.open(cur_path).convert('RGB')

    resampled = ''
    if ref_img.size != cur_img.size:
        rw, rh = ref_img.size
        cw, ch = cur_img.size
        if abs(cw - rw) / rw > SIZE_TOLERANCE or abs(ch - rh) / rh > SIZE_TOLERANCE:
            return FAIL, (f'size {cur_img.size} != published {ref_img.size} '
                          f'(beyond {SIZE_TOLERANCE:.0%} tolerance -- layout changed)')
        cur_img = cur_img.resize(ref_img.size, Image.LANCZOS)
        resampled = (f'resampled {cw}x{ch} -> {rw}x{rh}; ')

    ref_arr = np.asarray(ref_img, dtype=np.int16)
    cur_arr = np.asarray(cur_img, dtype=np.int16)
    delta = np.abs(ref_arr - cur_arr).max(axis=2)
    pct_changed = float((delta > PIXEL_CHANGE_THRESHOLD).mean() * 100)
    max_delta = int(delta.max())

    diff_note = ''
    if diff_dir:
        os.makedirs(diff_dir, exist_ok=True)
        out = os.path.join(diff_dir, f'diff_{name}')
        Image.fromarray((255 - delta.clip(0, 255)).astype('uint8')).save(out)
        diff_note = f'; diff -> {os.path.relpath(out, _repo)}'

    detail = (f'{resampled}{pct_changed:.3f}% of pixels changed (max channel '
              f'delta {max_delta}){diff_note}')

    if pct_changed > GROSS_CHANGE_PCT:
        return FAIL, detail
    return REVIEW, detail


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--tables', action='store_true', help='Check tables only')
    group.add_argument('--figures', action='store_true', help='Check figures only')
    parser.add_argument('--diff-dir', metavar='DIR',
                        default=os.path.join(_repo, 'diffs'),
                        help='Where to write difference images for figures that '
                             'are not byte-identical (default: diffs/)')
    parser.add_argument('--accept-review', action='store_true',
                        help='Treat REVIEW figures as passing, once inspected')
    parser.add_argument('--ignore-manifest', action='store_true',
                        help='Compare files on disk without checking whether the '
                             'last run_all.py run actually regenerated them')
    args = parser.parse_args()

    do_tables = not args.figures
    do_figures = not args.tables

    manifest = None if args.ignore_manifest else load_manifest()
    if manifest is None and not args.ignore_manifest:
        print("\nNOTE: no .run_manifest.json found, so freshness is unverified -- "
              "these files may be leftovers rather than regenerated output.\n"
              "      Run `python Analysis/run_all.py` first.")

    results = []

    if do_tables:
        names = sorted(f for f in os.listdir(REFERENCE_TABLES) if f.endswith('.tex'))
        print(f"\nTables ({len(names)})")
        print("-" * 72)
        for name in names:
            status, detail = compare_table(name, manifest)
            results.append((status, name))
            print(f"  {status:<8} {name:<32} {detail}")

    if do_figures:
        names = sorted(f for f in os.listdir(REFERENCE_FIGURES) if f.endswith('.png'))
        print(f"\nFigures ({len(names)})")
        print("-" * 72)
        for name in names:
            status, detail = compare_figure(name, args.diff_dir, manifest)
            results.append((status, name))
            print(f"  {status:<8} {name:<32} {detail}")

    n_pass = sum(1 for s, _ in results if s == PASS)
    review = [n for s, n in results if s == REVIEW]
    bad = [n for s, n in results if s in (FAIL, MISSING, STALE)]

    print("\n" + "=" * 72)
    print(f"  {n_pass}/{len(results)} outputs are identical to the published version")
    if review:
        print(f"  {len(review)} need visual review: {', '.join(review)}")
        print(f"  Diff images in {os.path.relpath(args.diff_dir, _repo)}/ "
              "(dark = changed pixels)")
    if bad:
        print(f"  {len(bad)} did NOT reproduce: {', '.join(bad)}")
        print("\n  A table that differs means the generating script and the published")
        print("  output disagree. Fix the script -- never edit the .tex by hand.")

    if bad:
        sys.exit(1)
    if review and not args.accept_review:
        print("\n  Inspect the diffs above, then rerun with --accept-review to sign off.")
        sys.exit(1)
    if review:
        print("  Reviewed figure differences accepted.")
    print("  Verification passed.")


if __name__ == '__main__':
    main()
