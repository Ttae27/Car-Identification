from fastapi import FastAPI, HTTPException, UploadFile, File, Form
import uuid
import base64
import requests
import os
import time
from datetime import datetime, timezone
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from dotenv import load_dotenv

# --- NEW: Load Environment Variables ---
# Get the directory where this main.py file lives
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, "cctv.env")
load_dotenv(dotenv_path=env_path)

# Initialize the CCTV FastAPI app
app = FastAPI(title="CCTV Frame Ingestion Service", version="1.0")

# --- NEW: Secure Qdrant Connections ---
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("COLLECTION_NAME")

SIGLIP_API_URL = "http://127.0.0.1:8080/predict"

# Connect using the URL and API Key
q_client = QdrantClient(
    url=QDRANT_URL, 
    api_key=QDRANT_API_KEY if QDRANT_API_KEY else None
)

# Define and create the local storage directory for CCTV frames
CCTV_STORAGE_DIR = "cctv_saved_frames"
os.makedirs(CCTV_STORAGE_DIR, exist_ok=True)

@app.on_event("startup")
def startup_event():
    """Ensure Qdrant collection exists when the microservice starts."""
    try:
        collections = q_client.get_collections().collections
        if not any(c.name == QDRANT_COLLECTION for c in collections):
            q_client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=qmodels.VectorParams(size=1152, distance=qmodels.Distance.COSINE),
            )
            print(f"Created Qdrant collection: {QDRANT_COLLECTION}")
        else:
            print(f"Successfully connected to existing collection: {QDRANT_COLLECTION}")
    except Exception as e:
        print(f"Warning: Could not connect to Qdrant at {QDRANT_URL} on startup. {e}")


@app.post("/cctv-frames/")
async def ingest_cctv_frame(
    camera_id: str = Form(..., description="The ID of the camera sending this frame (e.g., CAM_01)"),
    file: UploadFile = File(...)
):
    """
    Receives a single image from a CCTV camera, gets its embedding from LitServe,
    saves the physical file locally, and saves the vector/path into Qdrant.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    # 1. Read the single file and convert to Base64 string for the API
    file_bytes = await file.read()
    b64_string = base64.b64encode(file_bytes).decode('utf-8')

    # 2. Build the exact payload LitServe expects for a single image
    payload = {"image_base64": b64_string}

    # 3. Request the AI embedding from LitServe
    try:
        response = requests.post(SIGLIP_API_URL, json=payload)
        response.raise_for_status() 
        api_data = response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to AI Model: {e}")

    # 4. Extract the single vector
    embedding = api_data.get("embedding")
    if not embedding:
        raise HTTPException(status_code=500, detail="AI Model did not return an embedding.")

    # 5. Save the physical file locally
    timestamp = int(time.time())
    unique_filename = f"{camera_id}_{timestamp}_{file.filename}"
    local_file_path = os.path.join(CCTV_STORAGE_DIR, unique_filename)
    
    try:
        with open(local_file_path, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image to disk: {e}")

    # 6. Build the single Qdrant point
    point_id = str(uuid.uuid4())
    point = qmodels.PointStruct(
        id=point_id,
        vector=embedding,
        payload={
            "camera_id": camera_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "filename": file.filename, 
            "image_path": local_file_path,  
            "processed": False 
        }
    )

    # 7. Save directly into the specific QDRANT_COLLECTION
    try:
        q_client.upsert(collection_name=QDRANT_COLLECTION, points=[point])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save to Qdrant: {e}")

    return {
        "message": f"Successfully extracted embedding and saved frame '{file.filename}' locally and to Qdrant.",
        "camera_id": camera_id,
        "saved_path": local_file_path
    }