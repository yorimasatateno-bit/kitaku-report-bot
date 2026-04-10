"""
main_send_line.py — surge デプロイ完了後に呼び出す。
.ready_to_send を読み込み、LINE送信・manifest更新・index.html再生成を行う。
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytz

from src.line_sender import send_image
from src.archive import (
    load_manifest,
    save_manifest,
    add_entry,
    generate_index_html,
)

JST = pytz.timezone("Asia/Tokyo")
ARCHIVE_DIR = Path(__file__).parent / "archive"
READY_FILE = ARCHIVE_DIR / ".ready_to_send"
DRY_RUN = os.environ.get("DRY_RUN", "").lower() == "true"


def main():
    if not READY_FILE.exists():
        print("⏭️  .ready_to_send が見つかりません。スキップします。")
        return

    data = json.loads(READY_FILE.read_text(encoding="utf-8"))
    png_url = data["png_url"]
    today = data["today"]
    parsed = data["parsed"]
    reply_text = data["reply_text"]
    png_saved = data["png_saved"]

    # ── LINE送信 ──
    if DRY_RUN:
        print(f"[DRY RUN] LINE送信をスキップ。URL: {png_url}")
    else:
        print("📱 LINEに送信中...")
        result = send_image(png_url)
        print(f"✅ LINE送信完了: {result}")

    # ── manifest更新 ──
    manifest_path = ARCHIVE_DIR / "manifest.json"
    manifest = load_manifest(manifest_path)
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

    # ── index.html 再生成 ──
    index_html = generate_index_html(manifest)
    (ARCHIVE_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print("📄 アーカイブ index.html を更新しました。")

    # ── フラグファイル削除 ──
    READY_FILE.unlink()
    print("🎉 完了！")


if __name__ == "__main__":
    main()
