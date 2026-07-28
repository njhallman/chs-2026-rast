"""
Produces: LaTeX/Figures/stackPlot.png
Stacked area chart of Big 4 auditors by year, gender, and rank.
Requires: revB4AudExp
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter

from shared.paths import figures_dir
from shared.data_loader import load_b4_exp

print("Creating stackPlot.png")

revB4AudExp = load_b4_exp()
revB4AudExpSP = revB4AudExp.copy()
revB4AudExpSP.loc[revB4AudExpSP['badrankdummy'] == 1, 'positionrank'] = 0

revB4AudStata_grouped = (
    revB4AudExpSP.groupby(["year", "female", "positionrank"])
    .size()
    .reset_index(name="count")
)

revB4AudStata_pivot = revB4AudStata_grouped.pivot_table(
    index="year", columns=["female", "positionrank"], values="count", fill_value=0
)

male_cmap   = plt.cm.Blues
female_cmap = plt.cm.Greens
male_colors   = {rank: male_cmap(0.3 + 0.6 * (rank - 1) / 5)   if rank > 0 else male_cmap(0.1)   for rank in range(0, 7)}
female_colors = {rank: female_cmap(0.3 + 0.6 * (rank - 1) / 5) if rank > 0 else female_cmap(0.1) for rank in range(0, 7)}
patterns = {0: "", 1: "+", 2: "/", 3: ".", 4: "*", 5: "o", 6: "\\"}

rank_descriptions = {
    0: "Unknown Rank",
    1: "Staff",
    2: "Senior",
    3: "Manager",
    4: "Senior Manager",
    5: "Director",
    6: "Partner",
}

years = revB4AudStata_pivot.index
cumulative_data = np.zeros(len(years))

sorted_columns = sorted(
    revB4AudStata_pivot.columns,
    key=lambda col: (col[1], col[0])
)

fig, ax = plt.subplots(figsize=(12, 8))
cumulative_data = np.zeros(len(years))

for female, rank in sorted_columns:
    if (female, rank) not in revB4AudStata_pivot:
        continue
    data = revB4AudStata_pivot[(female, rank)]
    color   = female_colors[rank] if female else male_colors[rank]
    pattern = patterns[rank]
    ax.fill_between(
        years, cumulative_data, cumulative_data + data,
        color=color, hatch=pattern, edgecolor="black", linewidth=0.5
    )
    cumulative_data += data

handles = [
    mpatches.Patch(facecolor="white", edgecolor="black", hatch=patterns[rank], label=desc)
    for rank, desc in rank_descriptions.items()
]

ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))
plt.xlabel("Year", fontsize=18)
plt.xlim([1975, 2022])
plt.ylabel("Count", fontsize=18)
plt.legend(handles=handles, loc="upper left", fontsize=14)
ax.tick_params(axis='x', labelsize=16)
ax.tick_params(axis='y', labelsize=16)
plt.tight_layout()

plt.savefig(f"{figures_dir}/stackPlot.png", transparent=False, dpi=500, bbox_inches='tight')
plt.close()
print(f"Saved {figures_dir}/stackPlot.png")
