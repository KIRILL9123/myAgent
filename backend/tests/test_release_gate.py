import importlib.util
import sys
from pathlib import Path


def _load_release_gate():
    path = Path(__file__).parents[2] / "dev-tools" / "release_gate.py"
    spec = importlib.util.spec_from_file_location("home_agent_release_gate", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_release_gate_check_reports_pass_and_failure(tmp_path):
    gate = _load_release_gate()
    passed = gate._run_check(
        "ok", [sys.executable, "-c", "print('deterministic pass')"], tmp_path, 10
    )
    failed = gate._run_check(
        "bad", [sys.executable, "-c", "raise SystemExit(3)"], tmp_path, 10
    )

    assert passed["status"] == "passed"
    assert "deterministic pass" in passed["output"]
    assert failed["status"] == "failed"
    assert failed["return_code"] == 3


def test_release_gate_output_is_bounded():
    gate = _load_release_gate()
    output = gate._summarize_output("x" * (gate.MAX_OUTPUT_CHARS + 100), "")
    assert len(output) == gate.MAX_OUTPUT_CHARS
    assert output.startswith("…")
