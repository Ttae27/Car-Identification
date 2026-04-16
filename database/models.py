import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass

class RegisteredCar(Base):
    __tablename__ = "registered_car"

    car_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    description: Mapped[Optional[str]] = mapped_column(Text)
    label: Mapped[Optional[str]] = mapped_column(Text) 
    plate: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    
    created_by: Mapped[Optional[str]] = mapped_column(String(255))
    created_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    updated_by: Mapped[Optional[str]] = mapped_column(String(255))
    updated_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=datetime.now(timezone.utc)
    )
    deleted_by: Mapped[Optional[str]] = mapped_column(String(255))
    deleted_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    images: Mapped[List["CarImage"]] = relationship(
        back_populates="car", cascade="all, delete-orphan"
    )
    logs: Mapped[List["Logs"]] = relationship(
        back_populates="car", cascade="all, delete-orphan"
    )


class CarImage(Base):
    __tablename__ = "car_image"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    
    EMBEDDING_DIMENSION = 768 
    embedding_vector = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)

    car_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("registered_car.car_id"), nullable=False, index=True
    )
    car: Mapped["RegisteredCar"] = relationship(back_populates="images")

class Logs(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location: Mapped[str] = mapped_column(Text, nullable=False, index=True) 
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    status: Mapped[bool] = mapped_column(Boolean, nullable=False) 
    camera: Mapped[str] = mapped_column(String(255), nullable=False) 

    car_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("registered_car.car_id"), nullable=False, index=True
    )
    car: Mapped["RegisteredCar"] = relationship(back_populates="logs")