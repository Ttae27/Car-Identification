import streamlit as st
import requests
import random
from PIL import Image, ImageOps  # <-- Add this line
import io
import os
import time

# Set the base URL for your FastAPI backend
BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="Car Registration Management", layout="wide")
st.title("Car Registration Management")

# --- Navigation ---
tab1, tab2 = st.tabs(["📋 View All Cars", "➕ Register New Car"])

if "selected_car_id" not in st.session_state:
    st.session_state.selected_car_id = None

# Helper function to load and crop images to exactly the same size
def get_uniform_image(image_path, size=(300, 300)):
    try:
        # Load image from local path or URL
        if image_path.startswith("http"):
            response = requests.get(image_path)
            img = Image.open(io.BytesIO(response.content)).convert("RGB")
        else:
            img = Image.open(image_path).convert("RGB")
        
        # ImageOps.fit crops and resizes the image from the center to perfectly fit the target size
        return ImageOps.fit(img, size, Image.Resampling.LANCZOS)
    except Exception as e:
        return None
# -----------------------------------------
# TAB 1: View All Cars & Details
# -----------------------------------------
with tab1:
    col_header, col_refresh = st.columns([4, 1])
    with col_header:
        st.header("📋 Registered Cars Overview")
    with col_refresh:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.session_state.selected_car_id = None # Reset selection on refresh
            st.rerun()

    try:
        response = requests.get(f"{BASE_URL}/cars/")
        if response.status_code == 200:
            cars = response.json()
            if not cars:
                st.info("No cars found in the database. Go to 'Register New Car' to add one.")
            else:
                # Create a Master-Detail Layout: List on left, Details on right
                list_col, detail_col = st.columns([1, 2], gap="large")
                
                # --- LEFT COLUMN: Clickable List ---
                with list_col:
                    st.subheader(f"Cars List ({len(cars)})")
                    with st.container(height=800): # Increased height slightly
                        for car in cars:
                            with st.container(border=True):
                                st.markdown(f"**Plate:** {car.get('plate')}")
                                st.caption(f"Label: {car.get('label') or 'N/A'}")
                                
                                if st.button("View Details", key=f"btn_{car['car_id']}", use_container_width=True):
                                    st.session_state.selected_car_id = car['car_id']
                                    st.rerun()

                # --- RIGHT COLUMN: Car Details ---
                with detail_col:
                    if st.session_state.selected_car_id is None:
                        st.info("👈 Click 'View Details' on a car from the list to see its full profile and images.")
                    else:
                        selected_id = st.session_state.selected_car_id
                        
                        with st.spinner("Fetching details..."):
                            detail_res = requests.get(f"{BASE_URL}/cars/{selected_id}")
                            
                            if detail_res.status_code == 200:
                                details = detail_res.json()
                                
                                # --- 1. Header & Metrics ---
                                st.subheader(f"🚗 {details.get('plate')}")
                                
                                images_list = details.get('images', [])
                                logs_list = details.get('logs', [])
                                
                                m1, m2, m3 = st.columns(3)
                                m1.metric("Label", details.get('label') or "None")
                                m2.metric("Images", len(images_list))
                                m3.metric("Logs", len(logs_list))
                                
                                st.write(f"**Description:** {details.get('description') or 'None'}")
                                st.caption(f"**ID:** `{details.get('car_id')}` | **Registered:** {details.get('created_date')}")
                                
                                # --- 2. UPDATE / DELETE CONTROLS ---
                                with st.expander("⚙️ Manage Car (Update / Delete)"):
                                    manage_tab_update, manage_tab_delete = st.tabs(["📝 Update Details", "⚠️ Delete Car"])
                                    
                                    # Update Form
                                    with manage_tab_update:
                                        with st.form(f"update_form_{selected_id}"):
                                            # Pre-fill inputs with existing details
                                            update_plate = st.text_input("License Plate *", value=details.get('plate'))
                                            update_label = st.text_input("Label", value=details.get('label') or "")
                                            update_desc = st.text_area("Description", value=details.get('description') or "")
                                            update_by = st.text_input("Updated By (Your Name/Email)")
                                            
                                            if st.form_submit_button("Save Changes", type="primary"):
                                                if not update_plate:
                                                    st.error("License Plate is required!")
                                                else:
                                                    payload = {
                                                        "plate": update_plate,
                                                        "label": update_label if update_label else None,
                                                        "description": update_desc if update_desc else None,
                                                        "updated_by": update_by if update_by else None
                                                    }
                                                    update_res = requests.put(f"{BASE_URL}/cars/{selected_id}", json=payload)
                                                    if update_res.status_code == 200:
                                                        st.success("Car updated successfully!")
                                                        time.sleep(1) # Brief pause so user sees success message
                                                        st.rerun()
                                                    else:
                                                        st.error(f"Error: {update_res.text}")
                                    
                                    # Delete Button
                                    with manage_tab_delete:
                                        st.warning("Are you sure you want to delete this car? This will mark it as inactive.")
                                        if st.button("🚨 Yes, Delete this Car", use_container_width=True):
                                            del_res = requests.delete(f"{BASE_URL}/cars/{selected_id}")
                                            if del_res.status_code == 200:
                                                st.session_state.selected_car_id = None # Clear selection
                                                st.success("Car deleted successfully!")
                                                st.rerun()
                                            else:
                                                st.error(f"Error: {del_res.text}")

                                st.divider()
                                
                                # --- 3. Uniform Image Grid ---
                                if images_list:
                                    st.write("#### 📸 Attached Images")
                                    cols = st.columns(3)
                                    for idx, img_data in enumerate(images_list):
                                        with cols[idx % 3]:
                                            img_path = img_data.get("image_path")
                                            uniform_img = get_uniform_image(img_path, size=(300, 300))
                                            
                                            if uniform_img:
                                                st.image(uniform_img, caption=f"ID: {img_data.get('id')}", use_container_width=True)
                                            else:
                                                st.warning("Image missing")
                                else:
                                    st.info("No images have been uploaded for this car yet.")
                                
                                # --- 4. Logs Table ---
                                if logs_list:
                                    st.divider()
                                    st.write("#### 📝 Activity Logs")
                                    st.dataframe(logs_list, use_container_width=True, hide_index=True)
                                    
                            else:
                                st.error("Failed to load details for this car. It may have been deleted.")
                                if st.button("Reset Selection"):
                                    st.session_state.selected_car_id = None
                                    st.rerun()
                                    
        else:
            st.error("Failed to fetch cars. Check your backend logs.")
            
    except requests.exceptions.ConnectionError:
        st.error("🔌 Cannot connect to the backend. Is FastAPI running on port 8000?")

