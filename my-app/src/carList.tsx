import React, { useState, useEffect } from 'react';

// --- TYPES ---
interface CarRecord {
  car_id: string;
  plate: string;
  label: string | null;
  description: string | null;
  image_url: string | null; // URL provided by FastAPI
}

interface PaginatedResponse {
  items: CarRecord[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// --- COMPONENTS ---

const Sidebar: React.FC = () => (
  <aside className="w-64 bg-[#4A4F53] h-full p-4 flex flex-col border-r border-gray-600 shrink-0">
    <div className="bg-[#F7C003] h-10 rounded-md w-full mb-6"></div>
    <div className="flex items-center justify-between cursor-pointer hover:opacity-80 transition-opacity">
      <span className="text-[#F7C003] font-medium text-sm">แสดงรายการข้อมูล</span>
      <div className="bg-[#F7C003] h-6 w-12 rounded-md"></div>
    </div>
  </aside>
);

const CarCard: React.FC<{ data: CarRecord }> = ({ data }) => {
  // Fallback image if the car has no image_url
  const imgSrc = data.image_url || 'https://via.placeholder.com/150x100/e0e0e0/000000?text=No+Image';

  return (
    <div className="bg-[#3d4957] flex p-4 shadow-md border border-[#3d4957]">
      <img
        src={imgSrc}
        alt={`รถทะเบียน ${data.plate}`}
        className="w-36 h-24 object-cover rounded-sm"
      />
      <div className="ml-4 flex flex-col justify-center flex-1">
        <h3 className="text-[#F7C003] text-xl font-bold mb-2">
          ทะเบียน: {data.plate}
        </h3>
        <p className="text-white text-sm mb-1">
          <span className="text-[#F7C003] font-medium mr-1">label:</span> 
          {data.label || '-'}
        </p>
        <p className="text-white text-sm">
          <span className="text-[#F7C003] font-medium mr-1">คำอธิบาย:</span> 
          {data.description || '-'}
        </p>
      </div>
    </div>
  );
};

// --- MAIN APP LAYOUT ---

const CarList: React.FC = () => {
  const [data, setData] = useState<CarRecord[]>([]);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Fetch data when the component mounts or when currentPage changes
  useEffect(() => {
    const fetchCars = async () => {
      setIsLoading(true);
      try {
        // Updated to use the explicit 127.0.0.1 IP address
        const response = await fetch(`http://127.0.0.1:8000/cars/?page=${currentPage}&size=8`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result: PaginatedResponse = await response.json();
        setData(result.items);
        setTotalPages(result.pages);
      } catch (error) {
        console.error("Error fetching cars:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchCars();
  }, [currentPage]);

  const handlePrevPage = () => {
    if (currentPage > 1) setCurrentPage(prev => prev - 1);
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) setCurrentPage(prev => prev + 1);
  };

  return (
    <div className="flex h-screen w-full bg-[#5C666B] font-sans overflow-hidden">
      <Sidebar />
        <main className="flex-1 flex flex-col relative overflow-y-auto">
          {/* Floating Action Button (+) */}
          <div className="absolute top-6 right-8 z-10">
            <button 
              className="bg-[#F7C003] w-11 h-11 rounded-full flex items-center justify-center text-black text-5xl font-bold leading-none shadow-lg hover:bg-yellow-500 transition-colors focus:outline-none"
              aria-label="Add new record"
            >
              {/* Adding pb-1 slightly nudges the plus sign up, 
                  offsetting the natural bottom-heavy baseline of text characters */}
              <span className="pb-3">+</span>
            </button>
          </div>

        <div className="px-8 pt-24 pb-6 flex-1 flex flex-col">
          {isLoading ? (
            <div className="flex-1 flex items-center justify-center">
              <span className="text-white text-xl font-medium">Loading...</span>
            </div>
          ) : data.length === 0 ? (
             <div className="flex-1 flex items-center justify-center">
              <span className="text-white text-xl font-medium">No cars found.</span>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-6 gap-y-6">
              {data.map((car) => (
                <CarCard key={car.car_id} data={car} />
              ))}
            </div>
          )}

          <div className="grow"></div>

          {/* Dynamic Pagination Component */}
          <div className="flex items-center justify-center space-x-2 mt-8 mb-4">
            <button 
              onClick={handlePrevPage}
              disabled={currentPage === 1}
              className="bg-[#e0e0e0] text-black px-4 py-1.5 font-bold text-sm hover:bg-gray-300 disabled:opacity-50 transition-colors cursor-pointer disabled:cursor-not-allowed"
            >
              Prev
            </button>
            
            <span className="text-[#F7C003] font-bold text-lg px-4">
              Page {currentPage} of {totalPages}
            </span>
            
            <button 
              onClick={handleNextPage}
              disabled={currentPage === totalPages}
              className="bg-[#F7C003] text-black px-4 py-1.5 font-bold text-sm hover:bg-yellow-500 disabled:opacity-50 transition-colors cursor-pointer disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default CarList;