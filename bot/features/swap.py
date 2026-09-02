# features/swap.py
import json

from redis_client import load_schedule, get_redis, schedule_redis_key
from config import GROUP_CHAT_ID, FRIEND_TELEGRAM_IDS, ordered_friend_names, RA_GROUPINGS, SCHEDULE_TARGETS
from telegram_api import send_message, inline_keyboard, edit_message_reply_markup


def _schedule_label(schedule_key):
    return next(
        (label for label, suffix in SCHEDULE_TARGETS.items() if schedule_redis_key(suffix) == schedule_key),
        schedule_key
    )


def _user_zone_schedule_key(user_name):
    group = RA_GROUPINGS.get(user_name)
    suffix = SCHEDULE_TARGETS.get(group) if group else None
    return schedule_redis_key(suffix) if suffix else None


def _swap_type_keyboard(prefix, cancel_data):
    return inline_keyboard([
        [("Admin Duty", f"{prefix}:duty"), ("Weekend Stay In", f"{prefix}:weekend")],
        [("❌ Cancel", cancel_data)]
    ])


def cmd_swap_duty(chat_id, args, user_id, user_name):
    send_message(chat_id, "🔁 *Swap which duty?*", reply_markup=_swap_type_keyboard("swap_type", "cancel:swap"))


def cmd_cover_duty(chat_id, args, user_id, user_name):
    send_message(chat_id, "🔁 *Cover which duty?*", reply_markup=_swap_type_keyboard("cover_type", "cancel:cover"))


def _start_swap_duty(chat_id, user_id, user_name, schedule_key):
    r = get_redis()
    if schedule_key == schedule_redis_key("duty"):
        candidates = ordered_friend_names()
    else:
        group = RA_GROUPINGS.get(user_name)
        candidates = [name for name in ordered_friend_names() if RA_GROUPINGS.get(name) == group]

    r.hset("pending_swap_schedule", str(user_id), schedule_key)
    msg = f"🔁 *Who do you want to swap {_schedule_label(schedule_key)} with?*"
    rows = [
        [(name, f"swap_target:{name}") for name in candidates[i:i + 2]]
        for i in range(0, len(candidates), 2)
    ]
    rows.append([("❌ Cancel", "cancel:swap")])
    send_message(chat_id, msg, reply_markup=inline_keyboard(rows))


def _start_cover_duty(chat_id, user_id, user_name, schedule_key):
    r = get_redis()
    schedule = load_schedule(schedule_key)
    if not schedule:
        send_message(chat_id, "❌ No duty schedule available.")
        return
    msg = f"📋 *All {_schedule_label(schedule_key)} Slots - Choose one to cover:*\n\n"
    for i, (slot, name) in enumerate(schedule.items(), 1):
        msg += f"{i}. {slot} ({name})\n"
    msg += "\n📝 Reply to this message with the number of your choice."
    r.hset("user_cover_state", str(user_id), schedule_key)
    send_message(chat_id, msg, reply_markup=inline_keyboard([[("❌ Cancel", "cancel:cover")]]))


def _try_handle_cover_reply(r, chat_id, text, user_id, user_name):
    schedule_key = r.hget("user_cover_state", str(user_id))
    if schedule_key:
        schedule_key = schedule_key.decode() if isinstance(schedule_key, bytes) else schedule_key
        try:
            choice = int(text.strip())
            schedule = json.loads(r.get(schedule_key) or '{}')
            duties = list(schedule.items())
            if 1 <= choice <= len(duties):
                selected_slot, original = duties[choice - 1]
                schedule[selected_slot] = user_name
                r.set(schedule_key, json.dumps(schedule))
                r.hdel("user_cover_state", str(user_id))
                msg = f"✅ *{_schedule_label(schedule_key)} Cover Completed!*\n\n📅 {selected_slot}: {user_name} (covering for {original})"
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

    state = swap_state.decode() if isinstance(swap_state, bytes) else swap_state
    schedule_key, rest = state.split("::", 1)
    schedule = json.loads(r.get(schedule_key) or '{}')

    if "|" not in rest:
        # User is choosing target's duty slot
        target = rest
        target_duties = [slot for slot, name in schedule.items() if name == target]
        try:
            choice = int(text.strip())
            if 1 <= choice <= len(target_duties):
                target_slot = target_duties[choice - 1]
                requester_duties = [slot for slot, name in schedule.items() if name == user_name]
                if not requester_duties:
                    send_message(chat_id, "❌ You have no duties to swap.")
                    r.hdel("user_swap_state", str(user_id))
                    return True

                msg = "🔄 *Your Duties - Choose which to swap:*\n"
                for i, duty in enumerate(requester_duties, 1):
                    msg += f"{i}. {duty}\n"
                msg += "\n📝 Reply to this message with the number of your choice."

                new_state = f"{schedule_key}::{target}|{target_slot}"
                r.hset("user_swap_state", str(user_id), new_state)
                send_message(chat_id, msg, reply_markup=inline_keyboard([[("❌ Cancel", "cancel:swap")]]))
            else:
                send_message(chat_id, "❌ Invalid choice.")
        except ValueError:
            send_message(chat_id, "❌ Please enter a valid number.")
    else:
        # User is choosing their own duty to swap
        target, target_slot = rest.split("|", 1)
        requester_duties = [slot for slot, name in schedule.items() if name == user_name]
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
                    "schedule_key": schedule_key,
                    "requester": user_name,
                    "target": target,
                    "requester_slot": requester_slot,
                    "target_slot": target_slot,
                    "requester_chat_id": str(chat_id),
                    "target_chat_id": target_chat_id
                })
                r.hset("active_swap_requests", target_chat_id, swap_data)

                msg = f"""🔄 *{_schedule_label(schedule_key)} Swap Request*

👤 From: {user_name}
📅 They want to swap:
   • Your: {target_slot}
   • Their: {requester_slot}"""
                send_message(target_chat_id, msg, reply_markup=inline_keyboard(
                    [[("✅ Yes", "swap_resp:yes"), ("❌ No", "swap_resp:no")]]
                ))
                send_message(chat_id, f"📨 Swap request sent to {target}!")
                r.hdel("user_swap_state", str(user_id))
            else:
                send_message(chat_id, "❌ Invalid choice.")
        except ValueError:
            send_message(chat_id, "❌ Please enter a valid number.")
    return True


