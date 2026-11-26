import sqlite3
from flask import Flask, request, jsonify
from core.logger import logger


# def init_db():
#     conn = sqlite3.connect("school_data.db")
#     with conn:
#         conn.executescript("""
#             CREATE TABLE IF NOT EXISTS students (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 name TEXT,
#                 father_name TEXT,
#                 mother_name TEXT,
#                 dob TEXT,
#                 roll_number TEXT UNIQUE,
#                 class TEXT,
#                 section TEXT,
#                 stream TEXT,
#                 domain_sub_1 TEXT,
#                 domain_sub_2 TEXT,
#                 domain_sub_3 TEXT,
#                 optional_sub TEXT,
#                 language_lit TEXT
#             );
#         """)
#     conn.close()
fields = [
    "name",
    "father_name",
    "mother_name",
    "date_of_birth",
    "roll_number",
    "class",
    "section",
    "stream",
    "domain_sub_1",
    "domain_sub_2",
    "domain_sub_3",
    "optional_sub",
    "language_lit",
]




def main():
    # init_db()
    # print("--- School Registration System ---\n1. Student\n2. Teacher")
    # role = input("Choose role (1/2): ").strip()

    print("\n=== STUDENT REGISTRATION ===")
    print("\n--- Student Information ---")
    name = input("Name: ").strip().upper()
    father = input("Father's Name: ").strip().upper()
    mother = input("Mother's Name: ").strip().upper()
    dob = input("Date of Birth: ").strip()
    roll = input("Roll Number: ").strip()
    cls = input("Class: ").strip()
    sec = input("Section: ").strip()
    stream = validate_stream()

    print("\n--- Subject Information ---")
    optional = input("Optional Subject: ").strip()
    print("-" * 30)
    lang = input("Language and Literature: ").strip()

    fields = [
        "name",
        "father_name",
        "mother_name",
        "date_of_birth",
        "roll_number",
        "class",
        "section",
        "stream", # PCM, PCB, Commerce, Humanities
        "optional_sub",
        "language_lit",
    ]
    values = [
        name,
        father,
        mother,
        dob,
        roll,
        cls,
        sec,
        stream,
        optional,
        lang,
    ]

    # save_data("students", fields, values)

if __name__ == "__main__":
    main()



class DataBaseSystem:
    def __init__(self):
        pass

    def connect(self):
        return sqlite3.connect("resources/database/registration.db")
    
    def init(self):
        conn = self.connect()

        with conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    father_name TEXT,
                    mother_name TEXT,
                    dob TEXT,
                    roll_number TEXT UNIQUE,
                    class TEXT,
                    section TEXT,
                    stream TEXT,
                    optional_sub TEXT,
                    language_lit TEXT
                );
            """)

        conn.close()

    def save_data(self, table, fields, values):
        conn = self.connect()
        sql = f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({', '.join(['?'] * len(values))})"
        with conn:
            try:
                conn.execute(sql, values)
                logger.info("Success: Registration complete!")
            except sqlite3.IntegrityError:
                logger.error("\nError: ID or Roll Number already exists.")
        conn.close()

    def add(self, data):
        self.save_data("students", fields, data)


    def validate_stream():
        valid_streams = ["PCM", "PCB", "COMMERCE", "HUMANITIES"]
        while True:
            stream = input("Stream (PCM/PCB/Commerce/Humanities): ").strip().upper()
            if stream in valid_streams:
                return stream
            logger.warning("Invalid stream. Please enter PCM, PCB, Commerce, Humanities.")



    @route("/api/attendance", methods=["POST"])
    def receive_attendance(self):
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "message": "Invalid JSON"
            }, 400)
