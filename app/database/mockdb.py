from flask import Flask, request, jsonify
import sqlite3




app = Flask(__name__)


class DataBase:
    def __init__(self):
        pass

    def get(self):
        return sqlite3.connect("resources/database/attendance.db")

    @app.route("/api/attendance", methods=["POST"])
    def receive_attendance(self):
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "message": "Invalid JSON"
            }, 400)



