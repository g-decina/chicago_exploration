import geopandas as gpd
from sklearn.cluster import HDBSCAN

def apply_clustering(
    gdf: gpd.GeoDataFrame,
    eps: float=0.02, 
    min_samples: int=5, 
    n_jobs: int=4
):
    if len(gdf) < min_samples:
        gdf['cluster'] = -1
        return gdf
    
    # Conversion to UTM Zone 16N (covers Illinois, Indiana, half of Wisconsin and Michigan)
    # This standard yields distances in meters to ensure consistency across lat and lon
    # For future reference: https://mangomap.com/robertyoung/maps/69585/what-utm-zone-am-i-in-#
    gdf_meters = gdf.to_crs(epsg=32616)
    
    coords = gdf_meters.geometry.apply(
        lambda geom: (geom.x, geom.y)
    ).tolist()
    
    clusterer=HDBSCAN(
        cluster_selection_method='leaf',
        cluster_selection_epsilon=eps,
        min_cluster_size=min_samples, 
        n_jobs=n_jobs
    )
    
    gdf['cluster']=clusterer.fit_predict(coords)
    return gdf