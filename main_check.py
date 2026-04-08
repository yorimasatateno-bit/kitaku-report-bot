"""
main_check.py — 15分おきに実行。Slack返信を確認し、カード生成→LINE送信→アーカイブ更新を行う。
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytz

from src.slack_client import open_dm_channel, get_today_alert_ts, get_thread_replies
from src.ai_parser import parse_reply
from src.card_generator import generate_html
from src.screenshot import html_to_png
from src.line_sender import send_image
from src.archive import (
    load_manifest,
    save_manifest,
    is_already_sent,
    find_reusable,
    add_entry,
    generate_index_html,
    ARCHIVE_SURGE_DOMAIN,
)

JST = pytz.timezone("Asia/Tokyo")
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]
ARCHIVE_DIR = Path(__file__).parent / "archive"
DRY_RUN = os.environ.get("DRY_RUN", "").lower() == "true"


def main():
    now_jst = datetime.now(JST)
    today = now_jst.strftime("%Y-%m-%d")
    date_str = f"{now_jst.year}年{now_jst.month}月{now_jst.day}日（{WEEKDAYS[now_jst.weekday()]}）"

    manifest_path = ARCHIVE_DIR / "manifest.json"
    manifest = load_manifest(manifest_path)

    # ── 1. 今日分が送信済みなら終了 ──
    if is_already_sent(manifest, today):
        print(f"✅ {today} は送信済みです。スキップします。")
        return

    # ── 2. 今日のSlackアラートを探す ──
    user_id = os.environ["SLACK_USER_ID"]
    channel_id = open_dm_channel(user_id)
    alert_ts = get_today_alert_ts(channel_id)

    if not alert_ts:
        print("⏳ 今日のアラートメッセージが見つかりません。スキップします。")
        return

    # ── 3. スレッド返信を取得 ──
    replies = get_thread_replies(channel_id, alert_ts)
    if not replies:
        print("⏳ まだ返信がありません。次回チェック時に再確認します。")
        return

    reply_text = replies[-1]["text"]
    print(f"📩 返信テキスト: {reply_text}")

    # ── 4. Claude で解析 ──
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

    # ── 8. surge.sh にデプロイ（LINE送信前に画像URLを有効化）──
    _deploy_archive()

    # ── 9. LINEに送信 ──
    if DRY_RUN:
        print(f"[DRY RUN] LINE送信をスキップ。URL: {png_url}")
    else:
        print("📱 LINEに送信中...")
        result = send_image(png_url)
        print(f"✅ LINE送信完了: {result}")

    # ── 10. マニフェスト更新 ──
    entry = {
        "date": today,
        "time": parsed["time"],
        "reason": parsed["reason"],
        "character": parsed["character"],
        "color_theme": parsed["color_theme"],
        "png_url": png_url,
        "sent_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "reply_text": reply_text,
        "reused": not png_saved,
    }
    manifest = add_entry(manifest, entry)
    save_manifest(manifest_path, manifest)

    # ── 11. アーカイブ index.html 再生成 → 再デプロイ（manifest反映）──
    index_html = generate_index_html(manifest)
    (ARCHIVE_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print("📄 アーカイブ index.html を更新しました。")
    _deploy_archive()

    print("🎉 完了！")


def _deploy_archive():
    surge_token = os.environ.get("SURGE_TOKEN")
    if not surge_token:
        print("⚠️  SURGE_TOKEN が未設定のためデプロイをスキップします。")
        return

    cmd = [
        "surge",
        str(ARCHIVE_DIR),
        "https://kitaku-archive.surge.sh",
        "--token", surge_token,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("🚀 surge.sh デプロイ完了: https://kitaku-archive.surge.sh")
    else:
        print(f"❌ surge デプロイ失敗:\n{result.stderr}")


if __name__ == "__main__":
    main()
