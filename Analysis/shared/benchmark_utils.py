"""
Shared constants, mappings, and helper functions for benchmark scripts.

All scripts in Analysis/benchmarks/ import from here.
"""
import os, sys, json
import pandas as pd
import numpy as np

_here = os.path.dirname(os.path.abspath(__file__))
_parent = os.path.dirname(_here)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from shared.r2 import ensure_data_file
from shared.paths import data_dir, figures_dir, tables_dir

# ── Period definitions ────────────────────────────────────────────────────────
# 11-period structure used by the main benchmark figures
PERIODS = [
    'female_pre_2004', 'female_2004_2005', 'female_2006_2007', 'female_2008_2009',
    'female_2010_2011', 'female_2012_2013', 'female_2014_2015', 'female_2016_2017',
    'female_2018_2019', 'female_2020_2021', 'female_2022_2023',
]
PERIOD_LABELS = [
    'Pre-2004', '2004-05', '2006-07', '2008-09', '2010-11',
    '2012-13', '2014-15', '2016-17', '2018-19', '2020-21', '2022-23',
]
SHORT_LABELS = [
    'Pre-\n2004', '04-\n05', '06-\n07', '08-\n09', '10-\n11',
    '12-\n13', '14-\n15', '16-\n17', '18-\n19', '20-\n21', '22-\n23',
]
PERIOD_STR = ' '.join(PERIODS)

# 9-period structure used for non-B4 audit figures (smaller early samples)
NB4_PERIODS = [
    'female_pre_2008', 'female_2008_2009', 'female_2010_2011', 'female_2012_2013',
    'female_2014_2015', 'female_2016_2017', 'female_2018_2019',
    'female_2020_2021', 'female_2022_2023',
]
NB4_PERIOD_LABELS = [
    'Pre-2008', '2008-09', '2010-11', '2012-13', '2014-15',
    '2016-17', '2018-19', '2020-21', '2022-23',
]
NB4_SHORT_LABELS = [
    'Pre-\n2008', '08-\n09', '10-\n11', '12-\n13', '14-\n15',
    '16-\n17', '18-\n19', '20-\n21', '22-\n23',
]
NB4_PERIOD_STR = ' '.join(NB4_PERIODS)

CONTROLS = 'masterorhigher top_university api black other'

# ── School mapping ────────────────────────────────────────────────────────────
school_mapping = {
    'The University of Texas at Austin': 'University of Texas at Austin',
    'McCombs School of Business at the University of Texas at Austin': 'University of Texas at Austin',
    'Brigham Young University': 'Brigham Young University',
    'Brigham Young University Marriott School of Business': 'Brigham Young University',
    'University of Illinois at Urbana-Champaign': 'University of Illinois at Urbana-Champaign',
    'Gies College of Business': 'University of Illinois at Urbana-Champaign',
    'Indiana University Bloomington': 'Indiana University Bloomington',
    'Kelley School of Business': 'Indiana University Bloomington',
    'University of Notre Dame': 'University of Notre Dame',
    'Mendoza College of Business': 'University of Notre Dame',
    'University of Michigan': 'University of Michigan',
    'Stephen M. Ross School of Business': 'University of Michigan',
    'University of Pennsylvania': 'University of Pennsylvania',
    'Wharton School of Business at University of Pennsylvania': 'University of Pennsylvania',
    'University of Southern California': 'University of Southern California',
    'USC Marshall School of Business': 'University of Southern California',
    'New York University': 'New York University',
    'The Leonard N Stern School of Business': 'New York University',
    'New York University School of Law': 'New York University',
    'The Ohio State University': 'Ohio State University',
    'Fisher College of Business': 'Ohio State University',
    'Massachusetts Institute of Technology': 'Massachusetts Institute of Technology',
    'MIT Sloan School of Management': 'Massachusetts Institute of Technology',
    'University of California Berkeley': 'University of California Berkeley',
    'Haas School of Business': 'University of California Berkeley',
    'Carnegie Mellon University': 'Carnegie Mellon University',
    'Tepper School of Business': 'Carnegie Mellon University',
    'University of North Carolina at Chapel Hill': 'University of North Carolina at Chapel Hill',
    'Kenan-Flagler Business School': 'University of North Carolina at Chapel Hill',
    'University of Virginia': 'University of Virginia',
    'University of Virginia Darden School of Business': 'University of Virginia',
    'Cornell University': 'Cornell University',
    'Johnson Graduate School of Management': 'Cornell University',
    'Stanford University': 'Stanford University',
    'Stanford Graduate School of Business': 'Stanford University',
    'Northwestern University': 'Northwestern University',
    'Kellogg School of Management at Northwestern University': 'Northwestern University',
    'The University of Chicago Booth School of Business': 'University of Chicago',
    'University of Chicago': 'University of Chicago',
    'Harvard University': 'Harvard University',
    'Harvard Business School': 'Harvard University',
    'Harvard Law School': 'Harvard University',
    'Columbia University in the City of New York': 'Columbia University',
    'Columbia Business School': 'Columbia University',
    'Columbia Law School': 'Columbia University',
    'Yale University': 'Yale University',
    'Yale School of Management': 'Yale University',
    'Princeton University': 'Princeton University',
    'Duke University': 'Duke University',
    'The Fuqua School of Business': 'Duke University',
}

