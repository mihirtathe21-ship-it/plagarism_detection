"""
Web Search & Plagiarism Detection Engine
Uses Wikipedia API (reliable, no key) + DuckDuckGo HTML / Bing fallback (scraped).
Install: pip install requests beautifulsoup4 sentence-transformers

SPEED NOTES:
- Page fetches now run in parallel via ThreadPoolExecutor (I/O bound, so this
  is a big win — was previously one fetch at a time in a loop).
- Reduced default fan-out: fewer key sentences searched, fewer results per
  sentence, shorter network timeouts, so a slow/blocked search engine can't
  stall the whole check for many seconds.
- Bing is now skipped by default (BING_ENABLED=False) since it's the slowest
  and least reliable leg. Flip it back on if you need the extra coverage.
"""

import re
import time
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    HTTPAdapter = None
    Retry = None
    REQUESTS_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BeautifulSoup = None
    BS4_AVAILABLE = False


HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1',
}

# --- Speed knobs ---
MAX_KEY_SENTENCES = 3       # few key sentences per check to stay responsive
RESULTS_PER_SENTENCE = 3    # broader source coverage improves recall
SEARCH_TIMEOUT = 6          # enough time for several engines without stalling
FETCH_TIMEOUT = 6           # page fetch latency is kept short but stable
FETCH_WORKERS = 6           # parallel page fetches
BRAVE_ENABLED = True        # additional web coverage for better plagiarism recall
GOOGLE_ENABLED = True       # search Google as a broader web source for plagiarism checks
BING_ENABLED = False        # Bing scraping is slow/unreliable; left off by default


def _get_session():
    if requests is None or Retry is None or HTTPAdapter is None:
        raise RuntimeError("requests support is unavailable")

    s = requests.Session()
    s.headers.update(HEADERS)
    retry = Retry(total=1, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    s.mount('http://', adapter)
    s.mount('https://', adapter)
    return s


def strip_html(html: str) -> str:
    if BS4_AVAILABLE and BeautifulSoup is not None:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'noscript']):
                tag.decompose()
            return re.sub(r'\s+', ' ', soup.get_text()).strip()
        except Exception:
            pass
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).strip()


def fetch_page(url: str, timeout: int = FETCH_TIMEOUT, max_chars: int = 20000) -> str:
    if not REQUESTS_AVAILABLE:
        return _fetch_urllib(url, timeout, max_chars)
    try:
        s = _get_session()
        r = s.get(url, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        return strip_html(r.text)[:max_chars]
    except Exception:
        return ""


def _fetch_urllib(url: str, timeout: int = FETCH_TIMEOUT, max_chars: int = 20000) -> str:
    import urllib.request
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(200000)
            html = raw.decode(resp.headers.get_content_charset() or 'utf-8', errors='replace')
            return strip_html(html)[:max_chars]
    except Exception:
        return ""


def search_wikipedia(query: str, num: int = 3, log=None) -> List[Dict]:
    results = []
    try:
        s = _get_session()
        resp = s.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": num,
            },
            timeout=SEARCH_TIMEOUT,
        )
        if log:
            log(f"[wikipedia] status={resp.status_code} query={query!r}")
        data = resp.json()
        hits = data.get("query", {}).get("search", [])
        for h in hits:
            title = h.get("title", "")
            page_url = "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
            snippet = re.sub(r'<[^>]+>', '', h.get("snippet", ""))
            results.append({"url": page_url, "snippet": snippet})
        if log:
            log(f"[wikipedia] {len(results)} result(s) found")
    except Exception as e:
        if log:
            log(f"[wikipedia] EXCEPTION: {e}")
    return results[:num]


