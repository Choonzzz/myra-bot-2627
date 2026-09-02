# features/misc.py
import random

from redis_client import get_redis
from config import FRIEND_TELEGRAM_IDS
from telegram_api import send_message

WELLBEING_QUESTIONS = [
    "How are you feeling today?",
    "Did you get enough sleep last night?",
    "Have you eaten properly today?",
    "Are you feeling stressed this week?",
    "Do you feel motivated for your classes?",
    "Is there anything making you anxious right now?",
    "Have you taken any breaks today?",
    "Did you spend time with friends recently?",
    "Do you feel overwhelmed by your workload?",
    "Are you managing your time well?",
    "Have you gone outside today?",
    "Do you feel supported by those around you?",
    "How’s your energy level today?",
    "Are you keeping up with your assignments?",
    "Have you exercised this week?",
    "Are you feeling lonely?",
    "Have you done anything just for fun lately?",
    "Do you feel in control of your schedule?",
    "Have you talked to anyone about how you’re feeling?",
    "Do you feel safe where you live?",
    "Have you been procrastinating a lot?",
    "Do you feel confident in your abilities?",
    "Have you experienced any mood swings recently?",
    "Are you drinking enough water?",
    "Do you feel pressure to perform well academically?",
    "Are you looking forward to anything this week?",
    "Have you had any conflicts with friends or classmates?",
    "Is there anything you're worried about right now?",
    "Have you laughed recently?",
    "Do you feel like you belong in your university community?",
    "Are you finding time to relax?",
    "Have you been feeling hopeful about the future?",
    "Do you feel bored or unchallenged?",
    "Have you been avoiding responsibilities?",
    "Are you satisfied with your social life?",
    "Do you feel homesick?",
    "Have you attended all your classes this week?",
    "Have you felt burnt out recently?",
    "Are you happy with your current routine?",
    "Have you had any trouble concentrating?",
    "Have you been sleeping too much or too little?",
    "Do you feel comfortable asking for help when needed?",
    "Have you been able to express your feelings openly?",
    "Are you worried about finances?",
    "Do you feel proud of something you did this week?",
    "Have you spent time offline today?",
    "Do you feel anxious about the future?",
    "Have you had a moment of peace today?",
    "Are you eating regular meals?",
    "Have you done something creative recently?",
    "Do you feel supported by faculty or staff?",
    "Are you keeping in touch with family or friends back home?",
    "Have you done anything relaxing this week?",
    "Are you worried about your grades?",
    "Have you been feeling down for more than a few days?",
    "Do you feel you’re growing as a person?",
    "Have you helped someone recently?",
    "Do you feel optimistic about your studies?",
    "Have you had any difficulty sleeping?",
    "Do you feel connected to your campus?",
    "Have you practiced any mindfulness or meditation?",
    "Do you feel you're doing your best?",
    "Have you spent time alone in a good way?",
    "Have you cried recently?",
    "Do you have something to look forward to this month?",
    "Have you felt appreciated lately?",
    "Do you feel your workload is manageable?",
    "Are you eating mostly healthy foods?",
    "Do you feel you're balancing work and life?",
    "Have you taken any time off for yourself recently?",
    "Are you excited about any of your classes?",
    "Do you feel pressure from your family?",
    "Have you been doomscrolling or glued to social media?",
    "Do you feel inspired by what you’re learning?",
    "Have you checked in with your mental health lately?",
    "Do you feel your goals are achievable?",
    "Have you had time for your hobbies?",
    "Do you feel you’ve made progress this semester?"
]

RESPONSE_TONE_SCALE = [
    # 1 - Mocking (Singlish)
    "Wah lao eh, again ah? Every week same story sia. You okay or not one?",

    # 2 - Dismissive (Singlish)
    "Aiyo, small thing only lah. Don’t so drama can?",

    # 3 - Sarcastic (Singlish)
    "Wah, so poor thing ah? Maybe go nap and see if life changes lor.",

    # 4 - Neutral / Polite
    "Okay, got it. Hope things look up soon.",

    # 5 - Acknowledging, but flat
    "Thanks for sharing. Noted.",

    # 6 - Mildly supportive
    "Hmm, sounds like a lot. Hope you're coping alright.",

    # 7 - Friendly and caring
    "I hear you. It's good you're talking about it.",

    # 8 - Warm and empathetic
    "That sounds tough. You're doing your best, and that counts.",

    # 9 - Genuinely supportive
    "Really appreciate you being open. You’re not alone in this.",

    # 10 - Deeply invested
    "Thank you so much for sharing. I’m truly here for you — do you want to talk more about it?"
]


