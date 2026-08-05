import platform
import socket
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from backend.app.agent import llm
from backend.app.observability.host_diagnostics import get_host_diagnostics


def _check_endpoint(name: str, url: str) -> dict:
    started = time.monotonic()
    parsed = urlparse(url)
    result = {"name": name, "url": url, "host": parsed.hostname, "port": parsed.port,
              "status": "unreachable", "latency_ms": None, "detail": None}
    try:
        request = Request(url, headers={"User-Agent": "HomeAgent-health/1.0"})
        with urlopen(request, timeout=3) as response:
            result["status"] = "ok" if 200 <= response.status < 400 else "degraded"
            result["detail"] = f"HTTP {response.status}"
    except Exception as exc:
        result["detail"] = type(exc).__name__
    result["latency_ms"] = round((time.monotonic() - started) * 1000, 2)
    return result


def _check_port(host: str | None, port: int | None) -> dict:
    if not host or not port:
        return {"host": host, "port": port, "reachable": False}
    started = time.monotonic()
    reachable = False
    try:
        with socket.create_connection((host, port), timeout=1):
            reachable = True
    except OSError:
        pass
    return {"host": host, "port": port, "reachable": reachable,
            "latency_ms": round((time.monotonic() - started) * 1000, 2)}


def get_system_status() -> dict:
    provider = llm.LLM_PROVIDER
    bonsai_url = f"{llm.OPENAI_BASE_URL}/models"
    ollama_url = f"{llm.OLLAMA_URL}/api/tags"
    bonsai = _check_endpoint("bonsai", bonsai_url)
    ollama = _check_endpoint("ollama", ollama_url)
    model = bonsai if provider == "openai_compatible" else ollama
    parsed = urlparse(model["url"])
    bonsai_parsed = urlparse(bonsai_url)
    ollama_parsed = urlparse(ollama_url)
    host_metrics = get_host_diagnostics()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall": "ok" if model["status"] == "ok" else "degraded",
        "backend": {"status": "ok", "message": "Mira API is running"},
        "llm": {
            "provider": provider,
            "model": llm.get_model_for_role("main"),
            "endpoint": f"{parsed.scheme}://{parsed.hostname}:{parsed.port or (443 if parsed.scheme == 'https' else 80)}",
            **model,
        },
        "services": {"bonsai": bonsai, "ollama": ollama},
        "ports": [
            _check_port(bonsai_parsed.hostname, bonsai_parsed.port or (443 if bonsai_parsed.scheme == "https" else 80)),
            _check_port(ollama_parsed.hostname, ollama_parsed.port or (443 if ollama_parsed.scheme == "https" else 80)),
            _check_port("127.0.0.1", 8000),
        ],
        "host": {"platform": platform.platform(), "hostname": socket.gethostname(),
                 "python": platform.python_version()},
        "host_metrics": host_metrics,
    }
