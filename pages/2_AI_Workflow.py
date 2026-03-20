import math
import sys
from pathlib import Path

import pydeck as pdk
import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.image_loader import get_esri_tile
from app.ollama_pipeline import load_config, describe_image, assess_risk, save_to_database

_CSS = """
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 1rem; }
    h1 { color: #1e3a5f; letter-spacing: -0.5px; }
    h2, h3 { color: #1e40af; }
    hr { border-color: #bfdbfe; margin: 1rem 0; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #eff6ff;
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 0.75rem 1rem;
    }

    /* Primary button */
    .stButton > button[kind="primary"] {
        background: #1d4ed8;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.55rem 2.5rem;
        font-size: 1rem;
        width: 100%;
    }
    .stButton > button[kind="primary"]:hover { background: #1e40af; }

    /* Input labels */
    label { font-weight: 600; font-size: 0.85rem; color: #374151; }

    /* Risk alert boxes */
    [data-testid="stAlert"] { border-radius: 10px; }
</style>
"""


def _tile_bounds(latitude: float, longitude: float, zoom: int):
    """Return the exact lon/lat bounding box of the ESRI tile at these coords."""
    n = 2 ** zoom
    tile_x = int((longitude + 180) / 360 * n)
    lat_rad = math.radians(latitude)
    tile_y = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)
    tile_x = max(0, min(n - 1, tile_x))
    tile_y = max(0, min(n - 1, tile_y))

    lon_min = tile_x / n * 360 - 180
    lon_max = (tile_x + 1) / n * 360 - 180
    lat_max = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * tile_y / n))))
    lat_min = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (tile_y + 1) / n))))
    return lon_min, lat_min, lon_max, lat_max


