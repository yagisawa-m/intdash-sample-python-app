# intdash-sample-python-app

intdash からリアルタイムにデータをダウンストリームして表示する、シンプルな Python サンプルアプリです。

---

## 概要

- intdash に接続し、特定のエッジデバイスからリアルタイムにデータを受信する
- 受信したデータ（JSON 文字列）をコンソールに表示する
- 将来的な GUI 対応を見据えた構成にする

---

## 要件

### 接続環境

| 項目 | 内容 |
|---|---|
| 接続先 | intdash |
| 認証方法 | API トークン（My Page で発行） |
| データ形式 | string（JSON） |
| ストリーミング | リアルタイムのみ（過去データ取得は対象外） |

### エッジデバイス

- 対象エッジは設定ファイル（config）で指定する
- 複数エッジへの対応は現時点では不要

### 表示

- 受信した JSON 文字列をコンソールに出力する
- 将来的には GUI アプリへの拡張を想定する

---

## 技術スタック

| 項目 | 内容 |
|---|---|
| 言語 | Python（バージョン指定なし） |
| ライブラリ | intdash SDK、Dear PyGui |
| 設定ファイル | TOML |

---

## 設計

### ファイル構成

```
intdash-sample-python-app/
├── README.md
├── config.toml.example   # 設定ファイルのサンプル（リポジトリ管理）
├── config.toml           # 実際の設定ファイル（.gitignore で除外）
├── main.py               # エントリーポイント（接続・受信ループ）
└── requirements.txt      # 依存ライブラリ
```

### セットアップ手順

```bash
pip install -r requirements.txt
cp config.toml.example config.toml
# config.toml に実環境の値を書き込む
python main.py
```

### 各ファイルの責務

**config.toml.example** — 設定ファイルのサンプル。リポジトリにコミットする

**config.toml** — 実環境の値を書き込む実行時設定ファイル。`.gitignore` で除外する

```toml
[intdash]
url       = "https://example.intdash.jp"
api_token = "your-api-token"
edge_uuid = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
channel   = 1
data_id   = ""   # 空文字 = 全データID、絞り込む場合は値を設定
```

| キー | 説明 |
|---|---|
| `url` | intdash サーバーの URL |
| `api_token` | My Page（`/console/me/`）で発行した API トークン |
| `edge_uuid` | 受信対象エッジの UUID |
| `channel` | データチャンネル番号（デフォルト: 1） |
| `data_id` | 受信するデータID（空文字の場合は全データIDを受信） |

**main.py** — 以下の処理を担う

1. `config.toml` を読み込む
2. intdash SDK でクライアントを生成する
3. 対象エッジの Measurement Session にサブスクライブする
4. ダウンストリームを別スレッドで起動し、受信データをキューに積む
5. Dear PyGui のウィンドウでキューを読み出してリアルタイム表示する
6. ウィンドウを閉じると終了する

### データフロー

```
config.toml
    ↓
main.py ─┬─→ [asyncio スレッド] → intdash SDK → WebSocket（リアルタイム）
         │                                            ↓ 受信
         │                                      on_data()
         │                                            ↓
         │                                      queue.Queue
         │                                            ↓
         └─→ [メインスレッド] → Dear PyGui レンダーループ → GUI 表示
```

### エラー処理方針

- 接続失敗（URL 誤り・トークン期限切れ・エッジ未存在）は `stderr` にメッセージを出力して終了する
- 受信中の例外は内容をログ出力し、可能な限り接続を維持する

---

## 将来の拡張予定

- GUI アプリの機能拡張（グラフ表示、フィルタリング UI など）
- 複数エッジへの対応
- 受信データのフィルタリング・加工
