import logging
from telegram import Update, ChatPermissions, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request
import threading
import asyncio

BOT_TOKEN = "8446918873:AAE3RUOqs__DoCQnwil85shVozugodVyk_I"
GROUP_ID = -1002463051483
WEBHOOK_URL = f"https://worker-production-ce19.up.railway.app/{BOT_TOKEN}"
PORT = 8080

FLYER1_PATH = "flyer1.jpg"
FLYER2_PATH = "flyer2.jpg"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Welcome to Axiom Community Vault — Let's grow together!")

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.id != context.bot.id:
            try:
                # Send DM
                await context.bot.send_message(
                    chat_id=member.id,
                    text=f"🎉 Welcome {member.full_name} to Axiom Community Vault!\nWe’re excited to have you onboard."
                )
                await context.bot.send_photo(chat_id=member.id, photo=InputFile(FLYER1_PATH))
                await context.bot.send_photo(chat_id=member.id, photo=InputFile(FLYER2_PATH))

                # Restrict in group
                await context.bot.restrict_chat_member(
                    chat_id=GROUP_ID,
                    user_id=member.id,
                    permissions=ChatPermissions(can_send_messages=False,
                                                can_send_media_messages=False,
                                                can_pin_messages=False)
                )

                # Delete join message
                await context.bot.delete_message(chat_id=GROUP_ID, message_id=update.message.message_id)

                logging.info(f"✅ Welcome flow completed for {member.full_name}")
            except Exception as e:
                logging.error(f"⚠️ Error handling new member {member.full_name}: {e}")

flask_app = Flask(__name__)
app_bot = None

@flask_app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_update = request.get_json(force=True)
    update = Update.de_json(json_update, app_bot.bot)
    asyncio.run_coroutine_threadsafe(app_bot.process_update(update), app_bot.loop)
    return "OK", 200

@flask_app.route("/", methods=["GET"])
def home():
    return "🤖 Axiom Community Vault Bot is running!", 200

async def run_bot():
    global app_bot
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    await app_bot.bot.set_webhook(WEBHOOK_URL)
    logging.info(f"✅ Webhook set to: {WEBHOOK_URL}")

if __name__ == "__main__":
    threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=PORT)).start()
    asyncio.run(run_bot())
