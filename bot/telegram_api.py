# telegram_api.py
import requests
from config import TELEGRAM_API_URL, FRIEND_TELEGRAM_IDS


def send_message(chat_id, text, parse_mode="Markdown"):
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    })


def get_user_name_from_id(user_id):
    for name, tid in FRIEND_TELEGRAM_IDS.items():
        if tid == str(user_id):
            return name
    return "Unknown User"
