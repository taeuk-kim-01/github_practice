"""입력 뉴스의 앞 세 문장을 날짜별 Markdown 파일로 정리합니다."""
import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parent


def parse_date(value):
    try:
        return date.fromisoformat(value).isoformat()
    except (ValueError, TypeError):
        raise ValueError(f"날짜는 YYYY-MM-DD 형식이어야 합니다: {value}") from None


def korea_today():
    try:
        return datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    except ZoneInfoNotFoundError:
        from datetime import timezone, timedelta
        return datetime.now(timezone(timedelta(hours=9))).date().isoformat()


def extract_summary(body):
    text = re.sub(r"\s+", " ", body).strip()
    # 소수점(예: 3.5)은 분리하지 않습니다. 문장 끝 부호 뒤 공백을 기준으로 나눕니다.
    sentences = re.split(r"(?<=[.!?。！？])\s+", text)
    return " ".join(sentences[:3])


def build_digest(articles, target_date):
    parse_date(target_date)
    if not isinstance(articles, list):
        raise ValueError("입력 파일의 최상위 값은 뉴스 목록이어야 합니다.")
    selected = []
    seen = set()
    for index, article in enumerate(articles, 1):
        if not isinstance(article, dict):
            raise ValueError(f"{index}번 뉴스는 객체 형태여야 합니다.")
        for key in ("date", "title", "body", "source"):
            if not isinstance(article.get(key), str) or not article[key].strip():
                raise ValueError(f"{index}번 뉴스의 {key} 항목이 비어 있거나 문자열이 아닙니다.")
        article_date = parse_date(article["date"])
        url = article.get("url", "")
        if not isinstance(url, str) or (url and not re.match(r"^https?://[^\s]+$", url)):
            raise ValueError(f"{index}번 뉴스의 url은 http 또는 https 주소여야 합니다.")
        if article_date != target_date:
            continue
        identity = url or (article["title"].strip(), article["source"].strip())
        if identity in seen:
            continue
        seen.add(identity)
        selected.append(article)
    lines = [f"# {target_date} 경제 뉴스 요약", "",
             "입력 본문의 앞 세 문장을 추출한 연습용 요약입니다. AI 재작성과 실시간 수집은 수행하지 않습니다.", "",
             f"기사 수: {len(selected)}개", ""]
    if not selected:
        lines.extend(["해당 날짜의 입력 기사가 없습니다.", ""])
    for index, article in enumerate(selected, 1):
        title = " ".join(article["title"].split())
        source = " ".join(article["source"].split())
        lines.extend([f"## {index}. {title}", "", extract_summary(article["body"]), "",
                      f"출처: {source}", f"기사 날짜: {article['date']}"])
        if article.get("url"):
            lines.append(f"원문: {article['url']}")
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "sample_news.json")
    parser.add_argument("--date", default=korea_today(), help="기사 날짜 YYYY-MM-DD (기본: 한국 오늘 날짜)")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output")
    args = parser.parse_args(argv)
    try:
        target = parse_date(args.date)
        articles = json.loads(args.input.read_text(encoding="utf-8-sig"))
        result = build_digest(articles, target)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        path = args.output_dir / f"{target}.md"
        if path.resolve() == args.input.resolve():
            raise ValueError("출력 경로가 입력 파일과 같습니다. 다른 출력 폴더를 선택하세요.")
        path.write_text(result, encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    print(f"요약 파일 생성 완료: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
