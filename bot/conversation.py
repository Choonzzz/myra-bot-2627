# conversation.py
from telegram_api import send_message, get_user_name_from_id, answer_callback_query
from features import status, swap, misc
# TEMP: myra disabled for local testing (Mongo cluster unreachable).
# Uncomment once MONGO_URI points to a reachable Atlas cluster.
# from features import myra

COMMANDS = {
    **status.COMMANDS,
    **swap.COMMANDS,
    # **myra.COMMANDS,  # TEMP: disabled for local testing
    **misc.COMMANDS,
}

def handle_update(data):
    if "callback_query" in data:
        handle_callback_query(data["callback_query"])
        return

    if "message" not in data:
        return

    message = data["message"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    user_name = get_user_name_from_id(user_id)

    # Allowlist: only users in FRIEND_TELEGRAM_MAPPINGS can use the bot
    if user_name == "Unknown User":
        return

    # Case: user is uploading file/photo while bot is expecting it
    # TEMP: myra disabled for local testing (Mongo cluster unreachable).
    # if myra.try_handle_upload(chat_id, message, user_id, user_name):
    #     return

    # Handle text messages
    text = message.get("text", "").strip()
    if not text:
        return

    if text.startswith("/"):
        handle_command(chat_id, text, user_id, user_name)
    else:
        handle_reply(chat_id, text, user_id, user_name)


def handle_command(chat_id, text, user_id, user_name):
    cmd = text.split()[0].lower()
    if "@rc4rabot" in cmd:
        cmd = cmd.replace("@rc4rabot", "")
    args = text.split()[1:]

    if cmd in COMMANDS:
        COMMANDS[cmd](chat_id, args, user_id, user_name)
    elif cmd.startswith("/thankyou"):
        misc.cmd_thankyou(chat_id, cmd, user_id, user_name)
    else:
        send_message(chat_id, "❌ Unknown command. Type /help to see available options.")


def handle_reply(chat_id, text, user_id, user_name):
    if status.try_handle_reply(chat_id, text, user_id, user_name):
        return
    if swap.try_handle_reply(chat_id, text, user_id, user_name):
        return
    if misc.try_handle_reply(chat_id, text, user_id, user_name):
        return


def handle_callback_query(callback_query):
    callback_id = callback_query["id"]
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    message_id = callback_query["message"]["message_id"]
    data = callback_query.get("data", "")
    user_name = get_user_name_from_id(user_id)

    answer_callback_query(callback_id)

    # Allowlist: only users in FRIEND_TELEGRAM_MAPPINGS can use the bot
    if user_name == "Unknown User":
        return

    if status.try_handle_callback(data, chat_id, user_id, message_id, user_name):
        return
    if swap.try_handle_callback(data, chat_id, user_id, message_id, user_name):
        return
