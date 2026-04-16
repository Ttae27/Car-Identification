import React, { useState, useEffect } from 'react';

// --- TYPES ---
interface CarRecord {
  car_id: string;
  plate: string;
  label: string | null;
  description: string | null;
  image_url: string | null; // ของเดิมมีแค่ URL เดียว (ถ้า API อัปเดตให้ส่งกลับมาเป็น Array ได้จะดีมากครับ)
}

interface CarFormProps {
  initialData?: CarRecord;
  onBack: () => void; 
}

const Sidebar: React.FC = () => (
  <aside className="w-64 bg-[#4A4F53] h-full p-4 flex flex-col border-r border-gray-600 shrink-0">
    <div className="bg-[#F7C003] h-10 rounded-md w-full mb-6"></div>
    <div className="flex items-center justify-between cursor-pointer hover:opacity-80 transition-opacity">
      <span className="text-[#F7C003] font-medium text-sm">แสดงรายการข้อมูล</span>
      <div className="bg-[#F7C003] h-6 w-12 rounded-md"></div>
    </div>
  </aside>
);

const CarForm: React.FC<CarFormProps> = ({ initialData, onBack }) => {
  const isEditMode = !!initialData;

  const [formData, setFormData] = useState({
    plate: '',
    label: '',
    description: ''
  });

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]); 
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);

  useEffect(() => {
    if (initialData) {
      setFormData({
        plate: initialData.plate || '',
        label: initialData.label || '',
        description: initialData.description || ''
      });
      if (initialData.image_url) {
        setPreviewUrls([initialData.image_url]);
      }
    }
    
    return () => {
      previewUrls.forEach(url => {
        if (url.startsWith('blob:')) URL.revokeObjectURL(url);
      });
    };
  }, [initialData]);
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files);
      
      setSelectedFiles(prev => [...prev, ...filesArray]);
      
      const newPreviews = filesArray.map(file => URL.createObjectURL(file));
      setPreviewUrls(prev => [...prev, ...newPreviews]);
    }
  };

  const handleRemoveImage = (indexToRemove: number) => {
    const urlToRemove = previewUrls[indexToRemove];
    if (urlToRemove.startsWith('blob:')) {
      URL.revokeObjectURL(urlToRemove); // คืน Memory
    }
    
    setPreviewUrls(prev => prev.filter((_, index) => index !== indexToRemove));
    
    setSelectedFiles(prev => prev.filter((_, index) => index !== indexToRemove));
  };

  const handleSubmit = async () => {
    if (!formData.plate) {
      alert("กรุณากรอกทะเบียนรถ (Plate is required)");
      return;
    }

    try {
      let currentCarId = initialData?.car_id;

      if (isEditMode && currentCarId) {
        const response = await fetch(`http://127.0.0.1:8000/cars/${currentCarId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            plate: formData.plate,
            label: formData.label || null,
            description: formData.description || null,
          }),
        });

        if (!response.ok) throw new Error("Failed to update car");
        alert("อัปเดตข้อมูลรถสำเร็จ!");

      } else {
        const response = await fetch(`http://127.0.0.1:8000/cars/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            plate: formData.plate,
            label: formData.label || null,
            description: formData.description || null,
          }),
        });

        if (!response.ok) throw new Error("Failed to create car");
        const newCar = await response.json();
        currentCarId = newCar.car_id; // ได้ ID รถคันใหม่มา
      }

      if (currentCarId && selectedFiles.length > 0) {
        const imageFormData = new FormData();
        selectedFiles.forEach(file => {
          imageFormData.append("images", file); 
        });

        const imgResponse = await fetch(`http://127.0.0.1:8000/cars/${currentCarId}/images/`, {
          method: 'POST',
          body: imageFormData,
        });

        if (!imgResponse.ok) throw new Error("Failed to upload images");
        alert(isEditMode ? "อัปโหลดรูปภาพใหม่สำเร็จ!" : "สร้างข้อมูลรถและอัปโหลดรูปสำเร็จ!");
      }

      onBack();

    } catch (error: any) {
      console.error("API Error:", error);
      alert(`เกิดข้อผิดพลาด: ${error.message}`);
    }
  };

  const handleDelete = async () => {

    if (!initialData) return;



    if (window.confirm('คุณแน่ใจหรือไม่ว่าต้องการลบข้อมูลนี้? (Are you sure you want to delete this?)')) {

      try {

        console.log("Deleting Data via API DELETE for ID:", initialData.car_id);

       

        const response = await fetch(`http://127.0.0.1:8000/cars/${initialData.car_id}`, {

          method: 'DELETE',

        });



        if (!response.ok) {

          const errorData = await response.json();

          throw new Error(errorData.detail || "Failed to delete car");

        }



        alert("ลบข้อมูลสำเร็จ!");

        onBack();



      } catch (error: any) {

        console.error("API Error:", error);

        alert(`เกิดข้อผิดพลาดในการลบ: ${error.message}`);

      }

    }

  };

  return (
    <div className="flex h-screen w-full bg-[#5C666B] font-sans overflow-hidden">
      <Sidebar />
      
      <main className="flex-1 flex flex-col items-center justify-center p-8 relative overflow-y-auto">
        <button 
          onClick={onBack}
          className="absolute top-6 left-8 text-white bg-[#4A4F53] px-4 py-2 rounded hover:bg-gray-600 transition"
        >
          &larr; กลับ
        </button>

        <div className="bg-[#4A4F53] rounded-xl p-8 shadow-lg max-w-4xl w-full border border-gray-600 my-auto">
          
          <div className="bg-[#3d4957] p-4 rounded-md mb-8">
            <div className="flex justify-between items-center mb-4">
              <span className="text-[#F7C003] font-bold">แกลลอรี่ภาพรถ</span>
              
              <label className="bg-[#F7C003] text-black px-4 py-1.5 rounded cursor-pointer hover:bg-yellow-500 transition font-medium text-sm">
                + อัปโหลดรูปภาพ
                <input 
                  type="file" 
                  multiple 
                  accept="image/*" 
                  onChange={handleFileChange} 
                  className="hidden" 
                />
              </label>
            </div>

            <div className="grid grid-cols-3 gap-2">
              {previewUrls.length === 0 ? (
                <div className="col-span-3 text-center py-8 text-gray-400 text-sm">
                  ยังไม่มีรูปภาพ กรุณาอัปโหลด
                </div>
              ) : (
                previewUrls.map((url, index) => (
                  <div key={index} className="relative group">
                    <img 
                      src={url} 
                      alt={`Car preview ${index}`} 
                      className="w-full h-32 object-cover rounded border border-gray-600"
                    />
                    <button
                      onClick={() => handleRemoveImage(index)}
                      className="absolute top-1 right-1 bg-red-600 text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold opacity-80 hover:opacity-100 hover:scale-110 transition-all shadow-md"
                      title="ลบรูปนี้"
                    >
                      X
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* --- ส่วน Form Inputs (เหมือนเดิม) --- */}
          <div className="grid grid-cols-2 gap-6 mb-6">
            <div>
              <label className="block text-[#F7C003] font-bold mb-2">ทะเบียนรถ (Plate)</label>
              <input type="text" name="plate" value={formData.plate} onChange={handleChange} className="w-full bg-[#e0e0e0] px-4 py-3 focus:outline-none" />
            </div>
            <div>
              <label className="block text-[#F7C003] font-bold mb-2">ป้ายกำกับ (Label)</label>
              <input type="text" name="label" value={formData.label} onChange={handleChange} className="w-full bg-[#e0e0e0] px-4 py-3 focus:outline-none" />
            </div>
          </div>

          <div className="mb-8">
            <label className="block text-[#F7C003] font-bold mb-2">คำอธิบาย (Description)</label>
            <textarea name="description" value={formData.description} onChange={handleChange} rows={4} className="w-full bg-[#e0e0e0] px-4 py-3 focus:outline-none resize-none" />
          </div>

          <div className="flex justify-end items-center space-x-4">
            <button onClick={handleSubmit} className="bg-[#F7C003] text-black font-bold px-8 py-2 rounded-sm shadow-md">
              {isEditMode ? 'update' : 'CREATE'}
            </button>
            {isEditMode && (
              <button onClick={handleDelete} className="bg-[#cc0000] text-white font-bold px-8 py-2 rounded-sm shadow-md">
                DELETE
              </button>
            )}
          </div>

        </div>
      </main>
    </div>
  );
};

export default CarForm;