import os
import logging
from telegram import Bot, Update, ChatPermissions
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram.error import TelegramError

# ========== CONFIG ==========
TOKEN = os.getenv("BOT_TOKEN", "YOUR_NEW_TOKEN_HERE")
GROUP_ID = -1002463051483
FLYER1_URL = "https://your-first-flyer-link.jpg"
FLYER2_URL = "https://your-second-flyer-link.jpg"

# ========== LOGGING ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== START COMMAND ==========
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hello! I’m the official Axiom Community Vault bot.")

# ========== NEW MEMBER HANDLER ==========
def welcome_new_member(update: Update, context: CallbackContext):
    for member in update.message.new_chat_members:
        try:
            # 1️⃣ Restrict new member permissions
            context.bot.restrict_chat_member(
                chat_id=GROUP_ID,
                user_id=member.id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_pin_messages=False,
                    can_change_info=False
                )
            )
            logger.info(f"Restricted permissions for {member.first_name}")

            # 2️⃣ Send welcome message
            welcome_text = (
                f"👋 Welcome {member.first_name} to Axiom Community Vault!\n"
                f"Let's grow together 🌱"
            )
            context.bot.send_message(chat_id=GROUP_ID, text=welcome_text)

            # 3️⃣ Send flyers
            context.bot.send_photo(chat_id=GROUP_ID, photo=FLYER1_URL)
            context.bot.send_photo(chat_id=GROUP_ID, photo=FLYER2_URL)

            # 4️⃣ Delete system join message
            try:
                context.bot.delete_message(chat_id=GROUP_ID, message_id=update.message.message_id)
                logger.info(f"Deleted join message for {member.first_name}")
            except TelegramError as e:
                logger.warning(f"Error deleting join message: {e}")

        except TelegramError as e:
            logger.error(f"Error welcoming {member.first_name}: {e}")

# ========== MAIN ==========
def main():
    # ✅ Validate token before starting
    try:
        bot = Bot(token=TOKEN)
        me = bot.get_me()
        logger.info(f"Bot connected successfully as {me.username}")
    except TelegramError as e:
        logger.error(f"Failed to connect: {e}")
        return

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, welcome_new_member))

    print("🚀 Bot is running and connected to Telegram!")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
