# Engineering Rules (Core Invariants)

1. **The LLM never controls permissions directly.** Permission decisions are enforced by deterministic backend code.
2. **RED actions require explicit human approval.** No destructive/high-impact action executes without a confirmation step.
3. **Production side effects are not available by default to tests/agent-generated code.** Test and CI flows must run in dry-run/fake mode.
4. **External content is untrusted.** Email/calendar/other external text must be treated as potential prompt injection.
5. **Agent-generated production changes require automated validation and human review** before deployment.