# -----------------------------------------
# TAB 2: Register New Car
# -----------------------------------------
with tab2:
    st.header("➕ Register a New Car")
    st.markdown("Fill out the vehicle details and upload associated images in one step.")
    
    # NOTE: st.form is removed here so the file uploader can trigger live image previews!
    
    col_text, col_img = st.columns([1, 1], gap="large")
    
    with col_text:
        st.subheader("Vehicle Details")
        plate = st.text_input("License Plate * (Required)", max_chars=20)
        label = st.text_input("Label (e.g., VIP, Staff, Unknown)")
        created_by = st.text_input("Operator Name / Email")
        description = st.text_area("Additional Description")
        
    with col_img:
        st.subheader("Vehicle Images")
        uploaded_files = st.file_uploader(
            "Drag and drop images here", 
            type=["jpg", "jpeg", "png"], 
            accept_multiple_files=True
        )
        st.caption("These will be processed by the Vision model for embeddings.")
        
        # --- NEW: Live Image Previews ---
        if uploaded_files:
            st.write("#### 👁️ Previews:")
            # Create a mini grid of 3 columns for the previews
            preview_cols = st.columns(3)
            for idx, file in enumerate(uploaded_files):
                with preview_cols[idx % 3]:
                    # Display the image preview
                    st.image(file, use_container_width=True)
    
    st.divider()
    
    # Standard st.button replaces the st.form_submit_button
    submitted = st.button("🚀 Register Car & Upload Images", type="primary", use_container_width=True)
    
    if submitted:
        if not plate:
            st.error("❌ License plate is strictly required!")
        else:
            with st.spinner("Processing registration..."):
                # STEP 1: Create the Car Record
                car_payload = {
                    "plate": plate,
                    "label": label if label else None,
                    "description": description if description else None,
                    "created_by": created_by if created_by else None
                }
                
                car_res = requests.post(f"{BASE_URL}/cars/", json=car_payload)
                
                if car_res.status_code == 200:
                    new_car_data = car_res.json()
                    new_car_id = new_car_data.get("car_id")
                    
                    # STEP 2: Upload Images (If any were provided)
                    if uploaded_files:
                        files_payload = [
                            ("images", (file.name, file.getvalue(), file.type)) 
                            for file in uploaded_files
                        ]
                        
                        img_res = requests.post(f"{BASE_URL}/cars/{new_car_id}/images/", files=files_payload)
                        
                        if img_res.status_code == 200:
                            st.success(f"✅ Car registered successfully and {len(uploaded_files)} image(s) processed!")
                            st.balloons()
                        else:
                            st.warning(f"⚠️ Car was registered (ID: {new_car_id}), but images failed to upload: {img_res.text}")
                    else:
                        # Success without images
                        st.success("✅ Car registered successfully! (No images were attached).")
                        
                else:
                    st.error(f"❌ Failed to register car: {car_res.text}")