# -*- coding: utf-8 -*-
# FINAL VERSION — hardcoded config, PTB v20+, Flask webhook, Railway
import logging
import asyncio
import time
from flask import Flask, request
from telegram import Update, ChatPermissions, InputFile, ChatMember
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ChatMemberHandler,
    ContextTypes, filters
)

# ====== HARD-CODED CONFIG ======
BOT_TOKEN = "8446918873:AAE3RUOqs__DoCQnwil85shVozugodVyk_I"
GROUP_ID = -1002463051483
WEBHOOK_PATH = BOT_TOKEN  # webhook endpoint path — keeps same style you used
WEBHOOK_URL = f"https://worker-production-ce19.up.railway.app/{WEBHOOK_PATH}"
PORT = 8080

# Put these two image files in your project root (same folder as bot.py)
FLYER1_PATH = "flyer1.jpg"
FLYER2_PATH = "flyer2.jpg"

# ====== LOGGING ======
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
log = logging.getLogger("axiom-bot")

# ====== TELEGRAM APPLICATION ======
application = Application.builder().token(BOT_TOKEN).build()

# Keep a short memory to prevent double-handling when both handlers fire
_recent_joins: dict[int, float] = {}
JOIN_COOLDOWN_SEC = 30


def _already_handled(user_id: int) -> bool:
    now = time.time()
    # Purge old
    for uid, at in list(_recent_joins.items()):
        if now - at > JOIN_COOLDOWN_SEC:
            del _recent_joins[uid]
    if user_id in _recent_joins:
        return True
    _recent_joins[user_id] = now
    return False


async def _restrict_in_group(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    try:
        # Deny everything (text, media, previews, polls, pins, topics, etc.)
        perms = ChatPermissions(
            can_send_messages=False,
            can_send_audios=False,
            can_send_documents=False,
            can_send_photos=False,
            can_send_videos=False,
            can_send_video_notes=False,
            can_send_voice_notes=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_topics=False,
        )
        await context.bot.restrict_chat_member(chat_id=GROUP_ID, user_id=user_id, permissions=perms)
    except Exception as e:
        log.warning(f"Could not restrict user {user_id}: {e}")


async def _dm_welcome_and_flyers(context: ContextTypes.DEFAULT_TYPE, user_id: int, full_name: str) -> bool:
    """Returns True if DM succeeded, False if bot could not DM the user (privacy)."""
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎉 Welcome {full_name} to Axiom Community Vault!\n"
                 f"Let’s grow together — here are two quick intro flyers:"
        )
        await context.bot.send_photo(chat_id=user_id, photo=InputFile(FLYER1_PATH))
        await context.bot.send_photo(chat_id=user_id, photo=InputFile(FLYER2_PATH))
        return True
    except Exception as e:
        log.warning(f"Could not DM user {user_id} (they likely haven't started the bot): {e}")
        return False


async def _temporary_group_note(context: ContextTypes.DEFAULT_TYPE, user_id: int, full_name: str) -> None:
    """Post a small welcome note in group and delete it after a few seconds."""
    try:
        mention_html = f"<a href='tg://user?id={user_id}'>{full_name}</a>"
        msg = await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"👋 {mention_html} joined. Check your DM for details!",
            parse_mode="HTML"
        )
        await asyncio.sleep(8)
        await context.bot.delete_message(chat_id=GROUP_ID, message_id=msg.message_id)
    except Exception as e:
        log.warning(f"Could not post/delete temporary group note: {e}")


async def _delete_join_message_if_any(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete the system join message if this handler came via Message update."""
    try:
        if update.message and update.message.message_id and update.effective_chat and update.effective_chat.id == GROUP_ID:
            await context.bot.delete_message(chat_id=GROUP_ID, message_id=update.message.message_id)
    except Exception as e:
        log.warning(f"Could not delete join message: {e}")


async def _handle_new_member(context: ContextTypes.DEFAULT_TYPE, user_id: int, full_name: str,
                             update: Update | None) -> None:
    # Ignore the bot itself
    if user_id == (context.bot.id or 0):
        return
    # Guard against double-handling
    if _already_handled(user_id):
        return

    # 1) Restrict user in the group
    await _restrict_in_group(context, user_id)

    # 2) Try to DM welcome + flyers
    dm_ok = await _dm_welcome_and_flyers(context, user_id, full_name)

    # 3) Always post a small group note and delete it
    await _temporary_group_note(context, user_id, full_name)

    # 4) Delete the original join message (when present)
    if update is not None:
        await _delete_join_message_if_any(update, context)

    log.info(f"✅ Onboarded user {user_id} ({full_name})")


# ====== HANDLERS ======
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Axiom Community Vault bot is alive. Welcome! ✨")


async def on_message_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fires when Telegram sends a Message with new_chat_members (common case)."""
    if not update.effective_chat or update.effective_chat.id != GROUP_ID:
        return
    if not update.message or not update.message.new_chat_members:
        return

    for member in update.message.new_chat_members:
        await _handle_new_member(context, member.id, member.full_name, update)


async def on_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fires on ChatMember updates (covers cases where join message is suppressed)."""
    chat_update = update.chat_member
    if not chat_update or chat_update.chat.id != GROUP_ID:
        return

    new = chat_update.new_chat_member
    # Trigger when the user becomes a member (joined)
    if new.status == ChatMember.MEMBER:
        user = new.user
        await _handle_new_member(context, user.id, user.full_name, None)


# Register handlers
application.add_handler(CommandHandler("start", cmd_start))
application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_message_new_members))
application.add_handler(ChatMemberHandler(on_chat_member, ChatMemberHandler.CHAT_MEMBER))

# ====== FLASK APP (Webhook endpoint) ======
flask_app = Flask("bot")


@flask_app.route(f"/{WEBHOOK_PATH}", methods=["POST"])
def webhook():
    # Deserialize update & hand over to PTB
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.create_task(application.process_update(update))
    return "OK", 200


@flask_app.route("/", methods=["GET"])
def home():
    return "🤖 Axiom Community Vault Bot is running!", 200


# ====== STARTUP ======
async def _startup():
    # Initialize PTB internals and start background processing
    await application.initialize()
    await application.start()
    # Ensure Telegram sends the events we need
    await application.bot.set_webhook(
        url=WEBHOOK_URL,
        allowed_updates=["message", "chat_member", "my_chat_member"]
    )
    log.info(f"✅ Webhook set to: {WEBHOOK_URL}")


if __name__ == "__main__":
    # Start PTB first (event loop + webhook registration)
    asyncio.get_event_loop().run_until_complete(_startup())
    # Then serve Flask (webhook target)
    flask_app.run(host="0.0.0.0", port=PORT)