# ── Firm mappings ─────────────────────────────────────────────────────────────
BB5_MAPPING = {
    'Goldman Sachs': 'gs', 'Goldman, Sachs & Co.': 'gs', 'Goldman Sachs & Co.': 'gs',
    'Goldman Sachs & Co': 'gs', 'Goldman, Sachs & Co': 'gs', 'GOLDMAN, SACHS & CO': 'gs',
    'Goldman Sachs Group': 'gs', 'Goldman Sachs Group Limited': 'gs', 'Goldman, Sachs': 'gs',
    'Goldman Sachs & Company': 'gs', 'Goldman Sachs and Co.': 'gs',
    'The Goldman Sachs Group, Inc.': 'gs', 'goldman sachs': 'gs', 'GOLDMAN SACHS': 'gs',
    'Goldman Sachs International': 'gs', 'Goldman Sachs Commercial Mortgage Capital': 'gs',
    'Goldman Sachs Specialty Lending Group': 'gs', 'Goldman, Sachs & Company': 'gs',
    'Goldman Sachs 10,000 Small Businesses': 'gs',
    'Morgan Stanley': 'ms', 'Morgan Stanley Dean Witter': 'ms', 'Morgan Stanley & Co.': 'ms',
    'morgan stanley': 'ms', 'MORGAN STANLEY': 'ms', 'Morgan Stanley & Co. Incorporated': 'ms',
    'Morgan Stanley USA': 'ms', 'Morgan Stanley & Co': 'ms',
    'Dean Witter Reynolds (Morgan Stanley)': 'ms', 'Morgan Stanley & Co. Inc.': 'ms',
    'Morgan Stanley & Company': 'ms', 'Morgan Stanley (financial services company)': 'ms',
    'Morgan Stanley Prime Brokerage': 'ms', 'Morgan Stanley Capital Partners': 'ms',
    'Morgan Stanley Fund Services': 'ms', 'Morgan Stanley Fund Services Inc': 'ms',
    'J.P. Morgan': 'jpm', 'JPMorgan Chase & Co.': 'jpm', 'JPMorgan Chase': 'jpm',
    'JP Morgan': 'jpm', 'JPMorganChase': 'jpm', 'JPMorgan': 'jpm',
    'JP Morgan Chase': 'jpm', 'J.P. Morgan Chase': 'jpm', 'J.P. Morgan Chase & Co.': 'jpm',
    'JPMorgan Chase & Co': 'jpm', 'J P Morgan': 'jpm', 'J.P. Morgan Securities': 'jpm',
    'JPMorgan Securities': 'jpm', 'JP Morgan Securities': 'jpm',
    'J.P. Morgan Securities Inc.': 'jpm', 'J.P. Morgan Securities LLC': 'jpm',
    'JPMorgan Securities LLC': 'jpm', 'JP Morgan Securities LLC': 'jpm',
    'J.P. Morgan Investment Bank': 'jpm', 'JPMorgan Chase Bank': 'jpm',
    'JPMorgan Chase Bank, N.A.': 'jpm', 'JPMorgan Securities Inc.': 'jpm', 'JP MORGAN': 'jpm',
    'Bank of America': 'bofa', 'Bank of America Merrill Lynch': 'bofa', 'Merrill Lynch': 'bofa',
    'Merrill Lynch & Co.': 'bofa', 'Bank of America Securities': 'bofa',
    'BofA Merrill Lynch': 'bofa', 'Merrill Lynch Capital': 'bofa', 'Merrill Lynch & Co': 'bofa',
    'Merrill Lynch Capital Markets': 'bofa', 'Bank of America/Merrill Lynch': 'bofa',
    'Bank Of America': 'bofa', 'Merrill Lynch & Co., Inc.': 'bofa', 'BofA Securities': 'bofa',
    'Bank of America - Merrill Lynch': 'bofa', 'MERRILL LYNCH': 'bofa',
    'Bank of America / Merrill Lynch': 'bofa', 'BANK OF AMERICA MERRILL LYNCH': 'bofa',
    'Merrill Lynch Investment Banking': 'bofa', 'Bank of America Corporation': 'bofa',
    'Bank of America, N.A.': 'bofa',
    'Merrill Lynch, Pierce, Fenner & Smith Incorporated': 'bofa',
    'Citi': 'citi', 'Citigroup': 'citi', 'Citibank': 'citi',
    'Citigroup Global Markets': 'citi', 'Citigroup Global Markets Inc.': 'citi',
    'Citi Group': 'citi', 'Citigroup Global Markets, Inc.': 'citi',
    'Citigroup Global Capital Markets Inc.': 'citi', 'Citigroup Global Markets Inc': 'citi',
    'Citigroup Inc.': 'citi', 'Citigroup, Inc.': 'citi', 'Citibank, N.A.': 'citi',
    'Citigroup Investment Banking': 'citi', 'Citi Bank': 'citi', 'CitiGroup': 'citi',
    'Citigroup Inc': 'citi', 'Citigroup USA Inc.': 'citi', 'Citibank N.A.': 'citi',
    'Citigroup Smith Barney': 'citi', 'Citi Smith Barney': 'citi',
    'Salomon Smith Barney (Citigroup)': 'citi', 'Salomon Smith Barney / Citigroup': 'citi',
    'Citigroup Investment Research': 'citi', 'Citigroup Energy, Inc.': 'citi',
    'Citi Capital Strategies': 'citi',
}
BB5_KEYS = {'gs': 1, 'ms': 2, 'jpm': 3, 'bofa': 4, 'citi': 5}

