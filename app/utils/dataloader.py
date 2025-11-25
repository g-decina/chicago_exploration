import pandas as pd
import geopandas as gpd

from shapely import wkb
from logging import Logger
from typing import Optional, List

from app.config import *

logger = Logger(__file__)

def load_data() -> gpd.GeoDataFrame:
    '''
    Loads data from the master Parquet file.
    '''
    data_path = Path(DATA_DIR)
    
    file_to_load = list(data_path.glob('*.parquet'))
    if len(file_to_load) > 1:
        logger.critical(f'More than one master file found in {DATA_DIR}.')
    else:
        master_path = Path(file_to_load[0])
    
    try:
        gdf = gpd.read_parquet(master_path)
        if 'geometry' in gdf.columns:
            gdf = gdf.dropna(subset='geometry')
        return gpd.GeoDataFrame(gdf, geometry='geometry', crs=CRS)
    except Exception as e:
        logger.error(f'Error reading {master_path}: {e}')