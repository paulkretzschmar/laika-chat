import os

API_BASE_URL = os.getenv("API_BASE_URL") or "http://localhost:8000"

http_url = f"{API_BASE_URL}/api"
ws_url = API_BASE_URL.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
