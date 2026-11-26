



import sqlite3
import json

from pathlib import Path
from datetime import datetime

from core.logger import logger
from core.paths import project_path


DATABASE_PATH = project_path("resources", "database", "registration.db")


STUDENT_FIELDS = [
    "name",
    "father_name",
    "mother_name",
    "date_of_birth",
    "roll_number",
    "class",
    "section",
    "stream",
    "optional_sub",
    "language_lit",
]


class DataBaseSystem:
    def __init__(self, path=DATABASE_PATH):
        resolved_path = Path(path)
        self._path = resolved_path if resolved_path.is_absolute() else project_path(*resolved_path.parts)

    def connect(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self._path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        return conn

    def init(self):
        with self.connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    name TEXT NOT NULL,
                    father_name TEXT NOT NULL,
                    mother_name TEXT NOT NULL,
                    date_of_birth TEXT NOT NULL,

                    roll_number TEXT UNIQUE NOT NULL,

                    class TEXT NOT NULL,
                    section TEXT NOT NULL,
                    stream TEXT NOT NULL,

                    optional_sub TEXT DEFAULT '',
                    language_lit TEXT DEFAULT '',

                    embedding TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    student_id INTEGER NOT NULL,

                    attendance_date TEXT NOT NULL,
                    timestamp TEXT NOT NULL,

                    FOREIGN KEY(student_id)
                        REFERENCES students(id),

                    UNIQUE(student_id, attendance_date)
                );

                CREATE TABLE IF NOT EXISTS teachers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    subject TEXT DEFAULT '',
                    embedding TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS teacher_attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id INTEGER NOT NULL,
                    attendance_date TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(teacher_id) REFERENCES teachers(id),
                    UNIQUE(teacher_id, attendance_date)
                );

                CREATE INDEX IF NOT EXISTS
                    idx_attendance_date
                    ON attendance(attendance_date);
            """)

            # Upgrade databases created by the earlier registration prototype.
            # That schema used `dob` and did not store face embeddings.
            student_columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(students)")
            }

            if "date_of_birth" not in student_columns and "dob" in student_columns:
                conn.execute(
                    "ALTER TABLE students RENAME COLUMN dob TO date_of_birth"
                )
                student_columns.remove("dob")
                student_columns.add("date_of_birth")

            if "embedding" not in student_columns:
                conn.execute(
                    "ALTER TABLE students ADD COLUMN embedding TEXT"
                )

        logger.info("Database initialized successfully")

    # --------------------------------------------------
    # STUDENT REGISTRATION
    # --------------------------------------------------

    def add_student(self, data: dict) -> tuple[bool, str]:

        if not isinstance(data, dict):
            return False, "Invalid student data"

        for field in STUDENT_FIELDS[:8]:
            value = data.get(field)

            if not isinstance(value, str) or not value.strip():
                return False, f"Invalid or missing field: {field}"

        embedding = data.get("embedding")

        if not isinstance(embedding, list) or len(embedding) != 512:
            return False, "Invalid FaceNet512 embedding"

        try:
            embedding = [
                float(value) for value in embedding
            ]
        except (ValueError, TypeError):
            return False, "Embedding contains invalid values"

        if not all(
            __import__("math").isfinite(value)
            for value in embedding
        ):
            return False, "Embedding contains non-finite values"

        values = {}
        for field in STUDENT_FIELDS:
            value = data.get(field, "")
            if not isinstance(value, str):
                return False, f"Invalid field: {field}"
            values[field] = value.strip()

        values["stream"] = values["stream"].upper()

        valid_streams = {
            "PCM", "PCB", "COMMERCE", "HUMANITIES"
        }

        if values["stream"] not in valid_streams:
            return False, "Invalid stream"

        try:
            with self.connect() as conn:
                conn.execute("""
                    INSERT INTO students (
                        name,
                        father_name,
                        mother_name,
                        date_of_birth,
                        roll_number,
                        class,
                        section,
                        stream,
                        optional_sub,
                        language_lit,
                        embedding
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    values["name"],
                    values["father_name"],
                    values["mother_name"],
                    values["date_of_birth"],
                    values["roll_number"],
                    values["class"],
                    values["section"],
                    values["stream"],
                    values["optional_sub"],
                    values["language_lit"],
                    json.dumps(embedding),
                ))

            logger.info(
                f"Student registered: {values['roll_number']}"
            )

            return True, "Student registered successfully"

        except sqlite3.IntegrityError:
            return False, "Roll number already exists"

        except sqlite3.Error as error:
            logger.error(f"Student registration error: {error}")
            return False, "Database error"

    def add_teacher(self, data: dict) -> tuple[bool, str]:
        teacher_id = data.get("teacher_id")
        name = data.get("name")
        subject = data.get("subject", "")
        embedding = data.get("embedding")

        if not isinstance(teacher_id, str) or not teacher_id.strip():
            return False, "Invalid or missing field: teacher_id"
        if not isinstance(name, str) or not name.strip():
            return False, "Invalid or missing field: name"
        if not isinstance(subject, str):
            return False, "Invalid subject"
        if not isinstance(embedding, list) or len(embedding) != 512:
            return False, "Invalid FaceNet512 embedding"

        try:
            embedding = [float(value) for value in embedding]
            if not all(__import__("math").isfinite(value) for value in embedding):
                return False, "Embedding contains non-finite values"

            with self.connect() as conn:
                conn.execute("""
                    INSERT INTO teachers (teacher_id, name, subject, embedding)
                    VALUES (?, ?, ?, ?)
                """, (
                    teacher_id.strip(), name.strip(), subject.strip(),
                    json.dumps(embedding)
                ))
            return True, "Teacher registered successfully"
        except (TypeError, ValueError):
            return False, "Embedding contains invalid values"
        except sqlite3.IntegrityError:
            return False, "Teacher ID already exists"
        except sqlite3.Error as error:
            logger.error(f"Teacher registration error: {error}")
            return False, "Database error"

    # --------------------------------------------------
    # GET STUDENT EMBEDDINGS
    # --------------------------------------------------

    def get_embeddings(self):

        try:
            with self.connect() as conn:
                rows = conn.execute("""
                    SELECT roll_number, name, embedding
                    FROM students
                """).fetchall()

            people = []

            for row in rows:
                if not row["embedding"]:
                    continue

                people.append({
                    "roll_number": row["roll_number"],
                    "person_id": row["roll_number"],
                    "name": row["name"],
                    "person_type": "student",
                    "embedding": json.loads(row["embedding"])
                })

            with self.connect() as conn:
                teacher_rows = conn.execute("""
                    SELECT teacher_id, name, embedding FROM teachers
                """).fetchall()

            for row in teacher_rows:
                if row["embedding"]:
                    people.append({
                        "roll_number": row["teacher_id"],
                        "person_id": row["teacher_id"],
                        "name": row["name"],
                        "person_type": "teacher",
                        "embedding": json.loads(row["embedding"])
                    })

            return people

        except (sqlite3.Error, ValueError, TypeError) as error:
            logger.error(f"Embedding retrieval error: {error}")
            return None

    # --------------------------------------------------
    # ATTENDANCE
    # --------------------------------------------------

    def mark_attendance(self, person_id: str, person_type: str = "student"):

        if person_type not in {"student", "teacher"}:
            return False, "Invalid person type"
        if not isinstance(person_id, str) or not person_id.strip():
            return False, "Invalid person ID"

        now = datetime.now().astimezone()

        attendance_date = now.date().isoformat()
        timestamp = now.isoformat()

        try:
            with self.connect() as conn:

                if person_type == "student":
                    person = conn.execute("""
                        SELECT id FROM students WHERE roll_number = ?
                    """, (person_id.strip(),)).fetchone()
                    table, column = "attendance", "student_id"
                    log_label = "Student"
                else:
                    person = conn.execute("""
                        SELECT id FROM teachers WHERE teacher_id = ?
                    """, (person_id.strip(),)).fetchone()
                    table, column = "teacher_attendance", "teacher_id"
                    log_label = "Teacher"

                if person is None:
                    return False, f"{log_label} not found"

                # Table and column names are selected only from the fixed
                # student/teacher branches above; request values stay bound.
                cursor = conn.execute(
                    f"INSERT OR IGNORE INTO {table} ({column}, attendance_date, timestamp) "
                    "VALUES (?, ?, ?)",
                    (person["id"], attendance_date, timestamp),
                )

                if cursor.rowcount == 0:
                    return True, "Attendance already recorded"

            logger.info(f"{log_label} attendance marked: {person_id}")

            return True, "Attendance recorded successfully"

        except sqlite3.Error as error:
            logger.error(f"Attendance error: {error}")
            return False, "Database error"

    def get_today_attendance(self):
        today = datetime.now().astimezone().date().isoformat()
        try:
            with self.connect() as conn:
                student_rows = conn.execute("""
                    SELECT s.roll_number, s.name, a.timestamp
                    FROM students AS s
                    LEFT JOIN attendance AS a
                      ON a.student_id = s.id AND a.attendance_date = ?
                    ORDER BY s.name COLLATE NOCASE
                """, (today,)).fetchall()
                teacher_rows = conn.execute("""
                    SELECT t.teacher_id AS person_id, t.name, a.timestamp
                    FROM teachers AS t
                    LEFT JOIN teacher_attendance AS a
                      ON a.teacher_id = t.id AND a.attendance_date = ?
                    ORDER BY t.name COLLATE NOCASE
                """, (today,)).fetchall()
            records = [{
                "person_type": "student",
                "person_id": row["roll_number"],
                "roll_number": row["roll_number"],
                "name": row["name"],
                "present": row["timestamp"] is not None,
                "timestamp": row["timestamp"],
            } for row in student_rows]
            records.extend({
                "person_type": "teacher",
                "person_id": row["person_id"],
                "roll_number": row["person_id"],
                "name": row["name"],
                "present": row["timestamp"] is not None,
                "timestamp": row["timestamp"],
            } for row in teacher_rows)
            return records
        except sqlite3.Error as error:
            logger.error(f"Attendance list error: {error}")
            return None
