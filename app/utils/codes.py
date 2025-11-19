import pandas as pd

from app.config import *

INDEX = pd.read_csv(DATA_DIR / 'cluster_index.csv', dtype=str)

def list_codes() -> list[str]:
    return sorted([f.stem for f in DATA_DIR.glob('*.parquet')])