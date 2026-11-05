# Document-to-domain links

Status: Implemented v1 — 2026-08-04

## Product placement

Document links belong to Document Vault, which is part of Knowledge. They are
shown inside each document card on `/documents`; no new top-level route or
domain is created.

## Source of truth

The `documents` table remains the source of truth for the uploaded artifact.
Tasks/commitments, calendar events, and subscriptions remain authoritative in
their own domain tables or configured provider. `document_links` stores only:

- the document ID;
- target type and provider/domain ID;
- a short display label captured at link time;
- relationship metadata and provenance (`created_by`, `created_at`).

The display label is convenience metadata, not a copied lifecycle record. The
user follows the target path to review or change the current source entity.

## Supported targets

| Target | Owning domain | Destination |
| --- | --- | --- |
| `commitment` | Tasks & Projects | `/commitments` |
| `calendar_event` | Calendar | `/calendar` |
| `subscription` | Finance | `/subscriptions` |

The picker exposes active/non-terminal commitments and subscriptions plus
events in a rolling ±365-day window from the configured calendar provider.
Provider-owned calendar UIDs stay opaque; the picker is the validation boundary
because some CalDAV providers do not support a portable get-by-UID operation.

## API contract

- `GET /api/documents/link-targets` returns current picker options.
- `GET /api/documents/{id}/links` returns links for one document.
- `POST /api/documents/{id}/links` creates an idempotent link.
- `DELETE /api/documents/{id}/links/{link_id}` removes only the relation.

The unique key `(document_id, target_type, target_id)` prevents duplicate
relations. Archiving a document removes its relations through the document
foreign key; it does not archive or modify the target entity.

## Explicitly out of scope for the link layer

- extracting dates or obligations from documents (implemented separately in [`DOCUMENT_PROPOSALS.md`](DOCUMENT_PROPOSALS.md));
- automatically creating commitments or calendar events without approval;
- OCR for scanned documents;
- replacing Approval Center provenance with an implicit document link.

OCR, semantic interpretation, and unapproved writes remain future work and
require their own feature proposal before they can write into another domain.
