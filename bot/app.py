# app.py
from flask import Flask, request
import os
from dotenv import load_dotenv
from conversation import handle_update
from features.status import auto_refresh, send_duty_reminders
from features.misc import daily_checkup
from redis_client import get_redis

load_dotenv()

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print(data)

    # Telegram retries the webhook if it doesn't get a 200 back quickly enough,
    # which resends the same update_id. Drop repeats so replies aren't processed twice.
    update_id = data.get("update_id")
    if update_id is not None:
        r = get_redis()
        is_new = r.set(f"seen_update:{update_id}", "1", nx=True, ex=3600)
        if not is_new:
            return "OK", 200

    handle_update(data)
    return "OK", 200
  
@app.route("/refresh", methods=["GET"])
def refresh():
    auto_refresh()
    return "OK", 200

@app.route("/reminder", methods=["GET"])
def reminder():
    send_duty_reminders()
    return "OK", 200

@app.route("/wellbeing", methods=["GET"])
def wellbeing():
    daily_checkup()
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
