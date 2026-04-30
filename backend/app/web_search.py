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
from app.config import SERPER_API_KEY, TAVILY_API_KEY

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
                text = soup.get_text(separator=" ", strip=True)

            # Normalize whitespace
            text = " ".join(text.split())

            return f"[Source: {url}]\n{text[:MAX_CHARS_PER_PAGE]}"
    except Exception:
        return ""

async def _fetch_pages_parallel(urls: list) -> list:
    """Fetch multiple pages in parallel with per-task timeout protection."""
    print("WEB FETCH PARALLEL")
    async with aiohttp.ClientSession() as session:
        async def _safe_fetch(url: str) -> str:
            try:
                return await asyncio.wait_for(
                    _async_fetch_page(session, url),
                    timeout=5
                )
            except asyncio.TimeoutError:
                print(f"FETCH TIMEOUT: {url}")
                return ""
        tasks = [_safe_fetch(url) for url in urls]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r and len(r) > 100]


def _search_ddgs(query: str, max_results: int = 5) -> list:
    """Run DuckDuckGo search with India region and fallback backends."""
    results = []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(
                query,
                region="in-en",
                safesearch="moderate",
                max_results=max_results
            ))
    except Exception:
        pass

    if not results:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    query,
                    backend="html",
                    region="in-en",
                    safesearch="moderate",
                    max_results=max_results
                ))
        except Exception:
            pass

    return results


def _search_serper(query: str, max_results: int = 5) -> list:
    """Google India search using Serper.dev API. Returns empty if no API key."""
    if not SERPER_API_KEY:
        return []
    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json",
            },
            json={"q": query, "gl": "in", "hl": "en"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"SERPER SEARCH ERROR: {e}")
        return []

    results = []
    for item in data.get("organic", []):
        if len(results) >= max_results:
            break
        title = item.get("title", "")
        href = item.get("link", "")
        body = item.get("snippet", "")
        if not title and not body:
            continue
        # Normalize keys to match existing format (href/body/title)
        results.append({"title": title, "body": body, "href": href})

    return results


def _search_tavily(query: str, max_results: int = 5) -> list:
    """Search using Tavily API — optimized for LLM/RAG. Returns empty if no API key."""
    if not TAVILY_API_KEY:
        return []
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=False,
        )
    except Exception as e:
        print(f"TAVILY SEARCH ERROR: {e}")
        return []

    results = []
    for item in response.get("results", []):
        if len(results) >= max_results:
            break
        title = item.get("title", "")
        href = item.get("url", "")
        body = item.get("content", "")
        if not title and not body:
            continue
        # Normalize keys to match existing format (href/body/title)
        results.append({"title": title, "body": body, "href": href})

    if results:
        print(f"[TAVILY] Found {len(results)} results")
    return results


# Indian domain ranking boost
INDIAN_DOMAINS = [
    ".in",
    "ndtv.com",
    "timesofindia",
    "hindustantimes",
    "moneycontrol",
    "cricbuzz",
    "espncricinfo",
    "indianexpress",
    "livemint",
    "thehindu",
]


def _domain_boost(url: str) -> int:
    """Give a ranking boost score to Indian domains."""
    score = 0
    url_lower = url.lower()
    for d in INDIAN_DOMAINS:
        if d in url_lower:
            score += 2
    return score


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


def _deduplicate_results(results: list) -> list:
    """Remove duplicate URLs from search results while preserving order."""
    unique = {}
    for r in results:
        url = r.get("href", "")
        if url and url not in unique:
            unique[url] = r
    return list(unique.values())


