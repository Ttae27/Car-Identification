import React, { useState, useEffect } from "react"
import { type CarRecord } from "./carList";


interface CarFormProps {
  initialData?: CarRecord;
  onBack: () => void;
}

const CarForm: React.FC<CarFormProps> = ({ initialData, onBack }) => {
  const isEditMode: boolean = !!initialData;

  const [ formData, setFormData ] = useState({
    plate: '',
    label: '',
    description: ''
  });

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

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
      previewUrls.forEach((url: string) => {
        if(url.startsWith('blob:')) URL.revokeObjectURL(url);
      });
    };
  }, [initialData]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev: typeof formData) => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if(e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files) as File[];
      setSelectedFiles((prev: File[]) => [...prev, ...filesArray]);

      const newPreviews = filesArray.map(file => URL.createObjectURL(file));
      setPreviewUrls((prev: string[]) => [...prev, ...newPreviews]);
    }
  };

  const handleRemoveImage = (indexToRemove: number) => {
    const urlToRemove = previewUrls[indexToRemove];
    if (urlToRemove.startsWith('blob:')){
      URL.revokeObjectURL(urlToRemove);
    }
    setPreviewUrls((prev: string[]) => prev.filter((_, index) => index !== indexToRemove));
    setSelectedFiles((prev: File[]) => prev.filter((_, index) => index !== indexToRemove));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.plate) {
      alert("กรุณากรอกหมายเลขทะเบียน");
      return;
    }

    setIsSubmitting(true);
    try {
      let currentCarId = initialData?.car_id;

      const method = isEditMode ? "PUT" : "POST";
      const url = isEditMode
        ? `http://127.0.0.1:8000/cars/${currentCarId}` 
        : `http://127.0.0.1:8000/cars/`;
      const response = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if(!response.ok) throw new Error("Failed to save car data");

      if (!isEditMode) {
        const newCar = await response.json();
        currentCarId = newCar.car_id;
      }

      if (currentCarId && selectedFiles.length > 0) {
        const imageFormData = new FormData();
        selectedFiles.forEach(file => imageFormData.append('images', file));

        const imgRes = await fetch(`http://127.0.0.1:8000/cars/${currentCarId}/images/`, {
          method: 'POST',
          body: imageFormData,
        });
        if(!imgRes.ok) throw new Error("Failed to upload images");
      }

      alert("บันทึกข้อมูลรถสำเร็จ");
      onBack();
    } catch (err: any) {
      alert(err.message || "เกิดข้อผิดพลาดในการบันทึกข้อมูลรถ");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!initialData || !window.confirm("คุณแน่ใจหรือไม่ว่าต้องการลบรถคันนี้?")) return;

    try {
      const res = await fetch(`http://127.0.0.1:8000/cars/${initialData.car_id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error("ลบข้อมูลไม่สำเร็จ");
      alert("ลบรถสำเร็จ");
      onBack();
    } catch (err: any) {
      alert(err.message || "เกิดข้อผิดพลาดในการลบรถ");
    }
  };

  return (
    <>
      <div className="car-form-container">
        <header className="form-header">
          <button className="back-btn" onClick={onBack}>&larr; กลับ</button>
          <h1>{isEditMode ? "แก้ไขข้อมูลรถ" : "สร้างรถใหม่"}</h1>
        </header>

        <main className="form-content">
          <form onSubmit={handleSubmit} className="car-form">
            <section className="form-gallery">
              <div className="gallery-header">
                <h3>รูปภาพรถ</h3>
                <label className="file-upload-btn">
                  + อัปโหลดรูปภาพ
                  <input
                    type="file"
                    multiple
                    accept="image/*"
                    onChange={handleFileChange}
                    className="input-file-hidden"
                  />
                </label>
              </div>
              
              <div className="image-grid-preview">
                {previewUrls.length === 0 ? (
                  <p className="empty-msg">ยังไม่มีรูปภาพ</p>
                ) : (
                  previewUrls.map((url, index) => (
                    <div key={index} className="preview-item">
                      <img src={url} alt="Preview"/>
                      <button
                        type="button"
                        className="btn-remove-img"
                        onClick={() => handleRemoveImage(index)}
                      >
                        &times;
                      </button>
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="form-inputs">
              <div className="input-row">
                <div className="input-group">
                  <label htmlFor="plate">หมายเลขทะเบียน</label>
                  <input
                    id="plate"
                    type="text"
                    name="plate"
                    value={formData.plate}
                    onChange={handleInputChange}
                    required
                  />
                </div>
                <div className="input-group">
                  <label htmlFor="label">ป้ายกำกับ</label>
                  <input
                    id="label"
                    type="text"
                    name="label"
                    value={formData.label}
                    onChange={handleInputChange}
                  />
                </div>
              </div>
              <div className="input-group full-width">
                <label htmlFor="description">รายละเอียด</label>
                <textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  rows={4}
                />
              </div>
            </section>

            <footer className="form-footer">
              {isEditMode && (
                <button type="button" className="btn-action-delete" onClick={handleDelete}>
                  DELETE
                </button>
              )}
              <button type="submit" className="btn-action-submit" disabled={isSubmitting}>
                {isSubmitting ? 'SAVING...' : (isEditMode ? 'UPDATE' : 'CREATE')}
              </button>
            </footer>

          </form>
        </main>
      </div>
    </>
  );
};

export default CarForm;