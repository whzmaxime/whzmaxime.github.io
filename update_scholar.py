"""Fetch Scholar figures for a GitHub Pages deployment. No third-party dependencies."""
import copy
import html
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen
from preview import AUTHOR_ID, ROOT, TARGETS, fetch_scholar, integer, ScholarSyncError

DATA = ROOT / 'dist' / 'scholar.json'
PAGE = ROOT / 'dist' / 'index.html'

def previous_snapshot():
    data = json.loads(DATA.read_text(encoding='utf-8'))
    base = os.environ.get('PAGES_BASE_URL', '').rstrip('/')
    # Only fetch the public JSON from the configured Pages origin; no credential is sent.
    if base and urlsplit(base).scheme == 'https':
        try:
            with urlopen(base + '/scholar.json', timeout=20) as response:
                online = json.load(response)
            if online.get('author_id') == AUTHOR_ID and online.get('fetched_at'):
                integer(online['citations']); integer(online['h_index'])
                data = online
        except Exception:
            print('Previous deployed snapshot unavailable; using bundled source figures.')
    return data

def merge(previous, fresh):
    result = copy.deepcopy(fresh)
    result['author_id'] = AUTHOR_ID
    result['publications'] = {**previous.get('publications', {}), **fresh['publications']}
    # Whitelist public output; never serialize raw provider replies or credentials.
    safe = {'author_id': AUTHOR_ID, 'citations': integer(result['citations']),
            'h_index': integer(result['h_index']), 'fetched_at': result['fetched_at'],
            'publications': {}}
    for target in TARGETS:
        item = result['publications'].get(target['id'])
        if item:
            safe['publications'][target['id']] = {
                'citations': integer(item['citations']) if item.get('fetched_at') and item.get('citations') is not None else None,
                'fetched_at': item.get('fetched_at'),
                'source_as_of': item.get('source_as_of')
            }
    return safe

def hydrate(source, data):
    """Publish actual figures into HTML as well as JSON, including their real dates."""
    for ident, value in [('gs-citations', data['citations']), ('gs-h-index', data['h_index'])]:
        pattern = rf'<strong\b(?=[^>]*\bid="{ident}")[^>]*>[^<]*</strong>'
        replacement = f'<strong id="{ident}" title="Google Scholar · retrieved {html.escape(data["fetched_at"])}">{value:,}</strong>'
        source, n = re.subn(pattern, lambda _: replacement, source)
        if n != 1: raise ValueError('Missing metric element')
    for ident, item in data['publications'].items():
        pattern = rf'(<strong\b[^>]*\bdata-citations="{re.escape(ident)}"[^>]*>)[^<]*(</strong>)'
        value = format(item['citations'], ',') if item.get('fetched_at') and item.get('citations') is not None else '—'
        source, n = re.subn(pattern, lambda m: m[1] + value + m[2], source)
        if n != 1: raise ValueError('Missing publication element')
        # The wrapper tooltip must agree even before JS runs.
        wrapper = rf'(<span\b[^>]*class="citation-count"[^>]*>)(\s*<strong\b[^>]*data-citations="{re.escape(ident)}")'
        date = item.get('fetched_at')
        tooltip = 'Google Scholar · retrieved ' + date if date else 'Google Scholar count will appear after the first successful synchronization.'
        def title(match):
            tag = re.sub(r'\s+title="[^"]*"', '', match[1])
            return tag[:-1] + ' title="' + html.escape(tooltip) + '">' + match[2]
        source = re.sub(wrapper, title, source)
    snapshot = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    source, count = re.subn(r'(<script\b[^>]*id="scholar-snapshot"[^>]*>).*?(</script>)',
                            lambda m: m[1] + snapshot + m[2], source, flags=re.S)
    if count != 1: raise ValueError('Missing embedded Scholar snapshot')
    base = os.environ.get('PAGES_BASE_URL', '').rstrip('/')
    if base and urlsplit(base).scheme == 'https':
        endpoint = html.escape(base + '/scholar.json', quote=True)
        source = re.sub(r'<meta\b[^>]*name="scholar-data-url"[^>]*>',
                        lambda _: '<meta name="scholar-data-url" content="' + endpoint + '">', source)
    return source

def report(fresh):
    lines = ['## Google Scholar synchronization', '', 'Retrieved: ' + fresh['fetched_at'],
             '', '| Work | Status | Citations |', '| --- | --- | --- |']
    for target in TARGETS:
        item = fresh['publications'].get(target['id'])
        lines.append('| ' + target['title'].replace('|', ' ') + ' | ' +
                     ('Updated | ' + str(item['citations']) if item else 'Not matched; previous count retained | —') + ' |')
    destination = os.environ.get('GITHUB_STEP_SUMMARY')
    if destination:
        with open(destination, 'a', encoding='utf-8') as output:
            output.write('\n'.join(lines) + '\n')


def main():
    key = os.environ.get('SERPAPI_API_KEY', '').strip()
    if not key:
        print('::error::Add repository Actions secret SERPAPI_API_KEY before running this workflow.')
        return 2
    try:
        previous = previous_snapshot()
        fresh = fetch_scholar(key)
        if not fresh['publications']:
            raise ScholarSyncError('Author metrics were returned but none of the selected papers matched. Check publications.json against the author profile.')
        data = merge(previous, fresh)
        updated_page = hydrate(PAGE.read_text(encoding='utf-8'), data)
    except ScholarSyncError as error:
        print('::error::' + str(error))
        print('Deployment stopped; the currently published website remains unchanged.')
        return 1
    except Exception:
        # A provider exception can contain the query URL and private key: never print it.
        print('::error::Scholar update failed. Deployment stopped; the currently published website remains unchanged.')
        return 1
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    PAGE.write_text(updated_page, encoding='utf-8')
    report(fresh)
    found = len(fresh['publications'])
    print(f'Scholar metrics refreshed; {found}/{len(TARGETS)} selected works matched exactly.')
    if found != len(TARGETS):
        print('::warning::Unmatched works retain their prior counts and original source dates.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
