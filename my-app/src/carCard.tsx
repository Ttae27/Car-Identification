import React from "react";
import { type CarRecord } from "./carList";

interface CarCardProps {
    data: CarRecord;
    onClick: (car: CarRecord) => void;
}

const CarCard: React.FC<CarCardProps> = ({data, onClick }) => {
    const imgSrc = data.image_url || "https://via.placeholder.com/150x100/e0e0e0/000000?text=No+Image";
    return (
        <article 
        className="car-card"
        onClick={() => onClick(data)}
        >
            <img src={imgSrc} alt={`รถทะเบียน ${data.plate}`} className="car-card-image" />
            <div className="car-card-content">
                <h3 className="car-card-title">ทะเบียน: {data.plate}</h3>
                <p className="car-card-label">ยี่ห้อ: {data.label || "ไม่ระบุ"}</p>
                <p className="car-card-description">คำอธิบาย: {data.description || "ไม่มีรายละเอียด"}</p>
            </div>
        </article>
    )
}

export default CarCard;