NEXT5_MAPPING = {
    'Wells Fargo': 'wf', 'Wells Fargo Securities': 'wf', 'Wells Fargo Bank': 'wf',
    'Wells Fargo Advisors': 'wf', 'Wachovia, A Wells Fargo Company': 'wf',
    'Wells Fargo Securities, LLC': 'wf', 'Wells Fargo Capital Finance': 'wf',
    'Credit Suisse': 'cs', 'Credit Suisse First Boston': 'cs',
    'Credit Suisse Securities (USA) LLC': 'cs', 'Credit Suisse Strategic Partners': 'cs',
    'Credit Suisse First Boston Technology Group': 'cs',
    'Donaldson, Lufkin & Jenrette / Credit Suisse': 'cs',
    'Credit Suisse First Boston / Donaldson, Lufkin & Jenrette': 'cs',
    'Deutsche Bank': 'db', 'Deutsche Bank Securities': 'db',
    'Deutsche Bank Alex. Brown': 'db', 'Deutsche Bank Alex Brown': 'db',
    'Bankers Trust (now Deutsche Bank)': 'db', 'Deutsche Bank Securities Inc.': 'db',
    'Deutsche Bank Securities Inc': 'db', 'Deutsche Bank Securities, Inc.': 'db',
    'Deutsche Bank Private Wealth Management': 'db',
    'Barclays': 'barc', 'Barclays Investment Bank': 'barc', 'Barclays Capital': 'barc',
    'Barclays Corporate & Investment Bank': 'barc', 'Barclays Corporate Banking': 'barc',
    'Barclays Bank': 'barc', 'Barclays Capital Inc.': 'barc',
    'Lehman Brothers / Barclays Capital': 'barc', 'Barclays Capital / Lehman Brothers': 'barc',
    'Barclays Capital (formerly Lehman Brothers)': 'barc',
    'RBC Capital Markets': 'rbc', 'RBC': 'rbc', 'RBC Dain Rauscher': 'rbc',
    'RBC Richardson Barr': 'rbc',
}
BB7_MAPPING = {**BB5_MAPPING,
    'Wells Fargo': 'wf', 'Wells Fargo Securities': 'wf', 'Wells Fargo Bank': 'wf',
    'Wells Fargo Advisors': 'wf', 'Wachovia, A Wells Fargo Company': 'wf',
    'Wells Fargo Securities, LLC': 'wf', 'Wells Fargo Capital Finance': 'wf',
    'Credit Suisse': 'cs', 'Credit Suisse First Boston': 'cs',
    'Credit Suisse Securities (USA) LLC': 'cs', 'Credit Suisse Strategic Partners': 'cs',
    'Credit Suisse First Boston Technology Group': 'cs',
    'Donaldson, Lufkin & Jenrette / Credit Suisse': 'cs',
    'Credit Suisse First Boston / Donaldson, Lufkin & Jenrette': 'cs',
}
BB7_KEYS = {**BB5_KEYS, 'wf': 6, 'cs': 7}
BB10_MAPPING = {**BB5_MAPPING, **NEXT5_MAPPING}
BB10_KEYS = {**BB5_KEYS, 'wf': 6, 'cs': 7, 'db': 8, 'barc': 9, 'rbc': 10}

