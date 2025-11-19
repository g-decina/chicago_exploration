import geopandas as gpd
from sklearn.cluster._hdbscan.hdbscan import HDBSCAN

def apply_clustering(
    gdf: gpd.GeoDataFrame,
    eps: float=0.02, 
    min_samples: int=5, 
    n_jobs: int=4
):
    coords = gdf.geometry.apply(
        lambda geom: (geom.x, geom.y)
    ).tolist()
    
    clusterer=HDBSCAN(
        cluster_selection_epsilon=eps,
        min_cluster_size=min_samples, 
        n_jobs=n_jobs
    )
    
    gdf['cluster']=clusterer.fit_predict(coords)
    return gdf