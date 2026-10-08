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
from pathlib import Path
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
BING_ENABLED = True         # use every available provider for broader coverage


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
        if 'application/pdf' in r.headers.get('Content-Type', '').lower() or url.lower().split('?')[0].endswith('.pdf'):
            from core.pdf_extractor import extract_text_from_pdf_bytes
            extracted, _ = extract_text_from_pdf_bytes(r.content)
            return extracted[:max_chars]
        return strip_html(r.text)[:max_chars]
    except Exception:
        return ""


def _fetch_urllib(url: str, timeout: int = FETCH_TIMEOUT, max_chars: int = 20000) -> str:
    import urllib.request
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(200000)
            content_type = resp.headers.get('Content-Type', '').lower()
            if 'application/pdf' in content_type or url.lower().split('?')[0].endswith('.pdf'):
                from core.pdf_extractor import extract_text_from_pdf_bytes
                extracted, _ = extract_text_from_pdf_bytes(raw)
                return extracted[:max_chars]
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


def search_openalex(query: str, num: int = 3, log=None) -> List[Dict]:
    """Find scholarly works by title using OpenAlex's public API."""
    results = []
    try:
        s = _get_session()
        resp = s.get(
            "https://api.openalex.org/works",
            params={"search": query, "per-page": num},
            timeout=SEARCH_TIMEOUT,
        )
        if log:
            log(f"[openalex] status={resp.status_code} query={query!r}")
        resp.raise_for_status()
        for work in resp.json().get("results", []):
            location = work.get("best_oa_location") or work.get("primary_location") or {}
            pdf_url = (location.get("pdf_url") or "").strip()
            landing_url = (location.get("landing_page_url") or "").strip()
            doi_url = (work.get("doi") or "").strip()
            url = pdf_url or landing_url or doi_url
            if not url:
                continue
            title = re.sub(r"\s+", " ", str(work.get("title") or "")).strip()
            authors = ", ".join(
                str(author.get("author", {}).get("display_name") or "")
                for author in work.get("authorships", [])[:3]
            )
            results.append({
                "url": url,
                "snippet": f"{title}. Authors: {authors}" if authors else title,
                "title": title,
                "source_type": "scholarly_paper",
            })
    except Exception as e:
        if log:
            log(f"[openalex] EXCEPTION: {e}")
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
    providers = [
        ('wikipedia', search_wikipedia),
        ('duckduckgo', search_duckduckgo),
    ]
    if BRAVE_ENABLED:
        providers.append(('brave', search_brave))
    if GOOGLE_ENABLED:
        providers.append(('google', search_google))
    if BING_ENABLED:
        providers.append(('bing', search_bing))

    # Query providers independently so one blocked or slow search engine does
    # not prevent results from the other sources from being used.
    provider_results = {}
    with ThreadPoolExecutor(max_workers=len(providers)) as executor:
        futures = {
            executor.submit(provider, query, num, log): name
            for name, provider in providers
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                provider_results[name] = future.result()
            except Exception as e:
                provider_results[name] = []
                if log:
                    log(f"[{name}] EXCEPTION: {e}")

    # Take turns between providers so Wikipedia cannot consume the whole
    # result budget before other resources contribute.
    results = []
    seen_urls = set()
    for index in range(num):
        for name, _ in providers:
            source_results = provider_results.get(name, [])
            if index >= len(source_results):
                continue
            result = source_results[index]
            url = result.get('url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                results.append(result)
                if len(results) >= num:
                    return results

    return results


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


def extract_document_title(text: str, document_meta: Dict | None = None) -> str:
    """Return the strongest available title candidate for source discovery."""
    document_meta = document_meta or {}
    metadata_title = str(document_meta.get('title') or '').strip()
    if metadata_title:
        return re.sub(r'\s+', ' ', metadata_title)[:200]

    filename = str(document_meta.get('filename') or '').strip()
    if filename:
        filename_title = Path(filename).stem.replace('_', ' ').replace('-', ' ')
        filename_title = re.sub(r'\s+', ' ', filename_title).strip()
        if len(filename_title.split()) >= 3 and not re.fullmatch(r'[0-9a-fA-F]{8,}', filename_title):
            return filename_title[:200]

    for line in text.splitlines()[:12]:
        candidate = re.sub(r'\s+', ' ', line).strip(' .:-')
        words = candidate.split()
        if 4 <= len(words) <= 20 and len(candidate) >= 25:
            return candidate[:200]
    return ''


def extract_arxiv_id(document_meta: Dict | None = None) -> str:
    """Extract a modern or legacy arXiv identifier from an uploaded filename."""
    filename = str((document_meta or {}).get('filename') or '')
    match = re.search(r'(?<![\w.])((?:\d{4}\.\d{4,5})(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?![\w])', filename, re.I)
    return match.group(1) if match else ''


def check_plagiarism_online(
    text: str,
    progress_callback=None,
    document_meta: Dict | None = None,
) -> List[Dict]:
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
    scholarly_candidates = {}

    arxiv_id = extract_arxiv_id(document_meta)
    if arxiv_id:
        arxiv_id = re.sub(r'v\d+$', '', arxiv_id, flags=re.I)
        arxiv_url = f'https://arxiv.org/abs/{arxiv_id}'
        arxiv_pdf_url = f'https://arxiv.org/pdf/{arxiv_id}.pdf'
        log(f'Identified arXiv research paper: {arxiv_id}')
        scholarly_candidates[arxiv_pdf_url] = {
            'url': arxiv_pdf_url,
            'title': f'arXiv:{arxiv_id}',
            'snippet': f'Identified paper: {arxiv_url}',
            'source_type': 'scholarly_paper',
            'landing_url': arxiv_url,
        }
        seen_urls.add(arxiv_pdf_url)
        tasks.append((arxiv_pdf_url, f'Identified paper: {arxiv_url}', arxiv_id))

    document_title = extract_document_title(text, document_meta)
    if document_title:
        log(f'Searching for the uploaded paper: "{document_title[:70]}…"')
        scholarly_results = search_openalex(document_title, num=3, log=log)
        for result in scholarly_results:
            url = result['url']
            if url in seen_urls:
                continue
            seen_urls.add(url)
            scholarly_candidates[url] = result
            tasks.append((url, result.get('snippet', ''), document_title))

        title_results = search_web(f'"{document_title}"', num=RESULTS_PER_SENTENCE, log=log)
        for result in title_results:
            url = result['url']
            if url in seen_urls:
                continue
            seen_urls.add(url)
            tasks.append((url, result.get('snippet', ''), document_title))

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

    matched_urls = {match['url'] for match in matches}
    for url, candidate in scholarly_candidates.items():
        if url in matched_urls:
            continue
        # Keep the identified paper visible even when its publisher blocks
        # automated fetching. It is not counted as similarity evidence.
        matches.append({
            'url': url,
            'title': candidate.get('title') or document_title,
            'snippet': candidate.get('snippet', ''),
            'similarity': 0.0,
            'tfidf_score': 0.0,
            'ngram_score': 0.0,
            'semantic_score': 0.0,
            'shared_terms': [],
            'matched_sentence': document_title,
            'sentence_matches': [],
            'sentences_matched_count': 0,
            'coverage_percent': 0,
            'source_type': 'scholarly_paper',
            'verification_status': 'paper_identified_page_unavailable',
        })

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
