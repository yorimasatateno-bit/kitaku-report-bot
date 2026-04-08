from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ARCHIVE_SURGE_DOMAIN = "https://kitaku-archive.surge.sh"


def load_manifest(path: Path) -> list:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def save_manifest(path: Path, manifest: list) -> None:
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def is_already_sent(manifest: list, date: str) -> bool:
    return any(e.get("date") == date for e in manifest)


def find_reusable(manifest: list, time: str, reason: str) -> dict | None:
    """同じtime・reasonのカードが過去にあれば返す。"""
    for entry in manifest:
        if entry.get("time") == time and entry.get("reason") == reason:
            return entry
    return None


def add_entry(manifest: list, entry: dict) -> list:
    manifest.append(entry)
    return manifest


def generate_index_html(manifest: list) -> str:
    sorted_entries = sorted(manifest, key=lambda e: e.get("date", ""), reverse=True)

    cards_html = ""
    if not sorted_entries:
        cards_html = '<p class="text-center text-slate-400 py-16">まだ記録がありません</p>'
    else:
        for e in sorted_entries:
            date = e.get("date", "")
            time = e.get("time", "--:--")
            reason = e.get("reason", "")
            png_url = e.get("png_url", "")
            sent_at = e.get("sent_at", "")
            try:
                dt = datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
                sent_label = dt.strftime("%Y/%m/%d %H:%M")
            except Exception:
                sent_label = sent_at

            cards_html += f"""
        <div class="bg-white rounded-2xl shadow-sm overflow-hidden border border-slate-100">
          <img src="{png_url}" alt="{date} 帰宅カード" class="w-full">
          <div class="px-4 py-3">
            <div class="text-sm font-bold text-slate-700">{date}</div>
            <div class="text-xs text-slate-500 mt-1">🕐 {time} ／ 📝 {reason}</div>
            <div class="text-xs text-slate-400 mt-1">送信: {sent_label}</div>
          </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>帰宅時間レポート アーカイブ</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">
  <style>body {{ font-family: 'Noto Sans JP', sans-serif; background: #f8fafc; }}</style>
</head>
<body class="py-10 px-4">
  <div class="max-w-2xl mx-auto">
    <h1 class="text-2xl font-bold text-slate-700 mb-1 text-center">🏠 帰宅時間レポート</h1>
    <p class="text-center text-slate-400 text-sm mb-8">過去の送信カード一覧（{len(sorted_entries)}件）</p>
    <div class="grid grid-cols-2 gap-4">
      {cards_html}
    </div>
  </div>
  <p class="text-center text-xs text-slate-300 mt-10">自動レポートBot × マジくん</p>
</body>
</html>"""
