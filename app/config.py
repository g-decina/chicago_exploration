import os

from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Main data directory
DATA_DIR = Path(os.getenv('DATA_DIR'))

# Geodata parameters
CRS = os.getenv('CRS', 'EPSG:4326')

# Geodata paths
CITY_FILE = Path(os.getenv('CITY_FILE'))
NEIGH_FILE = Path(os.getenv('NEIGH_FILE'))
COM_AREAS_FILE = Path(os.getenv('COM_AREAS_FILE'))

# Company file paths
RAW_DATA = Path(os.getenv('RAW_DATA'))
RAW_COMPANY_DATA = Path(str(os.getenv('RAW_COMPANY_DATA')))
COMPANY_DATA = Path(str(os.getenv('PROCESSED_COMPANY_DATA')))

# Key columns
ACT_COL = os.getenv('ACT', 'business_activity_id')
NAME_COL = os.getenv('NAME', 'doing_business_as_name')
DESC_COL = os.getenv('DESC', 'business_activity')

# Plot style
DOT_COLOR=os.getenv('DOT_COLOR')
EDGE_COLOR=os.getenv('EDGE_COLOR')
BACKGROUND_COLOR=os.getenv('BACKGROUND_COLOR')