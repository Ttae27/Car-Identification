from datetime import datetime, timezone
from sqlalchemy.orm import Session
from database import schemas, models
from uuid import UUID
from typing import List
import random
import time

import torch
from transformers import AutoImageProcessor, AutoModel
from PIL import Image
import requests
from io import BytesIO
import os
from fastapi import UploadFile

MODEL_NAME = "facebook/dinov3-vitb16-pretrain-lvd1689m" 

print(f"Loading {MODEL_NAME} model... This might take a moment.")
processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)
model.eval()

def extract_embedding_from_data(image: Image.Image) -> List[float]:
    """Extracts the embedding vector directly from a PIL Image object in memory."""
    inputs = processor(images=image, return_tensors="pt")
    
    with torch.no_grad():
        outputs = model(**inputs)
        
    return outputs.last_hidden_state[0, 0, :].tolist()

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
    ).first()

    if db_car is None:
        return None

    created_images = []

    for image in images:
        print(f"Processing and saving file: {image.filename}")
        
        try:
            # 1. Read the bytes once into memory
            file_bytes = image.file.read()
            
            # 2. Extract embedding (in-memory processing)
            pil_image = Image.open(BytesIO(file_bytes)).convert("RGB")
            real_vector = extract_embedding_from_data(pil_image)
            
            # 3. Create a unique filename and local path
            # Example: uploaded_images/123e4567-e89b..._167948302_car.png
            timestamp = int(time.time())
            unique_filename = f"{car_id}_{timestamp}_{image.filename}"
            local_file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            # 4. Save the actual file to your local folder
            with open(local_file_path, "wb") as f:
                f.write(file_bytes)
            
        except Exception as e:
            print(f"Failed to process or save image {image.filename}: {e}")
            continue 

        # 5. Save the real local path to the database
        new_image = models.CarImage(
            image_path=local_file_path,  # <-- Replaced placeholder
            embedding_vector=real_vector,
            car_id=car_id
        )
        db.add(new_image)
        created_images.append(new_image)
    
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