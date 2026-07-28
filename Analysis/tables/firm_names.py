"""
Produces: LaTeX/Tables/firmNamesTable.tex

Appendix table listing the raw Revelio `company_raw` values mapped to each Big 4
firm. Generated from AUDIT_FIRM_MAPPING in Analysis/shared/firm_mappings.py --
the same mapping Analysis/pipeline/06_build_interim.py applies when building the
primary sample, so the table cannot drift from the code.

Layout: two side-by-side firm pairs (Deloitte/EY, then KPMG/PwC), each firm's
values listed down a column in mapping order.

Requires no data files.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from shared.firm_mappings import (
    AUDIT_FIRM_MAPPING,
    FIRM_DISPLAY_NAME,
    FIRM_TABLE_BLOCKS,
    values_for,
)
from shared.paths import tables_dir

print("Creating firmNamesTable.tex")


def _esc(name):
    """Escape LaTeX special characters appearing in firm names."""
    return name.replace('&', r'\&')


def render_block(left_key, right_key):
    """Render one two-firm block as a list of tabular rows."""
    left, right = values_for(left_key), values_for(right_key)
    rows = []
    for i in range(max(len(left), len(right))):
        left_name = FIRM_DISPLAY_NAME[left_key] if i == 0 else ''
        right_name = FIRM_DISPLAY_NAME[right_key] if i == 0 else ''
        left_val = _esc(left[i]) if i < len(left) else ''
        right_val = _esc(right[i]) if i < len(right) else ''
        rows.append(f"{left_name} & {left_val} & {right_name} & {right_val} \\\\")
    return rows


lines = [
    r"\begin{tabular}{@{}ll@{\hspace{2cm}}ll@{}}",
    r"\toprule",
    r"Firm & Values of \textit{company\_raw} & Firm & Values of \textit{company\_raw} \\",
    r"\midrule",
]

for i, (left_key, right_key) in enumerate(FIRM_TABLE_BLOCKS):
    if i > 0:
        lines.append(r"\addlinespace[1em]")
    lines.extend(render_block(left_key, right_key))

lines += [r"\bottomrule", r"\end{tabular}"]

out_path = os.path.join(tables_dir, 'firmNamesTable.tex')
with open(out_path, 'w') as fout:
    # Leading newline matches the other generated tables (see nonb4_firms.py),
    # which \input cleanly either way.
    fout.write('\n' + '\n'.join(lines) + '\n')

print(f"Saved {out_path}")
print(f"  {len(FIRM_DISPLAY_NAME)} firms, {len(AUDIT_FIRM_MAPPING)} company_raw values")
