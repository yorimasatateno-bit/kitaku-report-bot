"""
main_alert.py — 平日 17:00 JST 想定で実行。Slack DM にアラートメッセージを投稿する。
"""
import os
from datetime import datetime
import pytz

from src.slack_client import open_dm_channel, post_alert, alert_already_posted_today

JST = pytz.timezone("Asia/Tokyo")
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]


def main():
    now = datetime.now(JST)
    date_str = f"{now.year}年{now.month}月{now.day}日（{WEEKDAYS[now.weekday()]}）"

    user_id = os.environ["SLACK_USER_ID"]
    channel_id = open_dm_channel(user_id)

    if alert_already_posted_today(channel_id, now):
        print(f"⏭️  本日のアラートは既に送信済みです。スキップします。（{date_str}）")
        return

    ts = post_alert(channel_id, date_str)

    print(f"✅ アラート送信完了")
    print(f"   日付: {date_str}")
    print(f"   channel: {channel_id}")
    print(f"   ts: {ts}")


if __name__ == "__main__":
    main()
