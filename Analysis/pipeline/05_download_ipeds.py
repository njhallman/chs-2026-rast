"""
05_download_ipeds.py — Download IPEDS Completions data from NCES.

Data source: NCES Integrated Postsecondary Education Data System (IPEDS)
Authentication: None (public data)
Survey: Completions (C) — awards/degrees conferred by field, gender, race

We download the "C{year}_A.csv" files which contain completions data at
the CIP code level by institution. We filter to CIP code 52.0301
(Accounting) at the Bachelor's level in the analysis scripts.

URL pattern: https://nces.ed.gov/ipeds/datacenter/data/C{year}_A.zip
Each zip contains a C{year}_A.csv file.

Outputs (in Analysis/Data/raw/ipeds/):
    - C{year}_A.csv for years 2000-2023

Usage:
    python Analysis/pipeline/05_download_ipeds.py
    python Analysis/pipeline/05_download_ipeds.py --force
"""
import sys, os, argparse, zipfile, io
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import requests
from shared.paths import data_dir

OUTPUT_DIR = os.path.join(data_dir, 'raw', 'ipeds')
os.makedirs(OUTPUT_DIR, exist_ok=True)

YEARS = range(2000, 2024)
URL_TEMPLATE = 'https://nces.ed.gov/ipeds/datacenter/data/C{year}_A.zip'


def download_year(year, force=False):
    """Download and extract IPEDS completions data for a single year."""
    csv_path = os.path.join(OUTPUT_DIR, f'C{year}_A.csv')

    if os.path.exists(csv_path) and not force:
        return True

    url = URL_TEMPLATE.format(year=year)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  {year}: FAILED ({e})")
        return False

    # Extract CSV from zip
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        csv_name = f'c{year}_a.csv'
        # Case-insensitive search for the CSV
        names = zf.namelist()
        match = [n for n in names if n.lower() == csv_name.lower()]
        if not match:
            print(f"  {year}: FAILED (no {csv_name} in zip, found: {names})")
            return False
        with open(csv_path, 'wb') as f:
            f.write(zf.read(match[0]))

    size_kb = os.path.getsize(csv_path) / 1024
    print(f"  {year}: {size_kb:.0f} KB")
    return True


def main():
    parser = argparse.ArgumentParser(description='Download IPEDS completions data')
    parser.add_argument('--force', action='store_true', help='Re-download existing files')
    args = parser.parse_args()

    print("=" * 60)
    print("  05_download_ipeds.py — IPEDS Completions data from NCES")
    print("=" * 60)
    print(f"\n  Years: {min(YEARS)}-{max(YEARS)}")
    print(f"  Output: {OUTPUT_DIR}\n")

    success = 0
    for year in YEARS:
        if download_year(year, force=args.force):
            success += 1

    print(f"\n  Downloaded {success}/{len(list(YEARS))} years.")
    if success < len(list(YEARS)):
        print("  Some years may not be available yet on the NCES server.")
    print("Done.")


if __name__ == '__main__':
    main()
