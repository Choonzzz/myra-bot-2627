# telegram_api.py
import requests
from config import TELEGRAM_API_URL, FRIEND_TELEGRAM_IDS, GROUP_CHAT_ID, GROUP_TOPIC_ID


def send_message(chat_id, text, parse_mode="Markdown"):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if str(chat_id) == GROUP_CHAT_ID:
        payload["message_thread_id"] = GROUP_TOPIC_ID
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)


def get_user_name_from_id(user_id):
    for name, tid in FRIEND_TELEGRAM_IDS.items():
        if tid == str(user_id):
            return name
    return "Unknown User"
