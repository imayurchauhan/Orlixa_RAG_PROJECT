import datetime
import asyncio
import aiohttp
import base64
import re
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, quote_plus, urlparse
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from langchain_core.tools import tool

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
MAX_CHARS_PER_PAGE = 2000
MAX_PAGES_TO_FETCH = 3
_QUERY_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "give",
    "i",
    "in",
    "is",
    "me",
    "of",
    "on",
    "please",
    "scorecard",
    "search",
    "show",
    "tell",
    "the",
    "to",
    "update",
    "what",
    "who",
    "won",
    "result",
    "yesterday",
}


async def _async_fetch_page(session: aiohttp.ClientSession, url: str) -> str:
    """Fetch a URL asynchronously and extract clean readable text."""
    try:
        async with session.get(url, headers=HEADERS, timeout=5) as resp:
            resp.raise_for_status()
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")

            # Remove unwanted elements
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "form", "noscript"]):
                tag.decompose()

            # Extract paragraph text
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

            if not text:
                text = soup.get_text(separator="\n", strip=True)

            return f"[Source: {url}]\n{text[:MAX_CHARS_PER_PAGE]}"
    except Exception:
        return ""

async def _fetch_pages_parallel(urls: list) -> list:
    print("WEB FETCH PARALLEL")
    async with aiohttp.ClientSession() as session:
        tasks = [_async_fetch_page(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r and len(r) > 100]


def _search_ddgs(query: str, max_results: int = 5) -> list:
    """Run DuckDuckGo search with fallback backends."""
    results = []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception:
        pass

    if not results:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, backend="html", max_results=max_results))
        except Exception:
            pass

    return results


def _decode_bing_redirect(url: str) -> str:
    try:
        parsed = urlparse(url)
        if "bing.com" not in parsed.netloc:
            return url
        encoded = parse_qs(parsed.query).get("u", [""])[0]
        if not encoded.startswith("a1"):
            return url
        payload = encoded[2:]
        payload += "=" * (-len(payload) % 4)
        return base64.b64decode(payload).decode("utf-8")
    except Exception:
        return url


def _search_bing_html(query: str, max_results: int = 5) -> list:
    """Fallback HTML scraping for Bing search results."""
    try:
        response = requests.get(
            f"https://www.bing.com/search?q={quote_plus(query)}",
            headers=HEADERS,
            timeout=10,
        )
        response.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    parsed_results = []
    for item in soup.select("li.b_algo"):
        if len(parsed_results) >= max_results:
            break
        link = item.select_one("h2 a")
        if not link:
            continue
        href = _decode_bing_redirect(link.get("href", ""))
        title = link.get_text(" ", strip=True)
        snippet_node = item.select_one(".b_caption p")
        body = snippet_node.get_text(" ", strip=True) if snippet_node else ""
        if not title and not body:
            continue
        parsed_results.append({"title": title, "body": body, "href": href})

    return parsed_results


