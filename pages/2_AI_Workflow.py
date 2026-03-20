import math
import sys
from pathlib import Path

import pydeck as pdk
import streamlit as st

# Ensure project root is on sys.path so `app.*` imports work from the pages/ folder.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.image_loader import get_esri_tile
from app.ollama_pipeline import load_config, describe_image, assess_risk, save_to_database


def render_page():
    st.set_page_config(page_title="AI Workflow", page_icon="🤖", layout="wide")

    st.title("🤖 AI Environmental Risk Analysis")
    st.markdown(
        "Enter geographic coordinates to fetch a satellite image and get an "
        "automated environmental risk assessment powered by local Ollama models."
    )

    # ── Session state init ────────────────────────────────────
    if "result" not in st.session_state:
        st.session_state.result = None

    # ── 1. Inputs ────────────────────────────────────────────
    col_lat_deg, col_lat_dir, col_lon_deg, col_lon_dir, col_zoom = st.columns(5)

    with col_lat_deg:
        lat_abs = st.number_input(
            "Latitude (°)", value=38.67989, min_value=0.0, max_value=90.0, format="%.6f",
            help="Degrees (0–90). Select hemisphere below.",
        )
    with col_lat_dir:
        lat_dir = st.selectbox("N / S", ["N", "S"], index=0)

    with col_lon_deg:
        lon_abs = st.number_input(
            "Longitude (°)", value=9.32563, min_value=0.0, max_value=180.0, format="%.6f",
            help="Degrees (0–180). Select direction below.",
        )
    with col_lon_dir:
        lon_dir = st.selectbox("E / W", ["E", "W"], index=1)

    with col_zoom:
        zoom = st.slider("Zoom", min_value=1, max_value=20, value=15)

    # Convert to signed decimal degrees
    latitude  = lat_abs if lat_dir == "N" else -lat_abs
    longitude = lon_abs if lon_dir == "E" else -lon_abs

    st.caption(f"Coordinates: **{latitude:+.6f}°** lat, **{longitude:+.6f}°** lon")

    # ── 2. Live map preview ──────────────────────────────────
    st.markdown("### 🗺️ Location Preview")

    # Compute the exact tile (x, y) that ESRI will serve
    n = 2 ** zoom
    tile_x = int((longitude + 180) / 360 * n)
    lat_rad = math.radians(latitude)
    tile_y = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)
    tile_x = max(0, min(n - 1, tile_x))
    tile_y = max(0, min(n - 1, tile_y))

    # Convert tile corners back to lon/lat (exact bounding box of that tile)
    lon_min = tile_x / n * 360 - 180
    lon_max = (tile_x + 1) / n * 360 - 180
    lat_max = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * tile_y / n))))
    lat_min = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (tile_y + 1) / n))))
    center_lat = (lat_min + lat_max) / 2
    center_lon = (lon_min + lon_max) / 2

    # Draw the tile bounding box as a filled rectangle
    tile_polygon = [{
        "polygon": [
            [lon_min, lat_min],
            [lon_max, lat_min],
            [lon_max, lat_max],
            [lon_min, lat_max],
            [lon_min, lat_min],
        ]
    }]

    layer = pdk.Layer(
        "PolygonLayer",
        data=tile_polygon,
        get_polygon="polygon",
        get_fill_color=[34, 197, 94, 60],
        get_line_color=[22, 163, 74, 255],
        stroked=True,
        filled=True,
        line_width_min_pixels=2,
    )

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=max(0, zoom - 2),
        pitch=0,
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        )
    )

    st.divider()

    # ── 3. Run Analysis button ────────────────────────────────
    if st.button("Run Analysis", type="primary"):
        config = load_config()

        with st.spinner("Downloading satellite image from ESRI …"):
            image_path = get_esri_tile(latitude, longitude, zoom)

        with st.spinner(
            f"Analysing image with **{config['image_model']['name']}** "
            "(this may take a minute or two) …"
        ):
            image_description = describe_image(image_path, config)

        with st.spinner(f"Assessing risk with **{config['text_model']['name']}** …"):
            risk_result = assess_risk(image_description, config)

        save_to_database(latitude, longitude, zoom, image_description, risk_result, config)

        # Store everything in session state so results survive widget interactions
        st.session_state.result = {
            "latitude": latitude,
            "longitude": longitude,
            "zoom": zoom,
            "image_path": image_path,
            "image_description": image_description,
            "risk_result": risk_result,
        }

    # ── 4. Display results (from session state) ───────────────
    if st.session_state.result:
        r = st.session_state.result
        st.success("Analysis complete — results saved to database.")
        st.divider()

        st.subheader("🌍 Satellite Image")
        with open(r["image_path"], "rb") as img_file:
            st.image(
                img_file.read(),
                caption=f"Lat: {r['latitude']:+.6f}, Lon: {r['longitude']:+.6f}, Zoom: {r['zoom']}",
            )

        st.subheader("👁️ Image Description")
        st.write(r["image_description"])

        st.subheader("⚠️ Environmental Risk Assessment")
        if r["risk_result"]["danger"] == "Y":
            st.error("🚨 ALERT: Environmental Risk Detected in this area!")
        else:
            st.success("✅ No evidence of critical environmental risk identified.")

        st.write("**Model Justification:**")
        st.write(r["risk_result"]["justification"])


render_page()
