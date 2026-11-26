import time
import threading
import uuid

from flask import Flask, Response, jsonify, render_template, request

from database.database import DataBaseSystem
from vision.camera import camera


app = Flask(__name__)
database = DataBaseSystem()
pending_scans = {}
pending_scans_lock = threading.Lock()


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/video_feed")
def video_feed():
    def frames():
        while True:
            frame = camera.get_stream_frame()
            if frame is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            time.sleep(0.05)

    return Response(
        frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/attendance/today")
def today_attendance():
    records = database.get_today_attendance()
    if records is None:
        return jsonify({"success": False, "message": "Could not load attendance"}), 500
    return jsonify({"success": True, "students": records})


@app.post("/api/attendance/mark")
def mark_attendance():
    data = request.get_json(silent=True)
    person_id = data.get("person_id") if isinstance(data, dict) else None
    person_type = data.get("person_type", "student") if isinstance(data, dict) else "student"
    success, message = database.mark_attendance(person_id, person_type)
    if not success:
        status = 404 if message in {"Student not found", "Teacher not found"} else 400
        return jsonify({"success": False, "message": message}), status
    return jsonify({"success": True, "message": message})


@app.post("/api/scan")
def scan_person():
    success, result = camera.scan_face()
    if not success:
        return jsonify({"success": False, "message": result}), 400

    now = time.monotonic()
    token = uuid.uuid4().hex
    with pending_scans_lock:
        expired = [key for key, (created, _) in pending_scans.items() if now - created > 600]
        for key in expired:
            pending_scans.pop(key, None)
        pending_scans[token] = (now, result)
    return jsonify({"success": True, "scan_id": token, "message": "Face scanned. Enter the details to finish."})


@app.post("/api/enroll")
def enroll_person():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "message": "Invalid form data"}), 400

    scan_id = data.pop("scan_id", None)
    with pending_scans_lock:
        scan = pending_scans.get(scan_id)
        if scan is not None and time.monotonic() - scan[0] > 600:
            pending_scans.pop(scan_id, None)
            scan = None
    if scan is None:
        return jsonify({"success": False, "message": "Please scan the face again before saving."}), 400

    success, message = camera.enroll_person(data, scan[1])
    if success:
        with pending_scans_lock:
            pending_scans.pop(scan_id, None)
    return jsonify({"success": success, "message": message}), (201 if success else 400)
