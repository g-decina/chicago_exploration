#!/bin/bash
PORT=${PORT:-8501}
exec streamlit run frontend/Home.py --server.port $PORT --server.address 0.0.0.0