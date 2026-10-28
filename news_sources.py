"""언론사의 공개 RSS에서 경제 뉴스 목록을 가져옵니다."""
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.request import Request, urlopen

KST = timezone(timedelta(hours=9))
DEFAULT_FEEDS = [
    ("한국경제", "https://www.hankyung.com/feed/economy"),
    ("매일경제", "https://www.mk.co.kr/rss/30100041/"),
]


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1
        elif tag in ("p", "div", "li"):
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_text(value):
    parser = PlainText()
    parser.feed(value)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def parse_feed(payload, source):
    root = ET.fromstring(payload)
    if root.tag != "rss" or root.find("channel") is None:
        raise ValueError("RSS 2.0 피드가 아닙니다.")
    articles, skipped = [], 0
    for item in root.findall("./channel/item"):
        try:
            title = plain_text(item.findtext("title", ""))
            url = item.findtext("link", "").strip()
            raw_date = item.findtext("pubDate", "").strip()
            # 일부 제공처는 RFC 822의 +0900 대신 +09:00을 사용합니다.
            raw_date = re.sub(r"([+-]\d{2}):(\d{2})$", r"\1\2", raw_date)
            published = parsedate_to_datetime(raw_date)
            if published.tzinfo is None:
                raise ValueError("발행 시간에 시간대가 없습니다.")
            if not title or not re.fullmatch(r"https?://[^\s]+", url):
                raise ValueError("제목 또는 원문 주소가 없습니다.")
            body = plain_text(item.findtext("description", ""))
            articles.append({"title": title, "url": url, "source": source,
                             "date": published.astimezone(KST).date().isoformat(),
                             "published_at": published.astimezone(KST).isoformat(),
                             "body": body or "RSS에 기사 소개문이 없습니다. 원문 링크에서 내용을 확인하세요.",
                             "content_type": "rss_description" if body else "headline_only"})
        except (ValueError, TypeError, OverflowError):
            skipped += 1
    return articles, skipped


def download_feed(url):
    request = Request(url, headers={"User-Agent": "EconomyNewsDigest/1.0", "Accept": "application/rss+xml, application/xml, text/xml"})
    with urlopen(request, timeout=15) as response:
        payload = response.read(2_000_001)
    if len(payload) > 2_000_000:
        raise ValueError("RSS 응답이 2MB를 초과했습니다.")
    return payload


def fetch_news(feeds=None):
    articles, warnings = [], []
    for source, url in DEFAULT_FEEDS if feeds is None else feeds:
        try:
            batch, skipped = parse_feed(download_feed(url), source)
            if not batch:
                raise ValueError("유효한 기사가 없습니다.")
            articles.extend(batch)
            if skipped:
                warnings.append(f"{source}: 필수 정보가 잘못된 기사 {skipped}개를 제외했습니다.")
        except (OSError, ValueError, ET.ParseError) as exc:
            warnings.append(f"{source} 수집 실패: {exc}")
    if not articles:
        raise ValueError("뉴스를 가져오지 못했습니다. 기존 결과는 보존됩니다. " + " / ".join(warnings))
    articles.sort(key=lambda article: article["published_at"], reverse=True)
    return articles, warnings
