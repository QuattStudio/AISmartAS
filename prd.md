# Product Requirements Document (PRD)

## Product

**AISmartAS — AI Smart Attendance System**

## Summary

AISmartAS is a prototype for helping school staff take attendance with a camera and face matching. A staff member should stay in control: the system can suggest a student match, while staff review uncertain results and can use a manual attendance option.

The current project has a local camera and face-matching prototype, separate student registration storage, a basic Flask page, and an unfinished API. The complete attendance workflow described below is a product goal, not a claim about current functionality.

## Problem

Taking attendance by hand can take class time and create recordkeeping work. A camera-assisted tool could help staff identify students more quickly, but incorrect matches, privacy concerns, or camera failures must not silently create attendance records.

## Goals

- Help authorized school staff record attendance for a class session.
- Make suggested matches and uncertain results easy to review.
- Prevent unknown or unconfirmed matches from becoming attendance records.
- Provide manual attendance when camera matching is unavailable or unsuitable.
- Keep student and biometric data limited, protected, and manageable.

## Out of scope

- Fully automatic attendance without staff oversight.
- Using face matching as the only attendance method.
- Disciplinary, grading, tracking, or other uses beyond taking attendance.
- Claiming a particular accuracy level before it has been measured in the intended setting.

## Users

- **School staff/operator:** starts a session, reviews suggested matches, corrects records, and closes attendance.
- **Student:** is represented by a school record and, where authorized, an enrolled face reference.
- **Administrator:** manages authorized users, enrollment, retention, and system settings.

## Core user journey

1. An authorized staff member opens a class session and checks camera status.
2. The system shows detected faces and possible student matches with clear uncertainty cues.
3. Staff confirms a match before it is added to the session, or records attendance manually.
4. Staff reviews and corrects the pending list, then saves the session.
5. Authorized staff can review or export the saved attendance record.

## Functional requirements

- **PR-01 — Student records:** Create and update student records with validated fields and a stable student identifier.
- **PR-02 — Enrollment:** Allow authorized, supervised enrollment and removal of a face reference linked to a student identifier.
- **PR-03 — Camera status:** Show whether the camera is ready, unavailable, or has failed, with a usable manual fallback.
- **PR-04 — Match suggestions:** Compare detected faces with enrolled references and show unknown or uncertain results as such.
- **PR-05 — Confirmation:** Require the configured staff confirmation before a suggested identity becomes an attendance event.
- **PR-06 — Session records:** Store student, session, timestamp, and confirmation details for each attendance event.
- **PR-07 — Duplicate handling:** Prevent or flag duplicate attendance for the same student and session.
- **PR-08 — Review and correction:** Let authorized staff review, correct, and export session attendance with an audit history.
- **PR-09 — Errors:** Report camera, model, and storage failures clearly; do not silently create records after a failure.

## Non-functional requirements

- **Privacy:** Collect only information needed for attendance. Set clear access, retention, and deletion rules before real use.
- **Security:** Protect student records and face references, validate inputs, and restrict administrative actions.
- **Usability:** Make status, uncertainty, confirmation, and manual entry understandable to school staff.
- **Accessibility:** Support keyboard use, readable contrast, clear text labels, and a workflow that does not rely on color alone.
- **Reliability:** Preserve saved records and recover safely from camera or application errors.
- **Performance:** Keep the interface responsive on the intended school device; set measurable targets after testing that device.

## Success measures

- Staff can complete and review a class session using camera suggestions or the manual path.
- Unknown and unconfirmed faces never create attendance events.
- Duplicate records and correction history follow the school's documented policy.
- Staff can identify and recover from camera or storage errors without losing confirmed work.
- Privacy, access, retention, and deletion procedures are documented before any real student data is used.

## Assumptions and decisions to resolve

- Which school roles may enroll students, confirm matches, edit records, and export attendance?
- How is a class session identified, and what counts as a duplicate event?
- What notice, authorization, retention, deletion, and manual alternative does the school require?
- Will the app run on one local computer or serve multiple devices?
- What performance and recognition measures are appropriate for a supervised pilot?

## Current implementation notes

- The camera and embedding comparison prototype lives under `app/vision/`.
- Student SQLite storage and face-reference JSON storage are separate and not yet joined by a stable identifier.
- Enrollment is currently terminal-driven.
- The Flask page is a demo, and the registration API is incomplete.
- Attendance session storage, confirmation, review, and export are not implemented yet.
