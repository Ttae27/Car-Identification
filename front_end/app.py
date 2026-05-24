import os
import streamlit as st
import requests
from requests.auth import HTTPDigestAuth
import urllib3
import io
import time
from PIL import Image, ImageOps

urllib3.disable_warnings()

# Set the base URL for your FastAPI backend
BASE_URL = "http://localhost:8100"

# Dahua AI box — frame_image_path values stored in Logs are device-side
# paths (e.g. /mnt/dvr/sda0/2026/04/30/xxx.jpg). They must be fetched via
# RPC_Loadfile with HTTP digest auth, the same mechanism back-end uses
# during ingest. Duplicated here rather than imported — front-end and
# back-end are separate deploy units.
DAHUA_HOST = os.getenv("DAHUA_HOST", "192.168.20.200")
DAHUA_USER = os.getenv("DAHUA_USER", "admin")
DAHUA_PASSWORD = os.getenv("DAHUA_PASSWORD", "admin123")

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


@st.cache_data(show_spinner=False, ttl=600)
def fetch_dahua_image_bytes(remote_path: str) -> bytes | None:
    """Pull a JPEG off the Dahua AI box via RPC_Loadfile (digest auth).

    Mirrors back-end/downloadImage.py. Returns None on any failure so the
    UI can fall back to a 'missing' placeholder instead of crashing.
    """
    if not remote_path or remote_path in ("-", ""):
        return None
    url = f"http://{DAHUA_HOST}/cgi-bin/RPC_Loadfile{remote_path}"
    try:
        r = requests.get(
            url,
            auth=HTTPDigestAuth(DAHUA_USER, DAHUA_PASSWORD),
            verify=False,
            timeout=15,
        )
        r.raise_for_status()
        ctype = r.headers.get("Content-Type", "")
        if "text" in ctype or "html" in ctype:
            return None
        return r.content
    except Exception:
        return None


def get_dahua_uniform_image(remote_path, size=(300, 300)):
    data = fetch_dahua_image_bytes(remote_path)
    if not data:
        return None
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        return ImageOps.fit(img, size, Image.Resampling.LANCZOS)
    except Exception:
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
        
        # FIX: The backend returns 404 when no cars exist, not an empty list. 
        # We need to handle 404 as a valid "empty" state.
        if response.status_code == 200 or response.status_code == 404:
            cars = response.json() if response.status_code == 200 else []
            
            if not cars:
                st.info("No cars found in the database. Go to 'Register New Car' to add one.")
            else:
                # Create a Master-Detail Layout: List on left, Details on right
                list_col, detail_col = st.columns([1, 2], gap="large")
                
                # --- LEFT COLUMN: Clickable List ---
                with list_col:
                    st.subheader(f"Cars List ({len(cars)})")
                    with st.container(height=800): 
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
                                                        time.sleep(1)
                                                        st.rerun()
                                                    else:
                                                        error_detail = update_res.json().get("detail", update_res.text)
                                                        st.error(f"Error: {error_detail}")
                                    
                                    # Delete Button
                                    with manage_tab_delete:
                                        st.warning("Are you sure you want to delete this car? This will mark it as inactive.")
                                        if st.button("🚨 Yes, Delete this Car", use_container_width=True):
                                            del_res = requests.delete(f"{BASE_URL}/cars/{selected_id}")
                                            if del_res.status_code == 200:
                                                st.session_state.selected_car_id = None
                                                st.success("Car deleted successfully!")
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                error_detail = del_res.json().get("detail", del_res.text)
                                                st.error(f"Error: {error_detail}")

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
                                
                                # --- 4. Detection Frames (Channel + Datetime) ---
                                if logs_list:
                                    st.divider()
                                    st.write(f"#### 🎯 Detections ({len(logs_list)})")
                                    sorted_logs = sorted(
                                        logs_list,
                                        key=lambda lg: lg.get("timestamp") or "",
                                        reverse=True,
                                    )
                                    match_cols = st.columns(3)
                                    for idx, log in enumerate(sorted_logs):
                                        with match_cols[idx % 3]:
                                            frame_path = log.get("frame_image_path")
                                            uniform_frame = get_dahua_uniform_image(frame_path, size=(300, 300)) if frame_path else None

                                            channel = log.get("camera") or "Unknown"
                                            ts = log.get("timestamp") or "—"
                                            method = log.get("match_method") or "—"
                                            score = log.get("similarity_score")
                                            score_str = f" · {score*100:.1f}%" if isinstance(score, (int, float)) else ""
                                            caption = f"📷 CH {channel} · 🕒 {ts} · 🔎 {method}{score_str}"

                                            if uniform_frame:
                                                st.image(uniform_frame, caption=caption, use_container_width=True)
                                            else:
                                                st.warning(f"Frame missing: {frame_path or '(no path)'}")
                                                st.caption(caption)

                                # --- 5. Logs Table ---
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
            st.error(f"Failed to fetch cars. Error {response.status_code}: {response.text}")
            
    except requests.exceptions.ConnectionError:
        st.error("🔌 Cannot connect to the backend. Is FastAPI running on port 8000?")

# -----------------------------------------
# TAB 2: Register New Car
# -----------------------------------------
with tab2:
    st.header("➕ Register a New Car")
    st.markdown("Fill out the vehicle details and upload associated images in one step.")
    
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
        
        # Live Image Previews
        if uploaded_files:
            st.write("#### 👁️ Previews:")
            preview_cols = st.columns(3)
            for idx, file in enumerate(uploaded_files):
                with preview_cols[idx % 3]:
                    st.image(file, use_container_width=True)
    
    st.divider()
    
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
                            error_detail = img_res.json().get("detail", img_res.text)
                            st.warning(f"⚠️ Car was registered (ID: {new_car_id}), but images failed to upload: {error_detail}")
                    else:
                        st.success("✅ Car registered successfully! (No images were attached).")
                        st.balloons()
                        
                else:
                    error_detail = car_res.json().get("detail", car_res.text)
                    st.error(f"❌ Failed to register car: {error_detail}")