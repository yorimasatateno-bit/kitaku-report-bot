"""
main_check.py — 15分おきに実行。Slack返信を確認し、カード生成まで行う。
surge デプロイと LINE 送信は YAML ワークフローのステップに委譲する。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pytz

from src.slack_client import open_dm_channel, get_today_alert_ts, get_thread_replies
from src.ai_parser import parse_reply
from src.card_generator import generate_html
from src.screenshot import html_to_png
from src.archive import (
    load_manifest,
    is_already_sent,
    find_reusable,
    ARCHIVE_SURGE_DOMAIN,
)

JST = pytz.timezone("Asia/Tokyo")
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]
ARCHIVE_DIR = Path(__file__).parent / "archive"
READY_FILE = ARCHIVE_DIR / ".ready_to_send"


def main():
    manifest_path = ARCHIVE_DIR / "manifest.json"
    manifest = load_manifest(manifest_path)

    # ── 1. 直近のSlackアラートを探す ──
    user_id = os.environ["SLACK_USER_ID"]
    channel_id = open_dm_channel(user_id)
    alert_ts = get_today_alert_ts(channel_id)

    if not alert_ts:
        print("⏳ 直近のアラートメッセージが見つかりません。スキップします。")
        return

    # alert_tsのJST日付を「有効日付」とする（cronが深夜に遅延実行されても正しい日付を使う）
    alert_jst = datetime.fromtimestamp(float(alert_ts), tz=JST)
    today = alert_jst.strftime("%Y-%m-%d")
    date_str = f"{alert_jst.year}年{alert_jst.month}月{alert_jst.day}日（{WEEKDAYS[alert_jst.weekday()]}）"
    print(f"📅 有効日付（アラート送信日）: {today}")

    # ── 2. 今日分が送信済みなら終了 ──
    if is_already_sent(manifest, today):
        print(f"✅ {today} は送信済みです。スキップします。")
        return

    # ── 3. スレッド返信を取得 ──
    replies = get_thread_replies(channel_id, alert_ts)
    if not replies:
        print("⏳ まだ返信がありません。次回チェック時に再確認します。")
        return

    reply_text = replies[-1]["text"]
    print(f"📩 返信テキスト: {reply_text}")

    # ── 4. 解析 ──
    parsed = parse_reply(reply_text)
    print(f"🤖 解析結果: {json.dumps(parsed, ensure_ascii=False)}")

    # ── 5. 再利用可能なカードがあるか確認 ──
    existing = find_reusable(manifest, parsed["time"], parsed["reason"])

    if existing:
        print(f"♻️  同じ時間・理由のカードを再利用: {existing['png_url']}")
        png_url = existing["png_url"]
        png_saved = False
    else:
        # ── 6. HTMLカード生成 → PNG化 ──
        print("🎨 カードを生成中...")
        html_content = generate_html(parsed, date_str)
        png_bytes = html_to_png(html_content)

        # ── 7. PNGをアーカイブに保存 ──
        cards_dir = ARCHIVE_DIR / "cards"
        cards_dir.mkdir(exist_ok=True)
        png_filename = f"{today}.png"
        (cards_dir / png_filename).write_bytes(png_bytes)
        print(f"💾 PNG保存: archive/cards/{png_filename}")

        png_url = f"{ARCHIVE_SURGE_DOMAIN}/cards/{png_filename}"
        png_saved = True

    # ── 8. surge デプロイ・LINE送信の情報をファイルに書き出し ──
    ready_data = {
        "today": today,
        "png_url": png_url,
        "png_saved": png_saved,
        "parsed": parsed,
        "reply_text": reply_text,
    }
    READY_FILE.write_text(json.dumps(ready_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"📝 .ready_to_send を作成しました。次のステップで surge デプロイ → LINE 送信を行います。")


if __name__ == "__main__":
    main()
