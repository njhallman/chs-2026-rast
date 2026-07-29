#!/usr/bin/env python3
"""
Install the Stata packages the analysis needs, into your own Stata.

Run this once after installing Stata. It uses the Stata installation that
Analysis/shared/stata_setup.py discovers -- $STATA_PATH, or the platform default
(/Applications/Stata/ on macOS, /usr/local/stata on Linux).

No licence material is distributed with this repository; supply your own Stata.

Usage:
    python tools/install_stata_packages.py
    STATA_PATH=/opt/stata18 python tools/install_stata_packages.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Analysis'))

from shared.stata_setup import REQUIRED_PACKAGES, init_stata, resolve_stata  # noqa: E402


def main():
    stata_dir, edition = resolve_stata()
    print(f"Stata: {stata_dir} (edition {edition})")
    print(f"Installing {len(REQUIRED_PACKAGES)} packages: {', '.join(REQUIRED_PACKAGES)}\n")

    init_stata(install_packages=True)

    print("\nDone. Verify inside Stata with e.g.  which reghdfe")


if __name__ == '__main__':
    main()
