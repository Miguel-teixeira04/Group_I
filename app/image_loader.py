import os
import math
import requests

# --- Tile math ---
def lat_lon_to_tile(lat, lon, zoom):
    n = 2 ** zoom
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
    return x, y, zoom

# --- Path builder (creates folder if needed) ---
def get_image_path(x, y, z, folder="images"):
    os.makedirs(folder, exist_ok=True)   # ← here, and only here
    return os.path.join(folder, f"esri_{z}_{x}_{y}.png")

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