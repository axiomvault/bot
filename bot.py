import logging
import os
from flask import Flask, request
from telegram import Update, ChatPermissions
from telegram.ext import Application

# ========================
# CONFIG (Hardcoded)
# ========================
BOT_TOKEN = "8446918873:AAE3RUOqs__DoCQnwil85shVozugodVyk_I"
WEBHOOK_URL = f"https://worker-production-ce19.up.railway.app/{BOT_TOKEN}"
FLYER1 = "https://yourdomain.com/flyer1.jpg"
FLYER2 = "https://yourdomain.com/flyer2.jpg"

# ========================
# Logging
# ========================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========================
# Telegram Bot App
# ========================
app_bot = Application.builder().token(BOT_TOKEN).build()

async def welcome_new_member(update: Update, context):
    """Handle new members joining the group"""
    if update.message and update.message.new_chat_members:
        for member in update.message.new_chat_members:
            chat_id = update.message.chat_id

            # Remove permissions
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=member.id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_pin_messages=False
                )
            )

            # Send DM with flyers
            try:
                await context.bot.send_message(
                    chat_id=member.id,
                    text=f"👋 Welcome {member.full_name} to our community!"
                )
                await context.bot.send_photo(chat_id=member.id, photo=FLYER1)
                await context.bot.send_photo(chat_id=member.id, photo=FLYER2)
            except Exception as e:
                logger.warning(f"Could not send DM to {member.id}: {e}")

            # Delete join message from group
            try:
                await update.message.delete()
            except Exception as e:
                logger.warning(f"Could not delete join message: {e}")

# Register handler
app_bot.add_handler(
    app_bot.chat_member_handler(welcome_new_member, allowed_updates=["message"])
)

# ========================
# Flask Web App
# ========================
flask_app = Flask(__name__)

@flask_app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    """Webhook endpoint for Telegram"""
    update = Update.de_json(request.get_json(force=True), app_bot.bot)
    app_bot.create_task(app_bot.process_update(update))
    return "OK", 200

@flask_app.route("/", methods=["GET"])
def home():
    return "🤖 Axiom Community Vault Bot is running!"

# ========================
# Set Webhook on startup
# ========================
async def set_webhook():
    await app_bot.bot.set_webhook(WEBHOOK_URL, allowed_updates=["message", "chat_member"])

if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(set_webhook())
    flask_app.run(host="0.0.0.0", port=8080)