MBB_MAPPING = {
    'McKinsey & Company': 'mckinsey', 'McKinsey & Co.': 'mckinsey', 'McKinsey': 'mckinsey',
    'McKinsey and Company': 'mckinsey', 'McKinsey & Co': 'mckinsey',
    'McKinsey & Company, Inc.': 'mckinsey', 'McKinsey&Company': 'mckinsey',
    'Mckinsey & Company': 'mckinsey', 'McKinsey Digital': 'mckinsey',
    'McKinsey & Company - McKinsey Digital': 'mckinsey',
    'Boston Consulting Group': 'bcg', 'The Boston Consulting Group': 'bcg',
    'BCG': 'bcg', 'BCG (Boston Consulting Group)': 'bcg',
    'Boston Consulting Group (BCG)': 'bcg', 'The Boston Consulting Group (BCG)': 'bcg',
    'BCG Digital Ventures': 'bcg', 'BCG Platinion': 'bcg', 'BCG GAMMA': 'bcg',
    'BCG Henderson Institute': 'bcg',
    'Bain & Company': 'bain', 'Bain and Company': 'bain', 'Bain & Co.': 'bain',
    'Bain & Co': 'bain', 'BAIN & COMPANY': 'bain', 'Bain & Company, Inc.': 'bain',
    'Bain': 'bain',
}
MBB_KEYS = {'mckinsey': 1, 'bcg': 2, 'bain': 3}

AUDIT_FIRM_MAPPING = {
    'PwC': 'pwc', 'PricewaterhouseCoopers': 'pwc',
    'PricewaterhouseCoopers LLP': 'pwc', 'Price Waterhouse Coopers': 'pwc',
    'PriceWaterhouseCoopers': 'pwc', 'Pricewaterhouse Coopers': 'pwc',
    'PricewaterhouseCoopers, LLP': 'pwc',
    'Deloitte': 'deloitte', 'Deloitte & Touche': 'deloitte',
    'Deloitte & Touche LLP': 'deloitte', 'Deloitte & Touche, LLP': 'deloitte',
    'Deloitte and Touche': 'deloitte', 'Deloitte (Accounting Firm)': 'deloitte',
    'Deloitte Tax LLP': 'deloitte',
    'EY': 'ey', 'Ernst & Young': 'ey', 'Ernst & Young LLP': 'ey',
    'Ernst & Young, LLP': 'ey', 'Ernst and Young': 'ey', 'E & Y': 'ey',
    'KPMG': 'kpmg', 'KPMG US': 'kpmg', 'KPMG LLP': 'kpmg',
    'KPMG Audit': 'kpmg', 'KPMG, LLP': 'kpmg', 'KPMG Advisory': 'kpmg',
}
AUDIT_FIRM_KEYS = {'pwc': 1, 'ey': 2, 'deloitte': 3, 'kpmg': 4}

# Non-B4 audit firm categories
ANNUAL_AT = {'Grant Thornton', 'BDO', 'RSM', 'Crowe', 'Forvis', 'Moss Adams', 'Baker Tilly'}

# ── Professional roles (for Top 100 FS benchmark) ────────────────────────────
PROFESSIONAL_ROLES = [
    'financial planning analyst', 'financial analyst fp a', 'financial planning analysis',
    'equity research analyst', 'investment banking analyst', 'quantitative analyst',
    'equity analyst', 'equity research', 'financial reporting', 'financial reporting analyst',
    'actuarial', 'actuarial analyst', 'finance controller', 'commercial finance',
    'portfolio analyst', 'financial planning', 'investment analyst',
    'mergers acquisitions', 'capital markets', 'investment banking',
    'actuary', 'business controller', 'pricing analyst',
]

FS_EXCLUDE = [
    'deloitte', 'pricewaterhousecoopers', 'pwc', 'ernst & young', 'ernst and young',
    'kpmg', 'arthur andersen',
    'rsm ', 'bdo ', 'grant thornton', 'baker tilly', 'cliftonlarsonallen',
    'crowe', 'plante moran', 'moss adams', 'mazars', 'marcum', 'forvis',
    'internal revenue', 'h&r block', 'h & r block',
    'securities and exchange commission', 'sec ', 'fdic',
    'coldwell banker', 'cbre', 're/max', 'keller williams',
    'self-employed', 'self employed', 'freelance',
]

def fs_exclude(name):
    if pd.isna(name):
        return True
    nl = name.lower()
    if nl in ('ey', 'e & y') or nl.startswith('ey '):
        return True
    for pat in FS_EXCLUDE:
        if pat in nl:
            return True
    return False


# ── Stata helper functions ────────────────────────────────────────────────────
def extract_coefs(stata, periods):
    """Extract coefficients and standard errors for named variables from last e()."""
    ret = stata.get_ereturn()
    b = ret['e(b)'].flatten()
    se = ret['e(V)'].diagonal() ** 0.5
    varnames = ret['e(indepvars)'].split()
    coefs = [b[varnames.index(v)] for v in periods]
    ses = [se[varnames.index(v)] for v in periods]
    return coefs, ses


