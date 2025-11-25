#!/bin/bash
if [ ! -f 'data/current/chicago_licenses_master.geojson' ]; then
    echo 'First run detected. Processing raw data...'
    python -m data.extraction
else
    echo 'Data found. Starting API...'
fi

PORT=${PORT:-8000}
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload