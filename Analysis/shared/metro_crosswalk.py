"""
Utilities for mapping ZIP codes and Revelio metro areas to CBSA codes.

Data sources (stored on R2, downloaded on first use):
  - raw/census/zip_cbsa.csv: ZIP5 → CBSA code (Census ZCTA-County + OMB delineation)
  - raw/census/cbsa_revelio_metro.csv: Revelio metro_area → CBSA code (manually reviewed)
"""
import os
import pandas as pd
from shared.r2 import ensure_data_file


def load_zip_cbsa():
    """Load ZIP5 → CBSA crosswalk. Returns DataFrame with columns: zip5, cbsa_code, cbsa_title."""
    path = ensure_data_file('raw/census/zip_cbsa.csv')
    df = pd.read_csv(path, dtype={'zip5': str, 'CBSA Code': 'Int64'})
    df = df.rename(columns={'CBSA Code': 'cbsa_code', 'CBSA Title': 'cbsa_title'})
    df = df[df['cbsa_code'].notna()][['zip5', 'cbsa_code']].copy()
    df['cbsa_code'] = df['cbsa_code'].astype(int)
    return df


def load_revelio_to_cbsa():
    """Load Revelio metro_area → CBSA crosswalk. Returns DataFrame with columns: revelio_metro, cbsa_code."""
    path = ensure_data_file('raw/census/cbsa_revelio_metro.csv')
    df = pd.read_csv(path)
    return df[['revelio_metro', 'cbsa_code']].copy()


def add_cbsa_to_companies(df, zip_col='zip', city_col=None, state_col=None,
                          cbsa_col='cbsa_code'):
    """Add CBSA code to a company DataFrame based on ZIP code.

    Uses a two-step approach:
      1. Primary: ZIP5 → CBSA via Census ZCTA crosswalk
      2. Fallback: city + state → CBSA (for PO Box ZIPs not in ZCTA data)

    The fallback is built from successfully matched records in the same
    DataFrame, so it requires no external geocoding.

    Args:
        df: DataFrame with a ZIP code column
        zip_col: name of the ZIP code column
        city_col: optional city column for fallback matching
        state_col: optional state column for fallback matching
        cbsa_col: name for the output CBSA code column

    Returns:
        DataFrame with cbsa_col added. Unmatched rows get NaN.
    """
    zip_cbsa = load_zip_cbsa()
    df = df.copy()
    df['_zip5'] = df[zip_col].astype(str).str[:5].str.zfill(5)
    df = df.merge(zip_cbsa, left_on='_zip5', right_on='zip5', how='left')
    df = df.drop(columns=['_zip5', 'zip5'], errors='ignore')
    df = df.rename(columns={'cbsa_code': cbsa_col})

    # Fallback: for unmatched US records, infer CBSA from city+state
    if city_col and state_col:
        matched = df[df[cbsa_col].notna()]
        if len(matched) > 0:
            city_lookup = (
                matched.groupby([city_col, state_col])[cbsa_col]
                .agg(lambda x: x.mode().iloc[0] if len(x) > 0 else None)
                .reset_index().rename(columns={cbsa_col: '_cbsa_fallback'})
            )
            unmatched_mask = df[cbsa_col].isna()
            df = df.merge(city_lookup, on=[city_col, state_col], how='left')
            df.loc[unmatched_mask & df['_cbsa_fallback'].notna(), cbsa_col] = \
                df.loc[unmatched_mask & df['_cbsa_fallback'].notna(), '_cbsa_fallback']
            df = df.drop(columns=['_cbsa_fallback'])

    return df


def add_cbsa_to_auditors(df, metro_col='metro_area', cbsa_col='cbsa_code'):
    """Add CBSA code to an auditor DataFrame based on Revelio metro_area.

    Args:
        df: DataFrame with a Revelio metro_area column
        metro_col: name of the metro area column
        cbsa_col: name for the output CBSA code column

    Returns:
        DataFrame with cbsa_col added. Unmatched rows (nonmetro, missing) get NaN.
    """
    rev_cbsa = load_revelio_to_cbsa()
    df = df.merge(rev_cbsa, left_on=metro_col, right_on='revelio_metro', how='left')
    df = df.drop(columns=['revelio_metro'], errors='ignore')
    df = df.rename(columns={'cbsa_code': cbsa_col})
    return df
