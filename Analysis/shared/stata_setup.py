"""
Initialize Stata via pystata and optionally install Stata packages.

The regression tables are estimated in Stata, called in-process through
pystata. You must supply your own Stata installation and licence; no licence
material is distributed with this repository.

Location and edition are discovered in this order:
    1. $STATA_PATH / $STATA_EDITION
    2. /Applications/Stata/ (macOS) or /usr/local/stata (Linux), edition 'se'

Required Stata packages: estout, ftools, reghdfe, outreg2, coefplot, ppmlhdfe.
Install them once with `python tools/install_stata_packages.py`.
"""
import os
import platform
import time

# Stata packages the analysis depends on
REQUIRED_PACKAGES = ['estout', 'require', 'reghdfe', 'ftools',
                     'outreg2', 'coefplot', 'ppmlhdfe']


def _default_stata_dir():
    return '/Applications/Stata/' if platform.system() == 'Darwin' else '/usr/local/stata'


def resolve_stata():
    """Return (stata_dir, edition), raising if Stata is not where we looked."""
    stata_dir = os.environ.get('STATA_PATH') or _default_stata_dir()
    edition = os.environ.get('STATA_EDITION', 'se')

    if not os.path.isdir(stata_dir):
        raise FileNotFoundError(
            f"Stata not found at {stata_dir}.\n"
            "The regression tables require Stata SE 18+ with reghdfe and estout. "
            "Set STATA_PATH to your installation directory (and STATA_EDITION if "
            "not 'se'). See SETUP.md."
        )
    return stata_dir, edition


def init_stata(install_packages=False):
    """
    Configure and return the pystata stata module.

    Parameters
    ----------
    install_packages : bool
        If True, install required Stata packages (estout, reghdfe, etc.).
        Only needed on first run or after a Stata reinstall.
    """
    stata_dir, edition = resolve_stata()

    try:
        import stata_setup
    except ImportError as e:
        raise ImportError(
            "The 'stata_setup' package is required to call Stata from Python. "
            "Install it with: pip install stata_setup"
        ) from e

    stata_setup.config(stata_dir, edition, splash=False)
    from pystata import stata

    if install_packages:
        for package in REQUIRED_PACKAGES:
            try:
                _run_stata_command(stata, f'ssc install {package}, replace')
            except Exception as e:
                print(f'Note: {package} install returned: {e}')

    return stata


def _run_stata_command(stata, cmd, max_retries=3):
    for attempt in range(max_retries):
        try:
            stata.run(cmd)
            return
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt)
