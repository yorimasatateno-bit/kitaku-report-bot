import base64
from pathlib import Path

CARDS_DIR = Path(__file__).parent.parent / "cards"

COLOR_THEMES = {
    "green": {
        "bg": "linear-gradient(145deg, #f0fdf4 0%, #dcfce7 55%, #bbf7d0 100%)",
        "header": "linear-gradient(90deg, #16a34a, #15803d)",
        "border": "#86efac",
        "label": "#166534",
        "time_color": "#15803d",
        "badge_bg": "#dcfce7",
        "badge_border": "#86efac",
        "badge_color": "#166534",
        "footer_color": "#16a34a",
    },
    "amber": {
        "bg": "linear-gradient(145deg, #fff8e7 0%, #fef3c7 55%, #fde68a 100%)",
        "header": "linear-gradient(90deg, #d97706, #f97316)",
        "border": "#fcd34d",
        "label": "#b45309",
        "time_color": "#d97706",
        "badge_bg": "#fef3c7",
        "badge_border": "#fcd34d",
        "badge_color": "#92400e",
        "footer_color": "#b45309",
    },
    "blue": {
        "bg": "linear-gradient(145deg, #eff6ff 0%, #dbeafe 55%, #bfdbfe 100%)",
        "header": "linear-gradient(90deg, #2563eb, #7c3aed)",
        "border": "#93c5fd",
        "label": "#1e40af",
        "time_color": "#2563eb",
        "badge_bg": "#dbeafe",
        "badge_border": "#93c5fd",
        "badge_color": "#1e3a8a",
        "footer_color": "#2563eb",
    },
    "red": {
        "bg": "linear-gradient(145deg, #fff1f2 0%, #ffe4e6 55%, #fecdd3 100%)",
        "header": "linear-gradient(90deg, #e11d48, #be123c)",
        "border": "#fca5a5",
        "label": "#9f1239",
        "time_color": "#e11d48",
        "badge_bg": "#ffe4e6",
        "badge_border": "#fca5a5",
        "badge_color": "#881337",
        "footer_color": "#e11d48",
    },
}

CHARACTER_FILES = {
    "standard":   "マジくん-標準-512×512-透過.png",
    "anxious":    "マジくん-焦り-512×512-透過.png",
    "tearful":    "マジくん-涙ぐむ-512×512-透過.png",
    "panicking":  "マジくん-ひどく慌てている-512×512-透過.png",
    "apologetic": "マジくん-自信がない、落ち込んでいる-512×512-透過.png",
    "confident":  "マジくん-調子に乗ってる-512×512-透過.png",
}


def _img_b64(filename: str) -> str:
    path = CARDS_DIR / filename
    return base64.b64encode(path.read_bytes()).decode()


def generate_html(parsed: dict, date_str: str) -> str:
    theme = COLOR_THEMES.get(parsed.get("color_theme", "amber"), COLOR_THEMES["amber"])
    char_file = CHARACTER_FILES.get(parsed.get("character", "anxious"), CHARACTER_FILES["anxious"])
    char_b64 = _img_b64(char_file)

    badges_html = "".join(
        f'<span class="badge">{b}</span>' for b in parsed.get("badges", [])
    )
    message_html = parsed.get("message", "").replace("\n", "<br>")

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ width: 480px; height: 480px; overflow: hidden; font-family: 'Noto Sans JP', sans-serif; }}
    .card {{ width: 480px; height: 480px; background: {theme['bg']}; display: flex; flex-direction: column; }}
    .header {{ background: {theme['header']}; padding: 14px 22px; display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; }}
    .sub {{ font-size: 11px; color: rgba(255,255,255,0.8); font-weight: 500; }}
    .title {{ font-size: 17px; color: white; font-weight: 700; }}
    .body {{ flex: 1; display: flex; flex-direction: column; padding: 16px 20px 12px; gap: 12px; }}
    .character-row {{ display: flex; align-items: flex-start; gap: 12px; }}
    .majikun {{ width: 110px; height: 110px; object-fit: contain; flex-shrink: 0; filter: drop-shadow(0 3px 8px rgba(0,0,0,0.12)); }}
    .bubble {{ background: white; border: 2px solid {theme['border']}; border-radius: 16px 16px 16px 4px; padding: 11px 14px; font-size: 13.5px; line-height: 1.7; color: #374151; box-shadow: 0 2px 8px rgba(0,0,0,0.07); flex: 1; }}
    .time-box {{ background: rgba(255,255,255,0.72); border: 2px solid {theme['border']}; border-radius: 18px; padding: 12px 18px; display: flex; align-items: center; justify-content: space-between; }}
    .time-label {{ font-size: 10px; font-weight: 700; color: {theme['label']}; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 2px; }}
    .time-value {{ font-size: 50px; font-weight: 900; color: {theme['time_color']}; line-height: 1; letter-spacing: -2px; }}
    .time-sub {{ font-size: 11px; color: #78716c; font-weight: 500; margin-top: 2px; }}
    .badges {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .badge {{ background: {theme['badge_bg']}; border: 1.5px solid {theme['badge_border']}; color: {theme['badge_color']}; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; }}
    .footer {{ padding: 8px 20px 10px; text-align: center; flex-shrink: 0; }}
    .footer-text {{ font-size: 10px; color: {theme['footer_color']}; opacity: 0.7; font-weight: 500; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div>
        <div class="sub">帰宅時間のお知らせ</div>
        <div class="title">{date_str} 🏠</div>
      </div>
      <div style="font-size:22px;">{parsed.get('transport_icon', '🚃')}</div>
    </div>
    <div class="body">
      <div class="character-row">
        <img src="data:image/png;base64,{char_b64}" class="majikun" alt="マジくん">
        <div style="flex:1;padding-top:4px;">
          <div class="bubble">{message_html}</div>
        </div>
      </div>
      <div class="time-box">
        <div>
          <div class="time-label">帰宅予定時刻</div>
          <div class="time-value">{parsed.get('time', '--:--')}</div>
          <div class="time-sub">ごろ帰ります</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:28px;">⏱️</div>
          <div class="time-sub" style="margin-top:4px;">{parsed.get('delay_label', '')}</div>
        </div>
      </div>
      <div class="badges">{badges_html}</div>
    </div>
    <div class="footer">
      <div class="footer-text">自動レポートBot 🤖 × マジくん ／ Slack返信から自動生成</div>
    </div>
  </div>
</body>
</html>"""
