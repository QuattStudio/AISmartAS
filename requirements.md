# Requirements

## Functional requirements

### Current prototype behavior

- **FR-01:** Start a local camera session and report if the camera cannot be opened.
- **FR-02:** Detect faces in camera frames and calculate embeddings with the configured DeepFace model.
- **FR-03:** Compare live embeddings with a local reference set using cosine distance and a configurable threshold.
- **FR-04:** Label a face as unknown when no reference matches the threshold.
- **FR-05:** Allow supervised terminal enrollment and save an embedding in the JSON reference store.
- **FR-06:** Initialize a local SQLite student table for registration data.
- **FR-07:** Serve a basic Flask page and expose an unfinished registration API route.

FR-06 and FR-07 describe code presence, not a completed end-to-end registration product.

### Required before operational attendance use

- **FR-08:** Link student records and face references using a stable, non-display-name identifier.
- **FR-09:** Create a timestamped attendance event only after an authorized confirmation policy is met.
- **FR-10:** Prevent or flag duplicate events for the same student and session.
- **FR-11:** Let an operator review, correct, and export attendance with an audit trail.
- **FR-12:** Offer manual attendance when camera, model, or network services are unavailable.
- **FR-13:** Support authorized enrollment updates and deletion of student and biometric records.

## Non-functional requirements

- **NFR-01 Reliability:** Camera and database failures must be visible and must not silently record attendance.
- **NFR-02 Privacy:** Collect and retain only necessary data; restrict access and provide a defined deletion process.
- **NFR-03 Security:** Validate input, use parameterized SQL, and protect local files and any network endpoints.
- **NFR-04 Usability:** Provide clear status, accessible controls, and operator guidance for uncertain results.
- **NFR-05 Performance:** Keep the interface responsive while camera capture and recognition run; measure performance on the target device before setting numeric targets.
- **NFR-06 Portability:** Document supported Python and operating system versions and provide reproducible setup instructions.
- **NFR-07 Accountability:** Keep an auditable record of attendance changes without logging biometric vectors or unnecessary personal data.

## Assumptions and open decisions

- Is the product single-device/local, or will multiple clients use a central server?
- What defines a session, attendance timestamp, duplicate window, and correction authority?
- Which database helper is authoritative: `mockdb.py` or `database.py`?
- What authorization, notice, retention, and alternative attendance processes will the school require?
- What accuracy, latency, and accessibility targets must be met in the intended environment?
