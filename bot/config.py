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

# The group has Topics enabled; all bot messages to the group are routed into this
# topic thread rather than the General thread. Update if the topic changes.
GROUP_TOPIC_ID = 2146 # points to choon corner
FRIEND_TELEGRAM_IDS = json.loads(os.getenv("FRIEND_TELEGRAM_MAPPINGS"))

# Explicit display order for RA names in listings (e.g. /swap_duty), independent
# of whatever order FRIEND_TELEGRAM_MAPPINGS happens to be written in. Reorder
# this list to change it. Defaults to the mapping's own order if left as-is.
RA_DISPLAY_ORDER = ["Anderson",
                    "Shi Hui",
                    "Zedd",
                    "Siyu",
                    "Brendon",
                    "Nicole",
                    "Kasthuri",
                    "Yap Han",
                    "Don",
                    "Liya",
                    "Jin Xian",
                    "Zhen Jie",
                    "Jeana",
                    "Choon Heng",
                    "Lex"]

def ordered_friend_names():
    """Friend names in RA_DISPLAY_ORDER, with any names missing from that list
    (e.g. newly added to FRIEND_TELEGRAM_MAPPINGS but not yet to the order list)
    appended at the end so nobody is silently dropped from listings."""
    ordered = [name for name in RA_DISPLAY_ORDER if name in FRIEND_TELEGRAM_IDS]
    remaining = [name for name in FRIEND_TELEGRAM_IDS if name not in RA_DISPLAY_ORDER]
    return ordered + remaining

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
