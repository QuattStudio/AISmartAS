# Project Phases

This roadmap separates the working prototype from capabilities needed for a dependable release. Phases are proposed; no completion status is implied.

## Phase 1 — Stabilize the prototype

- Document environment setup and one supported launch path.
- Confirm camera lifecycle, recognition worker behavior, logging, and shutdown.
- Remove confusing mock/legacy paths or clearly identify them.
- Keep sample data synthetic and outside production records.

## Phase 2 — Complete student enrollment

- Validate required student fields and duplicate roll numbers.
- Associate a face reference with a stable student record ID.
- Add supervised capture, enrollment confirmation, replacement, and deletion flows.
- Define who can enroll and how enrollment is audited.

## Phase 3 — Record and review attendance

- Add a timestamped attendance event store and documented duplicate policy.
- Expose validated API operations for registration and attendance.
- Build an operator view to review, correct, and export attendance.
- Provide a manual fallback and clear handling for camera/model failures.

## Phase 4 — Privacy and operational readiness

- Define notice, authorization, access roles, retention, deletion, backup, and incident procedures.
- Review performance and matching behavior in the intended environment with appropriate oversight.
- Check accessibility and fairness across the intended student population.
- Confirm applicable school policies and legal requirements before any real deployment.

## Phase 5 — Release and maintenance

- Package a reproducible environment and configuration.
- Add monitoring, recovery guidance, and a documented update process.
- Pilot with operator supervision and a non-biometric alternative before considering wider use.
