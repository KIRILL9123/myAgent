from backend.app.observability import host_diagnostics


def test_host_diagnostics_keeps_read_only_contract(monkeypatch):
    monkeypatch.setattr(host_diagnostics.platform, "system", lambda: "Windows")
    monkeypatch.setattr(host_diagnostics, "_windows_diagnostics", lambda: {
        "status": "ok", "detail": None, "generated_at": "now",
        "cpu": {"percent": 12.0, "cores": 12},
        "memory": {"total_bytes": 100, "available_bytes": 40, "used_percent": 60.0},
        "disks": [], "processes": [], "process_count": 2,
    })

    result = host_diagnostics.get_host_diagnostics()
    assert result["status"] == "ok"
    assert result["cpu"]["percent"] == 12.0
    assert result["process_count"] == 2
    assert "command" not in result
