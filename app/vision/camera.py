
import threading
import time

import cv2
import numpy as np

from app.core.logger import logger
from app.vision.recogination import referenceEmbedding, cosine_distance
from app.vision.network import Network



class Camera:
    def __init__(
        self,
        index: int = 0,
        aiScale: float = 0.5,
        threshold: float = 0.30,
        dbPath: str = "resources/data/mock.json",
    ):
        if aiScale <= 0:
            raise ValueError("aiScale must be greater than 0")

        self._index = index
        self._aiScale = aiScale
        self._threshold = threshold
        self._dbPath = dbPath
        self._camera = None

        self._running = False
        self._enrolling = False
        self._reload_db = False

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

        with self._lock:
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
            with self._lock:
                cam = self._camera
                enrolling = self._enrolling

            if cam is None:
                break

            if enrolling:
                time.sleep(0.02)
                continue

            ret, frame = cam.read()
            if not ret or frame is None:
                time.sleep(0.005)
                continue

            with self._lock:
                self._frame = frame

    def _match_face(self, live_emb: np.ndarray, known_db: dict[str, np.ndarray]) -> tuple[str, float]:
        if not known_db:
            return "Unknown", 1.0

        best_name = "Unknown"
        best_dist = float("inf")

        for name, ref_emb in known_db.items():
            dist = cosine_distance(live_emb, ref_emb)
            if dist < best_dist:
                best_dist = dist
                best_name = name

        return (best_name, best_dist) if best_dist < self._threshold else ("Unknown", best_dist)

    def _ai_loop(self):
        inv_scale = 1.0 / self._aiScale

        try:
            known_db = referenceEmbedding.load(self._dbPath)

        except Exception as e:
            logger.error(f"Failed to load reference embeddings: {e}")
            known_db = {}

        while self._running:
            with self._lock:
                if self._reload_db:
                    try:
                        known_db = referenceEmbedding.load(self._dbPath)
                        logger.info(f"Reloaded reference DB ({len(known_db)} entries)")

                    except Exception as e:
                        logger.error(f"Failed to reload reference embeddings: {e}")
                    self._reload_db = False

                enrolling = self._enrolling
                frame = None if self._frame is None else self._frame.copy()

            if enrolling or frame is None:
                time.sleep(0.02)
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
                live_faces = referenceEmbedding.getLiveEmbedding(smallFrame)

                matched_faces = []
                for x, y, w, h, emb in live_faces:
                    sx = int(x * inv_scale)
                    sy = int(y * inv_scale)
                    sw = int(w * inv_scale)
                    sh = int(h * inv_scale)

                    label, dist = self._match_face(emb, known_db)
                    matched_faces.append((sx, sy, sw, sh, label, dist))

                with self._lock:
                    if not self._enrolling:
                        self._faces = matched_faces

            except Exception as e:
                logger.error(f"Face recognition failed: {e}")
                time.sleep(0.05)

            finally:
                with self._lock:
                    self._aiBusy = False

            time.sleep(0.01)

    def _enroll_current_face(self, snapshot: np.ndarray, faces_snapshot: list) -> None:
        """Prompt terminal for a name and save embedding if not already recorded."""
        with self._lock:
            self._enrolling = True

        try:
            # Prefer an "Unknown" face if present; otherwise pick the largest detected face
            target_face = None
            unknown_faces = [f for f in faces_snapshot if f[4] == "Unknown"]
            if unknown_faces:
                target_face = max(unknown_faces, key=lambda f: f[2] * f[3])
            elif faces_snapshot:
                target_face = max(faces_snapshot, key=lambda f: f[2] * f[3])

            if target_face is None:
                logger.warning("No face detected on screen to register")
                print("[Enroll] No face detected. Position your face clearly in frame and press 'r'.")
                return

            x, y, w, h, label, dist = target_face
            if label != "Unknown":
                print(f"[Enroll] Face already matches '{label}' (distance={dist:.2f}).")
                ans = input("Save under a new name anyway? (y/N): ").strip().lower()
                if ans != "y":
                    print("[Enroll] Cancelled.")
                    return

            # Crop with slight padding on full-res snapshot for cleaner embedding
            pad_x = int(w * 0.15)
            pad_y = int(h * 0.15)
            fh, fw = snapshot.shape[:2]
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(fw, x + w + pad_x)
            y2 = min(fh, y + h + pad_y)
            crop = snapshot[y1:y2, x1:x2]

            name = input("Enter name for this face: ").strip()
            if not name:
                print("[Enroll] Empty name — skipped.")
                return

            # Extract full-resolution embedding from crop (fallback to full frame if needed)
            faces = referenceEmbedding.getLiveEmbedding(crop)

            if not faces:
                faces = referenceEmbedding.getLiveEmbedding(snapshot)

            if not faces:
                print("[Enroll] Could not extract face embedding. Try better lighting.")
                return

            best_emb = max(faces, key=lambda item: item[2] * item[3])[4]
            referenceEmbedding.saveEmbedding(name=name, embedding=best_emb, path=self._dbPath)

            with self._lock:
                self._reload_db = True

            print(f"[Enroll] Saved '{name}' to {self._dbPath}")
            logger.info(f"Registered new face '{name}' into {self._dbPath}")

        except Exception as e:
            logger.error(f"Enrollment failed: {e}")
            print(f"[Enroll] Error: {e}")

        finally:
            with self._lock:
                self._enrolling = False

    def show(self):
        try:
            while self._running:
                with self._lock:
                    frame = None if self._frame is None else self._frame.copy()
                    faces = list(self._faces)
                    ai_busy = self._aiBusy
                    enrolling = self._enrolling

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

                if enrolling:
                    status_text = "AI: Enrolling (check terminal)..."
                    status_color = (255, 200, 0)
                elif ai_busy:
                    status_text = "AI: Scanning..."
                    status_color = (0, 255, 255)
                else:
                    status_text = "AI: Ready | Press 'r' to register"
                    status_color = (0, 255, 0)

                cv2.putText(
                    frame,
                    status_text,
                    (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    status_color,
                    2,
                )

                cv2.imshow("Webcam Feed", frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                if key == ord("r") and not enrolling:
                    self._enroll_current_face(frame, faces)
        finally:
            self.close()

    def close(self):
        with self._lock:
            if not self._running and self._camera is None:
                return True
            self._running = False

        if self._captureThread is not None and self._captureThread.is_alive():
            self._captureThread.join(timeout=1.0)

        if self._aiThread is not None and self._aiThread.is_alive():
            self._aiThread.join(timeout=2.0)

        with self._lock:
            if self._camera is not None:
                self._camera.release()
                self._camera = None

        cv2.destroyAllWindows()
        logger.info("Camera closed successfully")
        return True


# camera variable is used for main.py
camera = Camera(aiScale=0.5)

