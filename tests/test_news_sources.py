import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from news_sources import parse_feed, fetch_news
from news_digest import main, build_digest

RSS = b'''<rss version="2.0"><channel><item><title>Economy</title><link>https://example.com/1</link><pubDate>Tue, 27 Oct 2026 18:00:00 +0000</pubDate><description><![CDATA[<p>First.</p><p>Second.</p><script>hidden()</script>]]></description></item><item><title>Headline</title><link>https://example.com/2</link><pubDate>Wed, 28 Oct 2026 10:00:00 +0900</pubDate></item><item><title>Broken</title></item></channel></rss>'''

class SourceTests(unittest.TestCase):
    def test_colon_timezone_used_by_maeil(self):
        payload = RSS.replace(b'+0000', b'+00:00').replace(b'+0900', b'+09:00')
        articles, skipped = parse_feed(payload, 'test')
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]['date'], '2026-10-28')

    def test_parse_timezone_html_missing_description(self):
        articles, skipped = parse_feed(RSS, 'test')
        self.assertEqual(skipped, 1)
        self.assertEqual(articles[0]['date'], '2026-10-28')
        self.assertEqual(articles[0]['body'], 'First. Second.')
        self.assertEqual(articles[1]['content_type'], 'headline_only')

    @patch('news_sources.download_feed', side_effect=[OSError('offline'), RSS])
    def test_partial_failure(self, download):
        articles, warnings = fetch_news([('a', 'https://a.test'), ('b', 'https://b.test')])
        self.assertEqual(len(articles), 2)
        self.assertEqual(len(warnings), 2)
        self.assertEqual(articles[0]['title'], 'Headline')

    @patch('news_sources.download_feed', return_value=b'<html>error</html>')
    def test_non_feed_fails(self, download):
        with self.assertRaises(ValueError):
            fetch_news([('a', 'https://a.test')])

    @patch('news_digest.fetch_news', side_effect=ValueError('offline'))
    def test_failed_fetch_preserves_output(self, fetch):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '2026-10-28.md'
            path.write_text('existing', encoding='utf-8')
            self.assertEqual(main(['--fetch', '--date', '2026-10-28', '--output-dir', directory]), 1)
            self.assertEqual(path.read_text(encoding='utf-8'), 'existing')

    def test_fetch_cli_creates_digest_and_cache(self):
        articles, _ = parse_feed(RSS, 'test')
        with tempfile.TemporaryDirectory() as directory, patch('news_digest.fetch_news', return_value=(articles, ['partial'])):
            self.assertEqual(main(['--fetch', '--date', '2026-10-28', '--limit', '1', '--output-dir', directory]), 0)
            text = (Path(directory) / '2026-10-28.md').read_text(encoding='utf-8')
            self.assertIn('기사 수: 1개', text)
            self.assertIn('partial', text)
            self.assertTrue((Path(directory) / '2026-10-28.sources.json').is_file())

    def test_headline_only_is_labeled(self):
        articles, _ = parse_feed(RSS, 'test')
        text = build_digest(articles, '2026-10-28', fetched=True)
        self.assertIn('본문 요약 없음', text)
        self.assertIn('https://example.com/2', text)
