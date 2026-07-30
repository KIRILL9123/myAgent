"""Small local comparison of Playwright/Chromium and Lightpanda.

The test intentionally uses a local page so that network variability does not
hide differences in JavaScript rendering. Lightpanda is expected to expose a
CDP endpoint on http://127.0.0.1:9222.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any

from playwright.async_api import BrowserContext, Page, async_playwright


PORT = 8765
HOST_URL = f"http://127.0.0.1:{PORT}/"
CONTAINER_URL = f"http://host.docker.internal:{PORT}/"
RUNS = int(os.environ.get("BROWSER_COMPARE_RUNS", "5"))


HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Browser comparison</title></head>
<body><main id="app"><span id="status">loading</span></main>
<script>
  setTimeout(() => {
    document.querySelector('#status').textContent = 'javascript-ready';
    document.querySelector('#app').dataset.renderedAt = String(Date.now());
  }, 250);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: Any) -> None:
        return


def start_server() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    return server


async def measure(label: str, context: BrowserContext, url: str) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    for _ in range(RUNS):
        page: Page = await context.new_page()
        started = time.perf_counter()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=10_000)
            await page.wait_for_timeout(600)
            marker = await page.locator("#status").text_content()
            html_length = len(await page.content())
            runs.append(
                {
                    "ok": marker == "javascript-ready",
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
                    "marker": marker,
                    "html_length": html_length,
                }
            )
        except Exception as exc:  # report an individual failure, keep the run going
            runs.append(
                {
                    "ok": False,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        finally:
            await page.close()

    successful = [run for run in runs if run["ok"]]
    return {
        "engine": label,
        "runs": runs,
        "success_rate": round(len(successful) / RUNS, 2),
        "average_elapsed_ms": round(
            sum(run["elapsed_ms"] for run in successful) / len(successful), 1
        )
        if successful
        else None,
    }


async def main() -> None:
    server = start_server()
    target_url = sys.argv[1] if len(sys.argv) > 1 else None
    host_target = target_url or HOST_URL
    container_target = target_url or CONTAINER_URL
    results: list[dict[str, Any]] = []
    async with async_playwright() as playwright:
        chromium = await playwright.chromium.launch(headless=True)
        try:
            results.append(
                await measure(
                    "playwright-chromium", await chromium.new_context(), host_target
                )
            )
        finally:
            await chromium.close()

        try:
            lightpanda = await playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
            try:
                context = lightpanda.contexts[0] if lightpanda.contexts else await lightpanda.new_context()
                results.append(await measure("lightpanda-cdp", context, container_target))
            finally:
                await lightpanda.close()
        except Exception as exc:
            results.append(
                {
                    "engine": "lightpanda-cdp",
                    "success_rate": 0,
                    "average_elapsed_ms": None,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    server.shutdown()
    print(
        json.dumps(
            {
                "host_url": host_target,
                "container_url": container_target,
                "runs_per_engine": RUNS,
                "results": results,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
