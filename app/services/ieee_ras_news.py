"""Scrape the public IEEE RAS news listing (HTML only)."""

from __future__ import annotations

import logging
import re
import threading
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlparse

logger = logging.getLogger(__name__)

NEWS_PAGE_URL = "https://www.ieee-ras.org/category/ras-news/"
FALLBACK_PAGE_URL = "https://www.ieee-ras.org/news/"
PAGE_URLS = (NEWS_PAGE_URL, FALLBACK_PAGE_URL)
REQUEST_TIMEOUT_SECONDS = 12
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
CACHE_TTL_SECONDS = 10 * 60
MAX_ITEMS = 18

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
HEADING_TAGS = {"h2", "h3", "h4"}

# Used only when the source card has no category/tag link.
CATEGORY_RULES = (
    ("Calls & Opportunities", ("call for", "apply", "application", "nomination", "submit", "deadline", "travel support", "ambassador")),
    ("Awards & Recognition", ("award", "awards", "elected", "fellow", "recognition", "winner", "in memoriam")),
    ("Events & Conferences", ("conference", "congress", "symposium", "workshop", "webinar", "event", "iros", "icra", "case ")),
    ("Research & Technology", ("research", "robot", "robotics", "automation", "artificial intelligence", "learning", "journal", "paper", "technology", "technical committee")),
)


class _Node:
    """Very small HTML tree node; keeps this service dependency-free."""

    def __init__(self, tag: str, attrs: list[tuple[str, str | None]] | None = None, parent: "_Node | None" = None):
        self.tag = tag.lower()
        self.attrs = dict(attrs or [])
        self.parent = parent
        self.children: list[_Node | str] = []


class _TreeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("document")
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = _Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag.lower() not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack[-1].children.append(_Node(tag, attrs, self.stack[-1]))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if data:
            self.stack[-1].children.append(data)


def _walk(node: _Node):
    for child in node.children:
        if isinstance(child, _Node):
            yield child
            yield from _walk(child)


def _text(node: _Node) -> str:
    parts: list[str] = []

    def visit(current: _Node) -> None:
        for child in current.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag not in {"script", "style", "noscript", "svg"}:
                visit(child)

    visit(node)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _classes(node: _Node) -> set[str]:
    return set((node.attrs.get("class") or "").lower().split())


def _first_descendant(node: _Node, tags: set[str]) -> _Node | None:
    for item in _walk(node):
        if item.tag in tags:
            return item
    return None


def _article_url(href: str, page_url: str) -> str | None:
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    absolute = urljoin(page_url, href)
    parsed = urlparse(absolute)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not (host == "ieee-ras.org" or host.endswith(".ieee-ras.org")):
        return None

    path = unquote(parsed.path or "/").lower().rstrip("/") or "/"
    if path in {"/", "/news", "/category/ras-news", "/category", "/search", "/component/search"}:
        return None
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        return None
    if any(part in {"category", "categories", "news_cat", "tag", "tags", "author", "page", "search", "feed", "rss"} for part in parts):
        return None
    return absolute


def _find_article_container(heading: _Node) -> _Node:
    # Prefer a card/article wrapper, but don't climb into the whole page/list.
    current = heading.parent
    hops = 0
    while current is not None and hops < 7:
        if current.tag == "article":
            return current
        class_names = _classes(current)
        if class_names.intersection({"item", "catitem", "article", "blog-item", "news-item", "item-container", "post", "card"}):
            if len(_text(current)) < 9000:
                return current
        current = current.parent
        hops += 1
    return heading.parent or heading


def _source_categories(container: _Node, page_url: str, article_href: str) -> list[str]:
    found: list[str] = []
    category_path_tokens = ("/category/", "/news_cat/", "/tag/", "/tags/")
    for node in _walk(container):
        if node.tag != "a":
            continue
        label = _text(node)
        href = urljoin(page_url, (node.attrs.get("href") or "").strip())
        path = urlparse(href).path.lower()
        parent_classes = _classes(node.parent) if node.parent else set()
        is_category = (
            any(token in path for token in category_path_tokens)
            or any("categor" in cls or cls in {"tag", "tags"} for cls in parent_classes)
        )
        if not is_category or not label or href.rstrip("/") == article_href.rstrip("/"):
            continue
        if len(label) > 55 or label.lower() in {"categories", "category", "read more", "read full article"}:
            continue
        if label not in found:
            found.append(label)
    return found[:4]


