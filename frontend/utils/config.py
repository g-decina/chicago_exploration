import os

from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv('BACKEND_URL', 'http://DEFAULT_MISSING:8000')
TIMEOUT = int(os.getenv('TIMEOUT', 0))