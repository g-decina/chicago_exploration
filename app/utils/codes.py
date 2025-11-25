import pandas as pd

from app.config import *

INDEX = pd.read_csv(DATA_DIR / 'cluster_index.csv', dtype=str)

def list_codes(gdf) -> list[str]:
    return gdf[ACT_CLEAN].sort_values().unique().tolist()