def _search_web(query: str, max_results: int = 5) -> list:
    print(f"[SEARCH] Searching query: {query}")
    print(f"[SEARCH] Using India region search")

    for candidate in _query_variants(query):
        # Priority 1: Serper (Google India) — best quality
        if SERPER_API_KEY:
            try:
                results = _search_serper(candidate, max_results=max_results)
                if results:
                    results = _deduplicate_results(results)
                    results.sort(key=lambda x: _domain_boost(x.get("href", "")), reverse=True)
                    print(f"[SEARCH] Serper returned {len(results)} results")
                    return results[:max_results]
            except Exception:
                pass
            print(f"[SEARCH] Serper failed for: {candidate}")

        # Priority 2: Tavily — LLM-optimized search
        if TAVILY_API_KEY:
            try:
                results = _search_tavily(candidate, max_results=max_results)
                if results:
                    results = _deduplicate_results(results)
                    results.sort(key=lambda x: _domain_boost(x.get("href", "")), reverse=True)
                    print(f"[SEARCH] Tavily returned {len(results)} results")
                    return results[:max_results]
            except Exception:
                pass
            print(f"[SEARCH] Tavily failed for: {candidate}")

        # Priority 3: DuckDuckGo (India region) — free fallback
        try:
            results = _search_ddgs(candidate, max_results=max_results)
            if results:
                results = _deduplicate_results(results)
                results.sort(key=lambda x: _domain_boost(x.get("href", "")), reverse=True)
                print(f"[SEARCH] DDGS returned {len(results)} results")
                return results[:max_results]
        except Exception:
            pass
        print(f"[SEARCH] DDGS failed for: {candidate}")

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

    # Detect "yesterday" (and common misspellings) or "last/recent/previous match"
    yesterday_keywords = ["last match", "recent match", "previous match", "yesterday match"]
    mentions_yesterday = bool(re.search(r"yest[a-z]*day", query.lower())) or any(k in query.lower() for k in yesterday_keywords)
    mentions_today = any(t in lowered_tokens for t in {"today", "live", "current", "now"})

    if mentions_yesterday:
        # Replace any yesterday-like token with the actual date
        keyword_tokens = [t for t in keyword_tokens if not (re.match(r"yest[a-z]*day", t.lower()) or t.lower() in ["last", "recent", "previous"])]
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


def _score_page(query: str, text: str) -> int:
    """Score page relevance by counting query keyword matches in text."""
    score = 0
    query_words = query.lower().split()
    text_lower = text.lower()
    for word in query_words:
        if len(word) > 2 and word in text_lower:
            score += 1
    return score


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
    for i, r in enumerate(results, 1):
        body = r.get("body", "")
        title = r.get("title", "")
        href = r.get("href", "")
        if body:
            if href:
                snippets.append(f"Source {i}: {title} ({href})\n{body}")
            else:
                snippets.append(f"Source {i}: {title}\n{body}")

    # Fetch full page content from top URLs
    urls_to_fetch = []
    for r in results:
        if len(urls_to_fetch) >= MAX_PAGES_TO_FETCH:
            break
        url = r.get("href", "")
        if url:
            urls_to_fetch.append(url)
            
    # Add a short delay to allow search results to stabilize/simulated loading wait
    print(f"WAITING 1.5s FOR WEB CONTENT TO LOAD...")
    import time
    time.sleep(1.5)
            
    fetched_pages = asyncio.run(_fetch_pages_parallel(urls_to_fetch))

    # Rank fetched pages by relevance to original query
    if fetched_pages and len(fetched_pages) > 1:
        fetched_pages.sort(key=lambda page_text: _score_page(query, page_text), reverse=True)
        fetched_pages = fetched_pages[:3]  # Keep top 3 ranked pages
        print(f"PAGES RANKED BY RELEVANCE: {len(fetched_pages)} pages kept")

    # Combine: numbered snippets first, then ranked page content
    all_parts = []
    if snippets:
        all_parts.append("--- Search Snippets ---\n" + "\n\n".join(snippets))
    if fetched_pages:
        detailed_parts = []
        for i, page in enumerate(fetched_pages, 1):
            detailed_parts.append(f"--- Detailed Source {i} ---\n{page}")
        all_parts.append("\n\n".join(detailed_parts))

    return "\n\n".join(all_parts) if all_parts else ""
