from telegram import Update, ChatPermissions
from telegram.ext import CommandHandler, ContextTypes
import logging

# Example: replace with your actual group IDs
GROUP_IDS = [-1002350016913]
GBAN_LIST = set()  # Replace with persistent storage in production

# Function to globally ban a user
async def gban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.effective_user:
        return

    # Only allow gban from admins or sudo users
    if not update.effective_user.id in [7039652738]:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /gban <user_id> [reason]")
        return

    user_id = int(context.args[0])
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
    GBAN_LIST.add(user_id)

    # Loop through all groups and ban the user
    for group_id in GROUP_IDS:
        try:
            await context.bot.ban_chat_member(chat_id=group_id, user_id=user_id)
        except Exception as e:
            logging.warning(f"Failed to ban in {group_id}: {e}")

    await update.message.reply_text(f"User {user_id} has been globally banned.\nReason: {reason}")

# Function to globally unban a user
async def ungban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user.id in [YOUR_ADMIN_USER_ID]:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /ungban <user_id>")
        return

    user_id = int(context.args[0])
    if user_id in GBAN_LIST:
        GBAN_LIST.remove(user_id)
        for group_id in GROUP_IDS:
            try:
                await context.bot.unban_chat_member(chat_id=group_id, user_id=user_id, only_if_banned=True)
            except Exception as e:
                logging.warning(f"Failed to unban in {group_id}: {e}")
        await update.message.reply_text(f"User {user_id} has been globally unbanned.")
    else:
        await update.message.reply_text("User is not in the GBAN list.")

# Add handlers
def add_gban_handlers(application):
    application.add_handler(CommandHandler("gban", gban))
    application.add_handler(CommandHandler("ungban", ungban))
