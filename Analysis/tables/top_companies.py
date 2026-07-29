"""
Produces: LaTeX/Tables/topCompanies.tex
A two-column table listing the top 50 employers in the other financial services sample.
Requires: revOtherFsExp
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from shared.paths import tables_dir
from shared.data_loader import load_other_exp

print("Creating topCompanies.tex")

revOtherFsExp = load_other_exp()

company_mapping = {
    'Morgan Stanley': 'Morgan Stanley',
    'Bank of America': 'Bank of America',
    'Wells Fargo': 'Wells Fargo',
    'Goldman Sachs': 'Goldman Sachs',
    'Citi': 'Citi',
    'Merrill Lynch': 'Merrill Lynch',
    'JPMorgan Chase & Co.': 'JPMorgan Chase',
    'J.P. Morgan': 'JPMorgan Chase',
    'Fidelity Investments': 'Fidelity Investments',
    'UBS': 'UBS',
    'Credit Suisse': 'Credit Suisse',
    'Bank of America Merrill Lynch': 'Bank of America',
    'Deutsche Bank': 'Deutsche Bank',
    'Charles Schwab': 'Charles Schwab',
    'Merrill Lynch Wealth Management': 'Merrill Lynch',
    'Prudential Financial': 'Prudential Financial',
    'RSM US LLP': 'RSM US LLP',
    'BNY Mellon': 'BNY Mellon',
    'Wells Fargo Advisors': 'Wells Fargo',
    'Edward Jones': 'Edward Jones',
    'BlackRock': 'BlackRock',
    'U.S. Bank': 'U.S. Bank',
    'PNC': 'PNC',
    'Capital One': 'Capital One',
    'State Street': 'State Street',
    'JPMorgan Chase': 'JPMorgan Chase',
    'Lehman Brothers': 'Lehman Brothers',
    'Vanguard': 'Vanguard',
    'Ameriprise Financial Services, LLC': 'Ameriprise Financial Services, LLC',
    'Northwestern Mutual': 'Northwestern Mutual',
    'AIG': 'AIG',
    'GE Capital': 'GE Capital',
    'Internal Revenue Service': 'Internal Revenue Service',
    'Travelers': 'Travelers',
    'MetLife': 'MetLife',
    'Liberty Mutual Insurance': 'Liberty Mutual Insurance',
    'Aon': 'Aon',
    'CBRE': 'CBRE',
    'Raymond James': 'Raymond James',
    'HSBC': 'HSBC',
    'BDO USA, LLP': 'BDO USA, LLP',
    'New York Life Insurance Company': 'New York Life Insurance Company',
    'Primerica': 'Primerica',
    'IBM': 'IBM',
    'Coldwell Banker Residential Brokerage': 'Coldwell Banker Residential Brokerage',
    'RBC Capital Markets': 'RBC Capital Markets',
    'Barclays Investment Bank': 'Barclays Investment Bank',
    'Citigroup': 'Citi',
    'Arthur Andersen & Co.': 'Arthur Andersen',
    'State Farm ®': 'State Farm',
}

BB5_FIRMS = {'JPMorgan Chase', 'Bank of America', 'Morgan Stanley', 'Citi', 'Goldman Sachs'}

revOtherFsExp['company_raw_standardized'] = revOtherFsExp['company_raw'].replace(company_mapping)
revOtherFsExp['company_raw_standardized'] = revOtherFsExp['company_raw_standardized'].str.replace('&', r'\&')

top_companies = revOtherFsExp['company_raw_standardized'].value_counts().head(50)

half = len(top_companies) // 2 + len(top_companies) % 2
column1 = top_companies.index[:half]
column2 = top_companies.index[half:]

def _fmt(name):
    # Add asterisk for BB5 firms (compare against un-escaped name)
    clean = name.replace(r'\&', '&')
    return name + '*' if clean in BB5_FIRMS else name

with open(f"{tables_dir}/topCompanies.tex", 'w') as fout:
    fout.write(r"""
\begin{tabular}{p{7cm}p{7cm}}
\toprule
 & \\
\midrule
""")
    for i in range(half):
        col1 = _fmt(column1[i]) if i < len(column1) else ""
        col2 = _fmt(column2[i]) if i < len(column2) else ""
        fout.write(f"{col1} & {col2} \\\\\n")

    fout.write(r"""
\bottomrule
\end{tabular}
""")

print(f"Saved {tables_dir}/topCompanies.tex")
