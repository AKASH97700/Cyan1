import sqlite3
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
)
import logging
from datetime import datetime, timedelta
from collections import defaultdict

# --- Config ---
TOKEN = "7737679888:AAGWAHt0-eBn1K3Mo9dOKISAhlu4rL0pHU8"
ADMIN_ID = 7039652738
GROUP_IDS = [-1002350016913]  # Add your group IDs

# --- Database Setup ---
conn = sqlite3.connect("bot_data.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS gban (user_id INTEGER PRIMARY KEY)")
c.execute("CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT, since TEXT)")
conn.commit()

# --- Logging ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- Flood Control ---
user_message_times = defaultdict(list)
FLOOD_LIMIT = 5
FLOOD_TIME = 10  # seconds

async def flood_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = datetime.now()
    user_message_times[user_id] = [t for t in user_message_times[user_id] if (now - t).seconds < FLOOD_TIME]
    user_message_times[user_id].append(now)

    if len(user_message_times[user_id]) > FLOOD_LIMIT:
        try:
            await update.message.chat.restrict_member(user_id, ChatPermissions())
            await update.message.reply_text(f"User {user_id} muted for flooding.")
            user_message_times[user_id] = []
        except Exception as e:
            logging.warning(f"Failed flood mute: {e}")

# --- Core Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /help to view available commands.")

async def alive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Yes, I'm alive and running!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Moderation", callback_data='mod')],
        [InlineKeyboardButton("AFK", callback_data='afk')],
        [InlineKeyboardButton("Search/Font", callback_data='search_font')],
        [InlineKeyboardButton("Flood/Welcome", callback_data='flood_welcome')],
        [InlineKeyboardButton("Lock/Unlock Media", callback_data='lock_unlock')]
    ]
    await update.message.reply_text("Select a command category:", reply_markup=InlineKeyboardMarkup(keyboard))

async def help_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    texts = {
        'mod': "Moderation Commands\n/ban, /unban, /mute, /unmute, /gban, /ungban",
        'afk': "AFK System\n/afk [reason] — Set AFK. Auto return on message.",
        'search_font': "Search & Font\n/google <query>, /font <text>",
        'flood_welcome': "Flood & Welcome\n/setwelcome <text>, Flood protection active (5 msgs/10s)",
        'lock_unlock': "Lock/Unlock Media\n/lockmedia — Lock media messages for everyone\n/unlockmedia — Unlock media messages"
    }
    await query.edit_message_text(texts.get(query.data, "Unknown section."), parse_mode="Markdown")

# --- Welcome Messages ---
WELCOME_TEXT = "Welcome {first_name}!"

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global WELCOME_TEXT
    if context.args:
        WELCOME_TEXT = ' '.join(context.args)
        await update.message.reply_text("Welcome message updated.")
    else:
        await update.message.reply_text("Usage: /setwelcome <text>")

async def greet_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in update.message.new_chat_members:
        await update.message.reply_text(WELCOME_TEXT.format(first_name=user.first_name))

# --- Lock/Unlock Media Commands ---
async def lock_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        permissions = ChatPermissions(can_send_messages=True, can_send_media_messages=False)
        await update.message.chat.restrict_members(update.message.chat.members, permissions)
        await update.message.reply_text("Media messages are locked for everyone.")

async def unlock_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        permissions = ChatPermissions(can_send_messages=True, can_send_media_messages=True)
        await update.message.chat.restrict_members(update.message.chat.members, permissions)
        await update.message.reply_text("Media messages are unlocked for everyone.")

# --- Moderation Commands ---
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            user_id = int(context.args[0])
            await update.message.chat.ban_member(user_id)
            await update.message.reply_text("User banned.")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            user_id = int(context.args[0])
            await update.message.chat.unban_member(user_id, only_if_banned=True)
            await update.message.reply_text("User unbanned.")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

async def gban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID and context.args:
        user_id = int(context.args[0])
        c.execute("INSERT OR IGNORE INTO gban (user_id) VALUES (?)", (user_id,))
        conn.commit()
        for gid in GROUP_IDS:
            try:
                await context.bot.ban_chat_member(gid, user_id)
            except:
                pass
        await update.message.reply_text("User globally banned.")

async def ungban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID and context.args:
        user_id = int(context.args[0])
        c.execute("DELETE FROM gban WHERE user_id = ?", (user_id,))
        conn.commit()
        for gid in GROUP_IDS:
            try:
                await context.bot.unban_chat_member(gid, user_id, only_if_banned=True)
            except:
                pass
        await update.message.reply_text("User globally unbanned.")

# --- Bot Runner ---
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("alive", alive))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(help_button))

    app.add_handler(CommandHandler("setwelcome", set_welcome))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_user))

    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("gban", gban))
    app.add_handler(CommandHandler("ungban", ungban))

    app.add_handler(CommandHandler("lockmedia", lock_media))
    app.add_handler(CommandHandler("unlockmedia", unlock_media))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
