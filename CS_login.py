from contextlib import closing
import sqlite3

DB_NAME = "school_data_8.db"


def init_db():
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.executescript(
                """
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
                    pin TEXT NOT NULL UNIQUE
                );
            """
            )


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def teacher_dashboard():
    print("\n--- Teacher Dashboard (Admin Access) ---")
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students")
        students = cursor.fetchall()

    if not students:
        print("No student records found.")
        return

    print(f"\nTotal Registered Students: {len(students)}")
    for s in students:
        print("-" * 40)
        print(f"Roll No: {s['roll_number']} | Name: {s['name']}")
        print(f"Class: {s['class']} | Section: {s['section']} | Stream: {s['stream']}")
        subjects = [s["optional_sub_1"], s["optional_sub_2"], s["language_lit"]]
        valid_subs = [sub for sub in subjects if sub and sub.strip()]
        print(f"Subjects: {', '.join(valid_subs)}")


def student_dashboard(roll_number):
    print(f"\n=== Student Dashboard (Roll No: {roll_number}) ===")
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE roll_number = ?", (roll_number,))
        student = cursor.fetchone()

    if student:
        print("\n--- Your Profile Details ---")
        for key in student.keys():
            print(f"{key.replace('_', ' ').title()}: {student[key]}")
    else:
        print("\nError: Student record not found.")


def main():
    init_db()
    while True:
        print("\n=== Login System ===")
        print("1. Teacher Login (PIN)")
        print("2. Student Login (Roll Number)")
        print("3. Exit")
        choice = input("Select role to login: ").strip()

        if choice == "1":
            pin = input("Enter 4-Digit PIN: ").strip()
            with closing(get_db_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM teachers WHERE pin = ?", (pin,))
                teacher = cursor.fetchone()

            if teacher:
                print(f"\nWelcome, {teacher['name']} ({teacher['subject']})!")
                teacher_dashboard()
            else:
                print("\nInvalid PIN. Access denied.")

        elif choice == "2":
            roll = input("Enter Roll Number: ").strip()
            with closing(get_db_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM students WHERE roll_number = ?", (roll,))
                student = cursor.fetchone()

            if student:
                print(f"\nWelcome back, {student['name']}!")
                student_dashboard(roll)
            else:
                print("\nRoll Number not found.")

        elif choice == "3":
            print("\nExiting system. Goodbye!")
            break
        else:
            print("\nInvalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    main()

