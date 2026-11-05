# Document-derived action proposals

Status: Implemented v1 — 2026-08-04

## Product decision

This is the final major Document Vault capability for the current v1 scope:
documents can surface explicit obligations with dates and offer a controlled
next action. The feature does not silently create tasks or calendar events.

The flow is:

1. User or Assistant asks Mira to inspect a ready document.
2. A deterministic extractor finds a sentence containing an obligation cue and
   a parseable date.
3. The user chooses `Предложить задачу` or `Предложить событие`.
4. A `DOCUMENT_PROPOSAL` enters the existing Approval Center and Action Center.
5. Approval creates the existing Commitment or Calendar event and adds a
   derived Document Vault link. Rejection creates nothing.

## Extraction contract

The v1 extractor is intentionally conservative and local. It supports common
ISO, `DD.MM.YYYY`, and Russian/German/English month-name dates. It requires an
obligation cue such as `оплатить`, `предоставить`, `срок`, `muss`, `Frist`,
`submit`, or `deadline` in the same sentence/line. The result includes the
document evidence, normalized deadline, candidate fingerprint, and confidence.

The extractor is a proposal detector, not a legal or semantic authority. It
does not infer a task from an isolated date and does not rewrite document text.

## Source of truth and approval

`approval_requests` remains the workflow source of truth. Its payload stores
the document ID, candidate fingerprint, action type, evidence, and deadline.
The resulting Commitment or Calendar event owns its own lifecycle. The derived
`document_links` relation preserves provenance without copying lifecycle data.

Both the web UI and the Assistant use the same service functions. Telegram
uses the same tool registry as Chat:

- `scan_document_proposals(document_id)` — read-only candidate scan;
- `propose_document_action(document_id, candidate_id, action_type)` — creates
  an approval request only.

## UI placement

The feature lives inside each `/documents` card as the collapsed
«Сроки и обязательства» panel. The panel previews evidence and offers the two
proposal actions. Confirmation remains centralized in `/notifications` or the
compatibility Approval Center route; no document-specific confirmation queue is
introduced.

## Explicitly deferred

- OCR for scanned PDFs and images;
- semantic extraction beyond high-precision date + obligation cues;
- version comparison and change summaries;
- automatic creation without approval;
- legal interpretation or confidence claims beyond the deterministic match.
