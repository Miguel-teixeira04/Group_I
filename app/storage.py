import pandas as pd
from pathlib import Path

_CSV_PATH = Path(__file__).resolve().parent.parent / "database" / "images.csv"

def check_existing(latitude: float, longitude: float, zoom: int) -> dict | None:
    """
    Check if a result already exists in the database for the given
    latitude, longitude and zoom. Returns the row as a dict if found,
    or None if not found.
    """
    if not _CSV_PATH.exists():
        return None

    df = pd.read_csv(_CSV_PATH)

    match = df[
        (df["latitude"] == latitude) &
        (df["longitude"] == longitude) &
        (df["zoom"] == zoom)
    ]

    if not match.empty:
        return match.iloc[0].to_dict()  

    return None  