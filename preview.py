"""Local-only preview and server-side Google Scholar sync. Python 3.10+, stdlib only."""
import argparse
import json
import os
import re
import threading
import time
import unicodedata
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent
AUTHOR_ID = '4JsyjokAAAAJ'
PROFILE = 'https://scholar.google.com/citations?user=' + AUTHOR_ID + '&hl=en'
CACHE = ROOT / '.cache' / 'scholar.json'
INTERVAL = 86400  # one refresh daily, at most 3 API requests per refresh
TARGETS = json.loads((ROOT / 'publications.json').read_text(encoding='utf-8'))

def normalize(title):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', title).casefold())

def integer(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError('Invalid citation count')
    return value

def parse_results(result, targets, timestamp):
    """Exact titles only, on the configured author profile; ambiguous matches are skipped."""
    if result.get('error'):
        raise ValueError('Provider error')
    if result.get('search_parameters', {}).get('author_id') != AUTHOR_ID:
        raise ValueError('Unexpected author profile')
    table = result.get('cited_by', {}).get('table', [])
    totals = {}
    for row in table:
        for key, value in row.items():
            if key in ('citations', 'h_index'):
                totals[key] = integer(value.get('all'))
    if set(totals) != {'citations', 'h_index'}:
        raise ValueError('Missing author metrics')
    articles = result.get('articles', [])
    matched = {}
    for target in targets:
        names = {normalize(target['title']), *(normalize(t) for t in target.get('aliases', []))}
        candidates = {a.get('citation_id'): a for a in articles
                      if normalize(a.get('title', '')) in names
                      and a.get('citation_id', '').startswith(AUTHOR_ID + ':')}
        if len(candidates) == 1:
            citation_id, article = next(iter(candidates.items()))
            try:
                count = integer(article.get('cited_by', {}).get('value'))
            except ValueError:
                continue
            matched[target['id']] = {'citations': count, 'fetched_at': timestamp,
                                     'citation_id': citation_id}
    return {**totals, 'fetched_at': timestamp, 'publications': matched, 'profile_url': PROFILE}

class ScholarSyncError(Exception):
    """A public diagnostic that never contains an API key or provider URL."""


def fetch_scholar(key):
    combined = None
    timestamp = datetime.now(timezone.utc).isoformat()
    for offset in (0, 100, 200):
        query = urlencode({'engine': 'google_scholar_author', 'author_id': AUTHOR_ID,
                           'hl': 'en', 'num': 100, 'start': offset, 'no_cache': 'true', 'api_key': key})
        try:
            with urlopen('https://serpapi.com/search.json?' + query, timeout=40) as response:
                result = json.load(response)
        except HTTPError as error:
            reasons = {401: 'SerpApi rejected the API key. Check SERPAPI_API_KEY.',
                       403: 'SerpApi denied access. Check your account and API key.',
                       429: 'SerpApi quota or rate limit reached. Check your account usage.'}
            raise ScholarSyncError(reasons.get(error.code, 'SerpApi request failed (HTTP ' + str(error.code) + '). Retry later.')) from None
        except (URLError, TimeoutError):
            raise ScholarSyncError('Cannot reach SerpApi. Check network access and retry.') from None
        if result.get('error'):
            raise ValueError('Provider error')
        if combined is None:
            combined = result
        else:
            if result.get('search_parameters', {}).get('author_id') != AUTHOR_ID:
                raise ValueError('Unexpected author profile')
            combined.setdefault('articles', []).extend(result.get('articles', []))
        parsed = parse_results(combined, TARGETS, timestamp)
        if len(parsed['publications']) == len(TARGETS) or not result.get('serpapi_pagination', {}).get('next'):
            return parsed
    return parsed

class ScholarStore:
    def __init__(self, key, cache=CACHE):
        self.key, self.cache = key, cache
        self.lock = threading.Lock()
        self.data = {'publications': {}}
        self.failed = False
        try:
            loaded = json.loads(cache.read_text(encoding='utf-8'))
            integer(loaded['citations']); integer(loaded['h_index'])
            datetime.fromisoformat(loaded['fetched_at'])
            self.data = loaded
        except (OSError, ValueError, KeyError, TypeError):
            pass

    def snapshot(self):
        with self.lock:
            out = json.loads(json.dumps(self.data))
            try:
                age = time.time() - datetime.fromisoformat(out['fetched_at']).timestamp()
            except (KeyError, ValueError):
                age = float('inf')
            out['status'] = 'current' if age < INTERVAL and not self.failed else 'saved'
            if not self.key and not out.get('fetched_at'):
                out['status'] = 'not_configured'
            return out

    def refresh(self, fetcher=fetch_scholar):
        if not self.key:
            return False
        try:
            fresh = fetcher(self.key)
            # Preserve previous exact matches if a publication is absent this time.
            with self.lock:
                fresh['publications'] = {**self.data.get('publications', {}), **fresh['publications']}
                self.cache.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.cache.with_suffix('.tmp')
                temporary.write_text(json.dumps(fresh), encoding='utf-8')
                temporary.replace(self.cache)
                self.data, self.failed = fresh, False
            return True
        except Exception:
            # Never emit provider URLs/errors: they can contain the API key.
            with self.lock:
                self.failed = True
            print('Scholar sync unavailable; retaining previous figures. Check the API key, quota and network.', flush=True)
            return False

    def loop(self):
        while True:
            snapshot = self.snapshot()
            if snapshot['status'] == 'current':
                fetched = datetime.fromisoformat(snapshot['fetched_at']).timestamp()
                time.sleep(max(60, INTERVAL - (time.time() - fetched)))
            else:
                success = self.refresh()
                time.sleep(INTERVAL if success or not self.key else 3600)

def load_key():
    key = os.environ.get('SERPAPI_API_KEY', '').strip()
    if key:
        return key
    path = ROOT / 'scholar-config.json'
    if path.exists():
        return str(json.loads(path.read_text(encoding='utf-8-sig')).get('api_key', '')).strip()
    return ''

def handler_for(store):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            # Explicit allowlist: configuration and source documents are never served.
            path = urlsplit(self.path).path
            if path in ('/api/scholar', '/scholar.json'):
                body = json.dumps(store.snapshot()).encode('utf-8')
                mime = 'application/json; charset=utf-8'
            elif path in ('/', '/index.html'):
                body = (ROOT / 'dist' / 'index.html').read_bytes()
                mime = 'text/html; charset=utf-8'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *_):
            pass
    return Handler

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    store = ScholarStore(load_key())
    threading.Thread(target=store.loop, daemon=True).start()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(store))
    print(f'Local preview: http://127.0.0.1:{args.port}', flush=True)
    print('Automatic Scholar sync enabled.' if store.key else 'No API key configured; displaying saved figures.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == '__main__':
    main()
