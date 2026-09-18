import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import preview
import update_scholar as updater

class ScholarTests(unittest.TestCase):
    def setUp(self):
        self.initial = json.loads((preview.ROOT / 'dist/scholar.json').read_text())
        self.html = (preview.ROOT / 'dist/index.html').read_text()
        self.fresh = {'citations': 71234, 'h_index': 127, 'fetched_at': '2026-09-16T11:00:00+00:00',
                      'publications': {'1': {'citations': 3210, 'fetched_at': '2026-09-16T11:00:00+00:00'}}}

    def test_partial_update_preserves_other_counts_and_dates(self):
        merged = updater.merge(self.initial, self.fresh)
        self.assertEqual(merged['publications']['1']['citations'], 3210)
        self.assertIsNone(merged['publications']['2']['citations'])
        self.assertIsNone(merged['publications']['2']['fetched_at'])

    def test_whitelists_data_and_hydrates_html(self):
        self.fresh['private_provider_url'] = 'secret-example'
        merged = updater.merge(self.initial, self.fresh)
        self.assertNotIn('secret-example', json.dumps(merged))
        page = updater.hydrate(self.html, merged)
        self.assertIn('>71,234</strong>', page)
        self.assertIn('>3,210</strong>', page)
        self.assertNotIn('secret-example', page)
        self.assertIn('Google Scholar count will appear after the first successful synchronization.', page)
        import re
        embedded = json.loads(re.search(r'<script[^>]*id="scholar-snapshot"[^>]*>(.*?)</script>', page, re.S)[1])
        self.assertEqual(embedded['publications']['1']['citations'],3210)
        self.assertEqual(embedded['h_index'],127)

    def test_fails_on_missing_html_metric(self):
        with self.assertRaises(ValueError):
            updater.hydrate('<html></html>', updater.merge(self.initial,self.fresh))

    def test_failure_keeps_files_unchanged_without_leaking_key(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)/'scholar.json'; page = Path(folder)/'index.html'
            data.write_text(json.dumps(self.initial)); page.write_text(self.html)
            before = data.read_bytes(), page.read_bytes()
            log = io.StringIO()
            with patch.object(updater,'DATA',data), patch.object(updater,'PAGE',page), \
                 patch.dict(os.environ,{'SERPAPI_API_KEY':'test-private','PAGES_BASE_URL':''}), \
                 patch.object(updater,'fetch_scholar',side_effect=ValueError('test-private')), redirect_stdout(log):
                self.assertEqual(updater.main(),1)
            self.assertEqual(before,(data.read_bytes(),page.read_bytes()))
            self.assertNotIn('test-private',log.getvalue())

    def test_success_writes_public_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)/'scholar.json'; page = Path(folder)/'index.html'
            data.write_text(json.dumps(self.initial)); page.write_text(self.html)
            with patch.object(updater,'DATA',data), patch.object(updater,'PAGE',page), \
                 patch.dict(os.environ,{'SERPAPI_API_KEY':'test-private','PAGES_BASE_URL':''}), \
                 patch.object(updater,'fetch_scholar',return_value=self.fresh), redirect_stdout(io.StringIO()):
                self.assertEqual(updater.main(),0)
            self.assertEqual(json.loads(data.read_text())['h_index'],127)
            self.assertNotIn('test-private', data.read_text()+page.read_text())

    def test_profile_identity_and_ambiguous_titles(self):
        stamp=self.fresh['fetched_at']
        article={'title':preview.TARGETS[0]['title'],'citation_id':preview.AUTHOR_ID+':one','cited_by':{'value':3210}}
        reply={'search_parameters':{'author_id':preview.AUTHOR_ID},'cited_by':{'table':[{'citations':{'all':71234}},{'h_index':{'all':127}}]},'articles':[article]}
        self.assertEqual(preview.parse_results(reply,preview.TARGETS,stamp)['publications']['1']['citations'],3210)
        duplicate=copy.deepcopy(article);duplicate['citation_id']=preview.AUTHOR_ID+':two';reply['articles'].append(duplicate)
        self.assertEqual(preview.parse_results(reply,preview.TARGETS,stamp)['publications'],{})
        reply['search_parameters']['author_id']='another-author'
        with self.assertRaises(ValueError):preview.parse_results(reply,preview.TARGETS,stamp)

    def test_http_errors_produce_safe_actionable_diagnostics(self):
        from urllib.error import HTTPError
        for code, phrase in [(401, 'API key'), (429, 'quota')]:
            error = HTTPError('https://example.invalid/?api_key=test-private', code, 'test-private', {}, None)
            with patch.object(preview, 'urlopen', side_effect=error):
                with self.assertRaises(preview.ScholarSyncError) as caught:
                    preview.fetch_scholar('test-private')
            self.assertIn(phrase, str(caught.exception))
            self.assertNotIn('test-private', str(caught.exception))

    def test_zero_paper_matches_cannot_publish_as_success(self):
        fresh = {**self.fresh, 'publications': {}}
        before = updater.DATA.read_bytes(), updater.PAGE.read_bytes()
        with patch.dict(os.environ, {'SERPAPI_API_KEY': 'test-private', 'PAGES_BASE_URL': ''}), \
             patch.object(updater, 'fetch_scholar', return_value=fresh), redirect_stdout(io.StringIO()):
            self.assertEqual(updater.main(), 1)
        self.assertEqual(before, (updater.DATA.read_bytes(), updater.PAGE.read_bytes()))

if __name__=='__main__':
    unittest.main()
