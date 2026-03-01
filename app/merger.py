import geopandas as gpd
import pandas as pd


def merge_world_with_data(world: gpd.GeoDataFrame, df: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    Merge a world GeoDataFrame with a data DataFrame using 3-letter ISO codes.

    - `world` must contain an `ISO_A3` column with 3-letter ISO country codes.
    - `df` must contain a `Code` column with 3-letter ISO codes (strings).
    - Normalizes `df["Code"]`, filters to codes with length 3, and excludes
      codes starting with "OWID_".
    - Uses a left join so all geometries from `world` are preserved.

    Returns a GeoDataFrame with the original geometry preserved.
    """
    if "ISO_A3" not in world.columns:
        raise ValueError("world doesn't have 'ISO_A3'")
    if "Code" not in df.columns:
        raise ValueError("df doesn't have 'Code' (ISO-3)")

    df = df.copy()
    df["Code"] = df["Code"].astype(str).str.strip()
    df = df[df["Code"].str.len() == 3]
    df = df[df["Code"].str.startswith("OWID_")]

    merged = world.merge(df, how="left", left_on="ISO_A3", right_on="Code")
    print(type(merged))
    return merged










