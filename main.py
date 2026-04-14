from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import math
from database.database import get_db
from uuid import UUID
from typing import List
import database.schemas as schemas
import services
import os


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CREATE
## Create a new car
@app.post("/cars/", response_model=schemas.RegisteredCarResponse)
async def create_car(
    car: schemas.RegisteredCarCreate,
    db: services.Session = Depends(get_db)):

    car_db = services.create_car(car, db)
    if car_db is None:
        raise HTTPException(status_code=400, detail="Car with this plate already exists")
    
    return car_db

## create a new image for a car
@app.post("/cars/{car_id}/images/", response_model=List[schemas.CarImageResponse])
async def add_car_image(
    car_id: UUID,
    images: List[UploadFile] = File(...),
    db: services.Session = Depends(get_db)
):
    image_db = services.add_car_image(car_id, images, db)
    
    if image_db is None:
        raise HTTPException(status_code=404, detail="Car not found")
    
    return image_db

# READ
## Get all active cars
@app.get("/cars/", response_model=schemas.PaginatedCarsResponse)
async def read_cars(
    request: Request, 
    page: int = 1, 
    size: int = 8, 
    db: services.Session = Depends(get_db)
):
    skip = (page - 1) * size
    cars, total = services.read_cars_paginated(db, skip=skip, limit=size)
    
    items = []
    for car in cars:
        image_url = None
        if car.images:
            image_url = str(request.url_for('get_car_image', car_id=car.car_id))
            
        car_dict = schemas.RegisteredCarResponse.model_validate(car).model_dump()
        items.append({**car_dict, "image_url": image_url})

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": math.ceil(total / size) if total > 0 else 1
    }

@app.get("/cars/{car_id}/image", response_class=FileResponse)
async def get_car_image(car_id: UUID, db: services.Session = Depends(get_db)):
    car = services.read_car_details(car_id, db)
    
    if not car or not car.images:
        raise HTTPException(status_code=404, detail="Image not found for this car")
        
    image_path = car.images[0].image_path
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image file missing on server")
        
    return FileResponse(image_path)

@app.get("/cars/{car_id}", response_model=schemas.RegisteredCarDetailResponse)
async def read_car_details(car_id: UUID, db: services.Session = Depends(get_db)):
    car = services.read_car_details(car_id, db)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    return car

# UPDATE
@app.put("/cars/{car_id}", response_model=schemas.RegisteredCarResponse)
async def update_car(car_id: UUID, car: schemas.RegisteredCarUpdate, db: services.Session = Depends(get_db)):
    updated_car = services.update_car(car_id, car, db)
    if updated_car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    return updated_car

@app.put("/cars/{car_id}/images/", response_model=List[schemas.CarImageResponse])
async def update_car_image(car_id: UUID, images: List[schemas.CarImageUpdate], db: services.Session = Depends(get_db)):
    updated_images = services.update_car_image(car_id, images, db)
    if updated_images is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return updated_images

# DELETE
@app.delete("/cars/{car_id}")
async def delete_car(car_id: UUID, db: services.Session = Depends(get_db)):
    deleted_car = services.delete_car(car_id, db)
    if deleted_car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    return {"detail": "Car deleted successfully"}

    