# features/status.py
import datetime
import json

from redis_client import load_duty_schedule, get_redis
from scheduler import should_trigger_refresh
from config import GROUP_CHAT_ID, FRIEND_TELEGRAM_IDS, SGT
from telegram_api import send_message


def cmd_in(chat_id, args, user_id, user_name):
    r = get_redis()
    r.hset("user_status", user_name, "IN")
    r.hset("user_id_map", user_name, str(user_id))
    send_message(chat_id, f"{user_name} is now IN ✅")


def cmd_out(chat_id, args, user_id, user_name):
    r = get_redis()
    r.hset("user_status", user_name, "OUT")
    r.hset("user_id_map", user_name, str(user_id))
    send_message(chat_id, f"{user_name} is now OUT ❌")


def cmd_status(chat_id, args, user_id, user_name):
    r = get_redis()
    statuses = r.hgetall("user_status")
    listStatus = [(k, v) for k, v in statuses.items()]
    listStatus.sort()
    msg = "📋 *Current Status:*\n" + "\n".join([f"{k}: {v}" for k, v in listStatus]) if statuses else "No updates yet."

    duty_schedule = load_duty_schedule()
    today_str = (datetime.datetime.now(SGT)).strftime("%b %d")
    msg += f"\n\n📅 *Duty Schedule for {today_str}:*\n" + "\n".join([f"{k}: {v}" for k, v in duty_schedule.items() if k.startswith(today_str)])
    send_message(chat_id, msg)


def cmd_refresh(chat_id, args, user_id, user_name):
    for user, uid in FRIEND_TELEGRAM_IDS.items():
        print(user, uid)
        send_message(uid, f"👋 Hi {user}, please reply /in or /out to update your status. Select IN if you will be in RC4 during the upcoming duty slot. Else select OUT. Thank you :)")
    send_message(chat_id, "🔄 Asking all members to update...")


def cmd_view_schedule(chat_id, args, user_id, user_name):
    duty_schedule = load_duty_schedule()
    if not duty_schedule:
        send_message(chat_id, "No duties scheduled yet.")
    else:
        msg = "*📅 Full Duty Schedule:*\n" + "\n".join([f"{k}: {v}" for k, v in duty_schedule.items()])
        send_message(chat_id, msg)


def cmd_view_mine(chat_id, args, user_id, user_name):
    duty_schedule = load_duty_schedule()
    my_slots = [slot for slot, name in duty_schedule.items() if name == user_name]
    msg = "*👤 Your Duties:*\n" + "\n".join(my_slots) if my_slots else "You have no assigned duties."
    send_message(chat_id, msg)


def cmd_update_schedule(chat_id, args, user_id, user_name):
    r = get_redis()
    if str(chat_id) != GROUP_CHAT_ID and int(chat_id) > 0:
        send_message(chat_id, "❌ Only allowed in group chat.")
    else:
        r.hset("waiting_for_schedule", str(user_id), "true")
        send_message(chat_id, "📤 Please send the full duty schedule as JSON.\n\nExample:\n```json\n{\"Jul 24 (Thu) PM\": \"Alycia\"}```")


def cmd_dutyramessage(chat_id, args, user_id, user_name):
    r = get_redis()
    statuses = r.hgetall("user_status")
    listStatus = [(k, v) for k, v in statuses.items()]
    listStatus.sort()
    RAsIn = ""
    count = 1
    duty_schedule = load_duty_schedule()
    if should_trigger_refresh(duty_schedule):
        RAsIn = "\n\nRAs/RFs in the building:\n"
        for k, v in listStatus:
            if v == "IN":
                RAsIn += f"{count}) {k}\n"
                count += 1
    duty_slot = datetime.datetime.now(SGT).strftime("%d %b %Y")
    if args and args[0]:
        duty_slot += " " + args[0]
    else:
        duty_slot += " PM"
    msg = f"""I ({user_name}) am the duty RA for {duty_slot}.\n\nI have collected the Duty RA phone from the letterbox. I will be staying in the building until the duty time is over.{RAsIn}
    """
    send_message(chat_id, msg)


def try_handle_reply(chat_id, text, user_id, user_name):
    """Handles the free-text reply to /update_schedule (pasting the new JSON)."""
    r = get_redis()
    if r.hget("waiting_for_schedule", str(user_id)) == "true":
        import ast
        try:
            json_data = json.loads(text)
        except json.JSONDecodeError:
            try:
                json_data = ast.literal_eval(text)
            except (ValueError, SyntaxError):
                send_message(chat_id, "❌ Invalid JSON. Please try again.")
                r.hdel("waiting_for_schedule", str(user_id))
                return True

        if not isinstance(json_data, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in json_data.items()
        ):
            send_message(chat_id, "❌ Schedule must be a JSON object mapping slot names to RA names, e.g. `{\"Jul 24 (Thu) PM\": \"Alycia\"}`. Please try again.")
            r.hdel("waiting_for_schedule", str(user_id))
            return True

        try:
            r.set("duty_schedule", json.dumps(json_data))
        except Exception:
            send_message(chat_id, "❌ Failed to save the schedule (storage error). Please try again.")
            r.hdel("waiting_for_schedule", str(user_id))
            return True

        r.hdel("waiting_for_schedule", str(user_id))
        schedule_lines = "\n".join(f"{k}: {v}" for k, v in json_data.items())
        send_message(chat_id, f"✅ Duty schedule updated successfully!\n\n*📅 New Schedule:*\n{schedule_lines}")
        return True
    return False


def auto_refresh():
    duty_schedule = load_duty_schedule()
    if should_trigger_refresh(duty_schedule):
        user_ids = FRIEND_TELEGRAM_IDS
        tomorrow_str = (datetime.datetime.now(SGT)).strftime("%b %d")
        closing = ""
        for slot, person in duty_schedule.items():
            if slot.startswith(tomorrow_str):
                closing = "Duty RA for " + slot + " is " + person + "."
        for user, uid in user_ids.items():
            print(user, uid)
            send_message(uid, f"👋 Hi {user}, please reply /in or /out to update your status. Select IN if you will be in RC4 during the upcoming duty slot. Else select OUT. Thank you :)\n(Auto-sent for duty RA)\n{closing}")


def send_duty_reminders():
    r = get_redis()
    now = datetime.datetime.now(SGT)
    tomorrow = now + datetime.timedelta(days=1)

    tomorrow_str = tomorrow.strftime("%b %d")

    if r.get("reminder_sent") == tomorrow_str:
        print(f"Reminder already sent for {tomorrow_str}.")
        return

    duty_schedule = load_duty_schedule()
    if not duty_schedule:
        print("No duty schedule found.")
        return

    reminder_sent = False
    for slot, person in duty_schedule.items():
        if slot.startswith(tomorrow_str):
            chat_id = FRIEND_TELEGRAM_IDS.get(person)
            if chat_id:
                msg = f"👋 Hi {person}, you have a duty scheduled for *{slot}* tomorrow. Please be prepared!"
                send_message(chat_id, msg)
                reminder_sent = True
                r.set("reminder_sent", tomorrow_str)

    if reminder_sent:
        send_message(GROUP_CHAT_ID, f"📢 Reminders sent for duties on {tomorrow_str}.")
    else:
        print(f"No duties scheduled for {tomorrow_str}.")


COMMANDS = {
    "/in": cmd_in,
    "/out": cmd_out,
    "/status": cmd_status,
    "/refresh": cmd_refresh,
    "/view_schedule": cmd_view_schedule,
    "/view_mine": cmd_view_mine,
    "/update_schedule": cmd_update_schedule,
    "/dutyramessage": cmd_dutyramessage,
}