def search_duckduckgo(query: str, num: int = 5, log=None) -> List[Dict]:
    results = []
    try:
        s = _get_session()
        s.headers.update({'Referer': 'https://duckduckgo.com/'})
        resp = s.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query, "kl": "us-en"},
            timeout=SEARCH_TIMEOUT,
        )
        html = resp.text
        if log:
            log(f"[ddg] status={resp.status_code} len={len(html)} query={query!r}")

        if BS4_AVAILABLE and BeautifulSoup is not None:
            soup = BeautifulSoup(html, 'html.parser')
            result_els = soup.select('.result') or soup.select('.web-result') or soup.select('.results_links')
            if log:
                log(f"[ddg] result elements found: {len(result_els)}")
            for res in result_els[:num]:
                a = res.select_one('.result__a') or res.select_one('a.result__url') or res.find('a')
                snippet_el = res.select_one('.result__snippet')
                raw_href = a.get('href') if a is not None else ''
                href = str(raw_href or '')
                if href:
                    if 'uddg=' in href:
                        import urllib.parse as up
                        params = dict(up.parse_qsl(up.urlparse(href).query))
                        href = str(params.get('uddg', href))
                    if href.startswith('http') and 'duckduckgo.com' not in href:
                        results.append({
                            'url': href,
                            'snippet': snippet_el.get_text(strip=True) if snippet_el else '',
                        })
        else:
            urls = re.findall(r'uddg=(https?[^&"]+)', html)
            import urllib.parse as up
            for u in urls[:num]:
                u = up.unquote(u)
                if 'duckduckgo.com' not in u:
                    results.append({'url': u, 'snippet': ''})

        if not results and log:
            log("[ddg] 0 results parsed — likely blocked/CAPTCHA or markup changed")

    except Exception as e:
        if log:
            log(f"[ddg] EXCEPTION: {e}")
    return results[:num]


def search_brave(query: str, num: int = 5, log=None) -> List[Dict]:
    results = []
    try:
        import urllib.parse
        q = urllib.parse.quote_plus(query)
        url = f"https://search.brave.com/search?q={q}&source=web"

        s = _get_session()
        resp = s.get(url, timeout=SEARCH_TIMEOUT)
        html = resp.text
        if log:
            log(f"[brave] status={resp.status_code} len={len(html)} query={query!r}")

        seen = set()
        if BS4_AVAILABLE and BeautifulSoup is not None:
            soup = BeautifulSoup(html, 'html.parser')
            candidates = soup.select('a.result-header') or soup.select('a[href]')
            for el in candidates[:num * 3]:
                href = str(el.get('href') or '')
                if not href.startswith('http'):
                    continue
                if 'brave.com' in href or href in seen:
                    continue
                seen.add(href)
                snippet = ''
                parent = el.parent
                if parent:
                    snippet_el = parent.select_one('p') or parent.select_one('.snippet') or parent.select_one('span')
                    if snippet_el:
                        snippet = snippet_el.get_text(' ', strip=True)
                results.append({'url': href, 'snippet': snippet})
        else:
            urls = re.findall(r'https?://[^"\'\s<>]+', html)
            for u in urls[:num]:
                candidate = str(u)
                if 'brave.com' not in candidate and candidate not in seen:
                    seen.add(candidate)
                    results.append({'url': candidate, 'snippet': ''})

        if not results and log:
            log("[brave] 0 results parsed — search page blocked or markup changed")
    except Exception as e:
        if log:
            log(f"[brave] EXCEPTION: {e}")
    return results[:num]


def search_google(query: str, num: int = 5, log=None) -> List[Dict]:
    results = []
    try:
        import urllib.parse
        q = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={q}&num={num}"

        s = _get_session()
        resp = s.get(url, timeout=SEARCH_TIMEOUT)
        html = resp.text
        if log:
            log(f"[google] status={resp.status_code} len={len(html)} query={query!r}")

        if BS4_AVAILABLE and BeautifulSoup is not None:
            soup = BeautifulSoup(html, 'html.parser')
            seen = set()
            for link in soup.select('a[href]'):
                href = str(link.get('href') or '')
                if not href.startswith('/url?q='):
                    continue
                target = href.split('/url?q=', 1)[1].split('&', 1)[0]
                if not target.startswith('http') or 'google.com' in target or target in seen:
                    continue
                seen.add(target)
                results.append({'url': target, 'snippet': ''})
                if len(results) >= num:
                    break
        else:
            urls = re.findall(r'https?://[^"\'\s<>]+', html)
            for u in urls[:num]:
                if 'google.com' not in u:
                    results.append({'url': u, 'snippet': ''})

        if not results and log:
            log("[google] 0 results parsed — likely blocked or requires browser consent")
    except Exception as e:
        if log:
            log(f"[google] EXCEPTION: {e}")
    return results[:num]


