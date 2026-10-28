import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from news_digest import build_digest, extract_summary


class DigestTests(unittest.TestCase):
    def article(self, **changes):
        value = dict(date="2026-10-28", title="가상 기사", source="가상 출처",
                     body="금리는 3.5%입니다. 둘째 문장입니다. 셋째 문장입니다. 넷째 문장입니다.")
        value.update(changes)
        return value

    def test_three_sentences_and_decimal(self):
        result = extract_summary(self.article()["body"])
        self.assertIn("3.5%", result)
        self.assertIn("셋째", result)
        self.assertNotIn("넷째", result)

    def test_date_filter_and_duplicate(self):
        result = build_digest([self.article(), self.article(), self.article(date="2026-10-27", title="전날")], "2026-10-28")
        self.assertIn("기사 수: 1개", result)
        self.assertNotIn("전날", result)

    def test_no_articles(self):
        self.assertIn("입력 기사가 없습니다", build_digest([], "2026-10-28"))

    def test_invalid_input(self):
        for articles in ({}, [None], [self.article(body=" ")], [self.article(date="2026-02-30")], [self.article(url="file:///tmp/news")]):
            with self.subTest(articles=articles), self.assertRaises(ValueError):
                build_digest(articles, "2026-10-28")

    def test_cli_and_input_preserved(self):
        script = Path(__file__).resolve().parents[1] / "news_digest.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "news.json"
            original = json.dumps([self.article()], ensure_ascii=False)
            source.write_text(original, encoding="utf-8")
            cmd = [sys.executable, str(script), "--input", str(source), "--date", "2026-10-28", "--output-dir", str(root / "result")]
            done = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn("기사 수: 1개", (root / "result/2026-10-28.md").read_text(encoding="utf-8"))
            self.assertEqual(source.read_text(encoding="utf-8"), original)
            source.write_text("{bad json", encoding="utf-8")
            failed = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(failed.returncode, 1)
            self.assertIn("오류:", failed.stderr)


if __name__ == "__main__":
    unittest.main()
