"""경제 뉴스 수집, 규칙 기반 키워드 분석과 중요 기사 본문 보고서."""
import argparse
import html
import json
import math
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from news_sources import KST, fetch_news

ROOT = Path(__file__).resolve().parent
TERMS = {
    '기준금리': 4, '금리': 3, '환율': 3, '물가': 3, '인플레이션': 4,
    '소비자물가': 4, '경기': 2, '성장률': 4, 'GDP': 4, '한국은행': 4,
    '연준': 4, '중앙은행': 4, '통화정책': 4, '고용': 3, '실업': 3,
    '수출': 3, '수입': 2, '무역': 3, '관세': 3, '무역수지': 4,
    '가계부채': 4, '부채': 2, '대출': 2, '부동산': 2, '주택': 2,
    '재정': 3, '예산': 2, '국채': 3, '채권': 2, '유가': 3,
    '원유': 3, '반도체': 2, '투자': 1, '코스피': 2, '코스닥': 2,
    '증시': 2, '주가': 2, '금융': 2, '은행': 1, '달러': 2,
    '소비': 2, '생산': 2, '산업': 1, '수출입': 3, '경상수지': 4,
    '경제성장': 3, '통상': 2, '공급망': 2, '임금': 2, '세금': 2,
    '세제': 2, '기업실적': 2, '매출': 1, '영업이익': 2, '금융위기': 4,
}


def terms_in(text):
    # 긴 용어를 먼저 매칭해 기준금리 안의 금리를 이중 집계하지 않습니다.
    pattern = '|'.join(re.escape(term) for term in sorted(TERMS, key=len, reverse=True))
    return set(re.findall(pattern, text))


def analyze(articles, start, end, top=5):
    unique, seen = [], set()
    for original in articles:
        item = dict(original)
        try:
            stamp = datetime.fromisoformat(item['published_at'])
            if stamp.tzinfo is None or not start <= stamp < end:
                continue
            url = item['url']
            if url in seen:
                continue
            seen.add(url)
            text = item['title'] + ' ' + (item['body'] if item.get('content_type') != 'headline_only' else '')
            item['keywords'] = sorted(terms_in(text))
            unique.append(item)
        except (KeyError, ValueError, TypeError):
            continue
    counts = Counter(term for item in unique for term in item['keywords'])
    sources = {term: {x['source'] for x in unique if term in x['keywords']} for term in counts}
    keyword_rows = [{'term': term, 'articles': count, 'sources': len(sources[term])}
                    for term, count in sorted(counts.items(), key=lambda x: (-x[1], -len(sources[x[0]]), x[0]))[:10]]
    for item in unique:
        title_terms = terms_in(item['title'])
        policy_score = sum(TERMS[t] for t in title_terms)
        repeated = sum(math.log2(1 + counts[t]) for t in item['keywords'])
        cross_source = sum(max(0, len(sources[t])-1) for t in item['keywords'])
        item['score'] = round(policy_score + repeated + cross_source, 2)
        common = [t for t in item['keywords'] if counts[t] >= 2]
        reasons = []
        if title_terms:
            reasons.append('제목의 경제 키워드: ' + ', '.join(sorted(title_terms)))
        if common:
            reasons.append('여러 기사에서 반복: ' + ', '.join(common))
        if not reasons:
            reasons.append('설정된 경제 키워드 일치 없음; 최신순으로 보완 선정')
        item['reasons'] = reasons
    unique.sort(key=lambda x: (x['score'], x['published_at']), reverse=True)
    return keyword_rows, unique[:top], len(unique)