def try_handle_reply(chat_id, text, user_id, user_name):
    """Handles cover-slot choice and swap-slot choice replies, in that order."""
    r = get_redis()
    if _try_handle_cover_reply(r, chat_id, text, user_id, user_name):
        return True
    if _try_handle_swap_choice_reply(r, chat_id, text, user_id, user_name):
        return True
    return False


def try_handle_callback(data, chat_id, user_id, message_id, user_name):
    """Handles the Admin/Weekend type buttons on /swap_duty and /cover_duty,
    the swap-target person buttons, the Cancel buttons, and the Yes/No
    buttons on a swap request DM."""
    r = get_redis()

    if data == "cancel:cover":
        r.hdel("user_cover_state", str(user_id))
        edit_message_reply_markup(chat_id, message_id)
        send_message(chat_id, "❌ Cover duty cancelled.")
        return True

    if data == "cancel:swap":
        r.hdel("user_swap_state", str(user_id))
        r.hdel("pending_swap_schedule", str(user_id))
        edit_message_reply_markup(chat_id, message_id)
        send_message(chat_id, "❌ Swap cancelled.")
        return True

    if data.startswith("swap_type:") or data.startswith("cover_type:"):
        is_swap = data.startswith("swap_type:")
        suffix = data.split(":", 1)[1]
        edit_message_reply_markup(chat_id, message_id)
        if suffix == "duty":
            schedule_key = schedule_redis_key("duty")
        else:
            schedule_key = _user_zone_schedule_key(user_name)
            if not schedule_key:
                send_message(chat_id, "❌ You're not assigned to a stay-in group yet.")
                return True
        if is_swap:
            _start_swap_duty(chat_id, user_id, user_name, schedule_key)
        else:
            _start_cover_duty(chat_id, user_id, user_name, schedule_key)
        return True

    if data.startswith("swap_target:"):
        target = data.split("swap_target:", 1)[1]
        schedule_key = r.hget("pending_swap_schedule", str(user_id))
        edit_message_reply_markup(chat_id, message_id)
        if not schedule_key:
            send_message(chat_id, "❌ Session expired. Please start again with /swap_duty.")
            return True
        schedule_key = schedule_key.decode() if isinstance(schedule_key, bytes) else schedule_key
        r.hdel("pending_swap_schedule", str(user_id))

        schedule = load_schedule(schedule_key)
        target_duties = [slot for slot, name in schedule.items() if name == target]
        if not target_duties:
            send_message(chat_id, f"❌ {target} has no assigned duties.")
            return True

        msg = f"📋 *{target}'s Duties - Choose one to swap:*\n\n"
        for i, duty in enumerate(target_duties, 1):
            msg += f"{i}. {duty}\n"
        msg += "\n📝 Reply to this message with the number of your choice."
        r.hset("user_swap_state", str(user_id), f"{schedule_key}::{target}")
        send_message(chat_id, msg, reply_markup=inline_keyboard([[("❌ Cancel", "cancel:swap")]]))
        return True

    if data in ("swap_resp:yes", "swap_resp:no"):
        active = r.hget("active_swap_requests", str(user_id))
        if not active:
            edit_message_reply_markup(chat_id, message_id)
            return True

        swap_data = json.loads(active.decode() if isinstance(active, bytes) else active)
        edit_message_reply_markup(chat_id, message_id)

        if data == "swap_resp:yes":
            schedule_key = swap_data["schedule_key"]
            schedule = json.loads(r.get(schedule_key) or '{}')
            schedule[swap_data["requester_slot"]] = swap_data["target"]
            schedule[swap_data["target_slot"]] = swap_data["requester"]
            r.set(schedule_key, json.dumps(schedule))
            msg = f"✅ *{_schedule_label(schedule_key)} Swap Completed!*\n\n📅 {swap_data['requester_slot']}: {swap_data['target']}\n📅 {swap_data['target_slot']}: {swap_data['requester']}"
            send_message(chat_id, msg)
            send_message(swap_data["requester_chat_id"], msg)
            send_message(GROUP_CHAT_ID, msg)
        else:
            send_message(chat_id, "✅ You declined the swap request.")
            send_message(swap_data["requester_chat_id"], f"❌ {swap_data['target']} declined the swap request.")

        r.hdel("active_swap_requests", str(user_id))
        return True

    return False


COMMANDS = {
    "/swap_duty": cmd_swap_duty,
    "/cover_duty": cmd_cover_duty,
}
