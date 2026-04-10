from sqlalchemy.orm import Session
from database import schemas, models
from uuid import UUID
from typing import List
import random

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
    db_car = db.query(models.RegisteredCar).filter(
        models.RegisteredCar.car_id == car_id,
    ).first()

    if db_car is None:
        return None

    created_images = []

    for image in images:
        print(f"Processing in-memory file: {image.filename}")
        
        try:
            file_bytes = image.file.read()
            pil_image = Image.open(BytesIO(file_bytes)).convert("RGB")
            real_vector = extract_embedding_from_data(pil_image)
            
        except Exception as e:
            print(f"Failed to process image data for {image.filename}: {e}")
            continue 

        placeholder_path = f"memory_upload_{image.filename}"

        new_image = models.CarImage(
            image_path=placeholder_path,  # See note above
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
    # return db.query(models.RegisteredCar).filter(models.RegisteredCar.is_active == True).all()
    db_cars = db.query(models.RegisteredCar).all()
    if not db_cars:
        return []
    return db_cars

## Read car details by car_id
def read_car_details(car_id: UUID, db: Session):
    db_car = db.query(models.RegisteredCar).filter(
        models.RegisteredCar.car_id == car_id,
        # models.RegisteredCar.is_active == True
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
def delete_car(car_id: UUID, db: Session):
    db_car = db.query(models.RegisteredCar).filter(
        models.RegisteredCar.car_id == car_id,
        # models.RegisteredCar.is_active == True
    ).first()

    if db_car is None:
        return None
    
    db_car.is_active = False
    db.commit()
    
    return {"message": f"Car {car_id} deleted successfully"}