class BodyParser(HTMLParser):
    """본문 컨테이너만 추출합니다. 로그인·유료 접근을 우회하지 않습니다."""
    VOID = {'br', 'img', 'hr', 'input', 'meta', 'link', 'source', 'wbr', 'area', 'base', 'embed', 'param', 'track', 'col'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.parts = []
        self.targets = {'articletxt', 'article_body', 'news_cnt_detail_wrap', 'news_cnt_detail'}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        active, hidden = self.stack[-1][1:] if self.stack else (False, False)
        classes = set(attrs.get('class', '').split())
        active = active or attrs.get('id') in self.targets or 'news_cnt_detail_wrap' in classes
        hidden = hidden or tag in ('script', 'style', 'noscript', 'iframe', 'button', 'figure', 'aside')
        hidden = hidden or bool(classes & {'ad', 'advertisement', 'article-related', 'related-news', 'image', 'img'})
        if active and not hidden and tag in ('p', 'div', 'br'):
            self.parts.append('\n')
        if tag not in self.VOID:
            self.stack.append((tag, active, hidden))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack)-1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                if tag in ('p', 'div'):
                    self.parts.append('\n')
                break

    def handle_data(self, data):
        if self.stack and self.stack[-1][1] and not self.stack[-1][2]:
            self.parts.append(data)

    def text(self):
        lines = [re.sub(r'\s+', ' ', line).strip() for line in ''.join(self.parts).splitlines()]
        return '\n\n'.join(line for line in lines if line)


def fetch_body(url):
    host = urlparse(url).hostname or ''
    if host not in ('www.hankyung.com', 'www.mk.co.kr'):
        raise ValueError('본문 수집을 지원하지 않는 언론사 주소입니다.')
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; EconomyNewsDigest/2.0)'})
    with urlopen(request, timeout=12) as response:
        if urlparse(response.geturl()).hostname not in ('www.hankyung.com', 'www.mk.co.kr'):
            raise ValueError('다른 사이트로 이동하여 본문 수집을 중단했습니다.')
        payload = response.read(3_000_001)
        if len(payload) > 3_000_000:
            raise ValueError('기사 응답이 너무 큽니다.')
        encoding = response.headers.get_content_charset() or 'utf-8'
    parser = BodyParser()
    parser.feed(payload.decode(encoding, errors='replace'))
    body = parser.text()
    if len(body) < 150:
        raise ValueError('공개 본문을 확인할 수 없습니다. 원문에서 확인하세요.')
    return body


def enrich(selected):
    results = []
    for article in selected:
        item = dict(article)
        try:
            item['full_body'] = fetch_body(item['url'])
            item['body_status'] = '공개 페이지에서 추출한 본문'
        except (OSError, ValueError) as exc:
            item['full_body'] = ''
            item['body_status'] = '본문 수집 실패: ' + str(exc)
        results.append(item)
    return results


def key_sentences(text, keywords):
    sentences = re.split(r'(?<=[.!?。！？])\s+', re.sub(r'\s+', ' ', text).strip())
    sentences = [s for s in sentences if s]
    ranked = sorted(range(len(sentences)), key=lambda i: (-sum(term in sentences[i] for term in keywords), i))[:3]
    return ' '.join(sentences[i] for i in sorted(ranked))