# ── Period dummy helpers ──────────────────────────────────────────────────────
def add_period_dummies(df, female_col='female', year_col='year'):
    """Add the standard 11-period female×period interaction dummies in place."""
    yr = df[year_col]
    fe = df[female_col]
    df['female_pre_2004'] = fe * (yr < 2004).astype(int)
    df['female_2004_2005'] = fe * yr.isin([2004, 2005]).astype(int)
    df['female_2006_2007'] = fe * yr.isin([2006, 2007]).astype(int)
    df['female_2008_2009'] = fe * yr.isin([2008, 2009]).astype(int)
    df['female_2010_2011'] = fe * yr.isin([2010, 2011]).astype(int)
    df['female_2012_2013'] = fe * yr.isin([2012, 2013]).astype(int)
    df['female_2014_2015'] = fe * yr.isin([2014, 2015]).astype(int)
    df['female_2016_2017'] = fe * yr.isin([2016, 2017]).astype(int)
    df['female_2018_2019'] = fe * yr.isin([2018, 2019]).astype(int)
    df['female_2020_2021'] = fe * yr.isin([2020, 2021]).astype(int)
    df['female_2022_2023'] = fe * yr.isin([2022, 2023]).astype(int)
    return df


def add_nb4_period_dummies(df, female_col='female', year_col='year'):
    """Add the 9-period (non-B4 variant) female×period interaction dummies in place."""
    yr = df[year_col]
    fe = df[female_col]
    df['female_pre_2008'] = fe * (yr < 2008).astype(int)
    df['female_2008_2009'] = fe * yr.isin([2008, 2009]).astype(int)
    df['female_2010_2011'] = fe * yr.isin([2010, 2011]).astype(int)
    df['female_2012_2013'] = fe * yr.isin([2012, 2013]).astype(int)
    df['female_2014_2015'] = fe * yr.isin([2014, 2015]).astype(int)
    df['female_2016_2017'] = fe * yr.isin([2016, 2017]).astype(int)
    df['female_2018_2019'] = fe * yr.isin([2018, 2019]).astype(int)
    df['female_2020_2021'] = fe * yr.isin([2020, 2021]).astype(int)
    df['female_2022_2023'] = fe * yr.isin([2022, 2023]).astype(int)
    return df


# ── Panel builders ────────────────────────────────────────────────────────────
def run_b4_audit_regression(stata, nb4=False):
    """
    Load B4 audit data, add period dummies, run reghdfe, return (coefs, ses, n_users).

    nb4=True uses the 9-period NB4_PERIODS structure instead of the standard 11-period PERIODS.
    """
    from shared.data_loader import load_b4_stata
    b4 = load_b4_stata()
    if nb4:
        add_nb4_period_dummies(b4, year_col='year')
        periods, period_str = NB4_PERIODS, NB4_PERIOD_STR
    else:
        add_period_dummies(b4, year_col='year')
        periods, period_str = PERIODS, PERIOD_STR
    n = b4['userid'].nunique()
    print(f"  B4 Audit: {len(b4):,} obs, {n:,} users")
    stata.pdataframe_to_data(b4, force=True)
    del b4
    stata.run(
        f'reghdfe retained {period_str} {CONTROLS}, '
        'absorb(auditorkey ib2000.year yearfirst) vce(cluster userid) version(5)',
        quietly=True
    )
    coefs, ses = extract_coefs(stata, periods)
    return coefs, ses, n


