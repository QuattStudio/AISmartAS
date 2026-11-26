# Project Memory

This file records stable project context for future work. Update it when the architecture or workflow changes.

## Snapshot

- Project name: **AISmartAS** (AI Smart Attendance System).
- Purpose: prototype for supervised, camera-assisted school attendance.
- Main language: Python.
- Core libraries include Flask, OpenCV, DeepFace, NumPy, and SQLite.
- Main launch path currently appears to be `python app/main.py` from the repository root.
- Face embeddings are read from and written to `resources/database/mock.json`.
- Student registration uses `resources/database/registration.db`.
- The camera and recognition flow is more developed than the web UI and API, which remain prototypes.

## Important limitations

- No attendance event workflow or review screen is currently documented in code.
- Student records and face embeddings are not linked by a stable ID.
- Enrollment is terminal-driven; the Flask UI is a simple demo page.
- `app/main.py` initializes `mockdb.DataBase`, while `app/database/database.py` contains a separate SQLite implementation. Confirm which is intended before expanding persistence.
- Some filenames and identifiers contain existing spelling inconsistencies (for example, `recogination.py`); avoid broad renames without updating imports and launch scripts.

## Data handling

Face embeddings and student registration data are sensitive. Never add real student data to commits or examples. Define access, retention, deletion, authorization, and manual alternatives before any real-world use.

## Working agreement

Keep docs honest about implemented versus planned behavior. Check the current code and local changes before editing; preserve unrelated user changes.
