import os

from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000/api')
TIMEOUT = int(os.getenv('TIMEOUT', 0))