def _infer_category(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    for category, keywords in CATEGORY_RULES:
        if any(word in text for word in keywords):
            return category
    return "IEEE RAS Updates"


def _extract_description(container: _Node, title: str) -> str:
    candidates: list[str] = []
    for node in _walk(container):
        if node.tag not in {"p", "blockquote"}:
            continue
        value = _text(node)
        if len(value) >= 35 and value.casefold() != title.casefold():
            if value.lower() not in {"read more", "read full article", "read more..."}:
                candidates.append(value)
    if not candidates:
        return "Read the full story on the official IEEE RAS website."
    # The most informative short paragraph is usually the article intro.
    description = max(candidates, key=lambda item: min(len(item), 500))
    if len(description) > 300:
        description = description[:297].rsplit(" ", 1)[0] + "…"
    return description


def _extract_image(container: _Node, page_url: str) -> str:
    for node in _walk(container):
        if node.tag != "img":
            continue
        src = (node.attrs.get("data-src") or node.attrs.get("data-original") or node.attrs.get("src") or "").strip()
        if not src and node.attrs.get("srcset"):
            candidates = [piece.strip().split(" ")[0] for piece in node.attrs["srcset"].split(",") if piece.strip()]
            src = candidates[-1] if candidates else ""
        if not src or src.startswith("data:"):
            continue
        lowered = src.lower()
        if any(token in lowered for token in ("logo", "icon", "avatar", "spacer", "placeholder")):
            continue
        return urljoin(page_url, src)
    return ""


def _extract_date(container: _Node) -> str:
    for node in _walk(container):
        if node.tag == "time":
            value = (node.attrs.get("datetime") or _text(node)).strip()
            if value:
                return value

    text = _text(container)
    patterns = (
        r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0)
    return ""


def _scrape_page(html: str, page_url: str) -> list[dict[str, str | list[str]]]:
    parser = _TreeParser()
    parser.feed(html)
    parser.close()
    posts: list[dict[str, str | list[str]]] = []
    seen: set[str] = set()

    for heading in _walk(parser.root):
        if heading.tag not in HEADING_TAGS:
            continue
        title_link = _first_descendant(heading, {"a"})
        if title_link is None:
            continue
        title = _text(title_link) or _text(heading)
        href = _article_url((title_link.attrs.get("href") or "").strip(), page_url)
        if not title or not href or href in seen:
            continue
        # Don't include social/share links or generic navigation headings.
        if len(title) < 8 or title.lower() in {"latest news", "ras news", "featured articles", "latest articles"}:
            continue

        container = _find_article_container(heading)
        description = _extract_description(container, title)
        source_categories = _source_categories(container, page_url, href)
        category = source_categories[0] if source_categories else _infer_category(title, description)
        categories = source_categories or [category]
        image = _extract_image(container, page_url)
        published = _extract_date(container)

        posts.append({
            "title": title,
            "description": description,
            "image": image,
            "href": href,
            "category": category,
            "categories": categories,
            "published": published,
        })
        seen.add(href)
        if len(posts) >= MAX_ITEMS:
            break

    return posts


def _download_html(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; IEEE-RAS-NIT-Silchar-News/2.0)",
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        content_type = (response.headers.get("Content-Type") or "").lower()
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError("news page exceeded the 4 MB safety limit")
    if content_type and "html" not in content_type and "text/plain" not in content_type:
        raise ValueError(f"expected an HTML page, received {content_type}")
    return payload.decode("utf-8", errors="replace")


_cache_lock = threading.Lock()
_cache_time = 0.0
_cache_posts: list[dict[str, str | list[str]]] = []


def fetch_ieee_ras_news() -> tuple[list[dict[str, str | list[str]]], str | None]:
    """Scrape IEEE RAS news pages; return posts and an optional status note."""
    global _cache_time, _cache_posts
    now = time.monotonic()
    with _cache_lock:
        if _cache_posts and now - _cache_time < CACHE_TTL_SECONDS:
            return list(_cache_posts), None

    errors: list[str] = []
    for page_url in PAGE_URLS:
        try:
            html = _download_html(page_url)
            posts = _scrape_page(html, page_url)
            if not posts:
                raise ValueError("page downloaded but no article links matched the scraper")
            with _cache_lock:
                _cache_posts = posts
                _cache_time = time.monotonic()
            logger.info("Scraped %d IEEE RAS stories from %s", len(posts), page_url)
            return list(posts), None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            errors.append(f"{page_url}: {exc}")
            logger.warning("Unable to scrape IEEE RAS news page %s: %s", page_url, exc)

    logger.error("All IEEE RAS HTML news pages failed: %s", " | ".join(errors))
    with _cache_lock:
        if _cache_posts:
            return list(_cache_posts), "The news page could not be refreshed. Showing previously fetched articles."
    return [], "We couldn't load current IEEE RAS news. Please visit https://www.ieee-ras.org/news/ for the latest updates."
