import logging
from telegram import Update, ChatPermissions, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request
import threading
import asyncio

# --- CONFIG ---
BOT_TOKEN = "8446918873:AAE3RUOqs__DoCQnwil85shVozugodVyk_I"  # Put your bot token here
GROUP_ID = -1002463051483  # Your group ID
WEBHOOK_URL = f"https://worker-production-ce19.up.railway.app/{BOT_TOKEN}"  # Hardcoded Railway URL
PORT = 8080  # Railway's default port

# Paths to your flyers (make sure these files are in your Railway project folder)
FLYER1_PATH = "flyer1.jpg"
FLYER2_PATH = "flyer2.jpg"

# --- LOGGING ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- TELEGRAM BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Welcome to Axiom Community Vault — Let's grow together!")

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.id != context.bot.id:
            try:
                # 1. Send welcome message in DM
                await context.bot.send_message(
                    chat_id=member.id,
                    text=f"🎉 Welcome {member.full_name} to Axiom Community Vault!\nWe’re excited to have you onboard."
                )

                # 2. Send 2 flyers in DM
                await context.bot.send_photo(chat_id=member.id, photo=InputFile(FLYER1_PATH))
                await context.bot.send_photo(chat_id=member.id, photo=InputFile(FLYER2_PATH))

                # 3. Restrict user from sending messages/media/pinning in group
                await context.bot.restrict_chat_member(
                    chat_id=GROUP_ID,
                    user_id=member.id,
                    permissions=ChatPermissions(can_send_messages=False,
                                                can_send_media_messages=False,
                                                can_pin_messages=False)
                )

                # 4. Delete join message from group
                await context.bot.delete_message(chat_id=GROUP_ID, message_id=update.message.message_id)

                logging.info(f"✅ Welcome flow completed for {member.full_name}")

            except Exception as e:
                logging.error(f"⚠️ Error handling new member {member.full_name}: {e}")

# --- FLASK APP FOR WEBHOOK ---
flask_app = Flask(__name__)
app_bot = None  # Will hold the Application instance

@flask_app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app_bot.bot)
    app_bot.update_queue.put_nowait(update)
    return "OK", 200

@flask_app.route("/", methods=["GET"])
def home():
    return "🤖 Axiom Community Vault Bot is running!", 200

# --- FUNCTION TO START TELEGRAM BOT ---
async def run_bot():
    global app_bot
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))

    await app_bot.bot.set_webhook(WEBHOOK_URL)
    logging.info(f"✅ Webhook set to: {WEBHOOK_URL}")

# --- THREAD TO RUN BOT & FLASK ---
if __name__ == "__main__":
    threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=PORT)).start()
    asyncio.run(run_bot())