def render_page():
    st.set_page_config(page_title="AI Workflow", page_icon="🤖", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)

    st.title("🤖 AI Environmental Risk Analysis")
    st.caption(
        "Set coordinates, preview the area on the map, then run the AI pipeline "
        "to get a satellite description and environmental risk assessment."
    )

    if "result" not in st.session_state:
        st.session_state.result = None

    # ── Layout: inputs left, map right ───────────────────────
    input_col, map_col = st.columns([1, 2], gap="large")

    with input_col:
        st.markdown("#### 📍 Coordinates")

        c1, c2 = st.columns(2)
        with c1:
            lat_abs = st.number_input(
                "Latitude °", value=38.67989, min_value=0.0, max_value=90.0,
                format="%.5f", label_visibility="visible",
            )
        with c2:
            lat_dir = st.selectbox("Hemisphere", ["N", "S"], label_visibility="visible")

        c3, c4 = st.columns(2)
        with c3:
            lon_abs = st.number_input(
                "Longitude °", value=9.32563, min_value=0.0, max_value=180.0,
                format="%.5f", label_visibility="visible",
            )
        with c4:
            lon_dir = st.selectbox("Direction", ["E", "W"], index=1, label_visibility="visible")

        latitude  = lat_abs  if lat_dir == "N" else -lat_abs
        longitude = lon_abs if lon_dir == "E" else -lon_abs

        st.markdown(
            f"<div style='background:#dbeafe;border-radius:8px;padding:0.5rem 0.75rem;"
            f"font-family:monospace;font-size:0.9rem;color:#1e3a8a;margin-top:0.25rem'>"
            f"{'N' if latitude >= 0 else 'S'} {abs(latitude):.5f}° &nbsp;|&nbsp; "
            f"{'E' if longitude >= 0 else 'W'} {abs(longitude):.5f}°</div>",
            unsafe_allow_html=True,
        )

        st.markdown("#### 🔍 Zoom Level")
        zoom = st.slider(
            "Zoom", min_value=1, max_value=20, value=15,
            help="Higher = more detail, smaller area captured.",
            label_visibility="collapsed",
        )
        zoom_labels = {
            range(1, 5): "Continental view",
            range(5, 9): "Country / region",
            range(9, 12): "City level",
            range(12, 15): "District level",
            range(15, 18): "Neighbourhood",
            range(18, 21): "Building level",
        }
        zoom_desc = next((v for k, v in zoom_labels.items() if zoom in k), "")
        st.caption(f"Zoom {zoom} — {zoom_desc}")

        st.markdown("<br>", unsafe_allow_html=True)
        run_clicked = st.button("Run Analysis", type="primary")

    with map_col:
        st.markdown("#### 🗺️ Area Preview")
        lon_min, lat_min, lon_max, lat_max = _tile_bounds(latitude, longitude, zoom)
        center_lat = (lat_min + lat_max) / 2
        center_lon = (lon_min + lon_max) / 2

        tile_polygon = [{
            "polygon": [
                [lon_min, lat_min], [lon_max, lat_min],
                [lon_max, lat_max], [lon_min, lat_max],
                [lon_min, lat_min],
            ]
        }]

        layer = pdk.Layer(
            "PolygonLayer",
            data=tile_polygon,
            get_polygon="polygon",
            get_fill_color=[59, 130, 246, 55],
            get_line_color=[29, 78, 216, 230],
            stroked=True,
            filled=True,
            line_width_min_pixels=2,
        )

        st.pydeck_chart(
            pdk.Deck(
                layers=[layer],
                initial_view_state=pdk.ViewState(
                    latitude=center_lat,
                    longitude=center_lon,
                    zoom=max(0, zoom - 2),
                    pitch=0,
                ),
                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            ),
            use_container_width=True,
        )

    st.divider()

    # ── Analysis pipeline ─────────────────────────────────────
    if run_clicked:
        config = load_config()

        prog = st.progress(0, text="Downloading satellite image …")
        image_path = get_esri_tile(latitude, longitude, zoom)

        prog.progress(33, text=f"Analysing with **{config['image_model']['name']}** …")
        image_description = describe_image(image_path, config)

        prog.progress(66, text=f"Assessing risk with **{config['text_model']['name']}** …")
        risk_result = assess_risk(image_description, config)

        save_to_database(latitude, longitude, zoom, image_description, risk_result, config)
        prog.progress(100, text="Done!")
        prog.empty()

        st.session_state.result = {
            "latitude": latitude, "longitude": longitude, "zoom": zoom,
            "image_path": image_path,
            "image_description": image_description,
            "risk_result": risk_result,
        }

    # ── Results ───────────────────────────────────────────────
    if st.session_state.result:
        r = st.session_state.result

        img_col, risk_col = st.columns([1, 1], gap="large")

        with img_col:
            st.markdown("#### 🛰️ Satellite Image")
            with open(r["image_path"], "rb") as f:
                st.image(
                    f.read(),
                    caption=(
                        f"{'N' if r['latitude'] >= 0 else 'S'} {abs(r['latitude']):.5f}°, "
                        f"{'E' if r['longitude'] >= 0 else 'W'} {abs(r['longitude']):.5f}° "
                        f"· Zoom {r['zoom']}"
                    ),
                    use_container_width=True,
                )
            with st.expander("Image description (AI)"):
                st.write(r["image_description"])

        with risk_col:
            st.markdown("#### ⚠️ Risk Assessment")
            danger = r["risk_result"]["danger"]
            if danger == "Y":
                st.error("### 🚨 Environmental Risk Detected", icon="🚨")
            else:
                st.success("### ✅ No Critical Risk Identified", icon="✅")

            st.markdown("**Model Justification**")
            st.info(r["risk_result"]["justification"])

            st.divider()
            st.markdown("**Analysis details**")
            config = load_config()
            c1, c2 = st.columns(2)
            c1.metric("Vision model", config["image_model"]["name"])
            c2.metric("Text model", config["text_model"]["name"])
            st.caption(
                f"Location: {'N' if r['latitude'] >= 0 else 'S'} {abs(r['latitude']):.5f}°, "
                f"{'E' if r['longitude'] >= 0 else 'W'} {abs(r['longitude']):.5f}° · "
                f"Zoom {r['zoom']} · Saved to database ✓"
            )


render_page()
