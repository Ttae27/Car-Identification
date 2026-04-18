from datetime import datetime, timezone
from sqlalchemy.orm import Session
from database import schemas, models
from uuid import UUID
from typing import List, Dict
import random
import time
import base64

import requests
import os
from fastapi import UploadFile

SIGLIP_API_URL = "http://localhost:8080/predict"

def get_embeddings_from_api_bytes(files: List[UploadFile]) -> List[dict]:
    if not files:
        return []

    # 1. Read files and convert to Base64
    b64_strings = []
    for file in files:
        file_bytes = file.file.read()
        b64_string = base64.b64encode(file_bytes).decode('utf-8')
        b64_strings.append(b64_string)
        # Reset file pointer just in case you need to save it locally later
        file.file.seek(0) 

    # 2. Build payload (Single vs Batch)
    if len(b64_strings) == 1:
        payload = {"image_base64": b64_strings[0]}
    else:
        payload = {"batch_image_base64": b64_strings}
    
    # 3. Request
    response = requests.post(SIGLIP_API_URL, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        
        # 4. Map results back to the original files
        final_results = []
        if len(b64_strings) == 1:
            final_results.append({
                "filename": files[0].filename,
                "embedding": data.get("embedding")
            })
        else:
            for item in data.get("results", []):
                original_file = files[item["index"]]
                if "embedding" in item:
                    final_results.append({
                        "filename": original_file.filename,
                        "embedding": item["embedding"]
                    })
        return final_results
    else:
        raise Exception(f"API Error {response.status_code}: {response.text}")

# CREATE
## Register a new car
def create_car(car: schemas.RegisteredCarCreate, db: Session):
    db_car = db.query(models.RegisteredCar).filter(
        models.RegisteredCar.plate == car.plate,
        # models.RegisteredCar.is_active == True
    ).first()

    if db_car:
        return None
    
    new_car = models.RegisteredCar(**car.model_dump())
    db.add(new_car)
    db.commit()
    db.refresh(new_car)
    return new_car

## Add image to a car
def add_car_image(car_id: UUID, images: List[UploadFile], db: Session):
    UPLOAD_DIR = "uploaded_images"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    db_car = db.query(models.RegisteredCar).filter(
        models.RegisteredCar.car_id == car_id,
        models.RegisteredCar.deleted_date.is_(None) 
    ).first()

    if db_car is None:
        return None

    # Step 1: Send the in-memory files directly to the API via Base64
    try:
        api_results = get_embeddings_from_api_bytes(images)
    except Exception as e:
        print(f"Embedding extraction failed: {e}")
        # If the API fails, return an empty list.
        return []

    # Convert the API results list into a dictionary for easy lookup by filename
    embeddings_map = {res["filename"]: res["embedding"] for res in api_results if res.get("embedding")}

    # Step 2: Save the files to disk (for the Streamlit UI) and save to the Database
    created_images = []
    
    for image in images:
        embedding = embeddings_map.get(image.filename)
        
        # Skip if the API returned an error for this specific image in the batch
        if embedding is None:
            print(f"Skipping DB save for {image.filename}: No embedding returned.")
            continue

        print(f"Saving file locally: {image.filename}")
        try:
            # Read the bytes (the pointer was safely reset to 0 in our API helper function)
            file_bytes = image.file.read()
            timestamp = int(time.time())
            unique_filename = f"{car_id}_{timestamp}_{image.filename}"
            
            # Save absolute path so the UI can easily locate it
            local_file_path = os.path.abspath(os.path.join(UPLOAD_DIR, unique_filename))
            
            with open(local_file_path, "wb") as f:
                f.write(file_bytes)
                
            # Create the database record
            new_image = models.CarImage(
                image_path=local_file_path,
                embedding_vector=embedding,
                car_id=car_id
            )
            db.add(new_image)
            created_images.append(new_image)
            
        except Exception as e:
            print(f"Failed to save image {image.filename} to disk: {e}")
    
    db.commit()
    for new_image in created_images:
        db.refresh(new_image)

    return created_images

# READ
## Read all active cars
def read_cars(db: Session):
    db_cars = db.query(models.RegisteredCar).filter(
        models.RegisteredCar.deleted_date.is_(None)
    ).all()
    
    if not db_cars:
        return []
    return db_cars

## Read car details by car_id
def read_car_details(car_id: UUID, db: Session):
    db_car = db.query(models.RegisteredCar).filter(
        models.RegisteredCar.car_id == car_id,
        models.RegisteredCar.deleted_date.is_(None)
    ).first()

    if db_car is None:
        return None
    
    return db_car

# UPDATE
## Update car details
def update_car(car_id: UUID, car: schemas.RegisteredCarUpdate, db: Session):
    db_car = db.query(models.RegisteredCar).filter(
        models.RegisteredCar.car_id == car_id,
        # models.RegisteredCar.is_active == True
    ).first()

    if db_car is None:
        return None
    
    for key, value in car.model_dump().items():
        setattr(db_car, key, value)

    db.commit()
    db.refresh(db_car)

    return db_car

## Update car image
def update_car_image(car_id: UUID, images: List[schemas.CarImageCreate], db: Session):
    db_images = db.query(models.CarImage).filter(
        models.CarImage.car_id == car_id
    ).first()

    if db_images is None:
        return None

    updated_images = []
    for image in images:
        mock_vector = [random.uniform(-1.0, 1.0) for _ in range(512)]
        db_images.image_path = image.image_path
        db_images.embedding_vector = mock_vector
        db.commit()
        updated_images.append(db_images)

    for updated_image in updated_images:
        db.refresh(updated_image)
    return updated_images

# DELETE
def delete_car(car_id: UUID, db: Session, deleted_by: str = "system"):
    db_car = db.query(models.RegisteredCar).filter(
        models.RegisteredCar.car_id == car_id,
        models.RegisteredCar.deleted_date.is_(None) 
    ).first()

    if db_car is None:
        return None
    
    db_car.deleted_date = datetime.now(timezone.utc)
    db_car.deleted_by = deleted_by
    
    db.commit()
    
    return {"message": f"Car {car_id} deleted successfully"}