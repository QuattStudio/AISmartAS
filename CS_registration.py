from contextlib import closing
import re
import sqlite3

DB_NAME = "school_data_8.db"


def init_db():
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    father_name TEXT,
                    mother_name TEXT,
                    dob TEXT,
                    roll_number TEXT UNIQUE NOT NULL,
                    class TEXT,
                    section TEXT,
                    stream TEXT,
                    optional_sub_1 TEXT NOT NULL,
                    optional_sub_2 TEXT,
                    language_lit TEXT
                );

                CREATE TABLE IF NOT EXISTS teachers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT NOT NULL,
                    emp_id TEXT UNIQUE NOT NULL,
                    pin TEXT NOT NULL
                );
            """)


def get_required_input(prompt, uppercase=False):
    while True:
        value = input(prompt).strip()
        if value:
            return value.upper() if uppercase else value
        print("This field cannot be empty. Please try again.")


def get_numeric_input(prompt):
    while True:
        value = input(prompt).strip()
        if value.isdigit():
            return value
        print("Invalid input. Only numbers are allowed.")


def get_date_input(prompt):
    while True:
        value = input(prompt).strip()
        cleaned = re.sub(r"[^\d]", "", value)
        if cleaned:
            return cleaned
        print("Invalid date. Please enter numbers.")


def get_phone_input(prompt):
    while True:
        value = get_numeric_input(prompt)
        if len(value) == 10:
            return value
        print("Phone number must be exactly 10 digits.")


def get_email_input(prompt):
    while True:
        value = input(prompt).strip()
        if re.match(r"[^@]+@email\.com$", value):
            return value
        print("Invalid email. Must end with @email.com")


def get_pin_input(prompt):
    while True:
        value = get_numeric_input(prompt)
        if len(value) == 4:
            return value
        print("PIN must be exactly 4 digits.")


def validate_stream():
    valid_streams = ["PCM", "PCB", "COMMERCE", "HUMANITIES"]
    while True:
        stream = input("Stream (PCM/PCB/Commerce/Humanities): ").strip().upper()
        if stream in valid_streams:
            return stream
        print("Invalid stream. Please enter PCM, PCB, Commerce, or Humanities.")


def save_data(table, fields, values):
    sql = f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({', '.join(['?'] * len(values))})"
    with closing(sqlite3.connect(DB_NAME)) as conn:
        try:
            with conn:
                conn.execute(sql, values)
                print("\nSuccess: Registration complete!")
        except sqlite3.IntegrityError:
            if table == "students":
                print("\nError: Roll Number already exists.")
            else:
                print("\nError: Employee ID already exists.")


def register_student():
    print("\n=== STUDENT REGISTRATION ===")
    print("\n--- Student Information ---")
    name = get_required_input("Name: ", uppercase=True)
    father = get_required_input("Father's Name: ", uppercase=True)
    mother = get_required_input("Mother's Name: ", uppercase=True)
    dob = get_date_input("Date of Birth (e.g., DD.MM.YYYY or numbers): ")
    roll = get_numeric_input("Roll Number (Numbers only): ")
    cls = get_numeric_input("Class (Numbers only): ")
    sec = get_required_input("Section: ", uppercase=True)
    stream = validate_stream()

    print("\n--- Subject Information ---")
    optional1 = get_required_input("Optional Subject 1 (Compulsory): ")
    optional2 = input("Optional Subject 2 (leave blank if none): ").strip()
    print("-" * 30)
    lang = get_required_input("Language and Literature: ")

    fields = [
        "name",
        "father_name",
        "mother_name",
        "dob",
        "roll_number",
        "class",
        "section",
        "stream",
        "optional_sub_1",
        "optional_sub_2",
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
        optional1,
        optional2,
        lang,
    ]
    save_data("students", fields, values)


def register_teacher():
    print("\n=== TEACHER REGISTRATION ===")
    name = get_required_input("Name: ", uppercase=True)
    subject = get_required_input("Subject: ")
    phone = get_phone_input("Phone Number: ")
    email = get_email_input("Email ID: ")
    emp_id = get_required_input("Employee ID: ")
    print("-" * 30)
    pin = get_pin_input("Set 4-Digit PIN: ")

    fields = ["name", "subject", "phone", "email", "emp_id", "pin"]
    values = [name, subject, phone, email, emp_id, pin]
    save_data("teachers", fields, values)


def main():
    init_db()
    while True:
        print("\n--- School Registration System ---")
        print("1. Student")
        print("2. Teacher")
        print("3. Exit")
        role = input("Choose role (1/2/3): ").strip()

        if role == "1":
            register_student()
        elif role == "2":
            register_teacher()
        elif role == "3":
            print("\nGood bye!\n")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    main()
