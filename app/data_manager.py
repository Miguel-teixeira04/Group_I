"""
Provides the OkavangoData class, which orchestrates downloading
and merging of environmental datasets for the Okavango project.
"""

import os

import geopandas as gpd
import pandas as pd

from .data_loader import download_datasets
from .merger import merge_dataframes

MAP_FILENAME: str = "ne_110m_admin_0_countries.zip"


def get_most_recent_year(df: pd.DataFrame) -> int:
    """
    Returns the most recent year available in a DataFrame.
    - `df`: A DataFrame containing a 'Year' column.
    - Returns the maximum year as an integer.
    - Raises ValueError if no valid years are found.
    """
    years = pd.to_numeric(df["Year"], errors="coerce").dropna()
    if years.empty:
        raise ValueError("No valid years found in the 'Year' column.")
    return int(years.max())


def filter_most_recent(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filters a DataFrame to only keep rows from the most recent year.
    - `df`: A DataFrame containing a 'Year' column.
    - Returns a filtered DataFrame with only the most recent year's data.
    """
    most_recent = get_most_recent_year(df)
    return df[df["Year"] == most_recent].copy()


class OkavangoData:
    """
    Handles downloading, loading, and merging of environmental datasets
    for the project Okavango.

    - Downloads all required datasets into download_dir.
    - Reads each CSV, filters to the most recent year dynamically.
    - Merges each filtered DataFrame with the world map GeoDataFrame.

    Attributes:
        download_dir (str): Directory where datasets are stored.
        world (gpd.GeoDataFrame): Base world map GeoDataFrame.
        forest_change (gpd.GeoDataFrame): Most recent annual change in forest area, merged with map.
        deforestation (gpd.GeoDataFrame): Most recent annual deforestation, merged with map.
        protected_land (gpd.GeoDataFrame): Most recent share of protected land, merged with map.
        degraded_land (gpd.GeoDataFrame): Most recent share of degraded land, merged with map.
        forest_cover (gpd.GeoDataFrame): Most recent share of land covered by forest, merged with map.
    """

    def __init__(self, download_dir: str = "downloads") -> None:
        """
        Initializes OkavangoData: downloads datasets and builds merged GeoDataFrames
        using only the most recent year available in each dataset.

        - `download_dir`: Directory to save downloaded files. Defaults to 'downloads'.
        """
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

        # Function 1: download everything
        download_datasets(self.download_dir)

        # Load the world map
        map_path = os.path.join(self.download_dir, MAP_FILENAME)
        self.world: gpd.GeoDataFrame = gpd.read_file(map_path)

        # Load each CSV, filter to most recent year, merge with world map
        self.forest_change: gpd.GeoDataFrame = self._load_and_merge(
            "annual_change_forest_area.csv"
        )
        self.deforestation: gpd.GeoDataFrame = self._load_and_merge(
            "annual_deforestation.csv"
        )
        self.protected_land: gpd.GeoDataFrame = self._load_and_merge(
            "share_protected_land.csv"
        )
        self.degraded_land: gpd.GeoDataFrame = self._load_and_merge(
            "share_degraded_land.csv"
        )
        self.forest_cover: gpd.GeoDataFrame = self._load_and_merge(
            "share_covered_forest_land.csv"
        )

    def _load_and_merge(self, filename: str) -> gpd.GeoDataFrame:
        """
        Loads a CSV dataset, filters to its most recent year, and merges with world map.
        - `filename`: Name of the CSV file inside download_dir.
        - Returns a GeoDataFrame merged with the world map for the most recent year.
        """
        file_path = os.path.join(self.download_dir, filename)
        df = pd.read_csv(file_path)
        df_recent = filter_most_recent(df)
        return merge_dataframes(self.world, df_recent)
