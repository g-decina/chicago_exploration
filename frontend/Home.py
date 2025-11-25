import folium
import re
import requests
import streamlit as st

from streamlit_folium import folium_static
from folium.plugins import FastMarkerCluster

from utils.utils import *
from utils.config import *

st.set_page_config(
        page_title='Mapping Chicago\'s Companies', 
        layout='wide',
        initial_sidebar_state='expanded'
        )

st.markdown("""
        <style>
                #MainMenu {visibility: hidden;}
                .stDeployButton {display:none;}
                footer {visibility: hidden;}
                /* Customize the sidebar title */
                [data-testid="stSidebarNav"]::before {
                        content: "Chicago Explorer";
                        margin-left: 20px;
                        margin-top: 20px;
                        font-size: 24px;
                        font-weight: bold;
                        color: #41B6E6;
                        position: relative;
                        top: 10px;
                }
        </style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 5])

with col1:
    # If you have a logo.png in your assets, uncomment this
    # image = Image.open('assets/chicago_star.png') 
    # st.image(image, width=100)
    st.markdown("# ✶✶✶✶")

with col2:
    st.title("Chicago Commercial Atlas")
    st.markdown("### *A Machine Learning-Powered Commercial Density Explorer*")

st.title('Mapping Chicago\'s Companies')
st.write(
    '''
    This application is designed to explore Chicago's economic geography.
    The dynamic map allows you to explore freely down to street-level data.
    ''')

st.info(
    '''
    **How it works:** This tool uses **Transformers (SBERT)** to clean messy business license data 
    and **Density Clustering (HDBSCAN)** to identify organic commercial districts in Chicago. \n
    Select a category on the sidebar, then click 'Generate Map' to begin.
    ''')

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
    activity_labels = tuple(activity_list)
    
    selected_code=st.selectbox(
        'Activity Codes',
        options=activity_labels,
        help='Select the activity codes to display.'
    )
    
    marker_size = st.slider('Dot size', 1.0, 10.0, 2.0, step=0.5)
    
    st.markdown('---')
    st.subheader('Clustering')
    enable_clustering = st.checkbox('Activate clustering', value=False)
    miles = st.slider(
        'Cluster Merging Distance (miles)', 
        min_value = 0.0, 
        max_value = 1.0,
        value = 0.0, 
        step = 0.05, 
        disabled = not enable_clustering,
        help = 'Distance threshold to merge clusters: clusters that have a gap closer than the specified distance between them will be merged together. \n\nSet to 0 for pure density-based clustering.')
    eps = 1609.34 * miles # Distances are calculated in meters; see app/utils/clustering.py
    min_samples = st.slider('Min. businesses per cluster', 1, 50, 10, disabled=not enable_clustering)
    
    st.markdown('---')
    generate = st.sidebar.button('Generate Map', on_click=trigger_map)

# --- Main logic ---
if 'map' not in st.session_state:
    st.session_state['map'] = None

map_placeholder = st.empty()

if st.session_state.get('trigger', False):
    with st.spinner('Map loading...'):
        if not selected_code:
            st.warning('Please select at least one activity code.')
            st.session_state['trigger'] = False
            st.rerun()
        
        geojson_data = get_api_data(
            'geojson',
            params={
                'act_codes': selected_code,
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
            
            noise_features = [f for f in geojson_data['features']
                            if f.get('properties', {}).get('cluster') == -1]
            clustered_features = [f for f in geojson_data['features']
                            if f.get('properties', {}).get('cluster') != -1]
            
            if noise_features:
                folium.GeoJson(
                    {'type': 'FeatureCollection', 'features': noise_features},
                    name='Noise Points',
                    marker=folium.Circle(
                        radius=marker_size * 0.5, color='#888888', fill_opacity=0.7
                    ),
                    tooltip=folium.GeoJsonTooltip(
                        fields=['doing_business_as_name', 'cluster'],
                        aliases=['Business Name:', 'Cluster:']
                    ),
                    zoom_on_click=True
                ).add_to(m)
            
            
            cluster_groups = {}
            for f in clustered_features:
                cid = f['properties']['cluster']
                coords = f['geometry']['coordinates']
                if cid not in cluster_groups: 
                    cluster_groups[cid] = []
                cluster_groups[cid].append(coords)
            
            hull_features = []
            for cid, points in cluster_groups.items():
                if len(points) < 3: continue
                
                hull = MultiPoint(points).convex_hull
                
                if hull.geom_type == 'Polygon':
                    exterior_coords = [[p[0], p[1]] for p in hull.exterior.coords]
                    
                    hull_features.append({
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Polygon',
                            'coordinates': [exterior_coords]
                        },
                        'properties': {'cluster': cid, 'tooltip': f'Cluster {cid} Territory'}
                    })

            if hull_features:
                folium.GeoJson(
                    {'type': 'FeatureCollection', 'features': hull_features},
                    name='Cluster Territories',
                    style_function=lambda x: {
                        'fillColor': cluster_colors.get(x['properties']['cluster'], '#3388ff'),
                        'color': cluster_colors.get(x['properties']['cluster'], '#3388ff'),
                        'weight': 2,
                        'fillOpacity': 0.1
                    },
                    tooltip=folium.GeoJsonTooltip(fields=['tooltip'], labels=False)
                ).add_to(m)
            
            if clustered_features:
                folium.GeoJson(
                    {'type': 'FeatureCollection', 'features': clustered_features},
                    name='Clustered Points',
                    marker=folium.CircleMarker(
                        radius=marker_size,
                    ),
                    tooltip=folium.GeoJsonTooltip(
                        fields=['doing_business_as_name', 'cluster'],
                        aliases=['Business Name:', 'Cluster:']
                    ),
                    style_function=lambda x: {
                        'fillColor': cluster_colors.get(x['properties']['cluster'], '#000000'),
                        'color': cluster_colors.get(x['properties']['cluster'], '#000000'),
                        'fillOpacity': 0.8,
                    },
                    zoom_on_click=True
                ).add_to(m)
                
        else:
            folium.GeoJson(
                geojson_data,
                name='Registered Businesses',
                marker=folium.CircleMarker(
                    radius=marker_size, color='#3676E3', fill_opacity=0.7
                ),
                tooltip=folium.GeoJsonTooltip(
                    fields=['doing_business_as_name'],
                    aliases=['Business Name:']
                ),
                zoom_on_click=True
            ).add_to(m)
        
        folium.LayerControl().add_to(m)
        
        st.session_state['map'] = m
    
    st.session_state['trigger'] = False


if st.session_state['map']:
    with map_placeholder.container():
        folium_static(
            st.session_state['map'],
            width=1400,
            height=700
        )