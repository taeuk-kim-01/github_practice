# 데일리 경제 뉴스 분석

한국경제·매일경제의 공개 경제 RSS를 모아 핵심 키워드와 중요 기사, 수집 가능한 기사 본문을 담은 개인용 보고서를 만듭니다.
추가 패키지와 API 키 없이 실행됩니다. 새 `daily_report.py`는 Python 3.8 이상을 지원합니다.

## 가장 쉬운 시작

1. 이 작업 브랜치에서 Code → Download ZIP으로 최신 프로젝트를 내려받아 압축을 풉니다.
2. Windows에서 **`run_daily.cmd`를 더블클릭**합니다.
3. 완료되면 브라우저에서 보고서가 열립니다. 나중에는 `output/latest.html`을 더블클릭하면 됩니다.

처음 실행하는 동안 인터넷 연결이 필요합니다. 실행 창에 오류가 나오면 그 내용을 확인하세요.
이 실행 파일은 같은 폴더의 `daily_report.py`를 실행하므로 프로젝트 파일을 함께 보관해야 합니다.
Python Launcher인 `py`를 찾지 못하면 설치된 Python을 이용해 아래 명령을 실행합니다.

```powershell
py -3 daily_report.py
```

특정 날짜 또는 기사 수를 지정할 수 있습니다.

```powershell
py -3 daily_report.py --date 2026-10-28 --top 5
```

## 어떤 내용을 분석하나요

기본은 **실행 시각 기준 최근 24시간**입니다. 아침에 실행해도 전날 낮과 밤의 기사를 포함합니다.
`--date`를 지정하면 한국 시간으로 해당 날짜 00시부터 다음 날 00시 직전까지 분석합니다.
RSS에 남아 있는 기사만 수집하므로 과거 전체 기사 검색이나 해당 기간 모든 기사 수집을 보장하지 않습니다.

보고서 구성:

- 분석한 기사 수와 기간, 수집 실패 안내
- 핵심 경제 키워드 최대 10개와 각 용어가 등장한 기사 수·출처 수
- 중요도 순으로 선정한 기사 5개, 점수와 선정 이유
- 선정 기사 본문에서 경제 키워드와 겹치는 정도가 높은 문장 최대 3개 추출
- 공개 페이지에서 수집한 기사 본문, 출처와 원문 주소

키워드는 코드에 정의한 약 50개의 경제 용어 사전을 매칭합니다. 자유로운 신조어나 기업명을 모두 추출하는 한국어 형태소 분석기는 아닙니다.
중요도는 **제목 경제 용어의 가중치 합 + 각 키워드의 log2(1+등장 기사 수) 합 + 해당 용어의 추가 출처 수 합**입니다.
통화정책·물가·성장률 등은 상대적으로 높은 가중치를 줍니다. 제목과 RSS 소개문으로 기사를 먼저 선정하고, 선정 기사만 본문을 요청합니다.
동점이면 최신 기사를 먼저 표시합니다. 같은 URL은 한 번만 집계하지만 서로 다른 URL의 유사 기사는 별개로 집계할 수 있습니다.

이 버전의 분석과 문장 추출은 **규칙 기반**입니다. AI의 의미 이해나 투자 중요도 판정은 아닙니다.
본문이 없으면 RSS 소개문을 이용하며, 근거 범위를 별도로 표시합니다. RSS 소개문도 없으면 핵심 문장을 만들지 않습니다.
HTTP 403, 유료·로그인 페이지, 본문 구조 변경 등으로 본문을 읽을 수 없는 경우 원문 링크와 실패 이유를 남깁니다.
가져온 텍스트는 페이지에서 추출 가능한 범위이며 원문 전체와 정확하게 일치한다고 보장하지 않습니다.

## 매일 자동으로 실행하기

Windows에서 **`install_daily.cmd`를 한 번 더블클릭**하면 현재 프로젝트 폴더와 Python 경로로 작업 스케줄러에 등록합니다.
기본 시간은 **매일 오전 08:00, Windows에 설정된 현지 시각 기준**입니다. 한국 PC라면 한국 오전 8시입니다.
스크립트를 제공한 상태이며 이 채팅에서 사용자의 PC에 등록한 것은 아닙니다.

