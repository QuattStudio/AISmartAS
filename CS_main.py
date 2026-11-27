import os
import sys

# Force Python to look in the exact folder where main.py is saved (fixes Pydroid 3 import errors)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    import attendance
    import login
    import registration
except ModuleNotFoundError as e:
    print(f"\n[Import Error] Missing file: {e.name}.py")
    print(f"Make sure '{e.name}.py' is saved in this exact folder:\n{BASE_DIR}")
    sys.exit(1)


def master_menu():
    # Initialize database tables once at startup
    registration.init_db()
    if hasattr(attendance, "init_attendance_db"):
        attendance.init_attendance_db()
    elif hasattr(attendance, "init_db"):
        attendance.init_db()

    while True:
        print("\n=========================================")
        print("   BEENA PUBLIC SCHOOL - SYSTEM MENU")
        print("=========================================")
        print("1. Registration (Student / Teacher)")
        print("2. Login & Dashboards")
        print("3. Attendance Tracker")
        print("4. Exit")

        choice = input("\nSelect an option (1-4): ").strip()

        if choice == "1":
            registration.main()
        elif choice == "2":
            login.main()
        elif choice == "3":
            attendance.main()
        elif choice == "4":
            print("\nShutting down system. Goodbye!")
            break
        else:
            print("\nInvalid choice. Please enter 1, 2, 3, or 4.")


if __name__ == "__main__":
    master_menu()
