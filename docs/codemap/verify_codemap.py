"""Validate the evidence-backed codemap against the current repository."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CODEMAP_DIR = ROOT / "docs" / "codemap"
JSON_PATH = CODEMAP_DIR / "codemap.json"
HTML_PATH = CODEMAP_DIR / "codemap.html"
LOCK_PATH = CODEMAP_DIR / "codemap.lock"
ALLOWED_EDGE_TYPES = {"imports", "calls", "reads", "writes", "publishes", "subscribes"}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def is_excluded(relative_path: str, excluded: set[str]) -> bool:
    normalized = relative_path.replace("\\", "/")
    parts = normalized.split("/")
    return any(
        normalized == item or normalized.startswith(item.rstrip("/") + "/") or part == item
        for item in excluded
        for part in parts
    )


def module_files(module_path: str, excluded: set[str]) -> list[str]:
    path = ROOT / module_path
    if path.is_file():
        return [module_path.replace("\\", "/")]
    if not path.is_dir():
        return []
    files: list[str] = []
    for candidate in path.rglob("*"):
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(ROOT).as_posix()
        if not is_excluded(relative, excluded):
            files.append(relative)
    return sorted(files)


def fingerprint(module_path: str, excluded: set[str]) -> str:
    digest = hashlib.sha256()
    for relative in module_files(module_path, excluded):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update((ROOT / relative).read_bytes())
    return digest.hexdigest()


def check_symbol(ref: dict, label: str, errors: list[str]) -> None:
    source_path = ref.get("path")
    symbol = ref.get("symbol")
    if not isinstance(source_path, str) or not isinstance(symbol, str) or not symbol:
        errors.append(f"{label}: malformed source reference")
        return
    path = ROOT / source_path
    if not path.is_file():
        errors.append(f"{label}: missing source path {source_path}")
        return
    if symbol not in path.read_text(encoding="utf-8", errors="replace"):
        errors.append(f"{label}: symbol not found {source_path}::{symbol}")


def validate() -> list[str]:
    errors: list[str] = []
    codemap = read_json(JSON_PATH)
    lock = read_json(LOCK_PATH)

    required_codemap = {"generated_at", "generated_from_commit", "scope", "nodes", "edges", "flows"}
    missing = required_codemap - codemap.keys()
    if missing:
        errors.append(f"codemap.json: missing keys {sorted(missing)}")
    required_lock = {
        "generated_at",
        "current_commit",
        "generated_from_commit",
        "working_tree_has_uncommitted_changes",
        "scanned_scope",
        "excluded_directories",
        "fingerprint_algorithm",
        "module_fingerprints",
    }
    missing = required_lock - lock.keys()
    if missing:
        errors.append(f"codemap.lock: missing keys {sorted(missing)}")

    nodes = codemap.get("nodes", [])
    edges = codemap.get("edges", [])
    flows = codemap.get("flows", [])
    if len(nodes) > 20:
        errors.append(f"codemap.json: {len(nodes)} primary nodes exceed the limit of 20")
    node_ids = {node.get("id") for node in nodes}

    for node in nodes:
        node_id = node.get("id", "<unknown>")
        if not (ROOT / str(node.get("path", ""))).exists():
            errors.append(f"node {node_id}: path does not exist")
        for field in ("entrypoints", "tests", "evidence"):
            for index, ref in enumerate(node.get(field, [])):
                check_symbol(ref, f"node {node_id} {field}[{index}]", errors)

    for index, edge in enumerate(edges):
        if edge.get("from") not in node_ids or edge.get("to") not in node_ids:
            errors.append(f"edge {index}: references an unknown node")
        if edge.get("type") not in ALLOWED_EDGE_TYPES:
            errors.append(f"edge {index}: invalid type {edge.get('type')!r}")
        evidence = edge.get("evidence")
        if not evidence or evidence.get("symbol") == "unknown":
            errors.append(f"edge {index}: relationship has unknown source evidence")
        else:
            check_symbol(evidence, f"edge {index} evidence", errors)

    edge_pairs = {(edge.get("from"), edge.get("to")) for edge in edges}
    for index, flow in enumerate(flows):
        steps = flow.get("steps", [])
        for step in steps:
            if step not in node_ids:
                errors.append(f"flow {index}: unknown step {step}")
        for left, right in zip(steps, steps[1:]):
            if (left, right) not in edge_pairs:
                errors.append(f"flow {index}: missing evidenced edge {left} -> {right}")

    html = HTML_PATH.read_text(encoding="utf-8")
    embedded_match = re.search(r"const CODEMAP = (.*?);\n\(function", html, re.DOTALL)
    if not embedded_match:
        errors.append("codemap.html: embedded CODEMAP object not found")
    else:
        try:
            embedded = json.loads(embedded_match.group(1))
            for field in ("nodes", "edges", "flows"):
                if embedded.get(field) != codemap.get(field):
                    errors.append(f"codemap.html: embedded {field} differs from codemap.json")
        except json.JSONDecodeError as exc:
            errors.append(f"codemap.html: embedded CODEMAP is invalid JSON: {exc}")

    if shutil.which("node"):
        script_match = re.search(r"<script>\n(.*?)\n</script>", html, re.DOTALL)
        if not script_match:
            errors.append("codemap.html: inline script not found")
        else:
            result = subprocess.run(
                ["node", "--check"],
                input=script_match.group(1),
                text=True,
                capture_output=True,
                cwd=ROOT,
            )
            if result.returncode:
                errors.append(f"codemap.html: JavaScript syntax check failed: {result.stderr.strip()}")
    else:
        errors.append("codemap.html: node is required for JavaScript syntax validation")

    current_commit = git("rev-parse", "HEAD")
    working_tree_dirty = bool(git("status", "--porcelain"))
    if lock.get("current_commit") != current_commit:
        # A codemap is often committed immediately after the source commit it
        # describes. In that case the source commit is still the authoritative
        # revision; accepting a codemap-only follow-up keeps the lock
        # self-consistent without pretending the map describes its own commit.
        try:
            parent_commit = git("rev-parse", "HEAD^")
            changed_in_commit = {
                path for path in git("diff", "--name-only", f"{parent_commit}..{current_commit}").splitlines()
                if path
            }
        except subprocess.CalledProcessError:
            parent_commit = ""
            changed_in_commit = set()
        if parent_commit != lock.get("current_commit") or not changed_in_commit or not all(
            path.startswith("docs/codemap/") for path in changed_in_commit
        ):
            errors.append("codemap.lock: current_commit does not match HEAD or its codemap-only parent")
    if lock.get("generated_from_commit") != codemap.get("generated_from_commit"):
        errors.append("codemap.lock: generated_from_commit differs from codemap.json")
    if lock.get("generated_at") != codemap.get("generated_at"):
        errors.append("codemap.lock: generated_at differs from codemap.json")
    if lock.get("working_tree_has_uncommitted_changes") != working_tree_dirty:
        errors.append("codemap.lock: working_tree_has_uncommitted_changes is stale")

    excluded = set(lock.get("excluded_directories", []))
    for module_path, recorded in lock.get("module_fingerprints", {}).items():
        if not module_files(module_path, excluded):
            errors.append(f"codemap.lock: fingerprint module has no files: {module_path}")
            continue
        actual = fingerprint(module_path, excluded)
        if actual != recorded.get("fingerprint"):
            errors.append(f"codemap.lock: fingerprint mismatch for {module_path}")

    return errors


if __name__ == "__main__":
    problems = validate()
    if problems:
        print("CODEMAP CHECK FAILED")
        print("\n".join(f"- {problem}" for problem in problems))
        sys.exit(1)
    print("CODEMAP CHECK PASSED")
