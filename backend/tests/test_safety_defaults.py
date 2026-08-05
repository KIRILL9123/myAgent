from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[2]


def _env_example() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def test_env_example_defaults_to_local_dry_run():
    values = _env_example()

    assert values["EXECUTION_MODE"] == "dry_run"
    assert values["CALENDAR_PROVIDER"] == "local"
    assert values["CALENDAR_ALLOW_WRITES"] == "false"
    assert values["TELEGRAM_ALLOW_NOTIFICATIONS"] == "false"
    assert values["SUBSCRIPTION_EMAIL_SCAN_ENABLED"] == "false"
    assert values["HOME_AGENT_API_KEY"] == ""


def test_pytest_does_not_collect_manual_integration_scripts():
    config = (PROJECT_ROOT / "pytest.ini").read_text(encoding="utf-8")

    assert 'testpaths = ["backend/tests"]' in config
    assert "norecursedirs = dev-tools" in config


def test_manual_credential_check_does_not_print_values():
    source = (PROJECT_ROOT / "dev-tools" / "test_gmail.py").read_text(encoding="utf-8")

    assert "repr(os.getenv" not in source
    assert 'print("GMAIL_APP_PASSWORD"' not in source
    assert "Configured credential fields" in source
