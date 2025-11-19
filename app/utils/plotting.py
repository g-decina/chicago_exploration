import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import io

from app.config import *

def plot_geodata(
    gdf: gpd.GeoDataFrame,
    overlay: dict[str, gpd.GeoDataFrame],
    marker_size: int=2.0
) -> gpd.GeoDataFrame:
    fig, ax = plt.subplots(figsize=(12, 12))
    overlay.get('city', gpd.GeoDataFrame).plot(
        ax=ax, color=BACKGROUND_COLOR, edgecolor=EDGE_COLOR, linewidth=2.0
    )
    
    if 'neighborhoods' in overlay:
        overlay.get('neighborhoods').plot(
        ax=ax, color=BACKGROUND_COLOR, edgecolor=EDGE_COLOR, linewidth=1.3
    )
    if 'community_areas' in overlay:
        overlay.get('community_areas').plot(
        ax=ax, color=BACKGROUND_COLOR, edgecolor=EDGE_COLOR, linewidth=0.7
    )
        
    if 'cluster' in gdf.columns:
        clustered=gdf[gdf['cluster'] != -1]
        noise = gdf[gdf['cluster'] == -1]
        clustered.plot(ax=ax, column='cluster', categorical=True,
                    cmap='Set3', markersize=marker_size, alpha=0.7)
        noise.plot(ax=ax, color='grey', markersize=marker_size, alpha=0.5)
    elif not gdf.empty:
        gdf.plot(ax=ax, color=DOT_COLOR, markersize=marker_size, alpha=0.7)
        
    ax.axis('off')
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=1500, bbox_inches='tight')
    buf.seek(0)
    
    return buf.getvalue()