def build_ib_panel(stata, firm_map, firm_keys, label):
    """Build an IB person-year panel from Revelio investment banking roles."""
    ib_dfs = []
    for role in ['investment banking', 'investment banking analyst']:
        path = ensure_data_file(f"raw/revelio/revelioPosUsr_role_{role}.feather")
        df_role = pd.read_feather(path)
        df_role['firm'] = df_role['company_raw'].map(firm_map)
        ib_dfs.append(df_role[df_role['firm'].notna()].copy())
    ib_raw = pd.concat(ib_dfs, ignore_index=True)
    ib_raw['female'] = (ib_raw['sex_predicted'] == 'F').astype(int)
    eth_ib = ib_raw['ethnicity_predicted'].fillna('')
    ib_raw['api'] = (eth_ib == 'API').astype(int)
    ib_raw['black'] = (eth_ib == 'Black').astype(int)
    ib_raw['other'] = (~eth_ib.isin(['White', 'API', 'Black', 'Hispanic', ''])).astype(int)
    ib_raw['startdate'] = pd.to_datetime(ib_raw['startdate'], errors='coerce')
    ib_raw['enddate'] = pd.to_datetime(ib_raw['enddate'], errors='coerce')
    ib_raw['enddate'] = ib_raw['enddate'].fillna(pd.Timestamp('2025-10-01'))
    ib_raw = ib_raw[ib_raw['startdate'].notna() & (ib_raw['startdate'] <= ib_raw['enddate'])]
    ib_raw = ib_raw[ib_raw['highest_degree'].notna()]
    ib_raw = ib_raw[~ib_raw['title_raw'].str.contains('intern', case=False, na=False)]
    ib_raw['user_firm_enddate'] = ib_raw.groupby('user_id')['enddate'].transform('max')
    ib_raw['user_firm_startdate'] = ib_raw.groupby('user_id')['startdate'].transform('min')
    ib_raw['start_year'] = ib_raw['startdate'].dt.year
    ib_raw['end_year'] = ib_raw['enddate'].dt.year.clip(upper=2024)
    ib_raw = ib_raw[ib_raw['start_year'] <= ib_raw['end_year']]
    ib_exp = ib_raw[['user_id', 'firm', 'female', 'api', 'black', 'other', 'start_year', 'end_year',
                     'user_firm_enddate', 'user_firm_startdate']].copy()
    ib_exp['position_year'] = [list(range(int(s), int(e)+1)) for s, e in zip(ib_exp['start_year'], ib_exp['end_year'])]
    panel = ib_exp.explode('position_year', ignore_index=True)
    panel['position_year'] = panel['position_year'].astype(int)
    panel = panel.sort_values(['user_id', 'position_year', 'start_year']).drop_duplicates(
        subset=['user_id', 'position_year'], keep='last')
    panel = panel[panel['position_year'] <= 2023]
    # Education
    edu_raw_ib = pd.read_feather(ensure_data_file("raw/revelio/revelioEdu_role_combined.feather"))
    edu_raw_ib = edu_raw_ib[edu_raw_ib['user_id'].isin(set(panel['user_id'].unique()))].copy()
    edu_raw_ib = edu_raw_ib[edu_raw_ib['degree'].isin(['Bachelor', 'Master', 'MBA', 'Doctor'])].copy()
    edu_raw_ib['degree_rank'] = edu_raw_ib['degree'].map({'Doctor': 4, 'MBA': 3, 'Master': 2, 'Bachelor': 1})
    edu_raw_ib['enddate'] = pd.to_datetime(edu_raw_ib['enddate'], errors='coerce').fillna(pd.to_datetime('2025-10-01'))
    edu_ib = (edu_raw_ib.sort_values(['user_id', 'degree_rank', 'enddate'], ascending=[False, True, True])
              .groupby('user_id').tail(1)[['user_id', 'university_name', 'degree']])
    edu_ib['university_name'] = edu_ib['university_name'].apply(lambda x: school_mapping.get(x, 'other'))
    panel = panel.merge(edu_ib, on='user_id', how='left')
    panel['masterorhigher'] = panel['degree'].isin(['Master', 'MBA', 'Doctor']).fillna(False).astype(int)
    panel['top_university'] = (panel['university_name'] != 'other').fillna(False).astype(int)
    panel['retained'] = (panel['user_firm_enddate'].dt.year > panel['position_year']).astype(int)
    panel['yearfirst'] = panel['user_firm_startdate'].dt.year
    panel['year'] = panel['position_year']
    panel['userid'] = panel['user_id']
    add_period_dummies(panel)
    panel['firmkey'] = panel['firm'].map(firm_keys)
    print(f"  {label}: {len(panel):,} obs, {panel['userid'].nunique():,} users, {panel['firmkey'].nunique()} firms")
    return panel


