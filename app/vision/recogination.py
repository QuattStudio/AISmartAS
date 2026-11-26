
































from deepface import DeepFace

import numpy as np
import math


FACE_RECOGINATION_MODEL = "Facenet512"
DETECTOR_BACKEND = "opencv"


def cosine_distance(
    emb_a: np.ndarray,
    emb_b: np.ndarray
) -> float:

    dot = float(np.dot(emb_a, emb_b))

    norm_a = math.sqrt(float(np.dot(emb_a, emb_a)))
    norm_b = math.sqrt(float(np.dot(emb_b, emb_b)))

    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0

    return 1.0 - (dot / (norm_a * norm_b))


class FaceDetector:

    def __init__(self, modelName=FACE_RECOGINATION_MODEL):
        self._modelName = modelName

    def represent(self, image, enforceDetection=True):

        return DeepFace.represent(
            img_path=image,
            model_name=self._modelName,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=enforceDetection,
            align=True
        )


class ReferenceEmbedding:

    def __init__(self):
        self._faceDetector = FaceDetector()

    def getEmbeddingOfImage(self, image):

        results = self._faceDetector.represent(
            image,
            enforceDetection=True
        )

        if not results:
            raise ValueError("No face detected")

        return results[0]["embedding"]

    def getLiveEmbedding(self, frame):

        results = self._faceDetector.represent(
            frame,
            enforceDetection=False
        )

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

                faces.append((
                    x, y, w, h,
                    np.asarray(emb, dtype=np.float32)
                ))

        return faces


referenceEmbedding = ReferenceEmbedding()
