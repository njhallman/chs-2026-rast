"""
Big 4 firm identification: raw Revelio employer strings to canonical firms.

Single source of truth for the primary sample. Two consumers:
  - Analysis/pipeline/06_build_interim.py -- applies it to build the audit panel
  - Analysis/tables/firm_names.py         -- renders it as the appendix table

Used only via Series.map(), so key order does not affect any result. The order
below is the order the appendix table displays; keep it stable so the generated
table stays byte-identical.

Note: Analysis/shared/benchmark_utils.py deliberately keeps a SEPARATE Big 4
mapping that also includes 'Deloitte Tax LLP'. That one identifies Big 4 *tax*
practices for the benchmark figures; this one identifies the audit practices
that make up the primary sample. They are not interchangeable.
"""

AUDIT_FIRM_MAPPING = {
    # PwC
    'PwC': 'pwc',
    'PricewaterhouseCoopers': 'pwc',
    'PricewaterhouseCoopers LLP': 'pwc',
    'PricewaterhouseCoopers, LLP': 'pwc',
    'PriceWaterhouseCoopers': 'pwc',
    'Pricewaterhouse Coopers': 'pwc',
    'Price Waterhouse Coopers': 'pwc',
    # Deloitte
    'Deloitte': 'deloitte',
    'Deloitte & Touche': 'deloitte',
    'Deloitte & Touche LLP': 'deloitte',
    'Deloitte & Touche, LLP': 'deloitte',
    'Deloitte and Touche': 'deloitte',
    'Deloitte (Accounting Firm)': 'deloitte',
    # EY
    'EY': 'ey',
    'Ernst & Young': 'ey',
    'Ernst & Young LLP': 'ey',
    'Ernst & Young, LLP': 'ey',
    'Ernst and Young': 'ey',
    'E & Y': 'ey',
    # KPMG
    'KPMG': 'kpmg',
    'KPMG US': 'kpmg',
    'KPMG LLP': 'kpmg',
    'KPMG, LLP': 'kpmg',
    'KPMG Audit': 'kpmg',
    'KPMG Advisory': 'kpmg',
}

AUDIT_FIRM_KEY = {'pwc': 1, 'ey': 2, 'deloitte': 3, 'kpmg': 4}

# Display names and the appendix table's two-firm column blocks
FIRM_DISPLAY_NAME = {'deloitte': 'Deloitte', 'ey': 'EY', 'kpmg': 'KPMG', 'pwc': 'PwC'}
FIRM_TABLE_BLOCKS = [('deloitte', 'ey'), ('kpmg', 'pwc')]


def values_for(firm_key):
    """Return the company_raw values mapped to firm_key, in mapping order."""
    return [raw for raw, key in AUDIT_FIRM_MAPPING.items() if key == firm_key]
