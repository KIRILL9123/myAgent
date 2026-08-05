# Code Sandbox

## Purpose

The Code Sandbox gives the agent a bounded place to draft small scripts,
examples, and tests without writing into the main repository. It is the first
delivery layer for the planned “agent can write code” capability.

Each experiment has a `session_id` and is stored below `CODE_SANDBOX_ROOT`
(by default, the repository-level `sandbox/` directory). The agent can list
and read text files, propose file writes, and run a small allowlist of checks:

- `python` — run one `.py` file;
- `pytest` — run one Python test file;
- `compile_python` — compile one `.py` file;
- `node` — run one `.js`/`.mjs` file when Node.js is installed.

There is no arbitrary shell command tool, no project-path parameter, and no
connector access from the sandbox runtime. File writes are `RED` actions and
therefore use the existing explicit-confirmation flow.

## Workspace lifecycle

The sandbox exposes a small derived lifecycle instead of becoming a general
app-hosting platform:

- `empty` — no captured files yet;
- `draft_changed` — files differ from the saved comparison point;
- `checkpointed` — the current workspace matches its saved checkpoint;
- `runtime_unavailable` — the configured runner cannot execute checks.

The existing baseline is the checkpoint. The snapshot API exposes the lifecycle
state, changed-file count, and checkpoint timestamp so the UI and future
automation can make the state explicit. Applying changes still requires the
existing Approval Center request, conflict check, and recoverable backup.
Named multi-checkpoint restore and live preview URLs remain intentionally out of
scope for the personal Mira workspace.

The execution runtime is Docker by default (`CODE_SANDBOX_RUNTIME=docker`).
The container receives only the session workspace and runs with no network,
read-only root filesystem, dropped Linux capabilities, `no-new-privileges`,
non-root user, CPU/RAM/PID limits, and a temporary `/tmp`. The local host
runtime is available only when explicitly setting `CODE_SANDBOX_RUNTIME=local`
for development or tests; it is never an automatic fallback.

## Limits

- relative paths only; `..`, absolute paths, and symlinks are rejected;
- UTF-8 text files only;
- 256 KB per file and 5 MB per workspace;
- 20,000 characters of captured output;
- 120 seconds maximum per check;
- the child process receives a minimal environment rather than the agent's
  secrets and API keys.

## Important security boundary

The Docker runner is the security boundary for normal operation. It still
requires Docker Desktop to be installed and running, and the image build is an
explicit operator action. If Docker is unavailable, checks fail closed rather
than executing on Windows. The local runtime is intentionally not an
OS-level security boundary and must remain limited to trusted development and
tests.

Build the images explicitly from the repository root:

```powershell
.\dev-tools\build_sandbox_images.ps1
```

## API

With a running backend, the current session can be inspected through:

- `GET /api/sandbox/{session_id}` — workspace snapshot and limits;
- `GET /api/sandbox/runtime` — Docker runner readiness;
- `GET /api/sandbox/{session_id}/file?path=main.py` — read a file;
- `POST /api/sandbox/{session_id}/files` — write a file;
- `POST /api/sandbox/{session_id}/checks` — run an allowlisted check.

The API is protected by the same local API-key middleware as the rest of the
backend.

## Diff and baseline

Each workspace has a comparison point stored outside the editable workspace
and outside the Docker mount. The baseline is created automatically before the
first workspace listing or write, and can be replaced explicitly from the UI.
This keeps the comparison metadata out of the agent's files and makes it
possible to review changes without touching the main repository.

- `GET /api/sandbox/{session_id}/diff` — added, modified and removed files as a unified diff;
- `POST /api/sandbox/{session_id}/baseline` — save the current workspace as the new comparison point;
- `POST /api/sandbox/{session_id}/apply` — create a pending Approval Center request for the reviewed diff;
- `DELETE /api/sandbox/{session_id}/file?path=main.py` — delete a file inside the sandbox;
- agent tool `sandbox_get_diff` — read-only access to the same diff.

The web page shows per-file additions/deletions and a collapsible diff. A
baseline does not apply anything to the main project. Applying changes is a
two-step operation: the sandbox creates a `SANDBOX_APPLY` request in the
Approval Center, then the user approves it there. Before writing, the backend
rechecks the sandbox fingerprint, rejects project conflicts, blocks protected
paths and keeps a recoverable backup under `.sandbox_backups/`. Failed applies
roll back the files changed during the operation.

The agent has two additional guarded tools: `sandbox_delete_file` (RED) and
`sandbox_request_apply` (RED). The latter only creates an approval request; it
cannot bypass the Approval Center.

## Follow-up

The remaining hardening work is broader adversarial evaluation, richer test
evidence and a task/history view. The current apply path is intentionally
limited to allowlisted text files and never exposes an arbitrary shell or
direct autonomous repository mutation.
