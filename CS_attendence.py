from contextlib import closing
from datetime import datetime
import sqlite3

DB_NAME = "school_data_8.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_attendance_db():
    with closing(get_db_connection()) as conn:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    roll_number TEXT NOT NULL,
                    date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    UNIQUE(roll_number, date),
                    FOREIGN KEY (roll_number) REFERENCES students(roll_number)
                )
            """)


def get_valid_date():
    today = datetime.now().strftime("%Y-%m-%d")
    date_input = input(
        f"Enter Date (YYYY-MM-DD) [Press Enter for Today ({today})]: "
    ).strip()
    if not date_input:
        return today
    try:
        datetime.strptime(date_input, "%Y-%m-%d")
        return date_input
    except ValueError:
        print("Invalid format. Using today's date instead.")
        return today


def mark_attendance():
    print("\n=== MARK ATTENDANCE ===")
    date_str = get_valid_date()

    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT roll_number, name, class, section FROM students ORDER BY CAST(roll_number AS INTEGER)"
        )
        students = cursor.fetchall()

        if not students:
            print("\nNo registered students found. Register students first!")
            return

        print(f"\nMarking attendance for Date: {date_str}")
        print("Enter 'P' for Present, 'A' for Absent, or 'S' to Skip:\n")

        for s in students:
            while True:
                prompt = f"Roll {s['roll_number']} | {s['name']} (Class {s['class']}-{s['section']}) [P/A/S]: "
                choice = input(prompt).strip().upper()

                if choice == "S":
                    break
                elif choice in ("P", "A"):
                    status = "Present" if choice == "P" else "Absent"
                    with conn:
                        conn.execute(
                            """
                            INSERT INTO attendance (roll_number, date, status)
                            VALUES (?, ?, ?)
                            ON CONFLICT(roll_number, date)
                            DO UPDATE SET status = excluded.status
                        """,
                            (s["roll_number"], date_str, status),
                        )
                    break
                else:
                    print("Invalid input. Enter P, A, or S.")

    print(f"\nAttendance saved for {date_str}!")


def view_student_attendance():
    print("\n=== STUDENT ATTENDANCE REPORT ===")
    roll = input("Enter Student Roll Number: ").strip()

    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, class, section FROM students WHERE roll_number = ?",
            (roll,),
        )
        student = cursor.fetchone()

        if not student:
            print("\nError: Roll Number not found.")
            return

        cursor.execute(
            "SELECT date, status FROM attendance WHERE roll_number = ? ORDER BY date DESC",
            (roll,),
        )
        records = cursor.fetchall()

    print(
        f"\nStudent: {student['name']} | Class: {student['class']}-{student['section']}"
    )
    print("-" * 45)

    if not records:
        print("No attendance records found for this student.")
        return

    total_days = len(records)
    present_days = sum(1 for r in records if r["status"] == "Present")
    percentage = (present_days / total_days) * 100

    for r in records:
        print(f"Date: {r['date']}  -->  {r['status']}")

    print("-" * 45)
    print(
        f"Summary: {present_days}/{total_days} Days Present ({percentage:.1f}%)"
    )


def view_attendance_by_date():
    print("\n=== DAILY ATTENDANCE SHEET ===")
    date_str = get_valid_date()

    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.roll_number, s.name, s.class, s.section, a.status
            FROM attendance a
            JOIN students s ON a.roll_number = s.roll_number
            WHERE a.date = ?
            ORDER BY CAST(s.roll_number AS INTEGER)
        """,
            (date_str,),
        )
        records = cursor.fetchall()

    print(f"\nAttendance Sheet for {date_str}:")
    print("-" * 50)
    if not records:
        print("No attendance marked for this date.")
        return

    for r in records:
        print(
            f"Roll {r['roll_number']} | {r['name']} ({r['class']}-{r['section']}) : {r['status']}"
        )


def main():
    init_attendance_db()
    while True:
        print("\n--- Attendance Tracker ---")
        print("1. Mark Daily Attendance")
        print("2. View Student Attendance & Percentage")
        print("3. View Attendance by Date")
        print("4. Return to Main Menu")

        choice = input("Select an option (1-4): ").strip()

        if choice == "1":
            mark_attendance()
        elif choice == "2":
            view_student_attendance()
        elif choice == "3":
            view_attendance_by_date()
        elif choice == "4":
            print("\nReturning to Main Menu...")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")


if __name__ == "__main__":
    main()
