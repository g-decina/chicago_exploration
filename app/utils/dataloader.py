import pandas as pd
import geopandas as gpd

from shapely import wkb
from logging import Logger

from app.config import *

logger = Logger(__file__)

def load_data(
    act_codes: list[str]
) -> gpd.GeoDataFrame:
    all_gdfs = []
    
    for code in act_codes:
        df_path = DATA_DIR / f'{code}.parquet'
        if not df_path.exists():
            logger.warning(f'Failed to load activity code: {code}')
            continue
        
        gdf = gpd.read_parquet(df_path)
        gdf = gdf.dropna(subset='geometry')
        
        all_gdfs.append(gdf)
        
    if all_gdfs:
        gdf = pd.concat(all_gdfs, ignore_index=True)
        gdf = gpd.GeoDataFrame(gdf, geometry='geometry', crs=CRS)
        return gdf
    else:
        return gpd.GeoDataFrame(geometry=[], crs=CRS)