def _search_bing_rss(query: str, max_results: int = 5) -> list:
    """Reliable fallback using Bing's RSS search feed."""
    try:
        response = requests.get(
            f"https://www.bing.com/search?format=rss&q={quote_plus(query)}",
            headers=HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        root = ET.fromstring(response.text)
    except Exception:
        return []

    parsed_results = []
    for item in root.findall("./channel/item"):
        if len(parsed_results) >= max_results:
            break
        title = (item.findtext("title") or "").strip()
        href = (item.findtext("link") or "").strip()
        body = (item.findtext("description") or "").strip()
        if not title and not body:
            continue
        parsed_results.append({"title": title, "body": body, "href": href})

    return parsed_results


def _search_web(query: str, max_results: int = 5) -> list:
    for candidate in _query_variants(query):
        results = _search_ddgs(candidate, max_results=max_results)
        if results:
            return results

        print(f"DDGS SEARCH FAILED FOR: {candidate}; FALLING BACK TO BING RSS")
        results = _search_bing_rss(candidate, max_results=max_results)
        if results:
            return results

        print(f"BING RSS FAILED FOR: {candidate}; FALLING BACK TO BING HTML")
        results = _search_bing_html(candidate, max_results=max_results)
        if results:
            return results

    return []


def _query_variants(query: str) -> list:
    variants = []
    seen = set()

    def add(candidate: str):
        normalized = " ".join(candidate.split())
        if not normalized:
            return
        key = normalized.lower()
        if key in seen:
            return
        seen.add(key)
        variants.append(normalized)

    # Compute useful date strings once
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    yesterday_str = yesterday.strftime("%B %d %Y")   # e.g. "April 27 2026"
    today_str     = today.strftime("%B %d %Y")

    add(query)

    stripped = re.sub(r"[\"'`]+", " ", query)
    stripped = re.sub(r"[^\w\s-]", " ", stripped)
    add(stripped)

    tokens = re.findall(r"[A-Za-z0-9]+", stripped)
    keyword_tokens = [token for token in tokens if token.lower() not in _QUERY_STOPWORDS]
    lowered_tokens = {token.lower() for token in keyword_tokens}

    # Detect "yesterday" (and common misspellings like "yeasterday")
    mentions_yesterday = bool(re.search(r"yest[a-z]*day", query.lower()))
    mentions_today = any(t in lowered_tokens for t in {"today", "live", "current", "now"})

    if mentions_yesterday:
        # Replace any yesterday-like token with the actual date
        keyword_tokens = [t for t in keyword_tokens if not re.match(r"yest[a-z]*day", t.lower())]
        keyword_tokens.append(yesterday_str)
    elif mentions_today and "today" not in lowered_tokens:
        keyword_tokens.append(today_str)

    if keyword_tokens:
        add(" ".join(keyword_tokens))

    # IPL-specific fallback variants
    if "ipl" in stripped.lower():
        if mentions_yesterday:
            add(f"IPL match result {yesterday_str}")
            add(f"IPL yesterday match winner")
        else:
            add(f"IPL match result {today_str}")
            add("IPL live score today")

    return variants


@tool
def web_search_tool(query: str) -> str:
    """Search the web for live information."""
    today = datetime.date.today().strftime("%B %d, %Y")
    print(f"WEB SEARCH TRIGGERED: {query}")
    
    # Check if query is a direct URL
    if query.strip().startswith(("http://", "https://")):
        print(f"DIRECT URL DETECTED: {query.strip()}")
        async def fetch_one(url):
            async with aiohttp.ClientSession() as session:
                return await _async_fetch_page(session, url)
        
        text = asyncio.run(fetch_one(query.strip()))
        if text:
            return f"--- Direct Page Content ---\n{text}"
    
    search_query = f"{query} {today}"
    print(f"SEARCH QUERY: {search_query}")
    results = _search_web(search_query, max_results=5)

    if not results:
        # Retry without date in case it narrows results too much
        results = _search_web(query, max_results=5)

    if not results:
        return ""

    # Collect snippet text from search result bodies
    snippets = []
    for r in results:
        body = r.get("body", "")
        title = r.get("title", "")
        href = r.get("href", "")
        if body:
            if href:
                snippets.append(f"{title} ({href}): {body}")
            else:
                snippets.append(f"{title}: {body}")

    # Fetch full page content from top URLs
    urls_to_fetch = []
    for r in results:
        if len(urls_to_fetch) >= MAX_PAGES_TO_FETCH:
            break
        url = r.get("href", "")
        if url:
            urls_to_fetch.append(url)
            
    fetched_pages = asyncio.run(_fetch_pages_parallel(urls_to_fetch))

    # Combine: snippets first, then full page content
    all_parts = []
    if snippets:
        all_parts.append("--- Search Snippets ---\n" + "\n\n".join(snippets))
    if fetched_pages:
        all_parts.append("--- Detailed Content ---\n" + "\n\n".join(fetched_pages))

    return "\n\n".join(all_parts) if all_parts else ""
