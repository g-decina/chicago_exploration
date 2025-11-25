import pandas as pd
import os

from functools import lru_cache
from fastapi import FastAPI
from app.routes.map import router as api_router

app = FastAPI(
    title='Chicago Geospatial Clustering',
    description='Application for the mapping and clustering of geospatial company data in Chicago',
    version='1.0.0'
)

app.include_router(api_router)

@app.get('/')
def health_check():
    return {'status': 'ok', 'message': 'Engine Online'}