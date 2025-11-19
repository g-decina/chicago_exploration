import folium
import re
import requests
import streamlit as st

from streamlit_folium import st_folium
from folium.plugins import FastMarkerCluster

from utils.utils import *
from utils.config import *

st.set_page_config(page_title='Interactive Map', layout='wide')
st.title('Interactive Map')

# --- Caching Function ---
@st.cache_data(ttl=5, show_spinner='Fetching data from API...')
def get_api_data(
    endpoint,
    params=None
):
    try:
        url = f'{BACKEND_URL}/{endpoint}'
        r = requests.get(url, params=params, timeout=TIMEOUT)
        return r.json()
    except requests.RequestException as e:
        st.error(f'Error API fetching {endpoint}: {e}')
        return None

# --- Sidebar ---
if 'trigger' not in st.session_state:
    st.session_state['trigger'] = False

def trigger_map():
    st.session_state['trigger'] = True
    
with st.sidebar:
    st.header('Filters')
    
    activity_list = fetch_activity_codes()
    activity_labels = list(activity_list)
    
    selected_codes=st.multiselect(
        'Activity Codes',
        options=activity_labels,
        default=[],
        help='Select the activity codes to display.'
    )
    
    marker_size = st.slider('Dot size', 2.0, 10.0, 4.0, step=0.5)
    
    st.markdown('---')
    st.subheader('Clustering')
    enable_clustering = st.checkbox('Activate clustering (HDBSCAN)', value=False)
    miles = st.slider('Max. distance (miles)', 0.1, 5.0, 1.0, step=0.05, disabled=not enable_clustering)
    eps = 0.00025259 * miles
    min_samples = st.slider('Min. samples per cluster', 1, 20, 5, disabled=not enable_clustering)
    
    st.markdown('---')
    generate = st.sidebar.button('Generate map', on_click=trigger_map)

# --- Main logic ---
if 'map' not in st.session_state:
    st.session_state['map'] = None

map_placeholder = st.empty()

if st.session_state.get('trigger', False):
    with st.spinner('Map loading...'):
        if not selected_codes:
            st.warning('Please select at least one activity code.')
            st.session_state['trigger'] = False
            st.rerun()
        
        geojson_data = get_api_data(
            'geojson',
            params={
                'act_codes': selected_codes,
                'clustering': enable_clustering,
                'eps': eps,
                'min_samples': min_samples
            }
        )
        
        if not geojson_data or not geojson_data.get('features'):
            st.warning('No data returned for the selected filters.')
            st.session_state['trigger'] = False
            st.rerun()
        
        center, zoom = get_bounds_from_geojson(geojson_data)
        m = folium.Map(location=center, zoom_start=zoom, tiles='cartodb positron')
        
        if enable_clustering:
            cluster_colors = get_cluster_colormap(geojson_data)
            
            for feature in geojson_data['features']:
                if not feature.get('geometry'):
                    continue
                
                coords=feature['geometry']['coordinates']
                name=feature['properties']['doing_business_as_name']
                cluster_id=feature.get('properties', {}).get('cluster', 'N/A')
                
                if cluster_id == -1:
                    cluster_name = 'Noise'
                    radius = marker_size * 0.5
                    opacity = 0.5
                else:
                    cluster_name = f'Cluster {cluster_id}'
                    radius = marker_size
                    opacity = 0.8
                
                color = cluster_colors.get(cluster_id, '#FFFFFF')
                
                tooltip_text=f'{name} — {cluster_name}'
                
                folium.CircleMarker(
                    location=[coords[1], coords[0]],
                    radius=marker_size,
                    color=color,
                    fill=True,
                    fill_opacity=opacity,
                    weight=1,
                    tooltip=tooltip_text
                ).add_to(m)
                
        else:
            for feature in geojson_data['features']:
                if not feature.get('geometry'):
                    continue
                
                coords = feature['geometry']['coordinates']
                tooltip_text = feature['properties']['doing_business_as_name']
            
                folium.CircleMarker(
                    location=[coords[1], coords[0]], 
                    radius=marker_size,
                    color='#3676E3',
                    tooltip=tooltip_text
                ).add_to(m)
        
        folium.LayerControl().add_to(m)
        
        st.session_state['map'] = m
    
    st.session_state['trigger'] = False

if st.session_state['map']:
    with map_placeholder.container():
        st_folium(
            st.session_state['map'], 
            use_container_width=True,
            key='folium_map_final'
        )
else:
    st.info('Click \'Generate map\' in the sidebar to get started.')