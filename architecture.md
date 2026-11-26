# Architecture

## Current structure

```text
app/main.py                 Application entry point and lifecycle
app/vision/camera.py        Camera capture, worker threads, matching, enrollment UI
app/vision/recogination.py  DeepFace embeddings and JSON reference store
app/vision/network.py       Network-related helper(s)
app/database/database.py    SQLite student registration storage
app/database/mockdb.py      Mock/local database helper used by main
app/server.py               Flask API prototype
app/frontend/app.py         Flask page prototype
app/frontend/templates/     HTML templates
app/core/logger.py          Asynchronous application logger
app/core/constants.py       Shared constants and exit status
resources/database/         Local SQLite and JSON data
resources/assets/           Sample images and asset notes
```

## Runtime flow

1. `app/main.py` initializes the logger and local database helper.
2. It opens the configured OpenCV camera and starts capture and recognition workers.
3. `ReferenceEmbedding` loads known vectors from the JSON reference store. DeepFace produces embeddings from frames.
4. The camera component compares each live vector with known vectors using cosine distance. A match below the configured threshold is labeled with the stored name; otherwise it is unknown.
5. The display loop renders frames and labels. Enrollment is currently prompted in the terminal and saves a face vector to JSON.
6. On exit, the camera and logger are closed.

## Data stores

- **Student records:** SQLite at `resources/database/registration.db`, initialized by `DataBaseSystem`.
- **Face reference vectors:** JSON at `resources/database/mock.json`, loaded and written by `ReferenceEmbedding`.
- **Logs:** session-specific log files under `resources/logs/` (the logger creates parent directories).

These stores are not yet joined by a stable student identifier. Names currently serve as face-vector keys, which can be ambiguous. A production design should link a vector to a student record ID and protect both stores consistently.

## Boundaries and current gaps

The camera, recognition, persistence, HTTP API, and web page are separate modules but do not yet form a complete service. The API only has a registration route stub; the frontend is a demo page; attendance event persistence and operator review are not implemented. The `network` module should be reviewed before relying on it. Treat the system as a local prototype rather than a deployed attendance platform.

## Suggested target separation

For future development, keep camera capture and recognition behind a vision service; use a repository/service layer for student and attendance data; expose validated operations through the Flask API; and let the frontend call that API. Keep identity keys stable, make event creation idempotent, and keep operator review separate from automatic matching. These are design recommendations, not descriptions of existing behavior.
