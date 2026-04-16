from __future__ import annotations

import os
import requests
from datetime import datetime, timedelta
import pytz

SLACK_API = "https://slack.com/api"
JST = pytz.timezone("Asia/Tokyo")


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


def get_today_alert_ts(channel_id: str) -> str | None:
    """直近のアラートメッセージのtsを返す。
    cronの大幅遅延で日付をまたぐケースに対応するため、前日分も検索対象とする。
    """
    now_jst = datetime.now(JST)
    yesterday_jst = now_jst - timedelta(days=1)
    target_dates = {
        f"{now_jst.year}年{now_jst.month}月{now_jst.day}日",
        f"{yesterday_jst.year}年{yesterday_jst.month}月{yesterday_jst.day}日",
    }

    resp = requests.get(
        f"{SLACK_API}/conversations.history",
        params={"channel": channel_id, "limit": 30},
        headers=_headers(),
    )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"conversations.history failed: {data.get('error')}")

    for msg in data.get("messages", []):
        text = msg.get("text", "")
        if "帰宅時間レポート" in text and any(d in text for d in target_dates):
            return msg["ts"]
    return None


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