- PC가 켜져 있고 인터넷에 연결되어 있어야 하며, 사용자가 Windows에 로그인한 상태여야 합니다.
- 예약 시각을 놓친 경우 Windows의 가능한 시각에 실행하도록 설정합니다. 꺼진 PC에서 클라우드 실행되는 기능은 아닙니다.
- 프로젝트를 이동·삭제하면 예약이 동작하지 않습니다. 새 위치에서 다시 등록한 뒤 이전 작업은 작업 스케줄러에서 제거하세요.
- 등록 여부와 실행 결과는 Windows의 작업 스케줄러에서 `EconomyNewsDaily-`로 시작하는 작업을 확인합니다.
- 보고서는 로컬 `output` 폴더에 저장되며 GitHub로 자동 전송하지 않습니다.

시간을 바꾸려면 프로젝트 폴더의 PowerShell에서 실행합니다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install_daily_task.ps1 -At 18:00
```

예약을 삭제하려면:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install_daily_task.ps1 -Remove
```

등록에 실패하면 창의 오류를 확인합니다. 조직 정책이나 계정 권한에 따라 스케줄러 등록이 제한될 수 있습니다.
Windows 예약 실행은 실제 Windows PC에서 등록 후 확인해야 합니다. 개발 환경에서는 Python 분석·수집 기능을 검증합니다.

## 폴더와 파일

| 파일 또는 폴더 | 역할 |
|---|---|
| `daily_report.py` | 기간 선택, 키워드 분석, 기사 선정, 본문 수집, HTML·Markdown 보고서 생성 |
| `news_sources.py` | 한국경제·매일경제 경제 RSS 수집과 한국 시간 변환 |
| `run_daily.cmd` | Windows에서 더블클릭으로 분석 실행 및 결과 열기 |
| `install_daily.cmd` | Windows 매일 실행 등록을 시작하는 파일 |
| `install_daily_task.ps1` | 매일 실행 예약 등록·삭제 |
| `output/` | 결과 보관. GitHub 기록에서 제외 |
| `tests/` | 날짜 범위, 키워드 집계, 중요도, 본문 추출, 오류 처리 검사 |
| `news_digest.py` | 기존 날짜별 RSS 소개문 추출 프로그램 |
| `data/sample_news.json` | 기존 프로그램의 가상 연습 데이터 |

## 결과 파일

- `output/latest.html`: 항상 최근 실행의 보고서. 브라우저에서 열기
- `output/YYYY-MM-DD.daily.html`: 날짜별 읽기용 보고서
- `output/YYYY-MM-DD.daily.md`: 날짜별 텍스트 보고서
- `output/YYYY-MM-DD.daily.json`: 키워드·점수·본문을 담은 분석 데이터

같은 날짜에 다시 실행하면 그 날짜의 결과를 갱신합니다. 전체 RSS 수집이 실패하면 기존 결과를 유지합니다.
본문과 보고서는 개인 PC에만 저장하도록 `.gitignore`에서 `output/`을 제외했습니다.

## 기존 명령과 검사

기존 소개문 추출 명령은 계속 사용할 수 있습니다. 이 명령도 Python 3.8 이상에서 실행할 수 있습니다.

```powershell
py news_digest.py --fetch
py news_digest.py --input data/sample_news.json --date 2026-10-28
```

전체 검사:

```powershell
py -3 -m unittest discover -s tests -v
```

## 제공처와 예약 기능 참고 문서

- 한국경제 경제 RSS: https://www.hankyung.com/feed/economy (안내 https://www.hankyung.com/feed)
- 매일경제 경제 RSS: https://www.mk.co.kr/rss/30100041/ (안내 https://www.mk.co.kr/rss)
- Microsoft 예약 등록: https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/register-scheduledtask
- Microsoft 매일 실행 트리거: https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasktrigger
