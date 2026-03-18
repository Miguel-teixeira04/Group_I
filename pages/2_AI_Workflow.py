import sys
from pathlib import Path

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

    # ── 1. Inputs ────────────────────────────────────────────
    col_lat, col_lon, col_zoom = st.columns(3)

    with col_lat:
        latitude = st.number_input(
            "Latitude", value=0.0, format="%.6f",
            help="Enter latitude. Example: 38.7223",
        )
    with col_lon:
        longitude = st.number_input(
            "Longitude", value=0.0, format="%.6f",
            help="Enter longitude. Example: -9.1393",
        )
    with col_zoom:
        zoom = st.slider("Zoom", min_value=1, max_value=20, value=15)

    # ── 2. Run Analysis ─────────────────────────────────────
    if st.button("Run Analysis", type="primary"):

        # Load model configuration from models.yaml
        config = load_config()

        # Step A — Download satellite image from ESRI
        with st.spinner("Downloading satellite image from ESRI …"):
            image_path = get_esri_tile(latitude, longitude, zoom)

        # Step B — Vision model describes the image
        with st.spinner(
            f"Analysing image with **{config['image_model']['name']}** "
            "(this may take a minute or two) …"
        ):
            image_description = describe_image(image_path, config)

        # Step C — Text model assesses environmental risk
        with st.spinner(
            f"Assessing risk with **{config['text_model']['name']}** …"
        ):
            risk_result = assess_risk(image_description, config)

        # Step D — Persist to database/images.csv
        save_to_database(
            latitude, longitude, zoom,
            image_description, risk_result, config,
        )

        st.success("Analysis complete — results saved to database.")
        st.divider()

        # ── 3. Display results ──────────────────────────────
        # Satellite image — read bytes so it works regardless of CWD
        st.subheader("🌍 Satellite Image")
        with open(image_path, "rb") as img_file:
            st.image(
                img_file.read(),
                caption=f"Lat: {latitude}, Lon: {longitude}, Zoom: {zoom}",
            )

        # Image description
        st.subheader("👁️ Image Description")
        st.write(image_description)

        # Environmental risk assessment
        st.subheader("⚠️ Environmental Risk Assessment")

        if risk_result["danger"] == "Y":
            st.error("🚨 ALERT: Environmental Risk Detected in this area!")
        else:
            st.success("✅ No evidence of critical environmental risk identified.")

        st.write("**Model Justification:**")
        st.write(risk_result["justification"])


render_page()
