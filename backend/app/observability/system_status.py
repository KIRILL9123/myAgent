import platform
import socket
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from backend.app.agent import llm
from backend.app.observability.host_diagnostics import get_host_diagnostics


def _check_endpoint(name: str, url: str, headers: dict[str, str] | None = None) -> dict:
    started = time.monotonic()
    parsed = urlparse(url)
    result = {"name": name, "url": url, "host": parsed.hostname, "port": parsed.port,
              "status": "unreachable", "latency_ms": None, "detail": None}
    try:
        request_headers = {"User-Agent": "HomeAgent-health/1.0", **(headers or {})}
        request = Request(url, headers=request_headers)
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
    provider = llm.get_active_provider()
    profiles = {item["id"]: item for item in llm.get_provider_profiles()}
    local_url = f"{llm.OLLAMA_URL}/api/tags"
    deepseek_url = f"{llm.DEEPSEEK_BASE_URL}/models"
    local = _check_endpoint("local", local_url)
    deepseek = _check_endpoint("deepseek", deepseek_url, {"Authorization": f"Bearer {llm.DEEPSEEK_API_KEY}"}) if profiles["deepseek"]["configured"] else {
        "name": "deepseek", "url": deepseek_url, "host": urlparse(deepseek_url).hostname,
        "port": urlparse(deepseek_url).port, "status": "not_configured", "latency_ms": None,
        "detail": "DEEPSEEK_API_KEY is not configured",
    }
    model = deepseek if provider == "deepseek" else local
    parsed = urlparse(model["url"])
    deepseek_parsed = urlparse(deepseek_url)
    local_parsed = urlparse(local_url)
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
        "services": {"deepseek": deepseek, "ollama": local},
        "ports": [
            _check_port(deepseek_parsed.hostname, deepseek_parsed.port or (443 if deepseek_parsed.scheme == "https" else 80)),
            _check_port(local_parsed.hostname, local_parsed.port or (443 if local_parsed.scheme == "https" else 80)),
            _check_port("127.0.0.1", 8000),
        ],
        "host": {"platform": platform.platform(), "hostname": socket.gethostname(),
                 "python": platform.python_version()},
        "host_metrics": host_metrics,
    }
