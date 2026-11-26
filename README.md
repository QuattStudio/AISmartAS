# AI Smart Attendance System

## Run the app

From the project folder, start the API server and the camera/web app in two terminals:

```powershell
python app/server.py
```

```powershell
python app/main.py
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000). The API runs on port 5000; the browser app and live camera view run on port 8000.

## Build Windows executables

Activate the project virtual environment, then run:

```bat
compile.bat -build-exe
```

This creates `app\server.exe` and `app\app.exe`. The server executable starts the API; the app executable starts the camera and web page.

## Attendance and enrollment

- The camera marks each recognized student or teacher present once per local calendar day.
- The attendance panel can also mark a person present manually.
- Student roll numbers and teacher IDs are unique; the database also prevents a second attendance mark for the same person on the same day.
- Select a person type, scan their face, then enter the matching details to enroll them.
