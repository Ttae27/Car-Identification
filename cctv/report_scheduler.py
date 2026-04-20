import sys
import os
import time
import schedule
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from dotenv import load_dotenv
from database.database import SessionLocal
from database import models

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

env_path = os.path.join(current_dir, "cctv.env")
load_dotenv(dotenv_path=env_path)


QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("COLLECTION_NAME")

q_client = QdrantClient(
    url=QDRANT_URL, 
    api_key=QDRANT_API_KEY if QDRANT_API_KEY else None
)

SIMILARITY_THRESHOLD = 0.95 

def process_unmatched_frames():
    print(f"Starting CCTV matching job (Threshold: {SIMILARITY_THRESHOLD*100}%)...")
    
    # 1. Fetch all vectors from Qdrant where processed == False
    unprocessed_points, _ = q_client.scroll(
        collection_name=QDRANT_COLLECTION,
        scroll_filter=qmodels.Filter(
            must=[qmodels.FieldCondition(key="processed", match=qmodels.MatchValue(value=False))]
        ),
        limit=1000,
        with_vectors=True, 
        with_payload=True
    )

    if not unprocessed_points:
        print("No new frames to process.")
        return

    db: Session = SessionLocal()
    processed_ids = []

    try:
        for point in unprocessed_points:
            cctv_vector = point.vector
            payload = point.payload
            camera_id = payload.get("camera_id", "Unknown")
            image_path = payload.get("image_path", "Path Missing")
            timestamp = payload.get("timestamp")
            
            print(f"\n--- Processing frame from {camera_id} ---")
            
            # 2. Convert pgvector distance to Cosine Similarity (1 - distance)
            similarity_col = (1 - models.CarImage.embedding_vector.cosine_distance(cctv_vector)).label("similarity")

            # 3. Query the Top 5 closest matches (Ordering by DESC so highest similarity is first)
            top_matches = db.query(
                models.RegisteredCar,
                similarity_col
            ).join(
                models.CarImage
            ).filter(
                models.RegisteredCar.deleted_date.is_(None) # Only active cars
            ).order_by(
                similarity_col.desc()
            ).limit(5).all()

            if top_matches:
                print(f"Top 5 Database Matches:")
                for i, (car, similarity) in enumerate(top_matches, 1):
                    print(f"  {i}. Plate: {car.plate:8} | Similarity: {similarity*100:.2f}%")

                # 4. Check if the BEST match passes our strict threshold
                best_car, best_similarity = top_matches[0]
                
                if best_similarity >= SIMILARITY_THRESHOLD:
                    print(f"✅ MATCH CONFIRMED! Logged Car {best_car.plate} to database.")
                    
                    # Log Registered Vehicle
                    new_log = models.Logs(
                        timestamp=timestamp,
                        status=True,  # Registered
                        similarity_score=best_similarity,
                        frame_image_path=image_path,
                        camera=camera_id,
                        car_id=best_car.car_id
                    )
                else:
                    print(f"❌ No match passed the strict threshold of {SIMILARITY_THRESHOLD*100}%. Logged as Unregistered.")
                    
                    # Log Unregistered/Unknown Vehicle
                    new_log = models.Logs(
                        timestamp=timestamp,
                        status=False, # Unregistered
                        similarity_score=best_similarity, # Log the highest score it got, even if it failed
                        frame_image_path=image_path,
                        camera=camera_id,
                        car_id=None # No car matched
                    )
                
                db.add(new_log)
                
            else:
                print("No registered cars found in the database to compare against. Logged as Unregistered.")
                # Failsafe: Log if the database has 0 registered cars
                new_log = models.Logs(
                    timestamp=timestamp,
                    status=False,
                    similarity_score=0.0,
                    frame_image_path=image_path,
                    camera=camera_id,
                    car_id=None
                )
                db.add(new_log)
            
            # Add to list of points we finished processing
            processed_ids.append(point.id)

        db.commit()

        # 5. Mark them as processed in Qdrant so we don't check them again
        if processed_ids:
            q_client.set_payload(
                collection_name=QDRANT_COLLECTION,
                payload={"processed": True},
                points=processed_ids
            )
            print(f"\nSuccessfully processed {len(processed_ids)} frames.")

    except Exception as e:
        print(f"Error during processing: {e}")
        db.rollback()
    finally:
        db.close()

schedule.every(1).minutes.do(process_unmatched_frames)

if __name__ == "__main__":
    process_unmatched_frames() 
    
    while True:
        schedule.run_pending()
        time.sleep(1)