# Project Rules

These rules guide changes to AISmartAS.

## Code and data

- Keep changes focused and follow the existing Python module layout unless there is a clear reason to change it.
- Use parameterized SQL values. Do not accept arbitrary table or column names from a request.
- Validate request data at the application boundary; return clear errors and do not expose stack traces or private records to clients.
- Keep student identity stable across the registration database, face references, and attendance records. Do not use a display name as the only production key.
- Do not log face embeddings, raw face images, credentials, or unnecessary student details.
- Keep generated databases, logs, and enrollment data out of source control unless a project owner explicitly needs a safe fixture.
- Handle camera, model, and database failures explicitly; always release opened resources on shutdown.

## Recognition and attendance

- Treat a face match as a suggestion, not proof of identity. Preserve an operator review and correction path.
- Never create attendance for an unknown or low-confidence match.
- Document and configure thresholds; do not silently loosen them to make a demo appear successful.
- Prevent repeated frame detections from generating unlimited attendance events. Define the duplicate window and correction policy before implementation.
- Provide a non-camera attendance fallback.

## Privacy and safety

- Collect only information needed for the stated school workflow.
- Before real use, provide clear notice and obtain appropriate authorization for students and guardians as required by the school and applicable rules.
- Restrict access to biometric and student data, define deletion and retention periods, and protect backups.
- Use synthetic or explicitly approved sample data in development. Do not commit real student biometric data.

## Documentation

- Keep documentation aligned with the code. Label proposed capabilities as proposed and incomplete features as incomplete.
- Record setup prerequisites and the actual run command when they change.
