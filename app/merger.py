"""
Provides a function to left join a GeoDataFrame, as the left element
and a DataFrame as the right element,
using 3-letter ISO country codes.
"""
import geopandas as gpd
import pandas as pd


def merge_dataframes(geopd: gpd.GeoDataFrame, df: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    Merge a world GeoDataFrame with a data DataFrame using 3-letter ISO codes.

    - `world` must contain an `ISO_A3` column with 3-letter ISO country codes.
    - `df` must contain a `Code` column with 3-letter ISO codes (strings).
    - Normalizes `df["Code"]`, filters to codes with length 3, and excludes
      codes starting with "OWID_".
    - Uses a left join so all geometries from `world` are preserved.

    Returns a GeoDataFrame with the original geometry preserved.
    """
    if "ISO_A3" not in geopd.columns:
        raise ValueError("world doesn't have 'ISO_A3'")
    if "Code" not in df.columns:
        raise ValueError("df doesn't have 'Code' (ISO-3)")

    df = df.copy()
    df["Code"] = df["Code"].astype(str).str.strip()
    df = df[df["Code"].str.len() == 3]
    df = df[df["Code"].str.startswith("OWID_")]

    merged = geopd.merge(geopd, df, how="left", left_on="ISO_A3", right_on="Code")
    print(type(merged))
    return merged

# Example usage:
world_geopd = gpd.read_file(".../downloads/ne_110m_admin_0_countries.zip")
annual_forest_df = pd.read_csv(".../downloads/annual_change_forest_area.csv")
test = merge_dataframes(world_geopd, annual_forest_df)
print(test.head())
