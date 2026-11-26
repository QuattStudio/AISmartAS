
import threading
import time
from datetime import datetime

import cv2
import numpy as np

from core.logger import logger
from vision.recogination import referenceEmbedding, cosine_distance
from vision.network import Network



class Camera:
    def __init__(
        self,
        index: int = 0,
        aiScale: float = 0.5,
        threshold: float = 0.30,
        dbPath: str = "resources/database/mock.json",
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
        self._recognition_lock = threading.Lock()
        self._captureThread = None
        self._aiThread = None

        self._network = Network()

        self._attendance_recorded = set()
        self._attendance_pending = set()
        self._attendance_last_attempt = {}

        self._attendance_lock = threading.Lock()

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

    def _match_face(
        self,
        live_emb: np.ndarray,
        known_db: dict
    ) -> tuple[str, float, tuple[str, str] | None]:

        if not known_db:
            return "Unknown", 1.0, None

        best_name = "Unknown"
        best_attendance = None
        best_dist = float("inf")

        for roll_number, student in known_db.items():

            dist = cosine_distance(
                live_emb,
                student["embedding"]
            )

            if dist < best_dist:
                best_dist = dist
                if student.get("person_type") == "teacher":
                    best_name = f"{student['name']} (Teacher)"
                else:
                    best_name = student["name"]
                best_attendance = (
                    student.get("person_type", "student"),
                    student.get("attendance_id", roll_number),
                )

        if best_dist < self._threshold:
            return best_name, best_dist, best_attendance

        return "Unknown", best_dist, None


    def _ai_loop(self):

        inv_scale = 1.0 / self._aiScale

        known_db = {}
        loaded = False

        while self._running:

            with self._lock:
                reload_requested = self._reload_db
                self._reload_db = False

                enrolling = self._enrolling

                frame = (
                    None if self._frame is None
                    else self._frame.copy()
                )

            # Download embeddings at startup or after registration
            if reload_requested or not loaded:

                students = self._network.get_embeddings()

                if students is not None:

                    new_db = {}

                    for student in students:

                        try:
                            roll = student["roll_number"]
                            person_type = student.get("person_type", "student")
                            name = student["name"]

                            emb = np.asarray(
                                student["embedding"],
                                dtype=np.float32
                            )

                            if emb.shape != (512,):
                                logger.warning(
                                    f"Invalid embedding for {roll}"
                                )
                                continue

                            new_db[f"{person_type}:{student.get('person_id', roll)}"] = {
                                "name": name,
                                "embedding": emb,
                                "person_type": person_type,
                                "attendance_id": roll,
                            }

                        except (KeyError, TypeError, ValueError) as error:
                            logger.warning(
                                f"Invalid student embedding: {error}"
                            )

                    known_db = new_db
                    loaded = True

                    logger.info(
                        f"Downloaded {len(known_db)} student embeddings"
                    )

                else:
                    logger.warning(
                        "Could not download embeddings. Retrying..."
                    )

                    time.sleep(2)
                    continue

            if enrolling or frame is None:
                time.sleep(0.02)
                continue

            if self._aiScale != 1.0:

                smallFrame = cv2.resize(
                    frame,
                    (0, 0),
                    fx=self._aiScale,
                    fy=self._aiScale,
                    interpolation=cv2.INTER_LINEAR
                )

            else:
                smallFrame = frame

            with self._lock:
                self._aiBusy = True

            try:

                with self._recognition_lock:
                    live_faces = referenceEmbedding.getLiveEmbedding(
                        smallFrame
                    )

                matched_faces = []

                for x, y, w, h, emb in live_faces:

                    sx = int(x * inv_scale)
                    sy = int(y * inv_scale)
                    sw = int(w * inv_scale)
                    sh = int(h * inv_scale)

                    label, dist, attendance_target = self._match_face(
                        emb,
                        known_db
                    )

                    matched_faces.append((
                        sx, sy, sw, sh,
                        label, dist, attendance_target
                    ))

                    # Submit attendance asynchronously
                    if attendance_target is not None:
                        person_type, person_id = attendance_target
                        self._schedule_attendance(person_type, person_id)

                with self._lock:

                    if not self._enrolling:
                        self._faces = matched_faces

            except Exception as error:

                logger.error(
                    f"Face recognition failed: {error}"
                )

                time.sleep(0.05)

            finally:

                with self._lock:
                    self._aiBusy = False

            time.sleep(0.01)

    def scan_face(self):
        """Capture one face embedding from the current camera frame."""
        with self._lock:
            if not self._running or self._frame is None:
                return False, "Camera is not ready yet"
            if self._enrolling:
                return False, "Another registration is in progress"
            self._enrolling = True
            snapshot = self._frame.copy()

        try:
            with self._recognition_lock:
                embedding = [
                    float(value)
                    for value in referenceEmbedding.getEmbeddingOfImage(snapshot)
                ]
            return True, embedding
        except Exception as error:
            logger.error(f"Face scan failed: {error}")
            return False, str(error)
        finally:
            with self._lock:
                self._enrolling = False

    def enroll_person(self, data, embedding):
        """Save person details together with an embedding from a prior scan."""
        if not isinstance(data, dict):
            return False, "Invalid registration details"
        if data.get("person_type") not in {"student", "teacher"}:
            return False, "Choose student or teacher"
        if not isinstance(embedding, list) or len(embedding) != 512:
            return False, "Scan the face before saving"

        person = dict(data)
        person["embedding"] = embedding
        status, response = self._network.register_person(person)
        if status == 201 and response and response.get("success"):
            with self._lock:
                self._reload_db = True
            return True, response.get("message", "Person registered")

        message = response.get("message") if response else None
        return False, message or "Registration request failed"


    def _schedule_attendance(self, person_type, person_id):

        now = time.monotonic()
        attendance_key = (
            person_type,
            person_id,
            datetime.now().astimezone().date().isoformat(),
        )

        with self._attendance_lock:

            if attendance_key in self._attendance_recorded:
                return

            if attendance_key in self._attendance_pending:
                return

            last_attempt = self._attendance_last_attempt.get(
                attendance_key, 0
            )

            # Retry failed requests after 30 seconds
            if now - last_attempt < 30:
                return

            self._attendance_pending.add(attendance_key)
            self._attendance_last_attempt[attendance_key] = now

        threading.Thread(
            target=self._send_attendance,
            args=(person_type, person_id, attendance_key),
            daemon=True
        ).start()


    def _send_attendance(self, person_type, person_id, attendance_key):

        try:

            status, response = self._network.send_attendance(person_type, person_id)

            if (
                status == 200
                and response is not None
                and response.get("success")
            ):

                with self._attendance_lock:
                    self._attendance_recorded.add(attendance_key)

                logger.info(
                    f"{person_type.title()} attendance submitted: {person_id} - "
                    f"{response.get('message')}"
                )

            else:

                logger.warning(
                    f"Attendance submission failed: "
                    f"{person_type} {person_id}, {response}"
                )

        finally:

            with self._attendance_lock:
                self._attendance_pending.discard(attendance_key)

    def get_stream_frame(self):
        with self._lock:
            frame = None if self._frame is None else self._frame.copy()
            faces = list(self._faces)
            ai_busy = self._aiBusy

        if frame is None:
            return None

        for x, y, w, h, label, distance, _ in faces:
            color = (0, 255, 0) if label != "Unknown" else (0, 165, 255)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(
                frame,
                f"{label} ({distance:.2f})",
                (x, max(y - 8, 15)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
            )

        status = "AI: Scanning..." if ai_busy else "AI: Ready"
        cv2.putText(
            frame, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
            0.6, (0, 255, 0), 2
        )

        encoded, buffer = cv2.imencode(".jpg", frame)
        return buffer.tobytes() if encoded else None



    def _enroll_current_face(self, snapshot, faces_snapshot):

        with self._lock:
            self._enrolling = True

        try:

            target_face = None

            unknown_faces = [
                f for f in faces_snapshot
                if f[4] == "Unknown"
            ]

            if unknown_faces:
                target_face = max(
                    unknown_faces,
                    key=lambda f: f[2] * f[3]
                )

            elif faces_snapshot:
                target_face = max(
                    faces_snapshot,
                    key=lambda f: f[2] * f[3]
                )

            if target_face is None:
                print("[Enroll] No face detected.")
                return

            x, y, w, h = target_face[:4]
            label = target_face[4]

            if label != "Unknown":

                print(
                    f"[Enroll] This face already matches '{label}'."
                )

                answer = input(
                    "Continue registration anyway? (y/N): "
                ).strip().lower()

                if answer != "y":
                    return

            # Crop face from original resolution
            pad_x = int(w * 0.15)
            pad_y = int(h * 0.15)

            fh, fw = snapshot.shape[:2]

            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(fw, x + w + pad_x)
            y2 = min(fh, y + h + pad_y)

            crop = snapshot[y1:y2, x1:x2]

            print("\n--- Student Registration ---")

            data = {
                "name": input("Student name: ").strip(),
                "father_name": input("Father name: ").strip(),
                "mother_name": input("Mother name: ").strip(),
                "date_of_birth": input("Date of birth (YYYY-MM-DD): ").strip(),
                "roll_number": input("Roll number: ").strip(),
                "class": input("Class: ").strip(),
                "section": input("Section: ").strip(),
                "stream": input("Stream: ").strip().upper(),
                "optional_sub": input("Optional subject: ").strip(),
                "language_lit": input("Language and literature: ").strip()
            }

            # Generate face embedding
            embedding = referenceEmbedding.getEmbeddingOfImage(
                crop
            )

            data["embedding"] = [
                float(value) for value in embedding
            ]

            # Send complete registration to server
            status, response = self._network.register_student(data)

            if (
                status == 201
                and response is not None
                and response.get("success")
            ):

                print(
                    f"[Enroll] Registered successfully: "
                    f"{data['roll_number']}"
                )

                logger.info(
                    f"Student registered: {data['roll_number']}"
                )

                # Ask AI thread to download the new embeddings
                with self._lock:
                    self._reload_db = True

            else:

                print(
                    f"[Enroll] Registration failed: {response}"
                )

        except Exception as error:

            logger.error(f"Enrollment failed: {error}")
            print(f"[Enroll] Error: {error}")

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
                
                for x, y, w, h, label, dist, roll in faces:
                # for x, y, w, h, label, dist in faces:
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

