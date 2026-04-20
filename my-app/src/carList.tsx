import React, { useState, useEffect } from "react"
import CarCard from "./carCard";
import CarForm from "./carForm";
import Sidebar from "./sideBar";

export interface CarRecord {
  car_id: string;
  plate: string;
  label: string | null;
  description: string | null;
  image_url: string | null;
}

interface PaginationResponse {
  items: CarRecord[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

const CarList: React.FC = () => {
  const [data, setData] = useState<CarRecord[]>([]);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [currentView, setCurrentView] = useState<'list' | 'form'>('list');
  const [selectedCar, setSelectedCar] = useState<CarRecord | null>(null);

  const fetchCars = async () => {
    try {
      const resposne = await fetch(`http://127.0.0.1:8000/cars/?page=${currentPage}&size=8`);
      if (!resposne.ok) throw new Error("Failed to fetch data");
      const result: PaginationResponse = await resposne.json();
      setData(result.items || []);
      setTotalPages(result.pages);
    }
    catch (error) {
      console.error("Error fetching data:", error);
      setData([]);
  }
    finally {
      setIsLoading(false);
    }
  };
  useEffect(() => {
      fetchCars();
  }, [currentPage]);

  const handlePrevPage = () => {
    if (currentPage > 1) setCurrentPage((prev) => prev - 1);
  };

  const handleNextpage = () => {
    if (currentPage < totalPages) setCurrentPage((prev) => prev + 1);
  };

  const handleCreateCar = () => {
    setSelectedCar(null);
    setCurrentView('form');
  };

  const handleEditCar = (car: CarRecord) => { 
    setSelectedCar(car);
    setCurrentView('form');
  };

  const handleBackToList = () => {
    setCurrentView('list');
    setSelectedCar(null);
    fetchCars();
  };

  return (
    <div className="car-list-container">
      <div className="car-list-sidebar">
      <Sidebar 
        currentView={currentView} 
        onNavigate={(view) => {
          setCurrentView(view as 'list' | 'form');
          if(view === 'list') {
            fetchCars(); // โหลดข้อมูลใหม่ถ้าย้ายกลับมาหน้า List
            setSelectedCar(null);
          }
        }} 
      />
      </div>

      {currentView === 'form' ? (
        <CarForm initialData={selectedCar || undefined} onBack={handleBackToList} />
      ) : (
        <main className="car-list-view">
          <header className="car-list-header">
            <h1>Car List</h1>
            <button onClick={handleCreateCar}>
              Create New Car
            </button>
          </header>

          <section className="car-list-content">
            {isLoading ? (
              <div className="loading-indicator">
                <p>Loading...</p>
              </div>
            ) : data.length === 0 ? (
              <div className="empty-container">
                <p>No cars found.</p>
              </div>
            ) : (
              <div className="car-grid">
                {data.map((car) => (
                  <CarCard key={car.car_id} data={car} onClick={handleEditCar} />
                ))}
              </div>
            )}
          </section>

          {!isLoading && data.length > 0 && (
            <nav className="pagination-container">
              <button
                className="page-btn"
                onClick={handlePrevPage}
                disabled={currentPage === 1}
              >
                ก่อนหน้า
              </button>
              <span className="page-info">
                หน้า {currentPage} จาก {totalPages}
              </span>
              <button
                className="page-btn"
                onClick={handleNextpage}
                disabled={currentPage === totalPages}
              >
                ถัดไป
              </button>
            </nav>
          )}
        </main>
      )}
    </div>
  );
}
export default CarList;