def render_report(start, end, keywords, selected, total, warnings):
    lines = ['# 데일리 경제 뉴스 분석', '',
             '분석 구간: ' + start.strftime('%Y-%m-%d %H:%M') + ' ~ ' + end.strftime('%Y-%m-%d %H:%M') + ' (한국 시간, 종료 시각 제외)', '',
             f'분석 기사 {total}개 · 선정 기사 {len(selected)}개', '',
             '분석 방식: 경제 용어 사전 매칭과 기사별 등장 빈도를 사용한 규칙 기반 분석입니다. AI의 의미 분석이나 중요도에 대한 객관적 판정은 아닙니다.', '',
             '중요도 = 제목 경제 용어 가중치 합 + 각 용어의 log2(1+등장 기사 수) 합 + 추가 출처 수 합. 동일 URL은 한 번만 집계합니다.', '',
             '수집 범위는 RSS에 현재 남아 있는 기사이며 해당 기간의 모든 보도를 포함하지 않을 수 있습니다.', '']
    for warning in warnings:
        lines.extend(['수집 안내: ' + warning, ''])
    lines += ['## 핵심 키워드', '', '| 키워드 | 등장 기사 수 | 출처 수 |', '|---|---:|---:|']
    for row in keywords:
        lines.append(f"| {row['term']} | {row['articles']} | {row['sources']} |")
    if not keywords:
        lines.append('| 해당 용어 없음 | 0 | 0 |')
    lines.extend(['', '## 선정 기사', ''])
    if not selected:
        lines.extend(['분석 구간에 포함되는 기사가 없습니다.', ''])
    for i, item in enumerate(selected, 1):
        lines.extend([f"### {i}. {item['title']}", '',
                      f"출처: {item['source']} · 발행: {item['published_at']}", '',
                      f"원문: {item['url']}", '', f"중요도 점수: {item['score']}", '',
                      '선정 이유: ' + '; '.join(item['reasons']), '',
                      '키워드: ' + (', '.join(item['keywords']) or '해당 용어 없음'), '',
                      '#### 핵심 문장 추출', ''])
        text = item.get('full_body') or (item['body'] if item.get('content_type') != 'headline_only' else '')
        lines.extend([key_sentences(text, item['keywords']) if text else '본문과 소개문이 없어 핵심 문장을 생성하지 않았습니다.', '',
                      '근거 범위: ' + ('수집한 본문' if item.get('full_body') else 'RSS 소개문만 사용 또는 내용 없음'), '',
                      '#### 기사 본문', '', item['body_status'], '',
                      item.get('full_body') or '가져온 본문이 없습니다. 위 원문 링크에서 확인하세요.', ''])
    return '\n'.join(lines)


def html_report(markdown):
    # 외부 기사 HTML과 스크립트를 실행하지 않고 텍스트로만 표시합니다.
    return ('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>데일리 경제 뉴스 분석</title><style>body{max-width:920px;margin:40px auto;padding:0 20px;background:#fafafa;color:#17212b}'
            'pre{white-space:pre-wrap;overflow-wrap:anywhere;font:16px/1.85 sans-serif}</style><pre>' + html.escape(markdown) + '</pre></html>')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', help='해당 날짜 00시~24시 분석. 생략하면 최근 24시간')
    parser.add_argument('--top', type=int, default=5, help='중요 기사 수 (1~20, 기본 5)')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'output')
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.top <= 20:
            raise ValueError('--top은 1부터 20까지 지정하세요.')
        if args.date:
            start = datetime.strptime(args.date, '%Y-%m-%d').replace(tzinfo=KST)
            end = start + timedelta(days=1)
            label = args.date
        else:
            end = datetime.now(KST)
            start = end - timedelta(hours=24)
            label = end.date().isoformat()
        articles, warnings = fetch_news()
        keywords, selected, total = analyze(articles, start, end, args.top)
        selected = enrich(selected)
        report = render_report(start, end, keywords, selected, total, warnings)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        stem = args.output_dir / (label + '.daily')
        stem.with_suffix('.daily.md').write_text(report, encoding='utf-8')
        stem.with_suffix('.daily.html').write_text(html_report(report), encoding='utf-8')
        stem.with_suffix('.daily.json').write_text(json.dumps({'start':start.isoformat(), 'end':end.isoformat(), 'total':total, 'keywords':keywords, 'articles':selected, 'warnings':warnings},ensure_ascii=False,indent=2),encoding='utf-8')
        (args.output_dir / 'latest.html').write_text(html_report(report), encoding='utf-8')
        print(f'분석 {total}개 / 선정 {len(selected)}개 / 본문 수집 {sum(bool(x.get("full_body")) for x in selected)}개')
        print('보고서: ' + str(stem.with_suffix('.daily.html')))
        print('항상 최신 보고서: ' + str(args.output_dir / 'latest.html'))
        return 0
    except (OSError, ValueError) as exc:
        print('오류: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
