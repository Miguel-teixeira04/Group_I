import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_CSV_PATH = _ROOT / "database" / "images.csv"


def render_page():
    st.set_page_config(page_title="Analysis History", page_icon="📋", layout="wide")

    st.title("📋 Analysis History")
    st.markdown("Past environmental risk analyses stored in the database.")

    if not _CSV_PATH.exists() or _CSV_PATH.stat().st_size == 0:
        st.info("No analyses have been run yet. Go to the AI Workflow page to run your first analysis.")
        return

    df = pd.read_csv(_CSV_PATH, parse_dates=["timestamp"])

    # ── Summary metrics ───────────────────────────────────────
    total = len(df)
    at_risk = (df["danger"] == "Y").sum()
    safe = total - at_risk

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Analyses", total)
    col2.metric("At Risk", int(at_risk), delta=None)
    col3.metric("Safe", int(safe), delta=None)

    st.divider()

    # ── Filters ───────────────────────────────────────────────
    filter_col, sort_col = st.columns(2)
    with filter_col:
        danger_filter = st.selectbox("Filter by risk", ["All", "At Risk (Y)", "Safe (N)"], index=0)
    with sort_col:
        sort_order = st.selectbox("Sort by date", ["Newest first", "Oldest first"], index=0)

    filtered = df.copy()
    if danger_filter == "At Risk (Y)":
        filtered = filtered[filtered["danger"] == "Y"]
    elif danger_filter == "Safe (N)":
        filtered = filtered[filtered["danger"] == "N"]

    ascending = sort_order == "Oldest first"
    filtered = filtered.sort_values("timestamp", ascending=ascending).reset_index(drop=True)

    st.caption(f"Showing {len(filtered)} of {total} records.")

    # ── Table overview ────────────────────────────────────────
    display_cols = ["timestamp", "latitude", "longitude", "zoom", "danger", "image_model", "text_model"]
    st.dataframe(
        filtered[display_cols].style.map(
            lambda v: "background-color: #ffd6d6; color: #900" if v == "Y"
            else ("background-color: #d6f5d6; color: #060" if v == "N" else ""),
            subset=["danger"],
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ── Detailed expandable rows ──────────────────────────────
    st.subheader("Detailed Records")
    for _, row in filtered.iterrows():
        ts = pd.Timestamp(row["timestamp"]).strftime("%Y-%m-%d %H:%M UTC")
        danger_icon = "🚨" if row["danger"] == "Y" else "✅"
        label = f"{danger_icon} {ts} — Lat {row['latitude']:+.4f}, Lon {row['longitude']:+.4f}, Zoom {row['zoom']}"

        with st.expander(label):
            img_col, text_col = st.columns([1, 2])

            with img_col:
                # Try to load the cached image tile
                from app.image_loader import lat_lon_to_tile, get_image_path
                try:
                    x, y, z = lat_lon_to_tile(row["latitude"], row["longitude"], int(row["zoom"]))
                    img_path = Path(get_image_path(x, y, z))
                    if img_path.exists():
                        with open(img_path, "rb") as f:
                            st.image(f.read(), caption="Cached satellite image")
                    else:
                        st.caption("Satellite image not cached locally.")
                except Exception:
                    st.caption("Could not load image.")

            with text_col:
                st.markdown(f"**Risk:** {'🚨 AT RISK' if row['danger'] == 'Y' else '✅ Safe'}")
                st.markdown(f"**Models:** `{row['image_model']}` (vision) · `{row['text_model']}` (text)")
                st.markdown("**Justification:**")
                st.write(row["text_description"])
                with st.expander("Full image description"):
                    st.write(row["image_description"])

    # ── Map of all analysed locations ────────────────────────
    st.divider()
    st.subheader("🗺️ All Analysed Locations")
    map_df = filtered[["latitude", "longitude"]].rename(
        columns={"latitude": "lat", "longitude": "lon"}
    )
    st.map(map_df, zoom=1)


render_page()
