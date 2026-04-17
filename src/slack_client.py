from __future__ import annotations

import os
import requests
from datetime import datetime, timedelta
import pytz

SLACK_API = "https://slack.com/api"
JST = pytz.timezone("Asia/Tokyo")
_HISTORY_LIMIT = 30


def _jst_date_key(dt: datetime) -> str:
    """投稿本文に含まれる日付プレフィックス（例: 2026年4月17日）。"""
    return f"{dt.year}年{dt.month}月{dt.day}日"


def _collect_alert_tss_for_date(messages: list, date_key: str) -> list[str]:
    tss: list[str] = []
    for msg in messages:
        text = msg.get("text", "")
        if "帰宅時間レポート" in text and date_key in text:
            tss.append(msg["ts"])
    return tss


def _oldest_ts(tss: list[str]) -> str | None:
    if not tss:
        return None
    return min(tss, key=lambda s: float(s))


def _fetch_im_history(channel_id: str) -> list:
    resp = requests.get(
        f"{SLACK_API}/conversations.history",
        params={"channel": channel_id, "limit": _HISTORY_LIMIT},
        headers=_headers(),
    )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"conversations.history failed: {data.get('error')}")
    return data.get("messages", [])


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}",
        "Content-Type": "application/json",
    }


def open_dm_channel(user_id: str) -> str:
    """ユーザーとのDMチャンネルを開き、チャンネルIDを返す。"""
    resp = requests.post(
        f"{SLACK_API}/conversations.open",
        json={"users": user_id},
        headers=_headers(),
    )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"conversations.open failed: {data.get('error')}")
    return data["channel"]["id"]


def post_alert(channel_id: str, date_str: str) -> str:
    """帰宅時間レポートのアラートを投稿し、メッセージのtsを返す。"""
    resp = requests.post(
        f"{SLACK_API}/chat.postMessage",
        json={
            "channel": channel_id,
            "text": (
                f":house: *帰宅時間レポート* — {date_str}\n\n"
                "今日の帰宅予定時刻と理由を *このメッセージにスレッド返信* してください。\n"
                "例: `2030 コンテンツチェックが長引いた`"
            ),
        },
        headers=_headers(),
    )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"chat.postMessage failed: {data.get('error')}")
    return data["ts"]


def alert_already_posted_today(channel_id: str, day_jst: datetime) -> bool:
    """同一JST日のアラートが既にあれば True（launchd と遅延 cron の二重投稿を防ぐ）。"""
    date_key = _jst_date_key(day_jst)
    messages = _fetch_im_history(channel_id)
    return bool(_collect_alert_tss_for_date(messages, date_key))


def get_today_alert_ts(channel_id: str) -> str | None:
    """対象日のアラートメッセージのtsを返す。
    cronの大幅遅延で日付をまたぐケースに対応するため、前日分も検索対象とする。
    同一日に複数ある場合は **最古の ts**（先に投稿されたアラート）を採用する。
    """
    now_jst = datetime.now(JST)
    yesterday_jst = now_jst - timedelta(days=1)
    today_key = _jst_date_key(now_jst)
    yesterday_key = _jst_date_key(yesterday_jst)

    messages = _fetch_im_history(channel_id)

    today_ts = _oldest_ts(_collect_alert_tss_for_date(messages, today_key))
    if today_ts:
        return today_ts

    return _oldest_ts(_collect_alert_tss_for_date(messages, yesterday_key))


def get_thread_replies(channel_id: str, thread_ts: str) -> list[dict]:
    """スレッドの返信一覧を返す（元メッセージを除く）。"""
    resp = requests.get(
        f"{SLACK_API}/conversations.replies",
        params={"channel": channel_id, "ts": thread_ts},
        headers=_headers(),
    )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"conversations.replies failed: {data.get('error')}")

    messages = data.get("messages", [])
    # 最初のメッセージ（元の投稿）を除いた返信のみ返す
    return [m for m in messages[1:] if m.get("text")]
