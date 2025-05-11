# Advanced Telegram Group Management Bot
# Supports: Welcome, Ban/Gban, Mute/Unmute, AFK, Google Search, Font Styling, Flood Control,
# Lock/Unlock Restrictions, Command Help Menu, Logging to Log Channel

import sqlite3
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

# ---------------------------- Configuration ----------------------------
TOKEN = "7737679888:AAGWAHt0-eBn1K3Mo9dOKISAhlu4rL0pHU8"  # Replace with your bot token
ADMIN_ID =  7039652738     # Replace with your Telegram user ID
GROUP_IDS = [-1002350016913]  # Replace with your actual group IDs for GBAN
LOG_CHANNEL_ID = -1002231034844  # Replace with your log group/channel ID

# ---------------------------- Database Setup ----------------------------
conn = sqlite3.connect("bot_data.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS gban (user_id INTEGER PRIMARY KEY)")
c.execute("CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT, since TEXT)")
conn.commit()

# ---------------------------- Logging Setup ----------------------------
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

async def log_action(context: ContextTypes.DEFAULT_TYPE, action: str):
    try:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=action)
    except Exception as e:
        logging.warning(f"Log send failed: {e}")

# ---------------------------- Flood Control ----------------------------
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
            await log_action(context, f"Flood Mute: User {user_id} in {update.effective_chat.title}")
            user_message_times[user_id] = []
        except Exception as e:
            logging.warning(f"Failed flood mute: {e}")

# ---------------------------- Core Commands ----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /help to view available commands.")

async def alive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Yes, I'm alive and running!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Moderation", callback_data='mod')],
        [InlineKeyboardButton("AFK", callback_data='afk')],
        [InlineKeyboardButton("Search/Font", callback_data='search_font')],
        [InlineKeyboardButton("Flood/Welcome", callback_data='flood_welcome')]
    ]
    await update.message.reply_text("Select a command category:", reply_markup=InlineKeyboardMarkup(keyboard))

async def help_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    texts = {
        'mod': "Moderation\n/ban, /unban, /mute, /unmute, /gban, /ungban, /lock <type>, /unlock <type>",
        'afk': "AFK\n/afk [reason] — Set AFK. Auto return when you message.",
        'search_font': "Search & Font\n/google <query>, /font <style> <text>",
        'flood_welcome': "Flood & Welcome\n/setwelcome <text>. Flood protection active (5 messages in 10s)"
    }
    await query.edit_message_text(texts.get(query.data, "Unknown section."), parse_mode="Markdown")

# ---------------------------- Welcome System ----------------------------
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

# ---------------------------- Moderation ----------------------------
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            user_id = int(context.args[0])
            await update.message.chat.ban_member(user_id)
            await update.message.reply_text("User banned.")
            await log_action(context, f"Ban: User {user_id} banned in {update.effective_chat.title}")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            user_id = int(context.args[0])
            await update.message.chat.unban_member(user_id, only_if_banned=True)
            await update.message.reply_text("User unbanned.")
            await log_action(context, f"Unban: User {user_id} unbanned in {update.effective_chat.title}")
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
            except: pass
        await update.message.reply_text("User globally banned.")
        await log_action(context, f"GBAN: User {user_id} globally banned.")

async def ungban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID and context.args:
        user_id = int(context.args[0])
        c.execute("DELETE FROM gban WHERE user_id = ?", (user_id,))
        conn.commit()
        for gid in GROUP_IDS:
            try:
                await context.bot.unban_chat_member(gid, user_id, only_if_banned=True)
            except: pass
        await update.message.reply_text("User globally unbanned.")
        await log_action(context, f"UNGBAN: User {user_id} globally unbanned.")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        user_id = int(context.args[0])
        await update.message.chat.restrict_member(user_id, ChatPermissions())
        await update.message.reply_text("User muted.")
        await log_action(context, f"Mute: User {user_id} muted in {update.effective_chat.title}")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        user_id = int(context.args[0])
        perms = ChatPermissions(can_send_messages=True)
        await update.message.chat.restrict_member(user_id, perms)
        await update.message.reply_text("User unmuted.")
        await log_action(context, f"Unmute: User {user_id} unmuted in {update.effective_chat.title}")

# ---------------------------- Lock/Unlock ----------------------------
lockable_permissions = {
    'media': ChatPermissions(can_send_media_messages=False),
    'links': ChatPermissions(can_add_web_page_previews=False),
    'stickers': ChatPermissions(can_send_other_messages=False),
    'polls': ChatPermissions(can_send_polls=False),
    'inline': ChatPermissions(can_use_inline_bots=False)
}

unlockable_permissions = {
    'media': ChatPermissions(can_send_media_messages=True),
    'links': ChatPermissions(can_add_web_page_previews=True),
    'stickers': ChatPermissions(can_send_other_messages=True),
    'polls': ChatPermissions(can_send_polls=True),
    'inline': ChatPermissions(can_use_inline_bots=True)
}

async def lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        item = context.args[0].lower()
        if item in lockable_permissions:
            perms = lockable_permissions[item]
            await context.bot.set_chat_permissions(update.effective_chat.id, perms)
            await update.message.reply_text(f"Locked {item} in this chat.")
        else:
            await update.message.reply_text("Unknown lock type. Try: media, links, stickers, polls, inline")

async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        item = context.args[0].lower()
        if item in unlockable_permissions:
            perms = unlockable_permissions[item]
            await context.bot.set_chat_permissions(update.effective_chat.id, perms)
            await update.message.reply_text(f"Unlocked {item} in this chat.")
        else:
            await update.message.reply_text("Unknown unlock type. Try: media, links, stickers, polls, inline")

# ---------------------------- AFK System ----------------------------
async def afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason = ' '.join(context.args) if context.args else "AFK"
    user_id = update.effective_user.id
    since = datetime.now().isoformat()
    c.execute("REPLACE INTO afk (user_id, reason, since) VALUES (?, ?, ?)", (user_id, reason, since))
    conn.commit()
    await update.message.reply_text(f"You're now AFK: {reason}")

async def return_from_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    c.execute("SELECT * FROM afk WHERE user_id = ?", (user_id,))
    if c.fetchone():
        c.execute("DELETE FROM afk WHERE user_id = ?", (user_id,))
        conn.commit()
        await update.message.reply_text("Welcome back! You're no longer AFK.")

async def check_afk_mentions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    c.execute("SELECT user_id, reason, since FROM afk")
    for user_id, reason, since in c.fetchall():
        if str(user_id) in text:
            dt = datetime.fromisoformat(since)
            duration = datetime.now() - dt
            await update.message.reply_text(f"User is AFK: {reason} ({duration})")
            break

# ---------------------------- Google & Font ----------------------------
async def google(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        query = ' '.join(context.args)
        link = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        await update.message.reply_text(f"Search result: {link}")

fancy_fonts = {
    'bold': lambda text: ''.join(chr(0x1D400 + ord(c) - ord('A')) if c.isupper() else c for c in text),
}

async def font(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /font <style> <text>")
        return
    style = context.args[0].lower()
    text = ' '.join(context.args[1:])
    styled = fancy_fonts.get(style, lambda x: x)(text)
    await update.message.reply_text(styled)

# ---------------------------- Bot Runner ----------------------------
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
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("lock", lock))
    app.add_handler(CommandHandler("unlock", unlock))

    app.add_handler(CommandHandler("afk", afk))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, return_from_afk))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_afk_mentions))

    app.add_handler(CommandHandler("google", google))
    app.add_handler(CommandHandler("font", font))

    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, flood_control))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
