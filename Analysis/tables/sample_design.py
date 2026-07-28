"""
Produces: LaTeX/Tables/sampleDesign.tex
Sample construction table showing observation counts at each filtering step.
Uses interim screening counts (from 06_build_interim.py) and processed
sample counts (from 07_prepare_data.py).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import json
from shared.paths import data_dir, tables_dir
from shared.r2 import ensure_data_file

print("Creating sampleDesign.tex")

# Interim screening counts (from 06_build_interim.py)
with open(os.path.join(data_dir, 'interim', 'interim_screening_counts.json')) as f:
    ic = json.load(f)

# Processed sample counts (from 07_prepare_data.py)
with open(ensure_data_file("processed/sample_counts.json")) as f:
    pc = json.load(f)

# Auditor sample counts
init_u, init_p = ic['initial_users'], ic['initial_positions']
date_u, date_p = ic['date_drop_users'], ic['date_drop_positions']
edu_u, edu_p = ic['edu_drop_users'], ic['edu_drop_positions']
intern_u, intern_p = ic['intern_drop_users'], ic['intern_drop_positions']
screened_u, screened_p = ic['final_users'], ic['final_positions']

# Post-explosion counts from prepare_data
explode_u, explode_py = pc['ua2'], pc['uay1']
drop2023_u, drop2023_py = pc['uad5'], pc['uayd1']
primary_u, primary_py = pc['ua3'], pc['uay2']
badrank_u, badrank_py = pc['uad6'], pc['uayd2']
rank_u, rank_py = pc['ua4'], pc['uay3']

with open(f"{tables_dir}/sampleDesign.tex", 'w') as f:
    f.write(r"\begin{tabular}{ l c c c}")
    f.write("\n")
    f.write(r"\\[-1.8ex]\hline \hline \\[-1.8ex]")
    f.write("\n")
    f.write(r" & \underline{Unique employees} & \underline{Unique positions} & \underline{Employee-years} \\")
    f.write("\n")
    f.write(f"Auditors at Big 4 firms in Revelio data & {init_u:,} & {init_p:,} & \\\\")
    f.write("\n")
    f.write(f"\\quad Less positions with missing or invalid dates & ({date_u:,}) & ({date_p:,}) & \\\\")
    f.write("\n")
    f.write(f"\\quad Less auditors missing educational data & ({edu_u:,}) & ({edu_p:,}) & \\\\")
    f.write("\n")
    f.write(f"\\quad Less internship positions & \\underline{{({intern_u:,})}} & ({intern_p:,}) & \\\\")
    f.write("\n")
    f.write(f"Exploded to create auditor-year panel & {explode_u:,} & & {explode_py:,} \\\\")
    f.write("\n")
    f.write(f"\\quad Less auditor-years after 2023 & \\underline{{({drop2023_u:,})}} & & \\underline{{({drop2023_py:,})}} \\\\")
    f.write("\n")
    f.write(f"Primary sample & {primary_u:,} & & {primary_py:,} \\\\")
    f.write("\n")
    f.write(f"\\quad Less observations without reliable ranks & \\underline{{({badrank_u:,})}} & & \\underline{{({badrank_py:,})}} \\\\")
    f.write("\n")
    f.write(f"Sample for rank and promotion analysis & {rank_u:,} & & {rank_py:,} \\\\")
    f.write("\n")
    f.write(r"\\[-1.8ex]\hline \hline \\[-1.8ex]")
    f.write("\n")
    f.write(r"\end{tabular}")

print(f"Saved {tables_dir}/sampleDesign.tex")
