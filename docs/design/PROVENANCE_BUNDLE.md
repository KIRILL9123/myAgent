# Provenance and Evidence Bundle

Status: **Design contract v1 — 2026-08-04**
Owner: Knowledge / cross-domain infrastructure

## Purpose

Mira should be able to explain where a conclusion, proposal, or generated domain
action came from without turning documents, emails, or web results into trusted
facts automatically.

An evidence bundle is a bounded set of source references and derivation metadata
attached to an answer, proposal, projection, or approved domain change. It is a
cross-cutting contract, not a new business domain and not a replacement for the
owning domain table.

## Conceptual shape

```text
EvidenceBundle
├── bundle_id
├── created_at / reference_time
├── source_items[]
│   ├── source_type: document | memory | email | calendar | web | system
│   ├── source_id / external_ref
│   ├── title
│   ├── locator: chunk, line, message, event or URL
│   ├── bounded_excerpt (optional, still untrusted)
│   ├── content_hash (when available)
│   └── retrieved_at
├── derivation
│   ├── operation: retrieval | state_snapshot | proposal | tool_result | answer
│   ├── tool_or_service
│   ├── run_id / turn_id
│   ├── confidence (optional advisory value)
│   └── created_at
├── outputs[]
│   ├── output_type: answer | proposal | commitment | calendar_event | projection
│   └── output_ref
└── approval_ref (optional)
```

The contract is intentionally descriptive. It does not require one universal
database table yet; existing provenance payloads and relations are the v1
implementation surface.

## Rules

1. A source reference identifies evidence; it does not grant permission to act.
2. External content remains untrusted, even when it appears inside an excerpt.
3. A bundle may explain a proposal, but approval remains the only path to a
   high-impact mutation.
4. The target domain owns its lifecycle after creation. A document link does not
   own a Commitment, Calendar event, Subscription, or Finance record.
5. Excerpts are bounded and optional. Mira must not copy whole documents or
   private messages into every response.
6. A bundle should preserve the reference instant and source retrieval time so a
   later explanation can distinguish current state from historical evidence.
7. Confidence is advisory metadata, not an automatic approval decision.

## Current Mira mapping

| Flow | Existing evidence surface | Bundle direction |
|---|---|---|
| Document-derived task/event proposal | `approval_requests.payload` + `document_links` | Normalize into a shared bundle when the workflow is expanded |
| Document used as chat context | `documents_used` with document/chunk identifiers | Add bounded locator/excerpt metadata to the response contract |
| Memory-backed answer | `memory_used` with fact/note identifiers | Preserve source record and reference time in the answer metadata |
| Web research answer | Web source cards and retrieval metadata | Keep URL, retrieval time, freshness and untrusted status together |
| Today / Action Center projection | Owning source identifier and projection metadata | Link explanations back to the source domain, never to a copied signal |

## Deferred implementation

- one normalized persistence table for bundles and source items;
- user-visible source panels with bounded excerpts and freshness;
- citations for email and approved Memory facts;
- bundle versioning when a source document changes;
- retention and privacy rules for copied excerpts;
- automated claim verification or reviewer agents.

The first implementation should extend existing response metadata and approval
payloads, then add persistence only when at least two workflows need the same
contract. No new top-level route is justified by this capability.
