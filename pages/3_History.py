import sys
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_CSV_PATH = _ROOT / "database" / "images.csv"

_CSS = """
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 1rem; }
    h1 { color: #7c2d12; letter-spacing: -0.5px; }
    h2, h3 { color: #9a3412; }
    hr { border-color: #fed7aa; margin: 1rem 0; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #fff7ed;
        border-left: 4px solid #ea580c;
        border-radius: 8px;
        padding: 0.75rem 1rem;
    }

    /* Expander */
    [data-testid="stExpander"] {
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        margin-bottom: 0.5rem;
    }
</style>
"""


def render_page():
    st.set_page_config(page_title="Analysis History", page_icon="📋", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)

    st.title("📋 Analysis History")
    st.caption("Full log of past environmental risk analyses stored in the database.")

    if not _CSV_PATH.exists() or _CSV_PATH.stat().st_size == 0:
        st.info(
            "No analyses yet. Head to the **AI Workflow** page to run your first analysis.",
            icon="ℹ️",
        )
        return

    df = pd.read_csv(_CSV_PATH, parse_dates=["timestamp"])
    total    = len(df)
    at_risk  = int((df["danger"] == "Y").sum())
    safe     = total - at_risk
    risk_pct = round(at_risk / total * 100) if total else 0

    # ── Summary metrics ───────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Analyses", total)
    c2.metric("At Risk 🚨", at_risk)
    c3.metric("Safe ✅", safe)
    c4.metric("Risk Rate", f"{risk_pct}%")

    st.divider()

    # ── Filters ───────────────────────────────────────────────
    f1, f2, _ = st.columns([1, 1, 2])
    with f1:
        danger_filter = st.selectbox("Filter", ["All", "At Risk", "Safe"], index=0)
    with f2:
        sort_order = st.selectbox("Sort", ["Newest first", "Oldest first"], index=0)

    filtered = df.copy()
    if danger_filter == "At Risk":
        filtered = filtered[filtered["danger"] == "Y"]
    elif danger_filter == "Safe":
        filtered = filtered[filtered["danger"] == "N"]

    filtered = filtered.sort_values(
        "timestamp", ascending=(sort_order == "Oldest first")
    ).reset_index(drop=True)

    st.caption(f"Showing **{len(filtered)}** of {total} records.")

    # ── Table ────────────────────────────────────────────────
    display = filtered[["timestamp", "latitude", "longitude", "zoom", "danger",
                         "image_model", "text_model"]].copy()
    display.columns = ["Timestamp", "Latitude", "Longitude", "Zoom",
                       "Risk", "Vision Model", "Text Model"]
    display["Timestamp"] = pd.to_datetime(display["Timestamp"]).dt.strftime("%Y-%m-%d %H:%M UTC")
    display["Latitude"]  = display["Latitude"].map(lambda v: f"{'N' if v >= 0 else 'S'} {abs(v):.4f}°")
    display["Longitude"] = display["Longitude"].map(lambda v: f"{'E' if v >= 0 else 'W'} {abs(v):.4f}°")
    display["Risk"]      = display["Risk"].map(lambda v: "🚨 At Risk" if v == "Y" else "✅ Safe")

    st.dataframe(display, use_container_width=True, hide_index=True)

    st.divider()

    # ── Map (colour-coded by risk) ────────────────────────────
    st.markdown("### 🗺️ All Analysed Locations")

    map_df = filtered[["latitude", "longitude", "danger"]].copy()
    map_df["color"] = map_df["danger"].map(
        lambda d: [220, 38, 38, 200] if d == "Y" else [22, 163, 74, 200]
    )

    dot_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df.rename(columns={"latitude": "lat", "longitude": "lon"}),
        get_position=["lon", "lat"],
        get_fill_color="color",
        get_radius=80_000,
        pickable=True,
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[dot_layer],
            initial_view_state=pdk.ViewState(latitude=20, longitude=0, zoom=1, pitch=0),
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            tooltip={"text": "Lat: {lat}\nLon: {lon}"},
        ),
        use_container_width=True,
    )
    st.caption("🔴 At risk &nbsp;&nbsp; 🟢 Safe")

    st.divider()

    # ── Detailed records ──────────────────────────────────────
    st.markdown("### Detailed Records")

    from app.image_loader import lat_lon_to_tile, get_image_path  # noqa: E402

    for _, row in filtered.iterrows():
        ts   = pd.Timestamp(row["timestamp"]).strftime("%Y-%m-%d %H:%M UTC")
        icon = "🚨" if row["danger"] == "Y" else "✅"
        lat_str = f"{'N' if row['latitude'] >= 0 else 'S'} {abs(row['latitude']):.4f}°"
        lon_str = f"{'E' if row['longitude'] >= 0 else 'W'} {abs(row['longitude']):.4f}°"
        label = f"{icon} {ts}  ·  {lat_str}, {lon_str}  ·  Zoom {int(row['zoom'])}"

        with st.expander(label):
            img_col, text_col = st.columns([1, 2], gap="medium")

            with img_col:
                try:
                    x, y, z = lat_lon_to_tile(row["latitude"], row["longitude"], int(row["zoom"]))
                    img_path = Path(get_image_path(x, y, z))
                    if img_path.exists():
                        with open(img_path, "rb") as f:
                            st.image(f.read(), caption="Satellite tile", use_container_width=True)
                    else:
                        st.caption("Image not cached locally.")
                except Exception:
                    st.caption("Could not load image.")

            with text_col:
                if row["danger"] == "Y":
                    st.error("🚨 Environmental Risk Detected", icon="🚨")
                else:
                    st.success("✅ No Critical Risk Identified", icon="✅")

                st.markdown("**Justification**")
                st.info(row["text_description"])

                m1, m2 = st.columns(2)
                m1.metric("Vision model", row["image_model"])
                m2.metric("Text model",   row["text_model"])

                st.markdown("**Full image description**")
                st.caption(row["image_description"])


render_page()
