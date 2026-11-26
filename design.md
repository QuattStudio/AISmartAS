# Design Notes

## Product goal

Explore a supervised school attendance workflow that can use face matching to help an operator identify students. The tool should make uncertain matches visible and keep a human responsible for confirming attendance.

## Current interface

- The camera experience is an OpenCV window with face boxes and labels.
- Pressing `r` starts a terminal-based enrollment prompt (see `app/vision/camera.py`).
- The Flask template is a basic welcome page, not an attendance dashboard.

## Intended operator experience

1. The operator selects a class/session and starts the camera.
2. The interface shows camera status and detected identities without hiding uncertainty.
3. A confirmed match can be added once to a pending attendance list; unknown faces remain unrecorded.
4. The operator reviews the list, resolves mistakes, and saves or exports the session.
5. If recognition or the camera is unavailable, the operator switches to manual attendance.

The intended flow above is a design direction; these screens and attendance actions are not implemented yet.

## Interface principles

- Make camera and model status visible, with clear recovery instructions.
- Distinguish confirmed, pending, unknown, and failed states through text as well as color.
- Avoid displaying more student information than the operator needs.
- Make confirmation, correction, and manual entry straightforward and auditable.
- Support keyboard use, readable contrast, and a usable layout on the school device.

## Visual direction

Use a calm, readable school-operations interface with clear headings, restrained color, and a prominent session status. Do not use visual cues that imply a machine match is certain when an operator must verify it.
