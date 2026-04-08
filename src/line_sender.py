import os
import requests

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def send_image(image_url: str) -> dict:
    """LINE グループに画像を Push 送信する。"""
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    group_id = os.environ["LINE_GROUP_ID"]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "to": group_id,
        "messages": [
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url,
            }
        ],
    }
    resp = requests.post(LINE_PUSH_URL, json=payload, headers=headers)
    if not resp.ok:
        raise RuntimeError(f"LINE API error {resp.status_code}: {resp.text}")
    return resp.json()
