"""
Produces: LaTeX/Tables/nonB4FirmsTable.tex
A table listing the non-Big 4 accounting firms from the Accounting Today
Top 100 rankings used for benchmarking, split by PCAOB annual inspection status.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from shared.paths import tables_dir
from shared.r2 import ensure_data_file

print("Creating nonB4FirmsTable.tex")

with open(ensure_data_file('interim/at_revelio_firm_mapping.json')) as f:
    at_mapping = json.load(f)

B4_FIRMS = {'Deloitte', 'EY', 'KPMG', 'PwC'}
EXCLUDE = B4_FIRMS | {'Andersen'}
ANNUAL = {'Grant Thornton', 'BDO', 'RSM', 'Crowe', 'Forvis', 'Moss Adams', 'Baker Tilly'}

all_firms = [f for f in at_mapping.keys() if f not in EXCLUDE]
annual = sorted([f for f in all_firms if f in ANNUAL])
other = sorted([f for f in all_firms if f not in ANNUAL])


def _esc(name):
    return name.replace('&', r'\&')


with open(f"{tables_dir}/nonB4FirmsTable.tex", 'w') as fout:
    # Panel A: Annually inspected
    fout.write(r"""
\begin{tabular}{@{}p{14cm}@{}}
\toprule
\textbf{Panel A: Annually inspected firms} \\
\midrule
""")
    fout.write(', '.join(_esc(f) for f in annual))
    fout.write(r""" \\
\addlinespace[1em]
\textbf{Panel B: Non-annually inspected firms} \\
\midrule
""")
    # Lay out non-annual firms as flowing text
    fout.write(', '.join(_esc(f) for f in other))
    fout.write(r""" \\
\bottomrule
\end{tabular}
""")

print(f"Saved {tables_dir}/nonB4FirmsTable.tex")
print(f"  Annually inspected: {len(annual)} firms")
print(f"  Non-annually inspected: {len(other)} firms")
