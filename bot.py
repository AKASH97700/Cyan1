import logging
from pymongo import MongoClient
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ====== Configuration ======
BOT_TOKEN = "YOUR_BOT_TOKEN"
MONGO_URI = "mongodb+srv://demonxyonko:<db_password>@rickycyan.fswqzgl.mongodb.net/?retryWrites=true&w=majority&appName=rickycyan"

# ====== Logging ======
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====== MongoDB Setup ======
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["telegram_bot"]
gban_collection = db["gban_users"]

# ====== Helper Function ======
def is_globally_banned(user_id: int) -> bool:
    return gban_collection.find_one({"user_id": user_id}) is not None

# ====== Handlers ======

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm your advanced group management bot.")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to ban them.")
        return
    user_id = update.message.reply_to_message.from_user.id
    await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=user_id)
    await update.message.reply_text("User has been banned.")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to unban them.")
        return
    user_id = update.message.reply_to_message.from_user.id
    await context.bot.unban_chat_member(chat_id=update.effective_chat.id, user_id=user_id)
    await update.message.reply_text("User has been unbanned.")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to mute them.")
        return
    user_id = update.message.reply_to_message.from_user.id
    perms = ChatPermissions(can_send_messages=False)
    await context.bot.restrict_chat_member(
        chat_id=update.effective_chat.id,
        user_id=user_id,
        permissions=perms
    )
    await update.message.reply_text("User has been muted.")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to unmute them.")
        return
    user_id = update.message.reply_to_message.from_user.id
    perms = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_polls=True,
        can_send_other_messages=True
    )
    await context.bot.restrict_chat_member(
        chat_id=update.effective_chat.id,
        user_id=user_id,
        permissions=perms
    )
    await update.message.reply_text("User has been unmuted.")

async def gban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to gban them.")
        return
    user = update.message.reply_to_message.from_user
    user_id = user.id

    if is_globally_banned(user_id):
        await update.message.reply_text("User is already globally banned.")
        return

    gban_collection.insert_one({"user_id": user_id})
    await update.message.reply_text(f"{user.full_name} has been globally banned.")

    try:
        await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=user_id)
        await update.message.reply_text("User was also banned from this group.")
    except Exception as e:
        await update.message.reply_text(f"Couldn't ban from this group: {e}")

async def auto_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if is_globally_banned(member.id):
            await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=member.id)
            await update.message.reply_text(f"{member.full_name} is globally banned and was removed.")

# ====== Main Function ======

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("gban", gban))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, auto_kick))

    logger.info("Bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()