"""
Produces: LaTeX/Tables/rolesTable.tex
A two-column table listing the financial services roles used to construct the comparison sample.
No data loading required.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from shared.paths import tables_dir

print("Creating rolesTable.tex")

fsm_list = [
    "actuarial", "actuarial analyst", "actuary", "aml analyst", "audit", "auditor",
    "banking consultant", "broker", "brokerage", "business controller", "capital markets",
    "cfo", "commercial finance", "commercial underwriter", "controller", "credit analyst",
    "equity analyst", "equity research", "equity research analyst", "finance controller",
    "financial adviser", "financial analyst fp a", "financial consultant",
    "financial controller", "financial officer", "financial planner", "financial planning",
    "financial planning analysis", "financial planning analyst", "financial reporting",
    "financial reporting analyst", "fraud analyst", "fraud investigator",
    "investment analyst", "investment banking", "investment banking analyst",
    "investment consultant", "investments", "mergers acquisitions", "portfolio analyst",
    "pricing analyst", "project controller", "quantitative analyst", "sap fico consultant",
    "stock controller", "tax", "tax accountant", "tax analyst", "tax consultant",
    "trade finance", "trader", "trading", "underwriter", "underwriting"
]

FOOTNOTE_MARKERS = {
    'audit': r'$^\dagger$',
    'auditor': r'$^\dagger$',
    'investment banking': '*',
    'investment banking analyst': '*',
    'tax': r'$^\ddagger$',
    'tax accountant': r'$^\ddagger$',
    'tax analyst': r'$^\ddagger$',
    'tax consultant': r'$^\ddagger$',
}

fsm_list.sort()

half = len(fsm_list) // 2 + len(fsm_list) % 2
column1 = fsm_list[:half]
column2 = fsm_list[half:]

with open(f"{tables_dir}/rolesTable.tex", 'w') as fout:
    fout.write(r"""
\begin{tabular}{p{7cm}p{7cm}}
\toprule
 & \\
\midrule
""")
    for i in range(half):
        col1 = column1[i] if i < len(column1) else ""
        col2 = column2[i] if i < len(column2) else ""
        col1 += FOOTNOTE_MARKERS.get(col1, '')
        col2 += FOOTNOTE_MARKERS.get(col2, '')
        fout.write(f"{col1} & {col2} \\\\\n")

    fout.write(r"""
\bottomrule
\end{tabular}
""")

print(f"Saved {tables_dir}/rolesTable.tex")
