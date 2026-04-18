import litserve as ls
import numpy as np
import torch
import os
import base64
from io import BytesIO

from peft import PeftModel
from PIL import Image
from transformers import AutoModel, AutoProcessor

class SigLIP2VisionAPI(ls.LitAPI):
    """
    SigLIP2API supporting strictly Image Embedding and Batch Image Embedding from Bytes.
    """

    def setup(self, device):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        adapter_path = os.path.join(current_dir, "lora_adapter2")
        
        base_model_id = "google/siglip-so400m-patch14-384"

        self.device = device
        print(f"Worker spawned using device: {self.device}")
        
        base_model = AutoModel.from_pretrained(base_model_id)
        self.model = PeftModel.from_pretrained(base_model, adapter_path)
        self.model.to(self.device).eval()

        self.processor = AutoProcessor.from_pretrained(adapter_path)

    def get_image_embedding(self, image_bytes: bytes) -> np.ndarray:
        try:
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            print(f"Error loading image from bytes: {e}")
            raise ValueError("Invalid image bytes")

        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            features = self.model.get_image_features(**inputs)
            
            if hasattr(features, "pooler_output"):
                image_features = features.pooler_output[0]
            elif isinstance(features, tuple):
                image_features = features[0][0]
            else:
                image_features = features[0] 
            
        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        return image_features.cpu().numpy()

    def get_batch_image_embeddings(self, batch_image_bytes: list) -> list:
        batch_size = len(batch_image_bytes)
        images = []
        valid_indices = []

        for idx, img_bytes in enumerate(batch_image_bytes):
            try:
                image = Image.open(BytesIO(img_bytes)).convert("RGB")
                images.append(image)
                valid_indices.append(idx)
            except Exception as e:
                print(f"Error loading image at index {idx}: {e}")
                images.append(None)
                valid_indices.append(idx)

        sub_batch_size = 16 
        all_embeddings = []

        for i in range(0, batch_size, sub_batch_size):
            end_idx = min(i + sub_batch_size, batch_size)
            sub_batch_images = []

            for j in range(i, end_idx):
                if images[j] is not None:
                    sub_batch_images.append(images[j])

            if not sub_batch_images:
                for j in range(i, end_idx):
                    all_embeddings.append(None)
                continue

            inputs = self.processor(images=sub_batch_images, return_tensors="pt").to(self.device)

            with torch.no_grad():
                features = self.model.get_image_features(**inputs)
                
                if hasattr(features, "pooler_output"):
                    batch_features = features.pooler_output
                elif isinstance(features, tuple):
                    batch_features = features[0]
                else:
                    batch_features = features 
                
                batch_features = batch_features / batch_features.norm(p=2, dim=1, keepdim=True)
                batch_features = batch_features.cpu().numpy()

            sub_idx = 0
            for j in range(i, end_idx):
                if images[j] is not None:
                    all_embeddings.append(batch_features[sub_idx])
                    sub_idx += 1
                else:
                    all_embeddings.append(None)

        results = []

        for idx, embedding in zip(valid_indices, all_embeddings):
            if embedding is not None:
                results.append({"index": idx, "embedding": embedding.tolist()})
            else:
                results.append({"index": idx, "error": "Failed to process image"})
                
        return results

    def decode_request(self, request):
        image_b64 = request.get("image_base64")
        batch_b64 = request.get("batch_image_base64")

        if image_b64 and not batch_b64:
            # Decode the base64 string back to raw bytes
            return {"task": "image_embedding", "image_bytes": base64.b64decode(image_b64)}
        
        elif batch_b64 and isinstance(batch_b64, list):
            # Decode all base64 strings in the batch
            decoded_batch = [base64.b64decode(b) for b in batch_b64]
            return {"task": "batch_image_embedding", "batch_image_bytes": decoded_batch}

        else:
            raise ValueError(
                "Invalid request format. Provide 'image_base64' (string) or 'batch_image_base64' (list of strings)."
            )

    def predict(self, inputs):
        task = inputs["task"]

        if task == "image_embedding":
            embedding = self.get_image_embedding(inputs["image_bytes"])
            return {"type": "image_embedding", "embedding": embedding.tolist()}

        elif task == "batch_image_embedding":
            results = self.get_batch_image_embeddings(inputs["batch_image_bytes"])
            return {"type": "batch_image_embedding", "results": results}

    def encode_response(self, output):
        return output

if __name__ == "__main__":
    api = SigLIP2VisionAPI()
    server = ls.LitServer(api, accelerator="auto", devices=1, track_requests=True)
    server.run(port=8080)