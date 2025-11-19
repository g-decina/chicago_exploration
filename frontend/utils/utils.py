import json
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import requests
import streamlit as st

from shapely.geometry import shape, MultiPoint

from utils.config import *

@st.cache_data
def fetch_activity_codes():
    response = requests.get(f'{BACKEND_URL}/codes')
    if response.status_code == 200:
        return response.json()
    else:
        st.error('Failed to load activity codes.')
        return {}

def fetch_geojson(
    act_codes, clustering=False, eps=0.02, min_samples=5
):
    params={
        'act_codes': act_codes,
        'clustering': clustering,
        'eps': eps,
        'min_samples': min_samples
    }
    resp = requests.get(f'{BACKEND_URL}/geojson', params=params)
    if resp.status_code==200:
        try:
            return resp.json()
        except Exception as e:
            st.error(f'Failed to parse GeoJSON: {e}')
            return None
    elif resp.status_code == 204:
        return None
    else:
        st.error(f'Backend error({resp.status_code}): {resp.text}')
        return None
    
def fetch_csv(naf_codes):
    try:
        r = requests.get(f'{BACKEND_URL}/data', params={'naf_codes': naf_codes})
        r.raise_for_status()
        return r.content
    except requests.RequestException as e:
        st.error(f'Erorr while downloading data: {e}')

def get_bounds_from_geojson(geojson):
    features = geojson.get('features', [])
    points = [shape(f['geometry']) for f in features if f['geometry'] is not None]
    if not points:
        return [41.9, 87.6], 10
    
    multipoint = MultiPoint(points)
    bounds = multipoint.bounds  # (minx, miny, maxx, maxy)
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    return center, 10

def fetch_data_geojson(act_codes, clustering, eps, min_samples):
    params = {
        'act_codes': act_codes,
        'clustering': clustering,
        'eps': eps,
        'min_samples': min_samples
    }
    try:
        r = requests.get(f'{BACKEND_URL}/geojson', params=params)
        r.raise_for_status()
        
        if r.status_code == 204:
            return None
        return r.json()
    except requests.RequestException as e:
        st.error(f'Error fetching data GeoJSON: {e}')
        return None
    except json.JSONDecodeError:
        st.error(f'Failed to decode GeoJSON data from backend.')
        return None

def fetch_overlay_geojson(level):
    try:
        r = requests.get(f'{BACKEND_URL}/geojson/{level}')
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        st.error(f'Error fetching data GeoJSON: {e}')
        return None
    
def get_cluster_colormap(geojson_data):
    """
    Generates a color dictionary for clusters.
    Noise (-1) is always grey.
    Valid clusters get distinct colors from a colormap.
    """
    features = geojson_data['features']
    
    all_ids = sorted(list(set(
        f['properties'].get('cluster', -1) for f in features
    )))
    
    real_clusters = [c for c in all_ids if c != -1]
    n_clusters = len(real_clusters)
    
    color_map = {}
    
    color_map[-1] = '#808080'
    
    if n_clusters > 0:
        cmap_name = 'tab20' if n_clusters <= 20 else 'nipy_spectral'
        cmap = cm.get_cmap(cmap_name)
        
        for i, cluster_id in enumerate(real_clusters):
            rgba = cmap(i)
            hex_code = mcolors.to_hex(rgba)
            color_map[cluster_id] = hex_code
            
    return color_map