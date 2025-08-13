import os
import logging
from typing import Optional

from telegram import Update, ChatPermissions
from telegram.constants import ParseMode
from telegram.error import Forbidden, TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# --------------------------
# Env config
# --------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
GROUP_ID = int(os.getenv("GROUP_ID", "-1002463051483"))  # your group id
FLYER1_URL = os.getenv("FLYER1_URL", "").strip()  # set in Railway
FLYER2_URL = os.getenv("FLYER2_URL", "").strip()  # set in Railway
PORT = int(os.getenv("PORT", "8080"))

# Prefer PUBLIC_URL if you set it, else RAILWAY_STATIC_URL
PUBLIC_HOST = (os.getenv("PUBLIC_URL") or os.getenv("RAILWAY_STATIC_URL") or "").strip()
if PUBLIC_HOST.startswith("http://") or PUBLIC_HOST.startswith("https://"):
    PUBLIC_HOST = PUBLIC_HOST.split("://", 1)[1]
WEBHOOK_URL = f"https://{PUBLIC_HOST}/{BOT_TOKEN}" if PUBLIC_HOST else ""

# --------------------------
# Logging
# --------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
log = logging.getLogger("axiom-bot")

# --------------------------
# Helpers
# --------------------------
async def _is_admin(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(GROUP_ID, user_id)
        return member.status in ("administrator", "creator")
    except TelegramError as e:
        log.warning(f"Could not check admin status for {user_id}: {e}")
        return False

def _permissions_locked() -> ChatPermissions:
    # Deny sending anything and changing anything.
    return ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_audios=False,
        can_send_documents=False,
        can_send_photos=False,
        can_send_videos=False,
        can_send_video_notes=False,
        can_send_voice_notes=False,
        can_send_polls=False,
        can_add_web_page_previews=False,
        can_change_info=False,
        can_invite_users=False,
        can_pin_messages=False,
    )

async def _safe_delete_join_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        log.info("✅ Deleted join system message.")
    except TelegramError as e:
        log.warning(f"⚠️ Could not delete join message: {e}")

async def _dm_welcome(user_id: int, first_name: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    # DM welcome
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"👋 Hi {first_name}!\n\n"
                f"Welcome to **Axiom Community Vault**.\n"
                f"🌱 *Let’s Grow Together* 🤝\n\n"
                f"Here are two quick flyers with info:"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
        # Send flyers if provided
        if FLYER1_URL:
            await context.bot.send_photo(chat_id=user_id, photo=FLYER1_URL)
        if FLYER2_URL:
            await context.bot.send_photo(chat_id=user_id, photo=FLYER2_URL)
        log.info(f"📨 Sent DM + flyers to {first_name} ({user_id}).")
    except Forbidden:
        # User’s privacy settings block DMs / they didn't start the bot.
        # Fallback: post a short welcome in group (without tagging too aggressively).
        log.info(f"ℹ️ {first_name} ({user_id}) has DMs closed. Sending fallback in group.")
        try:
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=f"👋 Welcome to Axiom Community Vault! 🌱\nIf you’d like details, please DM me: @{(await context.bot.get_me()).username}",
            )
            if FLYER1_URL:
                await context.bot.send_photo(chat_id=GROUP_ID, photo=FLYER1_URL)
            if FLYER2_URL:
                await context.bot.send_photo(chat_id=GROUP_ID, photo=FLYER2_URL)
        except TelegramError as e:
            log.warning(f"⚠️ Could not send group fallback: {e}")
    except TelegramError as e:
        log.warning(f"⚠️ DM welcome failed for {first_name} ({user_id}): {e}")

# --------------------------
# Handlers
# --------------------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello! ✅ Axiom Community Vault bot is online (webhook mode).")

async def new_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle people joining the group: delete join message, restrict, DM + flyers."""
    if update.effective_chat is None or update.effective_chat.id != GROUP_ID:
        return  # only act in your target group

    if not update.message or not update.message.new_chat_members:
        return

    # Clean the join system message
    await _safe_delete_join_message(update, context)

    me = await context.bot.get_me()

    for m in update.message.new_chat_members:
        # Skip the bot itself
        if m.id == me.id:
            log.info("ℹ️ Bot joined event detected; skipping self.")
            continue

        # Skip admins/owners
        if await _is_admin(context, m.id):
            log.info(f"ℹ️ {m.first_name} is admin/owner; skipping restriction.")
            continue

        # Restrict the user
        try:
            await context.bot.restrict_chat_member(
                chat_id=GROUP_ID,
                user_id=m.id,
                permissions=_permissions_locked(),
            )
            log.info(f"🔒 Restricted {m.first_name} ({m.id}).")
        except TelegramError as e:
            log.warning(f"⚠️ Could not restrict {m.first_name} ({m.id}): {e}")

        # DM welcome & flyers (with group fallback if DMs closed)
        await _dm_welcome(user_id=m.id, first_name=m.first_name or "there", context=context)

# --------------------------
# App bootstrap
# --------------------------
async def on_startup(app: Application) -> None:
    # Verify token works
    me = await app.bot.get_me()
    log.info(f"✅ Connected as @{me.username}")

    if not WEBHOOK_URL:
        log.error(
            "❌ PUBLIC_URL or RAILWAY_STATIC_URL not set. "
            "Set one of them so the bot can register the webhook."
        )
        return

    # Ensure a clean webhook
    try:
        await app.bot.delete_webhook(drop_pending_updates=True)
    except TelegramError:
        pass

    # Register webhook
    await app.bot.set_webhook(url=WEBHOOK_URL, allowed_updates=["message", "chat_member", "my_chat_member"])
    log.info(f"🔗 Webhook set to: {WEBHOOK_URL}")

def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN is missing. Set it in Railway → Variables.")

    if not PUBLIC_HOST:
        log.warning(
            "⚠️ PUBLIC_URL / RAILWAY_STATIC_URL not set. "
            "Set one of them to your Railway domain (without protocol)."
        )

    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_members))

    # Run webhook server (built-in aiohttp)
    # We use a unique path (the token) so random traffic doesn't hit the webhook.
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=WEBHOOK_URL if WEBHOOK_URL else None,
        stop_signals=None,  # Railway sends SIGTERM on redeploy; PTB handles shutdown gracefully
        post_init=on_startup,
    )

if __name__ == "__main__":
    main()
