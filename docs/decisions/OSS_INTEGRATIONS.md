# Open-source integrations

Status: **Active decision record — 2026-08-04**

This file records the bounded GitHub audit and the integrations that were
accepted for Mira. The rule is selective reuse: a repository must improve a
real product surface without taking ownership of Mira's domain data, approval
flow, privacy boundary, or design system.

## Accepted

### Microsoft MarkItDown — Document Vault extractor

- Repository: [microsoft/markitdown](https://github.com/microsoft/markitdown)
- License: MIT; the selected dependency is pinned to `0.1.7` in
  `requirements.txt` with only `docx`, `pdf`, `pptx`, and `xlsx` extras.
- Integration: `backend/app/documents/document_service.py` passes accepted
  upload bytes through `convert_stream()` with plugins disabled.
- Mira still owns file-size limits, safe names, vault storage, SHA-256
  deduplication, extraction status, chunking, SQLite FTS5, provenance and
  approval-gated proposals.
- Security boundary: never pass a user-controlled path or URL to MarkItDown;
  document content remains untrusted input.
- The old per-format extraction branches were removed. PDF parsing is no
  longer a separate `pypdf` path.

### FullCalendar — Calendar renderer

- Repository: [fullcalendar/fullcalendar](https://github.com/fullcalendar/fullcalendar)
- License: MIT for the selected standard packages; no Premium/Scheduler
  packages are used.
- Integration: `frontend/src/components/CalendarView.tsx` renders Today,
  Week and Month through the React connector and standard day-grid/time-grid/
  interaction plugins.
- Mira still owns the event API, recurrence semantics, source filtering,
  conflict preview, confirmation, create/update/delete mutations and
  navigation state.
- The previous hand-written `MonthView`, `WeekView`, `TodayView` and
  `EventPill` implementations were deleted from `CalendarPage.tsx`.
- All FullCalendar packages are kept on the same `6.1.21` major/minor line.

### Radix Dialog — shared modal accessibility

- Repository: [radix-ui/primitives](https://github.com/radix-ui/primitives)
- License: MIT for `@radix-ui/react-dialog`.
- Integration: `frontend/src/components/ui.tsx` keeps Mira's existing `Dialog`
  wrapper API while Radix provides modal semantics, focus management, Escape,
  outside-click handling and keyboard-safe close behavior.
- Mira's existing visual tokens and dialog CSS remain the presentation layer;
  no second component system was introduced.

## Deliberately deferred

### Tiptap

Repository: [ueberdosis/tiptap](https://github.com/ueberdosis/tiptap).

Mira notes are currently plain text stored in SQLite and indexed directly by
FTS5. Replacing the textarea would require choosing and migrating a storage
format (Markdown, HTML or JSON), sanitizing/rendering it, and defining search
normalization. Until formatted notes are an approved product requirement,
Tiptap would add complexity without improving the personal workflow.

### Other audited projects

Open WebUI, Khoj, OpenLoaf, Tolaria, Memoh, OpenHuman and OpenHands remain
idea/reference sources only. They are full products or agent platforms, have
copyleft/custom-license or scope concerns, or would duplicate Mira's existing
orchestration and safety boundaries. sqlite-vec remains a future experiment
only after an FTS5 benchmark proves lexical retrieval is insufficient.

The broader 2026-08-04 comparison of Paperless-ngx, Super Productivity, Vikunja,
Actual Budget, AppFlowy, LobeHub, Radicale, Outline and Cal.com is recorded in
[OSS_AUDIT_2026-08-04.md](OSS_AUDIT_2026-08-04.md). Its only immediate candidate
is a bounded local OCR adapter for the existing Document Vault; no full product
or copyleft application is being embedded.

## Removal rule

When an accepted dependency is removed or replaced, delete its adapter and
unused styles/imports in the same change, update this record and rerun the
frontend build/lint plus the affected backend tests. No OSS dependency is
considered integrated while it is only present in `package.json` or
`requirements.txt` without a live adapter.
