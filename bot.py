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

# Config
BOT_TOKEN = "7737679888:AAGWAHt0-eBn1K3Mo9dOKISAhlu4rL0pHU8"
MONGO_URI = "mongodb+srv://Akash1234:Demon123@cluster0.lpghpdo.mongodb.net/?retryWrites=true&w=majority"  # e.g., mongodb+srv://...

# Logging
logging.basicConfig(
    format='[%(levelname)s] %(asctime)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# MongoDB client setup
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['telegram_bot']
gban_collection = db['gban_users']

# Helper to check GBAN
def is_globally_banned(user_id: int) -> bool:
    return gban_collection.find_one({"user_id": user_id}) is not None

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm your advanced group management bot.")

# Welcome handler
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if is_globally_banned(member.id):
            await update.effective_chat.ban_member(member.id)
            await update.message.reply_text(f"{member.full_name} is globally banned and was removed.")
        else:
            await update.message.reply_text(f"Welcome, {member.full_name}!")

# /ban
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to the user to ban.")
    user_id = update.message.reply_to_message.from_user.id
    await update.effective_chat.ban_member(user_id)
    await update.message.reply_text("User banned.")

# /unban
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to the user to unban.")
    user_id = update.message.reply_to_message.from_user.id
    await update.effective_chat.unban_member(user_id)
    await update.message.reply_text("User unbanned.")

# /mute
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to the user to mute.")
    user_id = update.message.reply_to_message.from_user.id
    perms = ChatPermissions(can_send_messages=False)
    await context.bot.restrict_chat_member(update.effective_chat.id, user_id, perms)
    await update.message.reply_text("User muted.")

# /unmute
async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to the user to unmute.")
    user_id = update.message.reply_to_message.from_user.id
    perms = ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                            can_send_polls=True, can_send_other_messages=True)
    await context.bot.restrict_chat_member(update.effective_chat.id, user_id, perms)
    await update.message.reply_text("User unmuted.")

# /gban
async def gban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("Reply to a user to gban them.")
    user = update.message.reply_to_message.from_user
    user_id = user.id

    if is_globally_banned(user_id):
        return await update.message.reply_text("User is already globally banned.")

    gban_collection.insert_one({"user_id": user_id})
    await update.message.reply_text(f"{user.full_name} has been globally banned.")

    try:
        await update.effective_chat.ban_member(user_id)
        await update.message.reply_text("User removed from this chat.")
    except Exception as e:
        await update.message.reply_text(f"Couldn't ban from this chat: {e}")

# Auto-kick GBANNED users when they join
async def auto_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if is_globally_banned(member.id):
            await update.effective_chat.ban_member(member.id)
            await update.message.reply_text(f"{member.full_name} is globally banned and was removed.")

# Main
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("gban", gban))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, auto_kick))

    logger.info("Bot running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
