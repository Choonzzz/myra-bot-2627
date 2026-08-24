# features/swap.py
import json

from redis_client import load_duty_schedule, get_redis
from config import GROUP_CHAT_ID, FRIEND_TELEGRAM_IDS
from telegram_api import send_message


def cmd_swap_duty(chat_id, args, user_id, user_name):
    msg = "🔁 *Who do you want to swap with?*\n" + "\n".join([f"• {name} → type `/swap {name}`" for name in FRIEND_TELEGRAM_IDS])
    send_message(chat_id, msg)


def cmd_swap(chat_id, args, user_id, user_name):
    r = get_redis()
    if not args:
        send_message(chat_id, "❌ Please specify a name. Use /swap_duty to view names.")
        return
    target = " ".join(args)
    duty_schedule = load_duty_schedule()
    target_duties = [slot for slot, name in duty_schedule.items() if name == target]
    if not target_duties:
        send_message(chat_id, f"❌ {target} has no assigned duties.")
        return
    msg = f"📋 *{target}'s Duties - Choose one to swap:*\n\n"
    for i, duty in enumerate(target_duties, 1):
        msg += f"{i}. {duty}\n"
    msg += "\n📝 Reply to this message with the number of your choice."
    r.hset("user_swap_state", str(user_id), target)
    send_message(chat_id, msg)


def cmd_cover_duty(chat_id, args, user_id, user_name):
    r = get_redis()
    duty_schedule = load_duty_schedule()
    if not duty_schedule:
        send_message(chat_id, "❌ No duty schedule available.")
        return
    msg = "📋 *All Duty Slots - Choose one to cover:*\n\n"
    for i, (slot, name) in enumerate(duty_schedule.items(), 1):
        msg += f"{i}. {slot} ({name})\n"
    msg += "\n📝 Reply to this message with the number of your choice."
    r.hset("user_cover_state", str(user_id), "waiting_for_slot_choice")
    send_message(chat_id, msg)


def _try_handle_cover_reply(r, chat_id, text, user_id, user_name):
    if r.hget("user_cover_state", str(user_id)) == "waiting_for_slot_choice":
        try:
            choice = int(text.strip())
            duty_schedule = json.loads(r.get("duty_schedule") or '{}')
            duties = list(duty_schedule.items())
            if 1 <= choice <= len(duties):
                selected_slot, original = duties[choice - 1]
                duty_schedule[selected_slot] = user_name
                r.set("duty_schedule", json.dumps(duty_schedule))
                r.hdel("user_cover_state", str(user_id))
                msg = f"✅ *Duty Cover Completed!*\n\n📅 {selected_slot}: {user_name} (covering for {original})"
                send_message(chat_id, msg)
                send_message(GROUP_CHAT_ID, msg)
            else:
                send_message(chat_id, "❌ Invalid choice.")
        except ValueError:
            send_message(chat_id, "❌ Please enter a valid number.")
        return True
    return False


def _try_handle_swap_choice_reply(r, chat_id, text, user_id, user_name):
    swap_state = r.hget("user_swap_state", str(user_id))
    if not swap_state:
        return False

    duty_schedule = json.loads(r.get("duty_schedule") or '{}')
    state = swap_state.decode() if isinstance(swap_state, bytes) else swap_state

    if "|" not in state:
        # User is choosing target's duty slot
        target = state
        target_duties = [slot for slot, name in duty_schedule.items() if name == target]
        try:
            choice = int(text.strip())
            if 1 <= choice <= len(target_duties):
                target_slot = target_duties[choice - 1]
                requester_duties = [slot for slot, name in duty_schedule.items() if name == user_name]
                if not requester_duties:
                    send_message(chat_id, "❌ You have no duties to swap.")
                    r.hdel("user_swap_state", str(user_id))
                    return True

                msg = "🔄 *Your Duties - Choose which to swap:*\n"
                for i, duty in enumerate(requester_duties, 1):
                    msg += f"{i}. {duty}\n"
                msg += "\n📝 Reply to this message with the number of your choice."

                new_state = f"{target}|{target_slot}"
                r.hset("user_swap_state", str(user_id), new_state)
                send_message(chat_id, msg)
            else:
                send_message(chat_id, "❌ Invalid choice.")
        except ValueError:
            send_message(chat_id, "❌ Please enter a valid number.")
    else:
        # User is choosing their own duty to swap
        target, target_slot = state.split("|", 1)
        requester_duties = [slot for slot, name in duty_schedule.items() if name == user_name]
        try:
            choice = int(text.strip())
            if 1 <= choice <= len(requester_duties):
                requester_slot = requester_duties[choice - 1]
                target_chat_id = FRIEND_TELEGRAM_IDS.get(target)
                if not target_chat_id:
                    send_message(chat_id, "❌ Could not find target user chat ID.")
                    return True

                # Store swap request for target to respond to
                swap_data = json.dumps({
                    "requester": user_name,
                    "target": target,
                    "requester_slot": requester_slot,
                    "target_slot": target_slot,
                    "requester_chat_id": str(chat_id),
                    "target_chat_id": target_chat_id
                })
                r.hset("active_swap_requests", target_chat_id, swap_data)

                msg = f"""🔄 *Duty Swap Request*

👤 From: {user_name}
📅 They want to swap:
   • Your: {target_slot}
   • Their: {requester_slot}

Reply with *Yes* or *No*"""
                send_message(target_chat_id, msg)
                send_message(chat_id, f"📨 Swap request sent to {target}!")
                r.hdel("user_swap_state", str(user_id))
            else:
                send_message(chat_id, "❌ Invalid choice.")
        except ValueError:
            send_message(chat_id, "❌ Please enter a valid number.")
    return True


def _try_handle_swap_response_reply(r, chat_id, text, user_id, user_name):
    active = r.hget("active_swap_requests", str(user_id))
    if not active:
        return False

    text_l = text.lower()
    if text_l not in ["yes", "y", "no", "n"]:
        return True

    swap_data = json.loads(active.decode() if isinstance(active, bytes) else active)
    if text_l in ["yes", "y"]:
        duty_schedule = json.loads(r.get("duty_schedule") or '{}')
        duty_schedule[swap_data["requester_slot"]] = swap_data["target"]
        duty_schedule[swap_data["target_slot"]] = swap_data["requester"]
        r.set("duty_schedule", json.dumps(duty_schedule))
        msg = f"✅ *Duty Swap Completed!*\n\n📅 {swap_data['requester_slot']}: {swap_data['target']}\n📅 {swap_data['target_slot']}: {swap_data['requester']}"
        send_message(chat_id, msg)
        send_message(swap_data["requester_chat_id"], msg)
        send_message(GROUP_CHAT_ID, msg)
    else:
        send_message(chat_id, "✅ You declined the swap request.")
        send_message(swap_data["requester_chat_id"], f"❌ {swap_data['target']} declined the swap request.")
    r.hdel("active_swap_requests", str(user_id))
    return True


def try_handle_reply(chat_id, text, user_id, user_name):
    """Handles cover-slot choice, swap-slot choice, and swap yes/no response replies, in that order."""
    r = get_redis()
    if _try_handle_cover_reply(r, chat_id, text, user_id, user_name):
        return True
    if _try_handle_swap_choice_reply(r, chat_id, text, user_id, user_name):
        return True
    if _try_handle_swap_response_reply(r, chat_id, text, user_id, user_name):
        return True
    return False


COMMANDS = {
    "/swap_duty": cmd_swap_duty,
    "/swap": cmd_swap,
    "/cover_duty": cmd_cover_duty,
}
