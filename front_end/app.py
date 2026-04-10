import streamlit as st
import requests
import random

# Set the base URL for your FastAPI backend
BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="Car Registration Management", layout="wide")
st.title("🚗 Car Registration Management")

# --- Navigation ---
tab1, tab2, tab3 = st.tabs(["📋 View All Cars", "➕ Register New Car", "⚙️ Manage Car (Update/Delete)"])

# -----------------------------------------
# TAB 1: View All Cars & Details
# -----------------------------------------
with tab1:
    st.header("Registered Cars")
    if st.button("Refresh List"):
        pass

    try:
        response = requests.get(f"{BASE_URL}/cars/")
        if response.status_code == 200:
            cars = response.json()
            if not cars:
                st.info("No cars found in the database.")
            else:
                # Display cars in a clean table
                st.dataframe(cars, use_container_width=True)
                
                st.divider()
                st.subheader("🔍 View Car Details")
                
                # Create a dictionary mapping plates/IDs for easier selection
                car_options = {f"{car['plate']} (ID: {car['car_id']})": car['car_id'] for car in cars}
                selected_display = st.selectbox("Select a Car to view details:", list(car_options.keys()))
                
                if st.button("Get Details"):
                    selected_car_id = car_options[selected_display]
                    detail_res = requests.get(f"{BASE_URL}/cars/{selected_car_id}")
                    
                    if detail_res.status_code == 200:
                        details = detail_res.json()
                        
                        # Layout for Car Details
                        col_info, col_extra = st.columns([1, 1])
                        with col_info:
                            st.write("### Basic Info")
                            st.write(f"**Plate:** {details.get('plate')}")
                            st.write(f"**Label:** {details.get('label')}")
                            st.write(f"**Description:** {details.get('description')}")
                            st.write(f"**Created By:** {details.get('created_by')} at {details.get('created_date')}")
                        
                        with col_extra:
                            st.write("### Associated Data")
                            st.write(f"**Images Attached:** {len(details.get('images', []))}")
                            st.write(f"**Logs Recorded:** {len(details.get('logs', []))}")
                        
                        # Show raw JSON for full visibility
                        with st.expander("View Raw JSON Data"):
                            st.json(details)
                    else:
                        st.error(f"Error fetching details: {detail_res.text}")
        else:
            st.warning("Failed to fetch cars. Check your backend.")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to the backend. Is FastAPI running on port 8000?")

# -----------------------------------------
# TAB 2: Register New Car
# -----------------------------------------
with tab2:
    st.header("Register a New Car")
    with st.form("create_car_form"):
        # Fields based on RegisteredCarCreate schema
        plate = st.text_input("License Plate * (Required)", max_chars=20)
        label = st.text_input("Label (Optional)")
        description = st.text_area("Description (Optional)")
        created_by = st.text_input("Created By (Optional - username/email)")
        
        submitted = st.form_submit_button("Register Car")
        if submitted:
            if not plate:
                st.error("License plate is required!")
            else:
                payload = {
                    "plate": plate,
                    "label": label if label else None,
                    "description": description if description else None,
                    "created_by": created_by if created_by else None
                }
                res = requests.post(f"{BASE_URL}/cars/", json=payload)
                if res.status_code == 200:
                    st.success("Car registered successfully!")
                    st.json(res.json())
                else:
                    st.error(f"Validation Error: {res.text}")

# -----------------------------------------
# TAB 3: Manage (Update, Add Image, Delete)
# -----------------------------------------
with tab3:
    st.header("Manage Existing Car")
    manage_car_id = st.text_input("Enter Car ID (UUID) to manage:")
    
    if manage_car_id:
        st.divider()
        col1, col2 = st.columns(2)
        
        # --- Update Car ---
        with col1:
            st.subheader("📝 Update Details")
            with st.form("update_car_form"):
                update_plate = st.text_input("New License Plate * (Required)", max_chars=20)
                update_label = st.text_input("New Label")
                update_description = st.text_area("New Description")
                updated_by = st.text_input("Updated By")
                
                if st.form_submit_button("Update Car"):
                    if not update_plate:
                        st.error("License plate is required for updates!")
                    else:
                        payload = {
                            "plate": update_plate,
                            "label": update_label if update_label else None,
                            "description": update_description if update_description else None,
                            "updated_by": updated_by if updated_by else None
                        }
                        res = requests.put(f"{BASE_URL}/cars/{manage_car_id}", json=payload)
                        if res.status_code == 200:
                            st.success("Car updated successfully!")
                        else:
                            st.error(f"Error: {res.text}")
                        
        # --- Add Image ---
        with col2:
            st.subheader("📸 Add Car Image")
            with st.form("add_image_form"):
                image_path = st.text_input("Image Path or URL *")
                
                st.caption("Note: A mock 512-dimension vector will be generated automatically to satisfy Pydantic schema constraints.")
                
                if st.form_submit_button("Add Image"):
                    if not image_path:
                        st.error("Image path is required!")
                    else:
                        # Generate a mock vector to satisfy the min_length=512, max_length=512 constraint
                        mock_vector = [random.uniform(-1.0, 1.0) for _ in range(512)]
                        
                        payload = {
                            "image_path": image_path,
                            "embedding_vector": mock_vector
                        }
                        # Assuming your endpoint handles a single image object as defined in main.py
                        res = requests.post(f"{BASE_URL}/cars/{manage_car_id}/images/", json=payload)
                        if res.status_code == 200:
                            st.success("Image added successfully!")
                        else:
                            st.error(f"Error: {res.text}")

        st.divider()
        # --- Delete Car ---
        st.subheader("⚠️ Danger Zone")
        with st.form("delete_car_form"):
            st.warning("Are you sure you want to delete this car?")
            if st.form_submit_button("Delete Car", type="primary"):
                res = requests.delete(f"{BASE_URL}/cars/{manage_car_id}")
                if res.status_code == 200:
                    st.success("Car deleted successfully!")
                else:
                    st.error(f"Error: {res.text}")