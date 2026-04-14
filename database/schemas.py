from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

# ==== Log schemas ====
class LogsBase(BaseModel):
    location: str
    status: bool
    camera: str

class LogsCreate(LogsBase):
    timestamp: Optional[datetime] = None

class LogsResponse(LogsBase):
    id: int
    car_id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

# ==== CarImage schemas ====
class CarImageBase(BaseModel):
    image_path: str
    embedding_vector: list[float] = Field(
        ...,
        min_length=768,
        max_length=768
    )

class CarImageCreate(CarImageBase):
    pass

class CarImageUpdate(CarImageBase):
    pass

class CarImageResponse(CarImageBase):
    id: int
    car_id: UUID

    model_config = ConfigDict(from_attributes=True)

# ==== Car schemas ====
class RegisteredCarBase(BaseModel):
    description: Optional[str] = None
    label: Optional[str] = None
    plate: str = Field(..., max_length=20)

class RegisteredCarCreate(RegisteredCarBase):
    created_by: Optional[str] = None

class RegisteredCarUpdate(RegisteredCarBase):
    updated_by: Optional[str] = None

class RegisteredCarResponse(RegisteredCarBase):
    car_id: UUID
    created_by: Optional[str] = None
    created_date: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class RegisteredCarDetailResponse(RegisteredCarResponse):
    images: list[CarImageResponse] = []
    logs: list[LogsResponse] = []

class PaginatedCarItem(RegisteredCarResponse):
    image_url: Optional[str] = None

class PaginatedCarsResponse(BaseModel):
    items: list[PaginatedCarItem]
    total: int
    page: int
    size: int
    pages: int