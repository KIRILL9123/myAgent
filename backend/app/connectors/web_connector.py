"""Read-only, policy-constrained access to public web content.

HTTP is the cheap default. JavaScript rendering is optional and uses a local
Lightpanda CDP endpoint when available, then Playwright/Chromium as fallback.
The returned page text is deliberately treated as untrusted by the agent.
"""

from __future__ import annotations

import json
import logging
import os
import re
import socket
from datetime import datetime, timezone
from html.parser import HTMLParser
from ipaddress import ip_address
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlsplit

import httpx

from backend.app.connectors.price_extractor import extract_price_info


HTTP_TIMEOUT_SECONDS = float(os.getenv("WEB_HTTP_TIMEOUT_SECONDS", "10"))
BROWSER_TIMEOUT_MS = int(os.getenv("WEB_BROWSER_TIMEOUT_MS", "12000"))
MAX_RESPONSE_BYTES = int(os.getenv("WEB_MAX_RESPONSE_BYTES", "524288"))
MAX_TEXT_CHARS = int(os.getenv("WEB_MAX_TEXT_CHARS", "12000"))
MAX_REDIRECTS = 3
MAX_CACHE_ITEMS = 64
CACHE_TTL_SECONDS = 120
LIGHTPANDA_CDP_URL = os.getenv("WEB_LIGHTPANDA_CDP_URL", "http://127.0.0.1:9222")
SEARCH_URL = "https://html.duckduckgo.com/html/"
SEARCH_REGION = os.getenv("WEB_SEARCH_REGION", "de-de")
logger = logging.getLogger(__name__)

_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_search_snippet_cache: dict[str, tuple[float, dict[str, str]]] = {}

_PRODUCT_QUERY_MAPPINGS = (
    (re.compile(r"\b(?:айфон|айфоны)\b", re.IGNORECASE), "iPhone"),
    (re.compile(r"\b(?:пс\s*5|пс5|плейстейшен\s*5|плейстейшн\s*5)\b", re.IGNORECASE), "PlayStation 5"),
    (re.compile(r"\b(?:наушники|беспроводные\s+наушники)\b", re.IGNORECASE), "Kopfhörer"),
)
_GERMAN_REGION_TERMS = ("germany", "deutschland", "германи", "германия", "немец")


class WebAccessError(RuntimeError):
    """Expected, user-safe web access failure."""


class WebHTTPError(WebAccessError):
    def __init__(self, status_code: int, url: str) -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(f"Сайт вернул HTTP {status_code}.")


def _configured_domains() -> set[str]:
    raw = os.getenv("WEB_ALLOWED_DOMAINS", "")
    return {item.strip().lower().lstrip(".") for item in raw.split(",") if item.strip()}


def _validate_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise WebAccessError("Разрешены только HTTP и HTTPS ссылки.")
    if parsed.username or parsed.password:
        raise WebAccessError("Ссылки с логином или паролем запрещены.")
    if not parsed.hostname:
        raise WebAccessError("У ссылки отсутствует домен.")

    hostname = parsed.hostname.rstrip(".").lower()
    allowed = _configured_domains()
    if allowed and not any(hostname == domain or hostname.endswith(f".{domain}") for domain in allowed):
        raise WebAccessError(f"Домен не входит в разрешённый список: {hostname}")

    try:
        addresses = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except OSError as exc:
        raise WebAccessError(f"Не удалось определить адрес домена: {hostname}") from exc
    for address in addresses:
        resolved = ip_address(address[4][0])
        if (
            resolved.is_private
            or resolved.is_loopback
            or resolved.is_link_local
            or resolved.is_reserved
            or resolved.is_multicast
            or resolved.is_unspecified
        ):
            raise WebAccessError("Доступ к локальным и приватным сетям запрещён.")
    return url.strip()


def _cache_get(key: str) -> dict[str, Any] | None:
    cached = _cache.get(key)
    if not cached:
        return None
    created_at, value = cached
    if (datetime.now(timezone.utc).timestamp() - created_at) > CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    result = dict(value)
    result["cached"] = True
    return result


