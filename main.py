from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
from database.database import get_db
from uuid import UUID
from typing import List
import database.schemas as schemas
import services


app = FastAPI()

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
@app.get("/cars/", response_model=List[schemas.RegisteredCarResponse])
async def read_cars(db: services.Session = Depends(get_db)):
    cars = services.read_cars(db)
    if cars == []:
        raise HTTPException(status_code=404, detail="No cars found")
    return cars

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
async def update_car_image(
    car_id: UUID,
    images: List[UploadFile] = File(...),
    db: services.Session = Depends(get_db),
):
    updated_images = services.update_car_image(car_id, images, db)
    if updated_images is None:
        raise HTTPException(status_code=404, detail="Car not found")
    return updated_images

# DELETE
@app.delete("/cars/{car_id}")
async def delete_car(car_id: UUID, db: services.Session = Depends(get_db)):
    deleted_car = services.delete_car(car_id, db)
    if deleted_car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    return {"detail": "Car deleted successfully"}

    