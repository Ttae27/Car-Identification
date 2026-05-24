from datetime import datetime, timezone
from sqlalchemy.orm import Session
from database import schemas, models
from uuid import UUID
from typing import List
import time
import os

from fastapi import UploadFile

from dinov3_client import embed_batch


def get_embeddings_from_api_bytes(files: List[UploadFile]) -> List[dict]:
    """Embed uploaded images using the shared DINOv3 service.

    Returns a list of {"filename", "embedding"} dicts (one per successful image).
    """
    if not files:
        return []

    images_bytes: List[bytes] = []
    for file in files:
        file_bytes = file.file.read()
        images_bytes.append(file_bytes)
        file.file.seek(0)

    vectors = embed_batch(images_bytes)

    return [
        {"filename": f.filename, "embedding": vec}
        for f, vec in zip(files, vectors)
    ]


# CREATE
## Register a new car
def create_car(car: schemas.RegisteredCarCreate, db: Session):
    db_car = db.query(models.RegisteredCar).filter(
        models.RegisteredCar.plate == car.plate,
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

    try:
        api_results = get_embeddings_from_api_bytes(images)
    except Exception as e:
        print(f"Embedding extraction failed: {e}")
        return []

    embeddings_map = {res["filename"]: res["embedding"] for res in api_results if res.get("embedding")}

    created_images = []

    for image in images:
        embedding = embeddings_map.get(image.filename)

        if embedding is None:
            print(f"Skipping DB save for {image.filename}: No embedding returned.")
            continue

        print(f"Saving file locally: {image.filename}")
        try:
            file_bytes = image.file.read()
            timestamp = int(time.time())
            unique_filename = f"{car_id}_{timestamp}_{image.filename}"

            local_file_path = os.path.abspath(os.path.join(UPLOAD_DIR, unique_filename))

            with open(local_file_path, "wb") as f:
                f.write(file_bytes)

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
    ).first()

    if db_car is None:
        return None

    for key, value in car.model_dump().items():
        setattr(db_car, key, value)

    db.commit()
    db.refresh(db_car)

    return db_car

## Update car image
def update_car_image(car_id: UUID, images: List[UploadFile], db: Session):
    db_car = db.query(models.RegisteredCar).filter(
        models.RegisteredCar.car_id == car_id,
        models.RegisteredCar.deleted_date.is_(None)
    ).first()

    if db_car is None:
        return None

    try:
        api_results = get_embeddings_from_api_bytes(images)
    except Exception as e:
        print(f"Embedding extraction failed: {e}")
        return []

    embeddings_map = {res["filename"]: res["embedding"] for res in api_results if res.get("embedding")}

    # Drop the car's existing images so an "update" is a clean replace.
    db.query(models.CarImage).filter(models.CarImage.car_id == car_id).delete()

    UPLOAD_DIR = "uploaded_images"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    updated_images = []
    for image in images:
        embedding = embeddings_map.get(image.filename)
        if embedding is None:
            continue

        file_bytes = image.file.read()
        timestamp = int(time.time())
        unique_filename = f"{car_id}_{timestamp}_{image.filename}"
        local_file_path = os.path.abspath(os.path.join(UPLOAD_DIR, unique_filename))
        with open(local_file_path, "wb") as f:
            f.write(file_bytes)

        new_image = models.CarImage(
            image_path=local_file_path,
            embedding_vector=embedding,
            car_id=car_id,
        )
        db.add(new_image)
        updated_images.append(new_image)

    db.commit()
    for img in updated_images:
        db.refresh(img)
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
