












from datetime import datetime
from flask import Flask, request, jsonify

from database.database import DataBaseSystem
from core.logger import logger
from core.paths import project_path

ACTUAL_DB_PATH = project_path("resources", "database", "registration.db")
server = Flask(__name__)


class ServerSystem:

    def __init__(self, db_path=None):
        self._database = DataBaseSystem(path=db_path or ACTUAL_DB_PATH)
        # self._database = DataBaseSystem()
        self._database.init()

        server.add_url_rule(
            "/api/registration",
            view_func=self.registration,
            methods=["POST"]
        )

        server.add_url_rule(
            "/api/students/embeddings",
            view_func=self.get_embeddings,
            methods=["GET"]
        )

        server.add_url_rule(
            "/api/attendance",
            view_func=self.attendance,
            methods=["POST"]
        )

        server.add_url_rule(
            "/api/attendance/today",
            view_func=self.today_attendance,
            methods=["GET"]
        )

        logger.info("Server initialized successfully")

    def registration(self):

        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "message": "Invalid JSON"
            }), 400

        person_type = data.get("person_type", "student")
        if person_type == "teacher":
            success, message = self._database.add_teacher(data)
        elif person_type == "student":
            success, message = self._database.add_student(data)
        else:
            return jsonify({
                "success": False,
                "message": "Person type must be student or teacher"
            }), 400

        if not success:
            status = 409 if message in {
                "Roll number already exists", "Teacher ID already exists"
            } else (500 if message == "Database error" else 400)

            return jsonify({
                "success": False,
                "message": message
            }), status

        return jsonify({
            "success": True,
            "message": message,
            "person_type": person_type,
            "person_id": data.get("teacher_id") if person_type == "teacher" else data["roll_number"]
        }), 201

    def get_embeddings(self):

        students = self._database.get_embeddings()

        if students is None:
            return jsonify({
                "success": False,
                "message": "Could not retrieve embeddings"
            }), 500

        return jsonify({
            "success": True,
            "count": len(students),
            "students": students
        }), 200

    def today_attendance(self):
        records = self._database.get_today_attendance()
        if records is None:
            return jsonify({
                "success": False,
                "message": "Could not retrieve today's attendance"
            }), 500
        return jsonify({
            "success": True,
            "date": datetime.now().astimezone().date().isoformat(),
            "students": records
        }), 200

    def attendance(self):

        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "message": "Invalid JSON"
            }), 400

        person_type = data.get("person_type", "student")
        person_id = data.get("person_id", data.get("roll_number"))

        success, message = self._database.mark_attendance(
            person_id,
            person_type,
        )

        if not success:
            status = 404 if message in {"Student not found", "Teacher not found"} else (
                500 if message == "Database error" else 400
            )

            return jsonify({
                "success": False,
                "message": message
            }), status

        return jsonify({
            "success": True,
            "message": message,
            "person_type": person_type,
            "person_id": person_id
        }), 200


if __name__ == "__main__":

    server_system = ServerSystem()

    server.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        threaded=True
    )



    



