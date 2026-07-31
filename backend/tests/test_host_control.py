from pathlib import Path


def test_host_control_capabilities_are_restricted(tmp_path, monkeypatch):
    from backend.app.host_control import host_control_service as service

    monkeypatch.setattr(service, "PROJECT_ROOT", tmp_path)
    capabilities = service.get_capabilities()
    assert capabilities["actions"]["get_host_diagnostics"]["permission"] == "green"
    assert capabilities["actions"]["open_url"]["permission"] == "red"
    assert "No arbitrary shell commands" in capabilities["restrictions"]


def test_host_control_rejects_unsafe_targets(tmp_path, monkeypatch):
    from backend.app.host_control import host_control_service as service

    monkeypatch.setattr(service, "PROJECT_ROOT", tmp_path)
    assert service.execute("open_url", "javascript:alert(1)")["status"] == "error"
    outside = Path(tmp_path).parent / "outside.txt"
    outside.write_text("no", encoding="utf-8")
    result = service.execute("open_path", str(outside))
    assert result["status"] == "error"
    assert "разрешённых" in result["message"]


def test_host_control_opens_only_allowed_existing_path(tmp_path, monkeypatch):
    from backend.app.host_control import host_control_service as service

    monkeypatch.setattr(service, "PROJECT_ROOT", tmp_path)
    target = tmp_path / "notes.txt"
    target.write_text("safe", encoding="utf-8")
    opened: list[Path] = []
    monkeypatch.setattr(service, "_open_path", lambda path: opened.append(path))
    result = service.execute("open_path", str(target))
    assert result["status"] == "success"
    assert opened == [target.resolve()]
