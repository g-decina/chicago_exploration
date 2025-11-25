import json
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import requests
import streamlit as st
import os
import requests
import streamlit as st
import google.auth.transport.requests
import google.oauth2.id_token
import logging

from shapely.geometry import shape, MultiPoint

from utils.config import *

logger = logging.getLogger('gunicorn.error')

# -----------------------
# TOKEN WRAPPER
# -----------------------

def get_id_token(url):
    try:
        auth_req = google.auth.transport.requests.Request()
        return google.oauth2.id_token.fetch_id_token(auth_req, url)
    except Exception as e:
        logger.warning(f"Could not fetch ID token: {e}")
        return None

# -----------------------
# CACHING FUNCTION
# -----------------------

@st.cache_data(ttl=5)
def get_api_data(
    endpoint,
    params=None
):
    headers = {}
    token = get_id_token(BACKEND_URL)    
    if token:
        headers['Authorization'] = f'Bearer {token}'
    else:
        logger.warning('Request sent without Auth token.')

    url = f'{BACKEND_URL}/{endpoint}'
    try:
        r = requests.get(
            url, 
            params=params, 
            headers=headers,
            timeout=TIMEOUT
        )
        r.raise_for_status()
        return r
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            st.error('Access Denied (403).')
        else:
            st.error(f'Error API fetching {endpoint}: {e}')
    except requests.RequestException as e:
        st.error(f'Error API fetching {endpoint}: {e}')
        return None

# -----------------------
# MAIN GET FUNCTIONS
# -----------------------

@st.cache_data
def get_activity_codes():
    response = get_api_data('codes')
    if response.status_code == 200:
        return response.json()
    else:
        st.error('Failed to load activity codes.')
        return {}

@st.cache_data
def get_geojson(
    act_codes, clustering=False, eps=0.02, min_samples=5
):
    params={
        'act_codes': act_codes,
        'clustering': clustering,
        'eps': eps,
        'min_samples': min_samples
    }
    response = get_api_data('geojson', params=params)
    if response.status_code==200:
        try:
            return response.json()
        except Exception as e:
            st.error(f'Failed to parse GeoJSON: {e}')
            return None
    elif response.status_code == 204:
        return None
    else:
        st.error(f'Backend error({response.status_code}): {response.text}')
        return None
    
# -----------------------
# OBSOLETE
# -----------------------

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