def _cache_put(key: str, value: dict[str, Any]) -> None:
    if len(_cache) >= MAX_CACHE_ITEMS:
        oldest = min(_cache, key=lambda item: _cache[item][0])
        _cache.pop(oldest, None)
    _cache[key] = (datetime.now(timezone.utc).timestamp(), dict(value))


def _download(url: str) -> tuple[str, str, bytes]:
    current_url = _validate_url(url)
    headers = {
        "User-Agent": "HomeAgent/1.0 (read-only web access)",
        "Accept": "text/html,application/xhtml+xml,application/json,text/plain;q=0.9,*/*;q=0.5",
    }
    for _ in range(MAX_REDIRECTS + 1):
        current_url = _validate_url(current_url)
        try:
            with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=False, headers=headers) as client:
                with client.stream("GET", current_url) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise WebAccessError("Сайт вернул перенаправление без адреса.")
                        current_url = urljoin(current_url, location)
                        continue
                    if response.status_code >= 400:
                        raise WebHTTPError(response.status_code, current_url)
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAX_RESPONSE_BYTES:
                            raise WebAccessError("Ответ сайта слишком большой для безопасной обработки.")
                        chunks.append(chunk)
                    return current_url, response.headers.get("content-type", ""), b"".join(chunks)
        except httpx.TimeoutException as exc:
            raise WebAccessError("Сайт не ответил вовремя.") from exc
        except httpx.HTTPError as exc:
            raise WebAccessError("Не удалось подключиться к сайту.") from exc
    raise WebAccessError("Слишком много перенаправлений.")


