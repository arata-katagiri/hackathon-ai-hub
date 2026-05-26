import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


BACKEND_BASE = _env("BACKEND_BASE", "https://parking-bishkek.onrender.com").rstrip("/")
LOCATION_ID = _env("LOCATION_ID", "ala-too")


def location_url(path: str = "") -> str:
    base = f"{BACKEND_BASE}/api/locations/{LOCATION_ID}"
    return f"{base}/{path.lstrip('/')}" if path else base


def parking_status_url(parking_id: str) -> str:
    return location_url(f"parkings/{parking_id}/status")


def parking_id(spot_index: int) -> str:
    """ID места в API. По умолчанию spot-00, spot-01, …"""
    fmt = _env("PARKING_ID_FORMAT", "spot-{id:02d}")
    return fmt.format(id=spot_index)


def auth_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    api_key = _env("API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key
    return headers
