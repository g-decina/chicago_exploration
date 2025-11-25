import geopandas as gpd
import io
import logging
import json

from functools import lru_cache
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response, StreamingResponse, JSONResponse, FileResponse
from typing import Tuple, List

from app.config import *
from app.utils.dataloader import load_data
from app.utils.plotting import plot_geodata
from app.utils.clustering import apply_clustering
from app.utils.codes import list_codes

router = APIRouter()
logger = logging.getLogger('gunicorn.error')

# ------------------------------
# GLOBAL STATE
# ------------------------------
try:
    logger.info('Loading Master Dataset into Memory...')
    MASTER_GDF = load_data() 
    logger.info(f'Data Loaded. Rows: {len(MASTER_GDF)}')
except Exception as e:
    logger.critical(f'CRITICAL: Failed to load data: {e}')
    MASTER_GDF = gpd.GeoDataFrame()

# ------------------------------
# CACHED FUNCTIONS
# ------------------------------

@lru_cache(maxsize=128)
def get_processed_clusters(
    codes: list[str],
    clustering: bool,
    eps: float,
    min_samples: int
) -> str:
    '''
    Perofrms filtering and clustering.
    Returns a JSON string (cached).
    '''
    
    if not codes:
        return '{}'
    
    filtered_gdf = MASTER_GDF[MASTER_GDF[ACT_COL].isin(codes)].copy()
    
    if filtered_gdf.empty:
        return '{}'

    if clustering:
        try:
            filtered_gdf = apply_clustering(
                gdf=filtered_gdf, 
                eps=eps, 
                min_samples=min_samples
            )
        except Exception as e:
            logger.error(f'Clustering failed: {e}')
            pass 

    return filtered_gdf.to_crs(CRS).to_json()

# ------------------------------
# API ROUTES
# ------------------------------

@router.get('/codes')
def get_codes():
    return list_codes(MASTER_GDF)

@router.get('/geojson')
def get_geojson(
    act_codes: list[str]=Query(...), 
    clustering: bool=False, 
    eps: float=0.02,
    min_samples: int=5
):
    '''
    Endpoint that acts as a wrapper around the cached function.
    '''
    # 1. Validate Input
    if not act_codes:
        return JSONResponse(status_code=400, content={'message': 'No codes provided'})

    # 2. Convert List to Tuple (necessary for caching)
    codes = tuple(sorted(act_codes))

    # 3. Call Cached Function
    geojson_str = get_processed_clusters(codes, clustering, eps, min_samples)
    
    # 4. Handle Empty Results
    if geojson_str == '{}':
        return Response(status_code=204)

    # 5. Return Pre-calculated JSON
    return JSONResponse(content=json.loads(geojson_str))

@router.get('/points')
def get_lean_points(
    act_codes: List[str] = Query(...)
):
    '''
    Fast path for simple coordinate lists.
    '''
    # Direct memory filter (No I/O)
    filtered_gdf = MASTER_GDF[MASTER_GDF[ACT_COL].isin(act_codes)]
    
    if filtered_gdf.empty:
        return []

    # Fast formatting
    data = filtered_gdf[[NAME_COL, 'geometry']].copy()
    data['lat'] = data.geometry.y # GeoPandas uses x=lon, y=lat
    data['lon'] = data.geometry.x
    
    return data[['lat', 'lon', NAME_COL]].values.tolist()