def build_top100_fs_panel():
    """
    Build the Top 100 FS professional roles person-year panel.
    Returns (fs_exp DataFrame, n_users int).
    """
    fs_int = pd.read_feather(ensure_data_file('interim/revOtherFs.feather'))
    fs_int['startdate'] = pd.to_datetime(fs_int['startdate'], errors='coerce')
    fs_int['enddate'] = pd.to_datetime(fs_int['enddate'], errors='coerce')
    fs_int = fs_int[fs_int['startdate'].notna() & (fs_int['startdate'] <= fs_int['enddate'])]
    fs_int = fs_int[fs_int['highest_degree'].isin(['Bachelor', 'Master', 'MBA', 'Doctor'])]
    fs_int = fs_int[~fs_int['title_raw'].str.contains('intern', case=False, na=False)]
    fs_int = fs_int[fs_int['ultimate_parent_rcid'].notna()]
    fs_int = fs_int[~fs_int['company_raw'].apply(fs_exclude)]
    fs_sub = fs_int[fs_int['role_k1500'].isin(PROFESSIONAL_ROLES)]
    fs_ranks = fs_sub.groupby('ultimate_parent_rcid')['user_id'].nunique().sort_values(ascending=False)
    top100 = set(fs_ranks.head(100).index)
    fs_p = fs_int[(fs_int['role_k1500'].isin(PROFESSIONAL_ROLES)) &
                  (fs_int['ultimate_parent_rcid'].isin(top100))].copy()
    fs_p = fs_p.sort_values(['user_id', 'ultimate_parent_rcid', 'startdate'])
    fs_p['new_spell'] = (
        (fs_p['user_id'] != fs_p['user_id'].shift(1)) |
        (fs_p['ultimate_parent_rcid'] != fs_p['ultimate_parent_rcid'].shift(1))
    ).fillna(True).astype(int)
    fs_p['spell_id'] = fs_p['new_spell'].cumsum()
    fs_p['spell_startdate'] = fs_p.groupby('spell_id')['startdate'].transform('min')
    fs_p['spell_enddate'] = fs_p.groupby('spell_id')['enddate'].transform('max')
    fs_p = fs_p.drop_duplicates(['user_id', 'spell_id'], keep='last')
    fs_p['position_year'] = fs_p.apply(
        lambda row: list(range(row['spell_startdate'].year, row['spell_enddate'].year + 1)), axis=1)
    fs_e = fs_p[['user_id', 'ultimate_parent_rcid', 'sex_predicted', 'ethnicity_predicted',
                 'spell_startdate', 'spell_enddate', 'position_year',
                 'degree', 'university_name']].explode('position_year', ignore_index=True)
    fs_e['position_year'] = fs_e['position_year'].astype(int)
    fs_e = fs_e.sort_values(['user_id', 'position_year', 'spell_enddate']).drop_duplicates(
        ['user_id', 'position_year'], keep='last')
    fs_e = fs_e[fs_e['position_year'] <= 2023]
    fs_e['userid'] = fs_e['user_id']
    fs_e['year'] = fs_e['position_year']
    fs_e['retained'] = (fs_e['spell_enddate'].dt.year > fs_e['year']).fillna(False).astype(int)
    fs_e['female'] = (fs_e['sex_predicted'] == 'F').astype(int)
    fs_e['yearfirst'] = fs_e['spell_startdate'].dt.year
    eth_t = fs_e['ethnicity_predicted'].fillna('')
    fs_e['api'] = (eth_t == 'API').astype(int)
    fs_e['black'] = (eth_t == 'Black').astype(int)
    fs_e['other'] = (~eth_t.isin(['White', 'API', 'Black', 'Hispanic', ''])).astype(int)
    fs_e['university_name'] = fs_e['university_name'].apply(
        lambda x: school_mapping.get(x, 'other') if pd.notna(x) else 'other')
    fs_e['masterorhigher'] = fs_e['degree'].isin(['Master', 'MBA', 'Doctor']).fillna(False).astype(int)
    fs_e['top_university'] = (fs_e['university_name'] != 'other').astype(int)
    add_period_dummies(fs_e)
    rcid_k = {r: i+1 for i, r in enumerate(sorted(fs_e['ultimate_parent_rcid'].unique()))}
    fs_e['firmkey'] = fs_e['ultimate_parent_rcid'].map(rcid_k)
    n = fs_e['userid'].nunique()
    print(f"  Top 100 FS: {len(fs_e):,} obs, {n:,} users")
    return fs_e, n


