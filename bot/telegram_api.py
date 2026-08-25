# telegram_api.py
import requests
from config import TELEGRAM_API_URL, FRIEND_TELEGRAM_IDS, GROUP_CHAT_ID, GROUP_TOPIC_ID


def send_message(chat_id, text, parse_mode="Markdown", reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if str(chat_id) == GROUP_CHAT_ID and GROUP_TOPIC_ID is not None:
        payload["message_thread_id"] = GROUP_TOPIC_ID
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)


def answer_callback_query(callback_query_id, text=None):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    requests.post(f"{TELEGRAM_API_URL}/answerCallbackQuery", json=payload)


def edit_message_reply_markup(chat_id, message_id, reply_markup=None):
    requests.post(f"{TELEGRAM_API_URL}/editMessageReplyMarkup", json={
        "chat_id": chat_id,
        "message_id": message_id,
        "reply_markup": reply_markup or {"inline_keyboard": []}
    })


def inline_keyboard(rows):
    """rows: list of rows, each row a list of (text, callback_data) tuples."""
    return {
        "inline_keyboard": [
            [{"text": text, "callback_data": data} for text, data in row]
            for row in rows
        ]
    }


def get_user_name_from_id(user_id):
    for name, tid in FRIEND_TELEGRAM_IDS.items():
        if tid == str(user_id):
            return name
    return "Unknown User"
