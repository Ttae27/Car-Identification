"""Minimal client for the shared DINOv3 embedding service (model/dino).

Both back-end (Dahua ingest) and regis-back-end (registered-car embeds + CCTV
matching) call this same service so the resulting vectors live in the same
metric space and cosine similarity is meaningful.
"""

import os
from typing import List, Sequence

import requests


DINOV3_URL = os.getenv("DINOV3_URL", "http://localhost:8000").rstrip("/")
DINOV3_TIMEOUT = float(os.getenv("DINOV3_TIMEOUT", 30.0))
DINOV3_BATCH_SIZE = int(os.getenv("DINOV3_BATCH_SIZE", 32))


def embed_image(image_bytes: bytes) -> List[float]:
    """Embed a single image. Returns the vector as a list of floats."""
    resp = requests.post(
        f"{DINOV3_URL}/embed",
        data=image_bytes,
        headers={"Content-Type": "application/octet-stream"},
        timeout=DINOV3_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def embed_batch(images: Sequence[bytes]) -> List[List[float]]:
    """Embed multiple images. Auto-chunks at DINOV3_BATCH_SIZE; preserves order."""
    all_embeddings: List[List[float]] = []
    for i in range(0, len(images), DINOV3_BATCH_SIZE):
        chunk = images[i : i + DINOV3_BATCH_SIZE]
        files = [
            ("files", (f"image_{i+j}", img, "application/octet-stream"))
            for j, img in enumerate(chunk)
        ]
        resp = requests.post(
            f"{DINOV3_URL}/embed/batch",
            files=files,
            timeout=DINOV3_TIMEOUT,
        )
        resp.raise_for_status()
        all_embeddings.extend(resp.json()["embeddings"])
    return all_embeddings
