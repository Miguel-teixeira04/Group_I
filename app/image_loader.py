import os
import math
import requests
from pathlib import Path

# Project root (one level up from app/)
_ROOT = Path(__file__).resolve().parent.parent

# --- Tile math ---
_MAX_LAT = 90 # Web Mercator upper limit (avoids division-by-zero at ±90°)

def lat_lon_to_tile(lat, lon, zoom):
    # Clamp to valid Web Mercator range so cos(lat) never reaches 0
    lat = max(-_MAX_LAT, min(_MAX_LAT, lat))
    n = 2 ** zoom
    x = int((lon + 180) / 360 * n)
    lat_rad = math.radians(lat)
    y = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)
    # Clamp tile indices to valid range
    x = max(0, min(n - 1, x))
    y = max(0, min(n - 1, y))
    return x, y, zoom

# --- Path builder (creates folder if needed) ---
def get_image_path(x, y, z):
    folder = _ROOT / "images"
    os.makedirs(folder, exist_ok=True)
    return str(folder / f"esri_{z}_{x}_{y}.png")

# --- Main function your app calls ---
def get_esri_tile(lat, lon, zoom=17):
    x, y, z = lat_lon_to_tile(lat, lon, zoom)
    image_path = get_image_path(x, y, z)   # folder created inside here

    if os.path.exists(image_path):
        return image_path

    url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    response.raise_for_status()

    with open(image_path, "wb") as f:
        f.write(response.content)

    return image_path


# Example Usage
if __name__ == "__main__":
    # Lisbon, Portugal — Praça do Comércio
    path = get_esri_tile(38.7075, -9.1364, zoom=17)
    print(f"[RESULT] image_path = {path}")

    # Run again to confirm cache hit
    path = get_esri_tile(38.7075, -9.1364, zoom=17)
    print(f"[RESULT] image_path = {path}")