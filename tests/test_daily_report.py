import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from news_sources import KST
from daily_report import BodyParser, analyze, enrich, html_report, main, terms_in


class DailyTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 10, 28, tzinfo=KST)
        self.end = self.start + timedelta(days=1)

    def article(self, **changes):
        data = {'title':'기준금리와 환율 발표', 'body':'물가와 금리 동향입니다.', 'url':'https://www.hankyung.com/article/1', 'source':'한국경제', 'published_at':'2026-10-28T12:00:00+09:00', 'content_type':'rss_description'}
        data.update(changes)
        return data

    def test_dictionary_longest_term(self):
        self.assertEqual(terms_in('기준금리 동결'), {'기준금리'})

    def test_ranking_counts_window_duplicates(self):
        a = self.article()
        b = self.article(title='환율 변화와 물가', url='https://www.mk.co.kr/news/economy/2', source='매일경제')
        old = self.article(url='https://example.com/old', published_at='2026-10-27T23:59:59+09:00')
        boundary = self.article(url='https://example.com/end', published_at='2026-10-29T00:00:00+09:00')
        bad = self.article(url='https://example.com/bad', published_at='broken')
        quiet = self.article(title='새 서비스 소개', body='제품을 소개합니다.',url='https://example.com/q')
        keywords, selected, total = analyze([quiet, a, a, b, old, boundary, bad], self.start, self.end)
        self.assertEqual(total, 3)
        self.assertNotEqual(selected[0]['title'], quiet['title'])
        row = next(x for x in keywords if x['term']=='환율')
        self.assertEqual((row['articles'], row['sources']), (2, 2))
        self.assertTrue(selected[0]['reasons'])

    def test_body_only_and_html_safety(self):
        p = BodyParser()
        p.feed('<nav>메뉴</nav><div id="articletxt"><p>본문 하나.</p><figure>사진 설명</figure><script>evil()</script><div class="ad">광고</div><p>본문 둘.</p></div><footer>꼬리말</footer>')
        self.assertEqual(p.text(), '본문 하나.\n\n본문 둘.')
        self.assertNotIn('<script>alert(1)</script>', html_report('<script>alert(1)</script>'))

    @patch('daily_report.fetch_body', side_effect=OSError('403'))
    def test_body_failure_not_disguised(self, fetch):
        result = enrich([self.article()])[0]
        self.assertEqual(result['full_body'], '')
        self.assertIn('수집 실패', result['body_status'])
        self.assertEqual(result['body'], self.article()['body'])

    def test_pipeline_saves_bodies_and_keywords(self):
        with tempfile.TemporaryDirectory() as directory, patch('daily_report.fetch_news',return_value=([self.article()], [])), patch('daily_report.fetch_body',return_value='공개 본문입니다. 환율이 변했습니다. 물가 동향입니다.'):
            status = main(['--date','2026-10-28','--output-dir',directory])
            self.assertEqual(status, 0)
            data = json.loads((Path(directory)/'2026-10-28.daily.json').read_text(encoding='utf-8'))
            self.assertTrue(data['articles'][0]['full_body'])
            self.assertTrue(data['keywords'])
            self.assertIn('선정 이유', (Path(directory)/'2026-10-28.daily.md').read_text(encoding='utf-8'))
            self.assertTrue((Path(directory)/'latest.html').is_file())

    @patch('daily_report.fetch_news',side_effect=ValueError('offline'))
    def test_network_failure_preserves_report(self, fetch):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'latest.html';p.write_text('existing',encoding='utf-8')
            self.assertEqual(main(['--output-dir',directory]),1)
            self.assertEqual(p.read_text(), 'existing')

    def test_invalid_top_and_date(self):
        self.assertEqual(main(['--top','0']),1)
        self.assertEqual(main(['--date','2026-02-30']),1)


if __name__ == '__main__':
    unittest.main()