def cmd_start(chat_id, args, user_id, user_name):
    send_message(chat_id, "👋 RC4 RA Bot is ready!")


def cmd_help(chat_id, args, user_id, user_name):
    msg = """🤖 *Bot Commands:*

# Attendance
• `/attendance` – Mark yourself IN or OUT via buttons
• `/status` – Show everyone's status

# Duties
• `/view_schedule` – View full duty schedule
• `/view_mine` – View your assigned slots
• `/swap_duty` – Start a duty swap request (choose Admin Duty or Weekend Stay In, then pick who to swap with via buttons)
• `/cover_duty` – Cover a duty slot (choose Admin Duty or Weekend Stay In, then pick a slot)
• `/dutyramessage [AM|PM]` – Generate the duty RA message, delete AM/PM where applicable

# Fluff
• `/eatwhat` – Get a random food suggestion
• `/gay` – Check how gay you are
• `/thankyou(name)` – thank someone
• `/help` – Show this list

# Admin Usage
• `/refresh` – Ask all users to update whether they're IN or OUT
• `/update_schedule` – Replace schedule"""
    send_message(chat_id, msg)

# Put this back in if you ever make this work again.
# • `/askmyra <question>` – Ask Myra a question
# • `/trainmyra <text>` – Train Myra with text (or send a file/photo)

def cmd_eatwhat(chat_id, args, user_id, user_name):
    options = [
        "FC kokka noodle",
        "FC mala",
        "FC danlao",
        "FC miniwok",
        "FC yongtaufoo",
        "FC cai png",
        "FC indian",
        "FC nasi lemak",
        "FC Japanese",
        "FC Chicken Rice",
        "Casa 1",
        "Casa 2",
        "Jollibee",
        "Subway",
        "Udon Don Bar",
        "WaaCow",
        "Bismillah",
        "Hwang's",
        "Mala mala",
        "Royals Bistro",
        "FF mala",
        "FF jap x western fusion",
        "FF banmian",
        "FF miniwok",
        "FF snail noodles",
        "FF XLB",
        "Fong Seng",
        "Amaans",
        "Nana Thai",
        "Niqqis",
        "Macs"
    ]
    send_message(chat_id, random.choice(options))


def cmd_gay(chat_id, args, user_id, user_name):
    num = random.randint(50, 110)
    msg = f"{user_name} is {num}% gay!"
    send_message(chat_id, msg)


def cmd_thankyou(chat_id, cmd, user_id, user_name):
    """cmd is the full command string, e.g. '/thankyoualycia'."""
    person = cmd.split("/thankyou")[1].strip()
    send_message(chat_id, f'WOW THANK YOU SO MUCH {person.upper() + " " if person else ""}FOR YOUR SERVICE. MYRA COMMENDS YOU')


def daily_checkup():
    r = get_redis()
    friend = random.choice(list(FRIEND_TELEGRAM_IDS.keys()))
    r.hset("wellbeing_questions", friend, "true")
    send_message(FRIEND_TELEGRAM_IDS[friend], random.choice(WELLBEING_QUESTIONS))


def try_handle_reply(chat_id, text, user_id, user_name):
    r = get_redis()
    wellbeing = r.hget("wellbeing_questions", str(user_name))
    if wellbeing:
        print("wellbeing reply")
        send_message(chat_id, random.choice(RESPONSE_TONE_SCALE))
        r.hdel("wellbeing_questions", str(user_name))
        return True
    return False


COMMANDS = {
    "/start": cmd_start,
    "/help": cmd_help,
    "/eatwhat": cmd_eatwhat,
    "/gay": cmd_gay,
}
