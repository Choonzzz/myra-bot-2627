# config.py
import os
import json
import pytz
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
FRIEND_TELEGRAM_IDS = json.loads(os.getenv("FRIEND_TELEGRAM_MAPPINGS"))
MONGO_URI = os.getenv("MONGO_URI")

# Singapore timezone, shared by scheduler.py and any feature that needs local time
SGT = pytz.timezone("Asia/Singapore")

# Date ranges where the bot should treat weekdays like F/S/S for refresh purposes.
# Update every semester — see README "Things to update each semester".
SCHOOL_HOLIDAYS = [
    ("2026-01-01", "2026-08-02"),  # Until 2 August 2026
    ("2026-12-06", "2027-01-10"),  # 6 December 2026 - 10 January 2027
    ("2027-05-09", "2027-08-01"),  # 9 May 2027 - 1 August 2027
]
