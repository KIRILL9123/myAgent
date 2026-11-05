# Commitment Tracker Domain Contract

## Purpose
Define shared semantics before implementation.

## Entity: Commitment
Fields (minimum):
- `id` (UUID)
- `title` (short human-readable statement)
- `description` (optional detail)
- `status` (`PROPOSED | ACTIVE | COMPLETED | CANCELLED | EXPIRED`)
- `confidence` (`0.0..1.0`, confidence in extraction/interpretation)
- `provenance` (source references + extraction trace)
- `source_type` (`CHAT | EMAIL | DOCUMENT | CALENDAR`)
- `source_ref` (message id / document id / calendar uid / etc.)
- `owner` (person responsible; default user)
- `deadline_at` (nullable datetime)
- `created_at`, `updated_at`
- `activated_at`, `completed_at`, `cancelled_at`, `expired_at` (nullable lifecycle timestamps)
- `related_fact_ids` (memory linkage)
- `related_calendar_event_ids` (calendar linkage)
- `conflicts_with_ids` (other commitments)

## Lifecycle
1. **PROPOSED**: extracted/suggested, not accepted yet.
2. **ACTIVE**: explicitly approved by human.
3. **COMPLETED**: marked done by human or verified completion evidence.
4. **CANCELLED**: explicitly cancelled by human.
5. **EXPIRED**: deadline passed while still non-terminal.

## State transitions
- `PROPOSED -> ACTIVE`: requires explicit human approval.
- `PROPOSED -> CANCELLED`: rejected suggestion.
- `ACTIVE -> COMPLETED`: explicit completion signal or trusted verification.
- `ACTIVE -> CANCELLED`: explicit human cancellation.
- `ACTIVE -> EXPIRED`: deadline passes without completion.
- `EXPIRED -> ACTIVE` (optional reopen): explicit human decision.

## Creation rules
Create only when a statement implies obligation/commitment (not general preference/fact). Ambiguous candidates remain `PROPOSED`.

## Human approval model
- Approval is mandatory before activation.
- Approval action should preserve provenance snapshot for auditability.

## Deadline behavior
- Missing deadline allowed.
- When deadline passes and status is ACTIVE, mark EXPIRED and emit review signal.

## Contradictions and conflicts
- Contradictory commitments should be linked via `conflicts_with_ids`.
- No auto-deletion; conflicts are resolved via explicit human decision.

## Relationship to Memory
- Memory stores facts/preferences; Commitment stores obligations/actions.
- Commitment may reference memory facts but has independent lifecycle.

## Relationship to Calendar
- Calendar events can support commitment execution but do not imply automatic completion.

## Relationship to future Personal State Engine
- Personal State should consume commitment status transitions as explicit signals, not infer silently.
