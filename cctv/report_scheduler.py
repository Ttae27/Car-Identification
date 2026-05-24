"""Match unchecked CCTV detections (Qdrant) against registered cars (pgvector).

Reads the same collection back-end writes to (CCTV_CAR with named vectors
`embedding_image` / `embedding_text`, payload includes `is_check` and `status`).
For each detection where `is_check` is False:
  1. Pull its image vector and payload (incl. Dahua-OCR `plate_no`).
  2. Plate-first: if `plate_no` exactly matches a `registered_car.plate`,
     that's the match. Otherwise fall back to cosine similarity against
     `car_image.embedding_vector`, matched when best score >= SIMILARITY_THRESHOLD.
  3. If matched, insert a `logs` row with `match_method` = "plate_no" or
     "similarity" depending on which path won. Unmatched detections are
     NOT logged to Postgres.
  4. Update the Qdrant point's payload: is_check=True (always),
     status=<matched bool>, and registered_car_plate_no when matched.
"""

import os
import sys
import time
import schedule
from datetime import datetime
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from database.database import SessionLocal
from database import models

env_path = os.path.join(current_dir, "cctv.env")
load_dotenv(dotenv_path=env_path)


QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "CCTV_CAR")

# Mirrors back-end/config.py:IMAGE_VECTOR_NAME (hardcoded there). Both
# services must agree on this key; don't make it env-configurable on one
# side only or the matcher will silently read None for every point.
IMAGE_VECTOR_NAME = "embedding_image"

SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.75))
SCAN_LIMIT = int(os.getenv("SCAN_LIMIT", 10000))

# Values for Logs.match_method — which decision path produced a match.
MATCH_BY_PLATE = "plate_no"
MATCH_BY_SIMILARITY = "similarity"

q_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY if QDRANT_API_KEY else None,
)


def _parse_timestamp(payload: dict):
    """Build a timestamp for the Logs row from the Qdrant payload.

    back-end stores `date` (YYYY-MM-DD) and `time` (HH:MM:SS) separately.
    Fall back to now() if either is missing or unparseable.
    """
    date_str = payload.get("date")
    time_str = payload.get("time")
    if date_str and time_str:
        try:
            return datetime.fromisoformat(f"{date_str}T{time_str}")
        except ValueError:
            pass
    return datetime.utcnow()


def process_unmatched_frames():
    print(f"Starting CCTV matching job (threshold={SIMILARITY_THRESHOLD*100:.1f}%) ...")

    unprocessed_points, _ = q_client.scroll(
        collection_name=QDRANT_COLLECTION,
        scroll_filter=qmodels.Filter(
            must=[qmodels.FieldCondition(
                key="is_check",
                match=qmodels.MatchValue(value=False),
            )]
        ),
        limit=SCAN_LIMIT,
        with_vectors=[IMAGE_VECTOR_NAME],
        with_payload=True,
    )

    if not unprocessed_points:
        print("No new frames to process.")
        return

    db: Session = SessionLocal()

    # Per-point payload update accumulator — applied at the end.
    updates: list[tuple[str, dict]] = []

    try:
        for point in unprocessed_points:
            # Named-vector collections return `point.vector` as a dict.
            vec = point.vector
            if isinstance(vec, dict):
                cctv_vector = vec.get(IMAGE_VECTOR_NAME)
            else:
                cctv_vector = vec

            if cctv_vector is None:
                print(f"Point {point.id} has no '{IMAGE_VECTOR_NAME}' vector — skipping.")
                continue

            payload = point.payload or {}
            camera_id = payload.get("camera_id", "Unknown")
            image_path = payload.get("file_path_car") or payload.get("image_path") or ""
            timestamp = _parse_timestamp(payload)

            print(f"\n--- Processing frame from {camera_id} (point {point.id}) ---")

            plate_no = (payload.get("plate_no") or "").strip()
            matched_car: Optional[models.RegisteredCar] = None
            match_method: Optional[str] = None
            best_similarity: Optional[float] = None

            # 1. Plate-first — exact (case-insensitive) match wins, no image gate.
            if plate_no:
                matched_car = (
                    db.query(models.RegisteredCar)
                    .filter(func.upper(models.RegisteredCar.plate) == plate_no.upper())
                    .filter(models.RegisteredCar.deleted_date.is_(None))
                    .first()
                )
                if matched_car:
                    match_method = MATCH_BY_PLATE
                    sim_col = (
                        1 - models.CarImage.embedding_vector.cosine_distance(cctv_vector)
                    ).label("similarity")
                    sim_row = (
                        db.query(sim_col)
                        .filter(models.CarImage.car_id == matched_car.car_id)
                        .order_by(sim_col.desc())
                        .first()
                    )
                    best_similarity = float(sim_row[0]) if sim_row else None
                    sim_str = f"{best_similarity*100:.2f}%" if best_similarity is not None else "n/a"
                    print(f"🪪 PLATE MATCH: {matched_car.plate} (image sim {sim_str} — audit only)")

            # 2. Image fallback when plate is missing or unknown to the registry.
            if matched_car is None:
                similarity_col = (
                    1 - models.CarImage.embedding_vector.cosine_distance(cctv_vector)
                ).label("similarity")
                top_matches = (
                    db.query(models.RegisteredCar, similarity_col)
                    .join(models.CarImage)
                    .filter(models.RegisteredCar.deleted_date.is_(None))
                    .order_by(similarity_col.desc())
                    .limit(5)
                    .all()
                )

                if top_matches:
                    print("Top 5 database matches:")
                    for i, (car, similarity) in enumerate(top_matches, 1):
                        print(f"  {i}. Plate: {car.plate:8} | Similarity: {similarity*100:.2f}%")

                    best_car, best_sim = top_matches[0]

                    if best_sim >= SIMILARITY_THRESHOLD:
                        print(f"✅ MATCH: {best_car.plate} ({best_sim*100:.2f}%)")
                        matched_car = best_car
                        match_method = MATCH_BY_SIMILARITY
                        best_similarity = float(best_sim)
                    else:
                        print(f"❌ No match >= {SIMILARITY_THRESHOLD*100:.1f}% (best {best_sim*100:.2f}%)")
                else:
                    print("No registered cars in DB — marking checked, no log written.")

            if matched_car is not None:
                new_log = models.Logs(
                    timestamp=timestamp,
                    match_method=match_method,
                    similarity_score=best_similarity,
                    frame_image_path=image_path,
                    camera=str(camera_id),
                    car_id=matched_car.car_id,
                )
                db.add(new_log)

            payload_patch = {
                "is_check": True,
                "status": matched_car is not None,
            }
            if matched_car is not None:
                payload_patch["registered_car_plate_no"] = matched_car.plate
            updates.append((point.id, payload_patch))

        db.commit()

        for pid, patch in updates:
            q_client.set_payload(
                collection_name=QDRANT_COLLECTION,
                payload=patch,
                points=[pid],
            )
        print(f"\nProcessed {len(updates)} frames.")

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