def build_nonb4_audit_panel():
    """
    Build the full non-B4 audit person-year panel from Revelio audit role files.

    Returns (nonb4_panel_all DataFrame, ANNUAL_AT set, OTHER_AT set).
    The panel contains all non-B4 AT firms, period dummies (NB4_PERIODS), and an
    'at_firm' column for subsetting.
    """
    with open(ensure_data_file('interim/at_revelio_firm_mapping.json')) as f:
        AT_FIRM_MAPPING = json.load(f)

    B4_FIRMS = {'Deloitte', 'EY', 'KPMG', 'PwC'}
    EXCLUDE_AT = B4_FIRMS | {'Andersen'}

    all_company_to_firm = {}
    for firm, matches in AT_FIRM_MAPPING.items():
        if firm not in EXCLUDE_AT:
            for company_raw, _count in matches:
                all_company_to_firm[company_raw] = firm

    ALL_AT_NONB4 = set(f for f in AT_FIRM_MAPPING.keys() if f not in EXCLUDE_AT)
    OTHER_AT = ALL_AT_NONB4 - ANNUAL_AT

    aud1 = pd.read_feather(ensure_data_file("raw/revelio/revelioPosUsr_role_audit.feather"))
    aud2 = pd.read_feather(ensure_data_file("raw/revelio/revelioPosUsr_role_auditor.feather"))
    aud1 = aud1[aud1['country'] == 'United States'].copy()
    aud2 = aud2[aud2['country'] == 'United States'].copy()
    raw = pd.concat([aud1, aud2], ignore_index=True)
    del aud1, aud2

    raw['at_firm'] = raw['company_raw'].map(all_company_to_firm)
    raw = raw[raw['at_firm'].notna()].copy()
    raw = raw.sort_values(['user_id', 'startdate', 'enddate']).drop_duplicates(
        subset=['user_id', 'position_id'], keep='first')
    raw['startdate'] = pd.to_datetime(raw['startdate'], errors='coerce')
    raw['enddate'] = pd.to_datetime(raw['enddate'], errors='coerce')
    raw = raw[raw['startdate'].notna() & raw['enddate'].notna()]
    raw = raw[raw['startdate'] <= raw['enddate']]

    # Spell aggregation
    raw = raw.sort_values(['user_id', 'at_firm', 'startdate'])
    raw['new_spell'] = (
        (raw['user_id'] != raw['user_id'].shift(1)) |
        (raw['at_firm'] != raw['at_firm'].shift(1))
    ).fillna(True).astype(int)
    raw['spell_id'] = raw['new_spell'].cumsum()
    raw['spell_startdate'] = raw.groupby('spell_id')['startdate'].transform('min')
    raw['spell_enddate'] = raw.groupby('spell_id')['enddate'].transform('max')
    spells = raw.drop_duplicates(['user_id', 'spell_id'], keep='last').copy()
    spells['start_year'] = spells['spell_startdate'].dt.year.clip(lower=1990)
    spells['end_year'] = spells['spell_enddate'].dt.year.clip(upper=2024)
    spells = spells[(spells['end_year'] - spells['start_year'] + 1) > 0]
    spells['position_year'] = [
        list(range(s, e + 1)) for s, e in zip(spells['start_year'], spells['end_year'])
    ]
    panel = spells[['user_id', 'at_firm', 'sex_predicted', 'ethnicity_predicted',
                    'spell_startdate', 'spell_enddate', 'position_year']].explode('position_year', ignore_index=True)
    panel['position_year'] = panel['position_year'].astype(int)
    panel = panel.sort_values(['user_id', 'position_year', 'spell_enddate'])
    panel = panel.drop_duplicates(subset=['user_id', 'position_year'], keep='last')

    # Education
    nonb4_users = set(panel['user_id'].unique())
    edu_raw = pd.read_feather(ensure_data_file("raw/revelio/revelioEdu_role_combined.feather"))
    edu_raw = edu_raw[edu_raw['user_id'].isin(nonb4_users)].copy()
    edu_raw = edu_raw[edu_raw['degree'].isin(['Bachelor', 'Master', 'MBA', 'Doctor'])].copy()
    edu_raw['degree_rank'] = edu_raw['degree'].map({'Doctor': 4, 'MBA': 3, 'Master': 2, 'Bachelor': 1})
    edu_raw['enddate'] = pd.to_datetime(edu_raw['enddate'], errors='coerce').fillna(pd.to_datetime('2025-10-01'))
    edu = (edu_raw.sort_values(['user_id', 'degree_rank', 'enddate'], ascending=[False, True, True])
           .groupby('user_id').tail(1)[['user_id', 'university_name', 'degree']])
    edu['university_name'] = edu['university_name'].apply(lambda x: school_mapping.get(x, 'other'))
    panel = panel.merge(edu, on='user_id', how='left')
    panel['masterorhigher'] = panel['degree'].isin(['Master', 'MBA', 'Doctor']).fillna(False).astype(int)
    panel['top_university'] = (panel['university_name'] != 'other').fillna(False).astype(int)

    panel['female'] = (panel['sex_predicted'] == 'F').astype(int)
    panel['year'] = panel['position_year']
    panel['yearfirst'] = panel.groupby('user_id')['year'].transform('min')
    eth = panel['ethnicity_predicted'].fillna('')
    panel['api'] = (eth == 'API').astype(int)
    panel['black'] = (eth == 'Black').astype(int)
    panel['other'] = (~eth.isin(['White', 'API', 'Black', 'Hispanic', ''])).astype(int)

    # Retained
    nxt = panel[['user_id', 'position_year']].copy()
    nxt['position_year'] = nxt['position_year'] - 1
    nxt['retained'] = 1
    panel = panel.merge(nxt, on=['user_id', 'position_year'], how='left')
    panel['retained'] = panel['retained'].fillna(0).astype(int)
    panel = panel[panel['year'] <= 2023].copy()

    panel['userid'] = panel['user_id'].astype('category').cat.codes + 1
    add_nb4_period_dummies(panel)

    print(f"  Non-B4 AT panel: {len(panel):,} obs, {panel['user_id'].nunique():,} users, "
          f"{panel['at_firm'].nunique()} firms")
    return panel, ANNUAL_AT, OTHER_AT
