# 家蔵への帰宅時間レポートBot 🏠

毎日**平日17:00（JST）**にSlack DMへアラートを送り（GitHub Actions の遅延対策で Mac の launchd から `workflow_dispatch` を併用する運用も可）、スレッド返信をもとにマジくん入りカード画像を生成して家族のLINEグループに送信するBot。

## 動作フロー

```
平日17:00 JST [GitHub Actions] send_alert.yml（cron: UTC 08:00）
  → Slack自分DM に帰宅時間レポートのアラートを投稿

あなたがスレッドに返信
  例: "2030 コンテンツチェックが遅くまでかかって"

17:00〜23:45 JST 相当の窓で 15分おきに [GitHub Actions] check_reply.yml
  → Slack返信を確認
  → Claude API で時間・理由・感情を解析
  → Tailwind HTMLカードを生成 → Playwright でPNG化
  → surge.sh アーカイブにアップロード
  → LINE家族グループに画像を送信
```

## セットアップ手順

### 1. このフォルダを独立したGitHubリポジトリにする

```bash
cd tools/kitaku-report-bot
git init
git add .
git commit -m "initial commit"
# GitHubで新しいリポジトリを作成してpush
git remote add origin https://github.com/YOUR_USERNAME/kitaku-report-bot.git
git push -u origin main
```

---

### 2. Slack Appを作成する

1. [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → From scratch
2. アプリ名: `帰宅レポートBot` など、任意のワークスペースを選択
3. **OAuth & Permissions** → **Bot Token Scopes** に以下を追加:
   - `chat:write`
   - `im:write`
   - `im:history`
4. **Install to Workspace** → Bot User OAuth Token（`xoxb-...`）をコピー
5. 自分のSlackユーザーIDを確認（プロフィール → ⋮ → **メンバーIDをコピー**）

---

### 3. LINE Messaging API チャンネルを作成する

1. [developers.line.biz](https://developers.line.biz) にログイン
2. **新規プロバイダー作成** → **新規チャンネル作成** → Messaging API
3. チャンネル名・説明を入力して作成
4. **Messaging API設定** タブ → **チャンネルアクセストークン（長期）** を発行・コピー
5. 作成したBotを家族のLINEグループに追加する
6. グループIDの取得（初回メッセージ受信後にWebhookで確認 or 下記の方法）

**グループIDを取得する方法:**
- LINEチャンネルのWebhook URLに一時的にRequestBinなどのURL（例: `https://webhook.site/xxx`）を設定
- グループでBotに話しかけると `destination` フィールドにグループIDが届く

---

### 4. surge トークンを取得する

```bash
surge token
# → 表示されたトークンをコピー
```

---

### 5. GitHub Secrets に登録する

GitHubリポジトリの **Settings → Secrets and variables → Actions → New repository secret**

| Secret名 | 値 |
|---|---|
| `SLACK_BOT_TOKEN` | Slack Bot Token（`xoxb-...`） |
| `SLACK_USER_ID` | 自分のSlackユーザーID（`U...`） |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) で取得 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE チャンネルアクセストークン |
| `LINE_GROUP_ID` | LINEグループID（`C...`） |
| `SURGE_TOKEN` | `surge token` で取得したトークン |

---

### 6. 動作確認（ローカル）

```bash
pip install -r requirements.txt
playwright install chromium

# 環境変数を設定
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_USER_ID="U..."
export ANTHROPIC_API_KEY="sk-ant-..."
export LINE_CHANNEL_ACCESS_TOKEN="..."
export LINE_GROUP_ID="C..."
export DRY_RUN="true"  # LINE送信をスキップ

# アラート送信テスト
python main_alert.py

# 返信チェック＆カード生成テスト（LINE送信はスキップ）
python main_check.py
```

### 7. GitHub Actions から手動実行テスト

**Actions タブ → 「帰宅時間レポート — 返信チェック＆LINE送信」→ Run workflow**

`dry_run: true` にするとLINE送信をスキップしてカード生成だけ確認できます。

---

## ファイル構成

```
.
├── main_alert.py              # 平日17:00 JST 想定: Slackアラート送信
├── main_check.py              # 15分おき実行: 返信チェック〜カード生成（送信は workflow 側）
├── requirements.txt
├── src/
│   ├── slack_client.py        # Slack API操作
│   ├── ai_parser.py           # Claude APIで返信を構造化
│   ├── card_generator.py      # Tailwind HTMLカード生成
│   ├── screenshot.py          # Playwright → PNG化
│   ├── line_sender.py         # LINE Messaging API送信
│   └── archive.py             # アーカイブ管理
├── cards/
│   └── マジくん-*.png          # キャラクター画像
├── archive/
│   ├── manifest.json          # 送信履歴（自動更新）
│   ├── index.html             # アーカイブページ（自動生成）
│   └── cards/                 # 生成されたPNG（自動保存）
└── .github/workflows/
    ├── send_alert.yml          # 17:00 JST cron（UTC 08:00）
    └── check_reply.yml         # 15分おき cron（17:00〜23:45 JST 相当）
```

## アーカイブページ

送信済みカードは [maji-kitaku.surge.sh](https://maji-kitaku.surge.sh) で確認できます（`src/archive.py` の `ARCHIVE_SURGE_DOMAIN` と一致）。

## 再利用ロジック

同じ帰宅時刻・同じ理由で過去に生成されたカードがある場合、PNG生成をスキップして既存の画像URLを再利用します（Playwright実行コストを節約）。

## 運用上の注意

- **GitHub Actions の schedule の遅延**: 発火が数時間ずれることがある。正時に近い実行が必要なら、Mac 常駐時は `workflow_dispatch` を launchd 等から叩く運用が有効（トークンは **Classic PAT**、`repo` + `workflow`）。Fine-grained PAT だと `workflow_dispatch` が 403 になりやすい。
- **日付ずれ（深夜に遅延実行）**: `get_today_alert_ts()` が前日アラートも拾い、`main_check.py` は `alert_ts` の JST 日付を有効日付にしている。
- **二重アラート / 二重 LINE**: 同一 JST 日は `main_alert.py` が履歴を見て **2通目を投稿しない**。返信探索は同日に複数ある場合 **最古のアラート** を採用。GitHub Actions は `concurrency` で同種ワークフローの同時実行を抑止。`main_send_line.py` は manifest 済みなら LINE を送らない。
- **トークン期限**: PAT / `SURGE_TOKEN` は失効前に再発行し、ローカル `.env` や GitHub Secrets を更新する。
- **Mac がスリープ中**: launchd は動かない。代替は手動ディスパッチまたは Actions の schedule 任せ（遅延あり）。
