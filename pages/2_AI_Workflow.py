import streamlit as st

# In the future, you will import your teammates' real functions here. Example:
# from utils.image_fetcher import get_esri_image
# from utils.ollama_pipeline import analyze_image_and_risk
# from utils.storage import check_cached_result, save_to_database

def render_page():
    st.set_page_config(page_title="AI Workflow", page_icon="🤖", layout="wide")

    st.title("🤖 AI Environmental Risk Analysis")
    st.markdown("Enter geographic coordinates to fetch a satellite image and get an automated environmental risk assessment.")

    # 1. Data Input Fields
    col_lat, col_lon, col_zoom = st.columns(3)
    
    with col_lat:
        latitude = st.number_input("Latitude", value=0.0, format="%.6f", help="Enter latitude. Example: 38.7223")
    with col_lon:
        longitude = st.number_input("Longitude", value=0.0, format="%.6f", help="Enter longitude. Example: -9.1393")
    with col_zoom:
        zoom = st.slider("Zoom", min_value=1, max_value=20, value=15)

    # 2. Execution Button
    if st.button("Run Analysis", type="primary"):
        with st.spinner("Processing coordinates. Please wait..."):
            
            # --- FUTURE INTEGRATION LOGIC ---
            # 1. Person 4's function checks if the analysis already exists in the database.
            # 2. If it does not exist, Person 2's function gets the image from ESRI.
            # 3. Person 3's function runs the Ollama models to get the descriptions.
            # 4. Person 4's function saves the new row to the CSV.
            
            # --- MOCK DATA FOR TESTING YOUR INTERFACE ---
            # (Remove this when you link your teammates' modules)
            mock_image_path = None # Person 2 will provide the saved image path
            mock_description = "The image shows a vast area of dense forest with a river crossing the center. There is noticeable recent deforestation on the right bank."
            mock_danger_flag = "Y"
            mock_risk_justification = "The presence of deforested areas near the watercourse indicates a potential risk of soil erosion and loss of local biodiversity."

            st.success("Analysis completed successfully!")
            st.divider()

            # 3. Image Presentation (Person 2's Result)
            st.subheader("🌍 Satellite Image")
            # When ready, replace the info box below with: 
            # st.image(mock_image_path, caption=f"Lat: {latitude}, Lon: {longitude}, Zoom: {zoom}")
            st.info("Placeholder for the satellite image (Person 2's Module).")

            # 4. Description Presentation (Person 3's Result)
            st.subheader("👁️ Image Description")
            st.write(mock_description)

            # 5. Visual Danger Indicator and Justification (Person 3's Results)
            st.subheader("⚠️ Environmental Risk Assessment")
            
            # Simple visual danger indicator using Streamlit's message boxes
            if mock_danger_flag == "Y":
                st.error("🚨 ALERT: Environmental Risk Detected in this area!")
            else:
                st.success("✅ No evidence of critical environmental risk identified.")
            
            st.write("**Model Justification:**")
            st.write(mock_risk_justification)

if __name__ == "__main__":
    render_page()