
import json
import math
import threading
import time

import cv2
import numpy as np
from deepface import DeepFace

from core.logger import logger


def get_reference_embedding(image_path: str, detector_backend: str = "opencv") -> list[float]:
    results = DeepFace.represent(
        img_path=image_path,
        model_name="Facenet512",
        detector_backend=detector_backend,
        enforce_detection=True,
        align=True,
    )
    return results[0]["embedding"]


def load_reference_embeddings(path: str = "resources/data/mock.json") -> dict[str, np.ndarray]:
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Support either {"Alice": [512 floats], ...} or a single [512 floats] list
    if isinstance(data, dict):
        return {
            name: np.asarray(vec, dtype=np.float32)
            for name, vec in data.items()
            if isinstance(vec, list) and len(vec) > 0
        }
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], (int, float)):
        return {"Known": np.asarray(data, dtype=np.float32)}

    return {}


def get_live_embedding(frame: np.ndarray, detector_backend: str = "opencv"):
    results = DeepFace.represent(
        img_path=frame,
        model_name="Facenet512",
        detector_backend=detector_backend,
        enforce_detection=False,
        align=True,
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
            faces.append((x, y, w, h, np.asarray(emb, dtype=np.float32)))
    return faces


def cosine_distance(emb_a: np.ndarray, emb_b: np.ndarray) -> float:
    dot = float(np.dot(emb_a, emb_b))
    norm_a = math.sqrt(float(np.dot(emb_a, emb_a)))
    norm_b = math.sqrt(float(np.dot(emb_b, emb_b)))
    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0
    return 1.0 - (dot / (norm_a * norm_b))


class Camera:
    def __init__(
        self,
        index: int = 0,
        detectorBackend: str = "opencv",
        aiScale: float = 0.5,
        threshold: float = 0.30,
        dbPath: str = "resources/data/mock.json",
    ):
        self._index = index
        self._detectorBackend = detectorBackend
        self._aiScale = aiScale
        self._threshold = threshold
        self._dbPath = dbPath
        self._camera = None

        self._running = False

        self._frame = None
        self._faces = []
        self._aiBusy = False

        self._lock = threading.Lock()
        self._captureThread = None
        self._aiThread = None

    def open(self) -> bool:
        if self._camera is not None:
            return True

        cam = cv2.VideoCapture(self._index)
        if not cam.isOpened():
            logger.error("Failed to open camera")
            cam.release()
            return False

        cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._camera = cam
        self._running = True

        self._captureThread = threading.Thread(
            target=self._capture_loop,
            name="CameraCaptureThread",
            daemon=True,
        )
        self._aiThread = threading.Thread(
            target=self._ai_loop,
            name="DeepFaceThread",
            daemon=True,
        )

        self._captureThread.start()
        self._aiThread.start()

        logger.info("Camera opened successfully")
        return True

    def _capture_loop(self):
        while self._running:
            if self._camera is None:
                break

            ret, frame = self._camera.read()
            if not ret or frame is None:
                time.sleep(0.005)
                continue

            with self._lock:
                self._frame = frame

    def _match_face(self, live_emb: np.ndarray, known_db: dict[str, np.ndarray]) -> tuple[str, float]:
        best_name = "Unknown"
        best_dist = 1.0

        for name, ref_emb in known_db.items():
            dist = cosine_distance(live_emb, ref_emb)
            if dist < best_dist:
                best_dist = dist
                if dist < self._threshold:
                    best_name = name

        return best_name, best_dist

    def _ai_loop(self):
        inv_scale = 1.0 / self._aiScale

        try:
            known_db = load_reference_embeddings(self._dbPath)
        except Exception as e:
            logger.error(f"Failed to load reference embeddings: {e}")
            known_db = {}

        while self._running:
            with self._lock:
                frame = None if self._frame is None else self._frame.copy()

            if frame is None:
                time.sleep(0.01)
                continue

            if self._aiScale != 1.0:
                smallFrame = cv2.resize(
                    frame,
                    (0, 0),
                    fx=self._aiScale,
                    fy=self._aiScale,
                    interpolation=cv2.INTER_LINEAR,
                )
            else:
                smallFrame = frame

            with self._lock:
                self._aiBusy = True

            try:
                live_faces = get_live_embedding(
                    smallFrame,
                    detector_backend=self._detectorBackend,
                )

                matched_faces = []
                for x, y, w, h, emb in live_faces:  
                    sx = int(x * inv_scale)
                    sy = int(y * inv_scale)
                    sw = int(w * inv_scale)
                    sh = int(h * inv_scale)

                    label, dist = self._match_face(emb, known_db)
                    matched_faces.append((sx, sy, sw, sh, label, dist))

                with self._lock:
                    self._faces = matched_faces

            except Exception as e:
                logger.error(f"Face recognition failed: {e}")
                time.sleep(0.05)

            finally:
                with self._lock:
                    self._aiBusy = False

            time.sleep(0.005)

    def show(self):
        try:
            while self._running:
                with self._lock:
                    frame = None if self._frame is None else self._frame.copy()
                    faces = list(self._faces)
                    ai_busy = self._aiBusy

                if frame is None:
                    time.sleep(0.01)
                    continue

                for x, y, w, h, label, dist in faces:
                    color = (0, 255, 0) if label != "Unknown" else (0, 165, 255)
                    cv2.rectangle(
                        frame,
                        (x, y),
                        (x + w, y + h),
                        color,
                        2,
                    )
                    cv2.putText(
                        frame,
                        f"{label} ({dist:.2f})",
                        (x, max(y - 8, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        color,
                        2,
                    )

                status_text = "AI: Scanning..." if ai_busy else "AI: Ready"
                cv2.putText(
                    frame,
                    status_text,
                    (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255) if ai_busy else (0, 255, 0),
                    2,
                )

                cv2.imshow("Webcam Feed", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            self.close()

    def close(self):
        if not self._running and self._camera is None:
            return True

        self._running = False

        if self._captureThread is not None and self._captureThread.is_alive():
            self._captureThread.join(timeout=1.0)

        if self._aiThread is not None and self._aiThread.is_alive():
            self._aiThread.join(timeout=2.0)

        if self._camera is not None:
            self._camera.release()
            self._camera = None

        cv2.destroyAllWindows()
        logger.info("Camera closed successfully")
        return True


# camera variable is used for main.py
camera = Camera(detectorBackend="opencv", aiScale=0.5)

