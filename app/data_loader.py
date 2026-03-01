import os, requests

def download_datasets(download_dir: str='downloads') -> None:
    owid_datasets = {
        "annual_change_forest_area.csv": "annual-change-forest-area",
        "annual_deforestation.csv": "annual-deforestation",
        "share_protected_land.csv": "terrestrial-protected-areas",
        "share_degraded_land.csv": "share-degraded-land",
        "share_covered_forest_land.csv": "forest-area-as-share-of-land-area"
    }

    for filename, slug in owid_datasets.items():
        url = f"https://ourworldindata.org/grapher/{slug}.csv?v=1"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        file_path = os.path.join(download_dir, filename)
        with open(file_path, "wb") as file:
            file.write(response.content)
            
    map_url = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
    response = requests.get(map_url, timeout=10)
    response.raise_for_status()
    
    map_path = os.path.join(download_dir, "ne_110m_admin_0_countries.zip")
    with open(map_path, "wb") as file:
        file.write(response.content)

if __name__ == "__main__":
    download_datasets()