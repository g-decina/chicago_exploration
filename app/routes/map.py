import geopandas as gpd
import io
import json

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse

from app.config import *
from app.utils.dataloader import load_data
from app.utils.plotting import plot_geodata
from app.utils.clustering import apply_clustering
from app.utils.codes import list_codes

router = APIRouter()

def load_overlay(levels):
    res = {}
    
    if 'city' in levels:
        res['city'] = gpd.read_file(CITY_FILE)
    if 'neighborhoods' in levels:
        res['neighborhoods'] = gpd.read_file(NEIGH_FILE)
    if 'com_areas' in levels:
        res['com_areas'] = gpd.read_file(COM_AREAS_FILE)
    
    return res
    
@router.get('/map')
def render_map(
    act_codes: list[str]=Query(...),
    clustering: bool=False,
    eps: float=0.02,
    min_samples: int=5,
    marker_size: float=2.0,
    overlay_levels: list[str]=[]
):
    gdf = load_data(act_codes)
    
    if clustering:
        try:
            gdf = apply_clustering(
                gdf=gdf, 
                eps=eps, 
                min_samples=min_samples
            )
        except TypeError as e:
            print(f'Failed to render map: {e}')
            
    overlay = load_overlay(overlay_levels)
    try:
        img_bytes=plot_geodata(
            gdf=gdf,
            overlay=overlay,
            marker_size=marker_size
        )
    except TypeError as e:
        print(f'Failed to plot data: {e}')
    return StreamingResponse(io.BytesIO(img_bytes), media_type='image/png')

@router.get('/codes')
def get_codes():
    return list_codes()

@router.get('/geojson')
def get_geojson(
    act_codes: list[str]=Query(...), 
    clustering: bool=False, 
    eps: float=0.02,
    min_samples: int=5
):
    gdf=load_data(act_codes)
    if gdf.empty:
        return JSONResponse(status_code=204, content={'message': 'No data found.'})
    if clustering:
        try:
            gdf=apply_clustering(
                gdf=gdf, 
                eps=eps, 
                min_samples=min_samples
            )
        except Exception as e:
            return JSONResponse(
                status_code=500, content={'error': f'Clustering failed: {e}'}
            )
        
    return JSONResponse(content=json.loads(gdf.to_crs(CRS).to_json()))

@router.get('/points')
def get_lean_points(
    act_codes: list[str]=Query(...)
):
    gdf=load_data(act_codes)
    data=gdf[['geometry', NAME_COL]].copy()
    data['lat'] = data.geometry.x
    data['lon'] = data.geometry.y
    return data[['lat', 'lon', NAME_COL]].values.tolist()

@router.get('/geojson/neighborhoods')
def get_neighborhoods_geojson():
    """
    Serves the neighborhoods GeoJSON file.
    """
    try:
        return FileResponse(NEIGH_FILE, media_type='application/json')
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Neighborhoods file not found.")

@router.get('/geojson/com_areas')
def get_com_areas_geojson():
    """
    Serves the community areas GeoJSON file.
    """
    try:
        return FileResponse(COM_AREAS_FILE, media_type='application/json')
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Community areas file not found.")

@router.get('/geojson/city')
def get_city_geojson():
    """
    Serves the city boundary GeoJSON file.
    """
    try:
        return FileResponse(CITY_FILE, media_type='application/json')
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="City file not found.")