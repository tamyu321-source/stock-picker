<p align="right">
  <a href="./README.md"><img src="https://flagcdn.com/w40/gb.png" alt="United Kingdom flag" width="22"> English</a> |
  <a href="./README.zh-TW.md"><img src="https://flagcdn.com/w40/tw.png" alt="Taiwan flag" width="22"> 繁體中文</a> |
  <a href="./README.nan-TW.md"><img src="./assets/taiwan-green-island.svg" alt="Green Taiwan island flag" width="22"> 臺語</a> |
  <a href="./README.zh-CN.md"><img src="https://flagcdn.com/w40/cn.png" alt="China flag" width="22"> 简体中文</a> |
  <a href="./README.ja.md"><img src="https://flagcdn.com/w40/jp.png" alt="Japan flag" width="22"> 日本語</a> |
  <a href="./README.ko.md"><img src="https://flagcdn.com/w40/kr.png" alt="South Korea flag" width="22"> 한국어</a>
</p>

# Open Stock Picker

[![CI](https://github.com/tamyu321-source/stock-picker/actions/workflows/ci.yml/badge.svg)](https://github.com/tamyu321-source/stock-picker/actions/workflows/ci.yml)
[![Deploy GitHub Pages](https://github.com/tamyu321-source/stock-picker/actions/workflows/deploy.yml/badge.svg)](https://github.com/tamyu321-source/stock-picker/actions/workflows/deploy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

Open Stock Picker는 다국어를 지원하는 AI 보조 주식 리서치 웹 앱입니다. 핵심 흐름은 코드 없이 시장을 스캔하는 것입니다. 시장과 전략을 선택하면 Python 백엔드가 중국 A주, 홍콩, 일본, 한국, 싱가포르, 미국, 대만의 후보 종목을 찾고 점수화해 투자 검토에 적합한 순서로 정렬합니다.

이 앱은 실제 리서치 흐름을 위해 설계되었습니다. 주문을 실행하지 않으며 증권사 계정이나 인증 정보를 저장하지 않습니다.

**호스팅 미리보기:** [tamyu321-source.github.io/stock-picker](https://tamyu321-source.github.io/stock-picker/)

GitHub Pages 빌드는 정적 데모 모드로 실행됩니다. 실시간 시세, RSS/뉴스 수집, 스트리밍 스캔을 사용하려면 로컬에서 Flask 백엔드를 실행하세요.

![Open Stock Picker preview](./preview-stock-picker.png)

## 유용한 점

- 종목 코드를 먼저 입력하지 않아도 시장을 바로 스캔할 수 있습니다.
- 백엔드 분석이 진행되는 동안 후보 종목이 순차적으로 표시됩니다.
- 긴 스캔은 중간에 취소할 수 있고, 이미 표시된 후보는 유지됩니다.
- 같은 점수화 결과로 개별 종목과 섹터 분석을 함께 비교할 수 있습니다.
- 최근 스캔을 로컬에 저장하고 Markdown 또는 JSON 리서치 노트로 내보낼 수 있습니다.
- 100점 점수를 모멘텀, 밸류에이션, 뉴스 심리, 리스크, 품질로 나눠 확인할 수 있습니다.
- UI는 영어, 간체 중국어, 번체 중국어, 대만어, 일본어, 한국어를 지원합니다.
- 이미 조사할 종목이 있다면 티커나 회사명으로 스캔 범위를 좁힐 수 있습니다.

## 기능

- Vue 3 + Vite 프론트엔드, 설정 저장, 반응형 리서치 작업공간.
- Python Flask 백엔드, 실시간 데이터 제공자, RSS/뉴스 수집, 설명 가능한 점수화.
- 종목 입력 없이 사용할 수 있는 직접 시장 스캔.
- 고정 종목 목록에만 의존하지 않는 시장 유니버스 탐색.
- NDJSON 스트리밍 API로 긴 스캔 중에도 후보를 점진적으로 표시.
- 브라우저 `AbortController`를 통한 스캔 취소.
- 시장 데이터와 뉴스 요청 중복을 줄이는 단기 메모리 TTL 캐시.
- 로컬 저장 스캔 기록과 Markdown/JSON 내보내기.
- Yahoo Finance chart endpoints 기반 가격 히스토리. 설치되어 있으면 `yfinance`도 사용할 수 있습니다.
- Google News, Eastmoney fallback, 현지 뉴스 소스 필터를 이용한 시장별 뉴스 수집.
- 균형형, 성장 모멘텀, 방어적 가치 기본 전략.
- 모멘텀, 밸류에이션, 뉴스 심리, 리스크, 품질 가중치를 조정하는 사용자 전략.
- 매수 후보, 관찰, 매도 리스크 판단과 판단 근거, 출처 링크, 행동 계획, 리스크 관리.

## 시장 범위

| 시장 | 티커 예시 | 탐색 방식 |
| --- | --- | --- |
| 미국 | `AAPL`, `MSFT`, `NVDA` | Yahoo Finance 스크리너와 뉴스 검색 |
| 중국 A주 | `600519.SS`, `300750.SZ` | Eastmoney 시장 목록, 현지 이름, fallback metadata |
| 홍콩 | `0700.HK`, `9988.HK` | Eastmoney 홍콩 목록과 회사 별칭 |
| 일본 | `7203.T`, `6758.T` | 현지 뉴스, Google News 검색, 고유동성 fallback 종목 |
| 한국 | `005930.KS`, `000660.KS` | 현지 뉴스, Google News 검색, 고유동성 fallback 종목 |
| 싱가포르 | `D05.SI`, `C38U.SI` | SGX securities API를 거래량 기준으로 정렬 |
| 대만 | `2330.TW`, `2317.TW` | TWSE 공개 데이터, 현지 회사명, Yahoo/TWSE fallback |

## 아키텍처

```text
Vue 3 web app
  -> /api/config          전략, 시장, 기본 티커 메타데이터
  -> /api/analyze         실시간 데이터 조회, RSS 수집, 점수화, 판단, 설명
  -> /api/analyze/stream  증분 NDJSON 스캔 이벤트

Flask backend
  -> backend/universe.py   동적 시장 유니버스 탐색
  -> backend/providers.py  시장 데이터 제공자와 RSS/뉴스 수집기
  -> backend/cache.py      단기 메모리 캐시
  -> backend/services.py   지표 계산, 전략 선택, 설명 가능한 점수화
  -> backend/app.py        REST API
```

## 로컬 개발

프론트엔드 의존성:

```powershell
npm install
```

백엔드 의존성:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

백엔드 실행:

```powershell
python -m backend.app
```

다른 터미널에서 프론트엔드 실행:

```powershell
npm run dev
```

`http://127.0.0.1:5173`을 여세요.

## 정적 데모와 실시간 백엔드

- GitHub Pages는 Vue 빌드만 제공합니다. Python 없이 화면을 확인할 수 있도록 내장 샘플 데이터를 사용합니다.
- 로컬에서 `python -m backend.app`를 실행하면 실시간 `/api/config`, `/api/analyze`, `/api/analyze/stream`을 사용할 수 있습니다.
- 상단의 데이터 모드 표시에서 샘플 데이터인지 실시간 백엔드인지 확인할 수 있습니다.

## 코드 없는 시장 스캔

기본 사용 흐름은 선택 입력인 종목 입력란을 비워 두는 것입니다. 백엔드가 요청 시점에 후보를 찾고 투자 리서치 아이디어로 순위를 매깁니다.

빈 입력 스캔의 탐색 우선순위:

1. 현지 금융 뉴스 소스.
2. Google News 시장 검색.
3. Yahoo, Eastmoney, SGX, TWSE 같은 시장 유니버스 API.
4. 실시간 소스에 접근할 수 없을 때의 curated fallback symbols.

## 점수화 모델

- `momentum`: 실시간 가격 히스토리에서 본 최근 추세.
- `value`: trailing PE, forward PE, PBR, 사용 가능한 proxy 지표 기반 밸류에이션.
- `sentiment`: 출처 신뢰도, 기사 신선도, 회사 관련도, 제목, RSS 요약을 반영한 뉴스 심리.
- `risk`: 베타, 실현 변동성, 급락 가격 움직임 점검.
- `quality`: ROE, 이익률, 부채비율, 성장, 규모, 유동성.

결과는 리서치 보조 자료이며 금융 조언이 아닙니다.

## 테스트

```powershell
python -m unittest discover backend/tests
npm run build
```

## 면책

이 애플리케이션은 투자 리서치 워크플로 지원용입니다. 금융 조언이 아니며 거래를 실행하지 않습니다.