def search_bing(query: str, num: int = 5, log=None) -> List[Dict]:
    results = []
    try:
        import urllib.parse
        q = urllib.parse.quote_plus(query)
        url = f"https://www.bing.com/search?q={q}&count={num}&setlang=en-US&cc=US"

        s = _get_session()
        resp = s.get(url, timeout=SEARCH_TIMEOUT)
        html = resp.text
        if log:
            log(f"[bing] status={resp.status_code} len={len(html)} query={query!r}")

        if BS4_AVAILABLE and BeautifulSoup is not None:
            soup = BeautifulSoup(html, 'html.parser')
            items = soup.select('li.b_algo')
            if log:
                log(f"[bing] li.b_algo found: {len(items)}")
            for li in items[:num]:
                a = li.select_one('h2 a') or li.find('a')
                href = str((a.get('href') if a is not None else '') or '')
                snippet_el = li.select_one('.b_caption p') or li.select_one('.b_lineclamp2')
                if href.startswith('http'):
                    results.append({
                        'url': href,
                        'snippet': snippet_el.get_text(strip=True) if snippet_el else '',
                    })
        else:
            urls = re.findall(r'(https?://[^<]+)', html)
            for u in urls[:num]:
                if 'bing.com' not in u:
                    results.append({'url': u.strip(), 'snippet': ''})

        if not results and log:
            log("[bing] 0 results parsed — likely blocked/consent page or markup changed")

    except Exception as e:
        if log:
            log(f"[bing] EXCEPTION: {e}")
    return results[:num]


def search_web(query: str, num: int = 5, log=None) -> List[Dict]:
    results = search_wikipedia(query, num=max(2, num // 2), log=log)

    if len(results) < num:
        ddg = search_duckduckgo(query, num, log=log)
        for r in ddg:
            if r['url'] not in {x['url'] for x in results}:
                results.append(r)

    if BRAVE_ENABLED and len(results) < num:
        brave = search_brave(query, num, log=log)
        for r in brave:
            if r['url'] not in {x['url'] for x in results}:
                results.append(r)

    if GOOGLE_ENABLED and len(results) < num:
        google = search_google(query, num, log=log)
        for r in google:
            if r['url'] not in {x['url'] for x in results}:
                results.append(r)

    if BING_ENABLED and len(results) < num:
        bing = search_bing(query, num, log=log)
        for r in bing:
            if r['url'] not in {x['url'] for x in results}:
                results.append(r)

    return results[:num]


def extract_key_sentences(text: str, max_sentences: int = 8) -> List[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    good = []
    for s in sentences:
        s = s.strip()
        words = s.split()
        if 8 <= len(words) <= 35 and len(s) >= 40:
            alpha = sum(c.isalpha() for c in s) / max(len(s), 1)
            if alpha > 0.55:
                good.append(s)
    good.sort(key=len, reverse=True)
    return good[:max_sentences]


def _fetch_and_score(url: str, snippet: str, text: str, sentence: str, log) -> Dict | None:
    """
    Fetch one candidate page and score it. Runs inside a thread pool worker,
    so `log` calls here will interleave from multiple threads — that's fine,
    it's just console/progress output.
    """
    from core.similarity_engine import (
        compute_tfidf_similarity,
        compute_ngram_overlap,
        find_matching_sentences,
    )
    from core.semantic_model import (
        compute_semantic_similarity_sentences,
        compute_combined_similarity,
    )
    from core.text_processor import extract_sentences

    log(f"Checking {_domain(url)}…")

    page_text = fetch_page(url)
    if len(page_text) < 150:
        log(f"  -> {_domain(url)}: page too short/unreadable ({len(page_text)} chars), skipping")
        return None

    total_doc_sentences = max(len(extract_sentences(text)), 1)

    semantic_matches = compute_semantic_similarity_sentences(text, page_text, top_k=15)
    lexical_matches = find_matching_sentences(text, page_text, threshold=0.55)

    merged = {}
    for m in lexical_matches:
        merged[m['index1']] = {
            'index1': m['index1'],
            'your_sentence': m['sentence1'],
            'source_sentence': m['sentence2'],
            'similarity': m['similarity'],
            'type': 'lexical',
        }
    for m in semantic_matches:
        idx = m['index1']
        if idx not in merged or m['semantic_similarity'] > merged[idx]['similarity']:
            merged[idx] = {
                'index1': idx,
                'your_sentence': m['sentence1'],
                'source_sentence': m['sentence2'],
                'similarity': m['semantic_similarity'],
                'type': 'semantic',
            }

    sentence_matches = list(merged.values())

    combined = compute_combined_similarity(text, page_text)
    combined_score = combined['combined_score'] / 100

    tfidf = combined['tfidf']
    ngram = combined['ngram']

    if sentence_matches:
        coverage = len(sentence_matches) / total_doc_sentences
        avg_sent_sim = sum(m['similarity'] for m in sentence_matches) / len(sentence_matches)

        # coverage, avg_sent_sim, combined_score are all 0-1 fractions; the
        # weights sum to 100, so this is already on a 0-100 scale — do not
        # multiply by 100 again.
        sim = round(
            coverage * 60
            + avg_sent_sim * 25
            + combined_score * 15,
            2
        )

        log(f"  -> {_domain(url)}: {len(sentence_matches)} sentence match(es), "
            f"coverage={round(coverage*100,1)}%, final_score={sim}")

        if sim > 2:
            return {
                'url': url,
                'title': _domain(url),
                'snippet': snippet or page_text[:200],
                'tfidf_score': round(tfidf['similarity'] * 100, 1),
                'ngram_score': round(ngram['overlap'] * 100, 1),
                'semantic_score': round(combined['semantic'].get('similarity', 0) * 100, 1),
                'similarity': round(sim, 1),
                'shared_terms': tfidf.get('shared_terms', [])[:8],
                'matched_sentence': sentence,
                'sentence_matches': [
                    {
                        'your_sentence': m['your_sentence'],
                        'source_sentence': m['source_sentence'],
                        'similarity': round(m['similarity'], 3),
                        'match_type': m['type'],
                    }
                    for m in sorted(sentence_matches, key=lambda x: -x['similarity'])[:10]
                ],
                'sentences_matched_count': len(sentence_matches),
                'coverage_percent': round(coverage * 100, 1),
            }
        return None
    else:
        sim = round(combined_score * 100, 2)
        log(f"  -> {_domain(url)}: no sentence-level matches; fallback score={sim}")
        if sim > 2:
            return {
                'url': url,
                'title': _domain(url),
                'snippet': snippet or page_text[:200],
                'tfidf_score': round(tfidf['similarity'] * 100, 1),
                'ngram_score': round(ngram['overlap'] * 100, 1),
                'semantic_score': round(combined['semantic'].get('similarity', 0) * 100, 1),
                'similarity': round(sim, 1),
                'shared_terms': tfidf.get('shared_terms', [])[:8],
                'matched_sentence': sentence,
                'sentence_matches': [],
                'sentences_matched_count': 0,
                'coverage_percent': 0,
            }
        return None


def check_plagiarism_online(text: str, progress_callback=None) -> List[Dict]:
    """
    Speed-optimized version:
    - Fewer key sentences searched (MAX_KEY_SENTENCES)
    - Fewer results per sentence (RESULTS_PER_SENTENCE)
    - Page fetch + scoring runs in parallel across a thread pool
    - Bing scraping off by default (slowest leg)
    """
    from core.semantic_model import get_model_status

    def log(msg):
        print(msg)
        if progress_callback:
            progress_callback(msg)

    status = get_model_status()
    log(f"[semantic] transformers_available={status['transformers_available']} "
        f"model={status.get('model_name')}")

    key_sentences = extract_key_sentences(text)
    if not key_sentences:
        key_sentences = [text[:150]]

    seen_urls = set()
    tasks = []  # (url, snippet, sentence)

    for sentence in key_sentences[:MAX_KEY_SENTENCES]:
        log(f"Searching: \"{sentence[:55]}…\"")
        results = search_web(sentence[:100], num=RESULTS_PER_SENTENCE, log=log)
        if not results:
            log("No search results at all for this sentence.")
            continue
        for r in results:
            url = r['url']
            if url in seen_urls:
                continue
            seen_urls.add(url)
            tasks.append((url, r.get('snippet', ''), sentence))

    if not tasks:
        return []

    log(f"Fetching and scoring {len(tasks)} candidate page(s) in parallel…")

    matches = []
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as executor:
        futures = {
            executor.submit(_fetch_and_score, url, snippet, text, sentence, log): url
            for url, snippet, sentence in tasks
        }
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    matches.append(result)
            except Exception as e:
                log(f"  -> worker error for {futures[future]}: {e}")

    matches.sort(key=lambda x: -x['similarity'])
    return _deduplicate(matches)[:10]


def _domain(url: str) -> str:
    m = re.search(r'https?://(?:www\.)?([^/]+)', url)
    return m.group(1) if m else url[:40]


def _deduplicate(matches: List[Dict]) -> List[Dict]:
    domain_count = {}
    out = []
    for m in matches:
        d = _domain(m['url'])
        if domain_count.get(d, 0) < 2:
            domain_count[d] = domain_count.get(d, 0) + 1
            out.append(m)
    return out
