"""
Produces: LaTeX/Figures/retentionGapMap.png
Side-by-side choropleth maps showing the female-male retention gap
by state, pre-Form AP (before 2015) vs post-Form AP (2015 onward).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from shared.paths import figures_dir
from shared.data_loader import load_b4_exp

print("Creating retentionGapMap.png")

df = load_b4_exp()
df = df[df['state'].notna()].copy()

# Map DC
df['state'] = df['state'].replace({'Washington, D.C.': 'District of Columbia'})

# Compute retention gap by state and period
def retention_gap(group):
    fem = group[group['female'] == 1]['retained'].mean()
    mal = group[group['female'] == 0]['retained'].mean()
    n = len(group)
    return pd.Series({'gap': fem - mal, 'n': n})

pre = df[df['year'] < 2015].groupby('state').apply(retention_gap).reset_index()
post = df[df['year'] >= 2015].groupby('state').apply(retention_gap).reset_index()

# Require at least 1,000 total auditor-year observations
MIN_N = 1000
total_by_state = pd.concat([pre[['state','n']], post[['state','n']]]).groupby('state')['n'].sum()
valid_states = total_by_state[total_by_state >= MIN_N].index
pre = pre[pre['state'].isin(valid_states)]
post = post[post['state'].isin(valid_states)]

print(f"  Pre-Form AP: {len(pre)} states")
print(f"  Post-Form AP: {len(post)} states")
print(f"  Pre gap range: [{pre['gap'].min():.3f}, {pre['gap'].max():.3f}]")
print(f"  Post gap range: [{post['gap'].min():.3f}, {post['gap'].max():.3f}]")

# Load US states shapefile
us_states = gpd.read_file(
    'https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json'
)

# Merge
pre_geo = us_states.merge(pre, left_on='name', right_on='state', how='left')
post_geo = us_states.merge(post, left_on='name', right_on='state', how='left')

# Symmetric colormap centered at 0
vmax = max(abs(pre['gap'].min()), abs(pre['gap'].max()),
           abs(post['gap'].min()), abs(post['gap'].max()))
vmax = np.ceil(vmax * 100) / 100  # round up to nearest 0.01
vmin = -vmax
norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)

# Plot
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5.5))

for ax, geo, title in [(ax1, pre_geo, 'Pre-Form AP (before 2015)'),
                         (ax2, post_geo, 'Post-Form AP (2015 onward)')]:
    # Continental US bounds
    ax.set_xlim(-130, -65)
    ax.set_ylim(24, 50)

    # Plot states with data
    geo.plot(column='gap', ax=ax, cmap='RdBu', norm=norm,
             edgecolor='gray', linewidth=0.3,
             missing_kwds={'color': 'lightgray', 'edgecolor': 'gray', 'linewidth': 0.3})
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.axis('off')

# Shared colorbar
sm = plt.cm.ScalarMappable(cmap='RdBu', norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=[ax1, ax2], orientation='horizontal',
                     fraction=0.04, pad=0.15, aspect=40)
cbar.set_label('Female retention rate − Male retention rate (pp)', fontsize=10)
cbar.ax.tick_params(labelsize=9)

plt.subplots_adjust(bottom=0.18)
out_path = os.path.join(figures_dir, 'retentionGapMap.png')
plt.savefig(out_path, dpi=200, bbox_inches='tight')
plt.close()

print(f"\nSaved {out_path}")
