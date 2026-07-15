import os

API_BASE_URL = os.getenv("API_BASE_URL") or "http://localhost:8000"

HTTP_URL = f"{API_BASE_URL}/api"
WS_URL = API_BASE_URL.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
