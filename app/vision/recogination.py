from deepface import DeepFace
from core.logger import logger

import os
import json
import numpy as np
import math



FACE_RECOGINATION_MODEL = "Facenet512"
DETECTOR_BACKEND        = "opencv"


def cosine_distance(emb_a: np.ndarray, emb_b: np.ndarray) -> float:
    dot = float(np.dot(emb_a, emb_b))
    norm_a = math.sqrt(float(np.dot(emb_a, emb_a)))
    norm_b = math.sqrt(float(np.dot(emb_b, emb_b)))
    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0
    return 1.0 - (dot / (norm_a * norm_b))





class FaceDetector:
    def __init__(self, modelName: str = FACE_RECOGINATION_MODEL):
        self._modelName = modelName

    def represent(
            self, 
            imagePath: str, 
            enforceDetection: bool = True
    ):
        return DeepFace.represent(
            img_path=imagePath,
            model_name=self._modelName,
            enforce_detection=enforceDetection,
            align=True
        )




class ReferenceEmbedding:
    def __init__(self, detectorBackend: str = DETECTOR_BACKEND):
        self._detectorBackend = detectorBackend
        self._faceDetector = FaceDetector()


    def getEmbeddingOfImage(self, imagePath: str) -> list[float]:
        
        results = self._faceDetector.represent(imagePath, enforceDetection=True)

        return results[0]["embedding"]


    def load(self, path: str = "resources/database/mock.json") -> dict[str, np.ndarray]:
        if not os.path.exists(path):
            return {}

        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            return {
                name: np.asarray(vec, dtype=np.float32)
                for name, vec in data.items()
                if isinstance(vec, list) and len(vec) > 0
            }
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], (int, float)):
            return {"Known": np.asarray(data, dtype=np.float32)}

        return {}


    def getLiveEmbedding(self, frame: np.ndarray):

        results = self._faceDetector.represent(frame, enforceDetection=False)

        faces = []
        for item in results:
            conf = float(item.get("face_confidence", 0.0))
            area = item.get("facial_area", {})
            emb = item.get("embedding")

            x = int(area.get("x", 0))
            y = int(area.get("y", 0))
            w = int(area.get("w", 0))
            h = int(area.get("h", 0))

            if conf > 0.5 and w > 20 and h > 20 and emb is not None:
                faces.append((x, y, w, h, np.asarray(emb, dtype=np.float32)))
        
        return faces


    def saveEmbedding(
        self,
        name: str,
        embedding: np.ndarray,
        path: str = "resources/database/mock.json",
    ) -> None:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Name cannot be empty")

        parent_dir = os.path.dirname(path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        existing_data: dict[str, list[float]] = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as file:
                loaded = json.load(file)
                if isinstance(loaded, dict):
                    for k, v in loaded.items():
                        if isinstance(v, list) and len(v) > 0:
                            existing_data[str(k)] = [float(x) for x in v]

        existing_data[clean_name] = [float(x) for x in np.asarray(embedding, dtype=np.float32).tolist()]

        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(existing_data, file, indent=2)
        os.replace(tmp_path, path)

        logger.debug(f"Emdebbing saved as: {name}")



# referenceEmbedding is used for working with embedding mainly included on camera.py
referenceEmbedding = ReferenceEmbedding()

