"""
Functions to load processed datasets from Analysis/Data/processed/.
Downloads from R2 on first access if the file is not yet local.
"""
import pandas as pd
from shared.r2 import ensure_data_file


def load_b4_exp():
    """Load Big 4 auditor employee-year panel (exploration/figures)."""
    return pd.read_feather(ensure_data_file("processed/revB4AudExp.feather"))


def load_b4_stata():
    """Load Big 4 auditor employee-year panel (Stata regressions)."""
    return pd.read_feather(ensure_data_file("processed/revB4AudStata.feather"))


def load_other_exp():
    """Load other financial services employee-year panel (exploration/figures)."""
    return pd.read_feather(ensure_data_file("processed/revOtherFsExp.feather"))


def load_other_stata():
    """Load other financial services employee-year panel (Stata regressions)."""
    return pd.read_feather(ensure_data_file("processed/revOtherFsStata.feather"))
