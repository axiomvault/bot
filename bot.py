import logging
import asyncio
from flask import Flask, request
from telegram import Update, ChatPermissions, InputFile, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, ChatMemberHandler, ContextTypes, filters

# ===== CONFIG =====
BOT_TOKEN = "8446918873:AAE3RUOqs__DoCQnwil85shVozugodVyk_I"
GROUP_ID = -1002463051483
WEBHOOK_PATH = BOT_TOKEN
WEBHOOK_URL = f"https://worker-production-ce19.up.railway.app/{WEBHOOK_PATH}"
PORT = 8080
FLYER1_PATH = "flyer1.jpg"
FLYER2_PATH = "flyer2.jpg"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("axiom-bot")

# ===== APPLICATION =====
application = Application.builder().token(BOT_TOKEN).build()

# ===== UTILS =====
_recent_joins = {}
JOIN_COOLDOWN_SEC = 30

def _already_handled(user_id: int) -> bool:
    import time
    now = time.time()
    for uid, ts in list(_recent_joins.items()):
        if now - ts > JOIN_COOLDOWN_SEC:
            del _recent_joins[uid]
    if user_id in _recent_joins:
        return True
    _recent_joins[user_id] = now
    return False

async def _restrict_in_group(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    perms = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_pin_messages=False
    )
    try:
        await context.bot.restrict_chat_member(chat_id=GROUP_ID, user_id=user_id, permissions=perms)
    except Exception as e:
        log.warning(f"Could not restrict user {user_id}: {e}")

async def _dm_welcome(context: ContextTypes.DEFAULT_TYPE, user_id: int, full_name: str):
    try:
        await context.bot.send_message(chat_id=user_id,
            text=f"🎉 Welcome {full_name} to Axiom Community Vault!\nCheck these flyers:")
        await context.bot.send_photo(chat_id=user_id, photo=InputFile(FLYER1_PATH))
        await context.bot.send_photo(chat_id=user_id, photo=InputFile(FLYER2_PATH))
    except Exception as e:
        log.warning(f"Could not DM {user_id}: {e}")

async def _delete_join_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message:
            await context.bot.delete_message(chat_id=GROUP_ID, message_id=update.message.message_id)
    except Exception:
        pass

async def _handle_new_member(update: Update | None, context: ContextTypes.DEFAULT_TYPE, user_id: int, full_name: str):
    if user_id == context.bot.id:
        return
    if _already_handled(user_id):
        return
    await _restrict_in_group(context, user_id)
    await _dm_welcome(context, user_id, full_name)
    await _delete_join_msg(update, context)
    log.info(f"✅ Handled new member {full_name}")

# ===== HANDLERS =====
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Axiom Community Vault bot is running!")

async def on_message_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return
    for member in update.message.new_chat_members:
        await _handle_new_member(update, context, member.id, member.full_name)

async def on_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_update = update.chat_member
    if not chat_update or chat_update.chat.id != GROUP_ID:
        return
    new = chat_update.new_chat_member
    if new.status == ChatMember.MEMBER:
        user = new.user
        await _handle_new_member(None, context, user.id, user.full_name)

application.add_handler(CommandHandler("start", cmd_start))
application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_message_new_members))
application.add_handler(ChatMemberHandler(on_chat_member, ChatMemberHandler.CHAT_MEMBER))

# ===== FLASK WEBHOOK =====
flask_app = Flask(__name__)

@flask_app.route(f"/{WEBHOOK_PATH}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    loop = asyncio.get_event_loop()
    loop.create_task(application.process_update(update))
    return "OK", 200

@flask_app.route("/", methods=["GET"])
def home():
    return "🤖 Axiom Community Vault Bot is running!", 200

# ===== STARTUP =====
async def _startup():
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(url=WEBHOOK_URL, allowed_updates=["message", "chat_member", "my_chat_member"])
    log.info(f"✅ Webhook set to: {WEBHOOK_URL}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_startup())
    flask_app.run(host="0.0.0.0", port=PORT)
