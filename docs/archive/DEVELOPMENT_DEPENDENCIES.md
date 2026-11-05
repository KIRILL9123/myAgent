# Development Dependency Map

Keep implementation order dependency-aware.

## Core dependency chain
1. **Memory foundations** (confidence/provenance/temporal metadata contract)
2. **Commitment Tracker contract + lifecycle mechanics**
3. **Personal State Engine consumption of commitment + memory signals**

## Integration dependencies
- **Email -> Commitment Tracker**: email extraction proposes commitments; requires commitment schema first.
- **Calendar -> Commitment Tracker**: calendar events may create/update deadlines; requires commitment lifecycle semantics.
- **Commitment Tracker -> Personal State**: personal state should consume normalized commitment statuses.

## Safety dependencies (cross-cutting)
- Dry-run architecture should precede broad side-effecting automation work.
- Tool argument validation should precede adding many new tools.
- Backup/restore plan should be in place before schema-heavy domain expansion.
