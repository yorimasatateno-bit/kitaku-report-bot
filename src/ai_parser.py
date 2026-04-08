"""
ルールベースの返信パーサー。
「2030 コンテンツチェックが遅くまでかかって」のような
Slack返信テキストを、カード生成用データに変換する。
"""
from __future__ import annotations

import re

# ── 時刻ベースのキャラクター・カラー設定 ──────────────────────
def _time_to_meta(hour: int, minute: int) -> dict:
    total = hour * 60 + minute
    if total <= 19 * 60 + 30:
        return {"character": "standard",  "color_theme": "green",  "transport_icon": "✅"}
    elif total <= 21 * 60:
        return {"character": "anxious",   "color_theme": "amber",  "transport_icon": "🚃"}
    elif total <= 22 * 60 + 30:
        return {"character": "tearful",   "color_theme": "blue",   "transport_icon": "🌙"}
    else:
        return {"character": "panicking", "color_theme": "red",    "transport_icon": "🚨"}


# ── 理由キーワード → キャラクター上書き ──────────────────────
REASON_OVERRIDES = {
    "apologetic": ["会食", "接待", "飲み", "ご飯", "食事", "dinner"],
    "panicking":  ["トラブル", "障害", "緊急", "事故", "炎上"],
    "confident":  ["定時", "早退"],
}

def _reason_to_character(reason: str, default: str) -> str:
    for character, keywords in REASON_OVERRIDES.items():
        if any(kw in reason for kw in keywords):
            return character
    return default


# ── 遅延ラベル（19:00退社基準）──────────────────────────────
def _delay_label(hour: int, minute: int) -> str:
    base = 19 * 60
    total = hour * 60 + minute
    diff = total - base
    if diff <= 0:
        return "定時退社！"
    h, m = divmod(diff, 60)
    if m == 0:
        return f"通常より約{h}h遅め"
    elif m <= 30:
        return f"通常より約{h}.5h遅め"
    else:
        return f"通常より約{h+1}h遅め"


# ── セリフテンプレート（時間帯 × 雰囲気）────────────────────
MESSAGES = {
    "green": [
        "今日は早く帰れるよ〜！😊\nご飯一緒に食べよう！\n楽しみにしてるね🍚",
        "定時で上がれました！\nもうすぐ帰るよ〜😄\nお腹すいた〜🍽️",
    ],
    "amber": [
        "{reason}で\nちょっと遅くなりそう😅\nご飯先に食べてて〜🙏",
        "{reason}が長引いてます…\nなるべく早く帰ります！\n待っててね😅",
        "もう少しかかりそうです🙏\n{reason}が終わったら出ます！\nごめんね〜😣",
    ],
    "blue": [
        "ごめんなさい😢\n{reason}で遅くなりました…\n先に寝ててもいいよ🌙",
        "{reason}で遅くなってしまいました😭\n本当にごめんね…\nもうちょっとで終わります🙏",
    ],
    "red": [
        "やばい！{reason}で\nめちゃくちゃ遅くなりました😱\n先に寝ててください！！🙏🙏",
        "本当に申し訳ない😱\n{reason}のせいで終電ギリギリ…\nごめんなさい！！！",
    ],
}

def _make_message(color_theme: str, reason: str) -> str:
    import random
    templates = MESSAGES.get(color_theme, MESSAGES["amber"])
    template = random.choice(templates)
    return template.format(reason=reason)


# ── バッジ生成 ────────────────────────────────────────────────
REASON_BADGES = {
    "会食":         "🍽️ 会食あり",
    "接待":         "🍽️ 接待あり",
    "飲み":         "🍺 飲み会あり",
    "打ち合わせ":   "💼 打ち合わせ",
    "会議":         "💼 会議",
    "トラブル":     "⚡ 緊急対応",
    "障害":         "⚡ 障害対応",
    "残業":         "⏰ 残業",
    "コンテンツ":   "📝 コンテンツ作業",
    "チェック":     "📝 チェック作業",
    "撮影":         "🎥 撮影",
    "ロケ":         "🎥 ロケ",
    "定時":         "🎉 定時退社",
}

def _make_badges(reason: str, color_theme: str) -> list[str]:
    badges = []
    for keyword, badge in REASON_BADGES.items():
        if keyword in reason and badge not in badges:
            badges.append(badge)
    if not badges:
        badges.append(f"📝 {reason[:10]}")
    badges.append("💬 返信不要")
    return badges[:3]


# ── 時刻パース ────────────────────────────────────────────────
def _parse_time(text: str) -> tuple[int, int] | None:
    """テキストから時刻を抽出して (hour, minute) を返す。"""
    patterns = [
        r'(\d{1,2})[:\s時](\d{2})分?',   # 20:30 / 20時30 / 20 30
        r'(\d{4})',                         # 2030
        r'(\d{1,2})時(半)',                 # 8時半
        r'(\d{1,2})時',                     # 20時
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            g = m.groups()
            if len(g) == 2 and g[1] == "半":
                return int(g[0]), 30
            elif len(g) == 2:
                h, mi = int(g[0]), int(g[1])
                if 0 <= h <= 23 and 0 <= mi <= 59:
                    return h, mi
            elif len(g) == 1:
                raw = g[0]
                if len(raw) == 4:
                    h, mi = int(raw[:2]), int(raw[2:])
                    if 0 <= h <= 23 and 0 <= mi <= 59:
                        return h, mi
                elif len(raw) <= 2:
                    h = int(raw)
                    if 0 <= h <= 23:
                        return h, 0
    return None


def _extract_reason(text: str) -> str:
    """テキストから時刻部分を取り除いた理由テキストを返す。"""
    cleaned = re.sub(
        r'\d{4}|\d{1,2}[:\s時]\d{2}分?|\d{1,2}時半?', '', text
    ).strip()
    cleaned = re.sub(r'^[\s\-ごろ頃くらいに帰りますで]+', '', cleaned).strip()
    return cleaned or "業務"


# ── メインパース関数 ──────────────────────────────────────────
def parse_reply(reply_text: str) -> dict:
    """Slack返信テキストをカード生成用データに変換する。"""
    time_result = _parse_time(reply_text)

    if time_result:
        hour, minute = time_result
        time_str = f"{hour:02d}:{minute:02d}"
    else:
        hour, minute = 20, 0
        time_str = "20:00"

    reason = _extract_reason(reply_text)
    meta = _time_to_meta(hour, minute)
    character = _reason_to_character(reason, meta["character"])

    return {
        "time":           time_str,
        "reason":         reason,
        "message":        _make_message(meta["color_theme"], reason),
        "character":      character,
        "badges":         _make_badges(reason, meta["color_theme"]),
        "delay_label":    _delay_label(hour, minute),
        "transport_icon": meta["transport_icon"],
        "color_theme":    meta["color_theme"],
    }
