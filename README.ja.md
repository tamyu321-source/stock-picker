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

Open Stock Picker は、多言語対応の AI 支援型株式リサーチ Web アプリです。主な流れはノーコードの市場スキャンです。市場と戦略を選ぶと、Python バックエンドが中国 A 株、香港、日本、韓国、シンガポール、米国、台湾の候補銘柄を発見し、投資研究向けにスコアリングして順位付けします。

このアプリは実際の調査ワークフロー向けです。売買注文は実行せず、証券会社の認証情報も保存しません。

**ホスト版プレビュー:** [tamyu321-source.github.io/stock-picker](https://tamyu321-source.github.io/stock-picker/)

GitHub Pages 版は静的デモモードで動作します。ライブの市場データ、RSS/ニュース取得、ストリーミングスキャンを使うには、ローカルで Flask バックエンドを起動してください。

![Open Stock Picker preview](./preview-stock-picker.png)

## 便利な点

- 銘柄コードを先に入力しなくても、市場を直接スキャンできます。
- バックエンドの分析中でも、候補銘柄が順次表示されます。
- 長いスキャンを途中でキャンセルしても、すでに表示された候補は残ります。
- 同じスコア済み候補から、個別株とセクター分析を比較できます。
- 最近のスキャンをローカル保存し、Markdown または JSON の研究メモとして出力できます。
- 100 点スコアをモメンタム、バリュエーション、ニュース心理、リスク、品質に分解して確認できます。
- UI は英語、簡体字中国語、繁体字中国語、台湾語、日本語、韓国語に対応します。
- 既に調べたい銘柄がある場合は、ティッカーまたは会社名でスキャン範囲を絞れます。

## 機能

- Vue 3 + Vite フロントエンド、設定保存、レスポンシブな研究ワークスペース。
- Python Flask バックエンド、ライブデータ取得、RSS/ニュースクロール、説明可能なスコアリング。
- 銘柄入力なしで使える直接市場スキャン。
- 固定リストだけに頼らない市場ユニバース探索。
- NDJSON ストリーミング API により、長いスキャンでも候補が段階的に表示されます。
- ブラウザの `AbortController` によるスキャンキャンセル。
- 市場データとニュース取得の重複を減らす短期メモリ TTL キャッシュ。
- 保存済みスキャン履歴、Markdown/JSON エクスポート。
- Yahoo Finance chart endpoints による価格履歴取得。`yfinance` がある場合は任意で利用できます。
- Google News、Eastmoney fallback、現地ニュースソースを使う市場別ニュース取得。
- バランス、成長モメンタム、防御的バリューの標準戦略。
- モメンタム、バリュエーション、センチメント、リスク、品質の重みを調整できるカスタム戦略。
- 買い候補、注視、売却リスクの判定と、判断理由、リンク、アクションプラン、リスク管理。

## 対象市場

| 市場 | ティッカー例 | 探索メモ |
| --- | --- | --- |
| 米国 | `AAPL`, `MSFT`, `NVDA` | Yahoo Finance スクリーナーとニュース検索 |
| 中国 A 株 | `600519.SS`, `300750.SZ` | Eastmoney 市場リスト、現地名、fallback metadata |
| 香港 | `0700.HK`, `9988.HK` | Eastmoney 香港リストと会社別名 |
| 日本 | `7203.T`, `6758.T` | 現地ニュース、Google News 検索、高流動性 fallback 銘柄 |
| 韓国 | `005930.KS`, `000660.KS` | 現地ニュース、Google News 検索、高流動性 fallback 銘柄 |
| シンガポール | `D05.SI`, `C38U.SI` | SGX securities API、出来高順 |
| 台湾 | `2330.TW`, `2317.TW` | TWSE オープンデータ、現地会社名、Yahoo/TWSE fallback |

## アーキテクチャ

```text
Vue 3 web app
  -> /api/config          戦略、市場、標準ティッカーのメタデータ
  -> /api/analyze         ライブデータ取得、RSS クロール、スコアリング、説明
  -> /api/analyze/stream  インクリメンタル NDJSON スキャンイベント

Flask backend
  -> backend/universe.py   動的な市場ユニバース探索
  -> backend/providers.py  市場データプロバイダーと RSS/ニュースクローラー
  -> backend/cache.py      短期メモリキャッシュ
  -> backend/services.py   指標計算、戦略選択、説明可能なスコアリング
  -> backend/app.py        REST API
```

## ローカル開発

フロントエンド依存関係:

```powershell
npm install
```

バックエンド依存関係:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

バックエンド起動:

```powershell
python -m backend.app
```

別ターミナルでフロントエンドを起動:

```powershell
npm run dev
```

`http://127.0.0.1:5173` を開いてください。

## 静的デモとライブバックエンド

- GitHub Pages は Vue ビルドのみを配信します。Python を起動しなくても画面を確認できるよう、内蔵サンプルデータを使います。
- ローカルで `python -m backend.app` を起動すると、ライブの `/api/config`、`/api/analyze`、`/api/analyze/stream` が使えます。
- 上部のデータモード表示で、サンプルデータかライブバックエンドかを確認できます。

## ノーコード市場スキャン

メインの使い方は、任意の銘柄入力欄を空欄のままにすることです。バックエンドがリクエスト時に候補を発見し、投資研究アイデアとして順位付けします。

空欄スキャンの探索優先順:

1. 現地金融ニュースソース。
2. Google News の市場検索。
3. Yahoo、Eastmoney、SGX、TWSE などの市場ユニバース API。
4. ライブソースに到達できない場合の curated fallback symbols。

## スコアリングモデル

- `momentum`: ライブ価格履歴から見た直近トレンド。
- `value`: PER、予想 PER、PBR、利用可能な proxy 指標によるバリュエーション。
- `sentiment`: ニュースソースの信頼性、鮮度、会社関連度、見出し、RSS 要約を加味したニュース心理。
- `risk`: ベータ、実現ボラティリティ、急落チェック。
- `quality`: ROE、利益率、負債比率、成長、規模、流動性。

この結果は調査支援であり、金融助言ではありません。

## テスト

```powershell
python -m unittest discover backend/tests
npm run build
```

## 免責

このアプリケーションは投資研究ワークフローの支援のみを目的としています。金融助言ではなく、取引も実行しません。
