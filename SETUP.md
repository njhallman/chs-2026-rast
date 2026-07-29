# Setup

## Python

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

The analysis needs pandas, numpy, pyarrow, matplotlib, geopandas (for the state map),
`stata_setup` (to call Stata), and `wrds` (only for the download scripts). `requirements.txt` is
a frozen environment known to work; looser versions are generally fine, with the caveat about
figure rendering noted in the README.

## Stata

The regression tables are estimated in Stata, called in-process through `pystata`. **You must
supply your own Stata installation and licence** — none is distributed here.

- **Stata SE 18 or later** (MP works; set `STATA_EDITION=mp`)
- Packages: `estout`, `ftools`, `reghdfe`, `outreg2`, `coefplot`, `ppmlhdfe`

Point the code at your installation if it is not in the default location:

```bash
export STATA_PATH=/opt/stata18       # default: /Applications/Stata/ (macOS), /usr/local/stata (Linux)
export STATA_EDITION=se              # default: se
```

Then install the packages once:

```bash
python tools/install_stata_packages.py
```

Scripts that do not run regressions (the descriptive tables, and all figures except the
benchmark coefficient plots) work without Stata.

## LaTeX

Needed only to recompile the manuscript. On Debian/Ubuntu:

```bash
sudo apt-get install -y --no-install-recommends \
    latexmk texlive-latex-extra texlive-bibtex-extra biber \
    texlive-fonts-recommended texlive-plain-generic cm-super
```

`texlive-plain-generic` provides `tracklang.sty`, which `datetime2` needs; `cm-super` gives
vector T1 fonts so URLs are not bitmapped.

## Data

See [DATA_AVAILABILITY.md](DATA_AVAILABILITY.md). The short version: the licensed Revelio,
BoardEx, and Audit Analytics inputs are not in this repository and must be obtained through
WRDS. Non-proprietary inputs are committed under `Analysis/Data/public/`.

## Troubleshooting

### `ModuleNotFoundError: No module named 'sfi'`

`pystata` cannot see Stata's `ado/` tree. This usually means the Stata installation is
incomplete — the `ado`, `base`, `bins`, and `docs` archives were never extracted. Reinstall
Stata, or extract them by hand from the installation media into the Stata directory and run
`./setrwxp now`.

It can also mean Stata's Python interpreter differs from the one running the scripts. Set it
explicitly:

```bash
$STATA_PATH/stata-se -b -e 'python set exec /usr/bin/python3, permanently'
```

### SIGILL / exit code 132 on a virtual machine

Some virtualised CPUs lack instruction-set extensions (AVX, SSE4) that recent numpy, pandas, and
pyarrow builds assume, and that Stata's shared library uses when loaded through `pystata`. Stata
may work standalone while the in-process API crashes.

Use package builds that do not require AVX:

```bash
conda create -n chs -c conda-forge -y python=3.10 numpy=1.24.4 pandas=2.0.3 pyarrow=12.0.1
conda run -n chs pip install stata_setup
conda run -n chs python Analysis/run_all.py
```

### `06_build_interim.py` is killed with exit code 137

Exit 137 is the OOM killer. The Big 4 phase is modest, but the
other-financial-services phase concatenates all 54 per-role Revelio position
files into a single frame of roughly nine million rows and then filters it, which
needs **more than 16 GB of RAM** even after the memory reductions applied here
(reading only the surviving columns, narrowing the education file, and releasing
the position frame before education loads).

`07_prepare_data.py` has the same problem in the same place: its
other-financial-services half explodes that panel to roughly 14.9 million
worker-years and is likewise OOM-killed on 16 GB. Its Big 4 half completes and its
panels are written first.

If you hit either, run on a machine with more memory (32 GB is comfortable), or
skip that half: the other-financial-services panels feed only `topCompanies.tex`,
`benchmarkBB5IB.png` and `benchmarkOFS.png`. Everything else -- Tables 1 through 7
and the other five figures -- depends solely on the Big 4 panel, which builds in a
few GB and is written before the heavy phase begins in both scripts.

One consequence worth knowing: `07` writes `processed/sample_counts.json` last, so
a run that dies in the other-financial-services half leaves you with rebuilt Big 4
panels but no counts file, and Table 1 cannot be regenerated even though every
number in it comes from the Big 4 half. Calling `prepare_audit_data()` on its own
produces those counts.

### `geopandas` import failures

`retention_gap_map.py` is the only script that needs it. On a system without GDAL, install from
conda-forge (`conda install -c conda-forge geopandas`) rather than pip.

### A table does not reproduce

Fix the script that generates it. Never edit files in `LaTeX/Tables/` by hand — they are
generated output and the next run overwrites them. `python Analysis/verify_outputs.py` reports
which outputs differ and where.
