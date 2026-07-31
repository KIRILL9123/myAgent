# Memory Evolution Roadmap

## Memory v2 — implemented baseline

Memory now has two local layers:

- **Notes**: manually created, editable, taggable items that can be archived. They are searchable and available to the agent as contextual knowledge.
- **Facts**: structured preferences, habits, projects and relationships extracted from chat. High-confidence `preference`, `habit`, and `project` facts are approved automatically; relationships, ambiguous and low-confidence facts remain in review.

The `Memory` screen now starts with an overview and provides Notes, Facts, Review, Consolidation, and Graph views. Facts expose their source type, approval mode, confidence, pin state, and last confirmation time. The chat response can expose the compact list of memory items that informed the answer.

SQLite FTS5 is used for local candidate retrieval across notes and active facts. Embeddings remain a later optimisation, not a requirement for the current personal scale.

## What exists today
Current `user_facts` fields already include:
- `content`, `category`, `confidence`, `status`, `source_conversation_id`, timestamps
- approval workflow: `pending_approval -> approved/rejected`
- merge tracking via `merged_into_id`

Current relations:
- `fact_relations` with typed links (`related_to`, `contradicts`, `clarifies`, `causes`)

## Missing fields for next evolution
- explicit provenance bundle (source type/source ref/extractor metadata)
- `last_confirmed_at`
- temporal validity window (`valid_from`, `valid_to`)
- decay metadata (`decay_policy`, `decay_score`)

## Incremental migration options
1. **Metadata-first**: add optional columns with defaults; keep existing retrieval behavior.
2. **Behavior flags**: add read-time filters for expired/low-confidence facts.
3. **Decay scoring**: compute in background and expose for review before auto-impacting prompts.

## Backward compatibility behavior
- Existing facts without new fields remain valid and non-expiring by default.
- Missing provenance should be displayed as `unknown` rather than dropped.

## Contradiction handling
- Preserve contradictory facts with explicit relation edges; do not auto-delete history.
- Prompt-retrieval policy should prefer latest human-confirmed facts when conflicts exist.

## Recommended sequencing
1. Provenance + `last_confirmed_at`
2. Temporal validity model
3. Decay scoring (advisory only)
4. Optional automatic retrieval weighting based on confidence/time
