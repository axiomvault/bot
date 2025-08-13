import os
from telegram import Update, ChatPermissions
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

# Bot Token from Railway environment variables
TOKEN = os.getenv("BOT_TOKEN")  # Set this in Railway Variables
GROUP_ID = -1002463051483  # Replace with your group's ID

# Flyer image URLs (Replace with your flyers)
FLYER_1 = "https://example.com/flyer1.jpg"
FLYER_2 = "https://example.com/flyer2.jpg"

def welcome_new_member(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Delete Telegram's "XYZ joined the group" message
    try:
        context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
    except Exception as e:
        print(f"Error deleting join message: {e}")

    for member in update.message.new_chat_members:
        try:
            # Restrict permissions in group
            context.bot.restrict_chat_member(
                chat_id=GROUP_ID,
                user_id=member.id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_polls=False,
                    can_change_info=False,
                    can_invite_users=False,
                    can_pin_messages=False
                )
            )

            # Send private welcome message
            context.bot.send_message(
                chat_id=member.id,
                text="Welcome to Axiom Community Vault! 🎉\nHere’s some information to get started:"
            )

            # Send flyers in private chat
            context.bot.send_photo(chat_id=member.id, photo=FLYER_1)
            context.bot.send_photo(chat_id=member.id, photo=FLYER_2)

        except Exception as e:
            print(f"Error welcoming {member.first_name}: {e}")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Listen for new members and clean join message
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, welcome_new_member))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