def normalize_search_query(query: str) -> str:
    """Normalize common RU product terms while keeping unknown text intact."""
    normalized = re.sub(r"\s+", " ", (query or "").strip())
    for pattern, replacement in _PRODUCT_QUERY_MAPPINGS:
        normalized = pattern.sub(replacement, normalized)

    lowered = normalized.lower()
    if not any(term in lowered for term in _GERMAN_REGION_TERMS):
        normalized = f"{normalized} Deutschland"
    elif "германи" in lowered or "германия" in lowered:
        normalized = re.sub(r"германи(?:я|и)?", "Deutschland", normalized, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", normalized).strip()


def _remember_search_snippet(item: dict[str, str]) -> None:
    url = item.get("url", "")
    if not url:
        return
    if len(_search_snippet_cache) >= MAX_CACHE_ITEMS:
        oldest = min(_search_snippet_cache, key=lambda key: _search_snippet_cache[key][0])
        _search_snippet_cache.pop(oldest, None)
    _search_snippet_cache[url] = (datetime.now(timezone.utc).timestamp(), dict(item))


def _search_snippet_for_url(url: str) -> dict[str, str] | None:
    cached = _search_snippet_cache.get(url)
    if not cached:
        return None
    created_at, item = cached
    if datetime.now(timezone.utc).timestamp() - created_at > CACHE_TTL_SECONDS:
        _search_snippet_cache.pop(url, None)
        return None
    return dict(item)


class _PageTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self._title_depth = 0
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self._title_depth += 1
        if tag.lower() in {"script", "style", "noscript", "svg", "template"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._title_depth = max(0, self._title_depth - 1)
        if tag.lower() in {"script", "style", "noscript", "svg", "template"}:
            self._ignored_depth = max(0, self._ignored_depth - 1)

    def handle_data(self, data: str) -> None:
        clean = re.sub(r"\s+", " ", data).strip()
        if not clean or self._ignored_depth:
            return
        if self._title_depth:
            self.title_parts.append(clean)
        else:
            self.text_parts.append(clean)


def _decode(body: bytes, content_type: str) -> str:
    match = re.search(r"charset=([\w-]+)", content_type, flags=re.IGNORECASE)
    encodings = [match.group(1)] if match else []
    encodings.extend(["utf-8", "cp1252"])
    for encoding in encodings:
        try:
            return body.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")


def _parse_page(body: bytes, content_type: str) -> tuple[str, str, bool]:
    text_body = _decode(body, content_type)
    if "html" in content_type.lower() or "<html" in text_body[:1000].lower():
        parser = _PageTextParser()
        parser.feed(text_body)
        title = " ".join(parser.title_parts).strip()
        content = "\n".join(parser.text_parts)
        has_javascript = bool(re.search(r"<script\b", text_body, flags=re.IGNORECASE))
    else:
        title = ""
        content = text_body
        has_javascript = False
    return title, content[:MAX_TEXT_CHARS], has_javascript


def _source(url: str, method: str, retrieved_at: str) -> dict[str, str]:
    return {
        "provider": "Web",
        "url": url,
        "method": method,
        "retrieved_at": retrieved_at,
    }


def _http_fetch(url: str) -> dict[str, Any]:
    final_url, content_type, body = _download(url)
    title, content, has_javascript = _parse_page(body, content_type)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    result = {
        "status": "success",
        "url": url,
        "final_url": final_url,
        "title": title,
        "content": content,
        "content_type": content_type,
        "content_truncated": len(content) >= MAX_TEXT_CHARS,
        "has_javascript": has_javascript,
        "source": _source(final_url, "http", retrieved_at),
        "retrieved_at": retrieved_at,
    }
    result["price_info"] = extract_price_info(f"{title}\n{content}", final_url)
    return result


def _browser_fetch(url: str, mode: str) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise WebAccessError("Браузерный fallback не установлен на сервере.") from exc

    with sync_playwright() as playwright:
        browser = None
        try:
            if mode in {"auto", "lightpanda"}:
                try:
                    browser = playwright.chromium.connect_over_cdp(LIGHTPANDA_CDP_URL, timeout=2500)
                    method = "lightpanda-cdp"
                except Exception as exc:
                    if mode == "lightpanda":
                        raise WebAccessError("Lightpanda CDP недоступен.") from exc
            if browser is None:
                if mode == "lightpanda":
                    raise WebAccessError("Lightpanda CDP недоступен.")
                browser = playwright.chromium.launch(headless=True)
                method = "playwright-chromium"

            context = browser.new_context()

            def route_guard(route: Any, _request: Any) -> None:
                try:
                    _validate_url(route.request.url)
                    route.continue_()
                except WebAccessError:
                    route.abort()

            try:
                context.route("**/*", route_guard)
            except Exception:
                pass

            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT_MS)
            page.wait_for_timeout(500)
            final_url = _validate_url(page.url)
            title = page.title()
            content = page.locator("body").inner_text(timeout=3000)
            content = re.sub(r"\n{3,}", "\n\n", content).strip()[:MAX_TEXT_CHARS]
            retrieved_at = datetime.now(timezone.utc).isoformat()
            result = {
                "status": "success",
                "url": url,
                "final_url": final_url,
                "title": title,
                "content": content,
                "content_type": "text/html",
                "content_truncated": len(content) >= MAX_TEXT_CHARS,
                "source": _source(final_url, method, retrieved_at),
                "retrieved_at": retrieved_at,
            }
            result["price_info"] = extract_price_info(f"{title}\n{content}", final_url)
            return result
        except WebAccessError:
            raise
        except Exception as exc:
            raise WebAccessError(f"Браузер не смог открыть страницу: {type(exc).__name__}") from exc
        finally:
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass


class _SearchParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._field: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        classes = set((attrs_map.get("class") or "").split())
        if tag == "a" and "result__a" in classes:
            href = attrs_map.get("href", "")
            parsed = urlsplit(href)
            query_url = parse_qs(parsed.query).get("uddg", [href])[0]
            self._current = {"url": unquote(query_url), "title": "", "snippet": ""}
            self._field = "title"
        elif self._current and classes.intersection({"result__snippet", "result__snippet_link"}):
            self._field = "snippet"

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current and self._field == "title":
            self._field = None
        if self._current and self._field == "snippet" and tag in {"a", "div", "td"}:
            self.results.append(self._current)
            self._current = None
            self._field = None

    def handle_data(self, data: str) -> None:
        if self._current and self._field:
            clean = re.sub(r"\s+", " ", data).strip()
            if clean:
                self._current[self._field] += (" " if self._current[self._field] else "") + clean


def web_fetch(url: str, render_js: bool = False, browser_mode: str = "auto") -> dict[str, Any]:
    """Fetch a public URL as read-only text, optionally rendering JavaScript."""
    try:
        url = _validate_url(url)
    except WebAccessError as exc:
        return {"status": "error", "message": str(exc)}
    if browser_mode not in {"auto", "http", "lightpanda", "chromium"}:
        return {"status": "error", "message": "Недопустимый режим браузера."}

    cache_key = f"fetch:{url}:{render_js}:{browser_mode}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    http_result: dict[str, Any] | None = None
    try:
        http_result = _http_fetch(url)
        needs_browser = render_js or (
            http_result.get("has_javascript") and len(http_result.get("content", "")) < 300
        )
        if browser_mode != "http" and needs_browser:
            try:
                browser_result = _browser_fetch(url, browser_mode)
                _cache_put(cache_key, browser_result)
                return browser_result
            except WebAccessError as exc:
                http_result["warning"] = f"JavaScript-режим недоступен: {exc}"
        _cache_put(cache_key, http_result)
        return http_result
    except WebHTTPError as exc:
        if exc.status_code == 403:
            snippet = _search_snippet_for_url(url)
            if snippet:
                retrieved_at = datetime.now(timezone.utc).isoformat()
                content = snippet.get("snippet", "")
                return {
                    "status": "success",
                    "url": url,
                    "final_url": url,
                    "title": snippet.get("title", ""),
                    "content": content,
                    "content_type": "text/plain",
                    "content_truncated": False,
                    "source": _source(url, "search-snippet-fallback", retrieved_at),
                    "retrieved_at": retrieved_at,
                    "source_blocked": True,
                    "source_status": 403,
                    "price_info": extract_price_info(
                        f"{snippet.get('title', '')}\n{content}", url
                    ),
                }
            return {
                "status": "error",
                "message": str(exc),
                "url": url,
                "source_blocked": True,
                "source_status": 403,
            }
        if browser_mode != "http":
            try:
                browser_result = _browser_fetch(url, browser_mode)
                _cache_put(cache_key, browser_result)
                return browser_result
            except WebAccessError as browser_exc:
                return {"status": "error", "message": f"Web fetch failed: {exc}; fallback: {browser_exc}"}
        return {"status": "error", "message": str(exc)}
    except WebAccessError as exc:
        if browser_mode != "http":
            try:
                browser_result = _browser_fetch(url, browser_mode)
                _cache_put(cache_key, browser_result)
                return browser_result
            except WebAccessError as browser_exc:
                return {"status": "error", "message": f"Не удалось получить страницу: {exc}; fallback: {browser_exc}"}
        return {"status": "error", "message": str(exc)}


def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the public web and return a small list of source links."""
    normalized_query = normalize_search_query(query)
    if len(normalized_query) < 2:
        return {"status": "error", "message": "Укажите поисковый запрос."}
    max_results = max(1, min(max_results, 10))
    logger.info("web_search.normalized_query=%r original_query=%r", normalized_query, query)
    search_url = f"{SEARCH_URL}?q={quote_plus(normalized_query)}&kl={quote_plus(SEARCH_REGION)}"
    try:
        final_url, content_type, body = _download(search_url)
        parser = _SearchParser()
        parser.feed(_decode(body, content_type))
        results = [item for item in parser.results if item.get("url", "").startswith(("http://", "https://"))][:max_results]
        enriched_results = []
        for item in results:
            item_copy = dict(item)
            item_copy["price_info"] = extract_price_info(
                f"{item_copy.get('title', '')}\n{item_copy.get('snippet', '')}",
                item_copy.get("url", ""),
            )
            _remember_search_snippet(item_copy)
            enriched_results.append(item_copy)
        retrieved_at = datetime.now(timezone.utc).isoformat()
        return {
            "status": "success",
            "query": normalized_query,
            "original_query": query,
            "results": enriched_results,
            "source": _source(final_url, "duckduckgo-html", retrieved_at),
            "retrieved_at": retrieved_at,
        }
    except WebAccessError as exc:
        return {"status": "error", "message": f"Поиск не выполнен: {exc}"}
