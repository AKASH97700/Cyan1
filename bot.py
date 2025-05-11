#!/usr/bin/env python3
# bot.py

import sqlite3
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from telegram import (
    Update,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# --------------------- CONFIGURATION ---------------------
TOKEN          = "7737679888:AAGWAHt0-eBn1K3Mo9dOKISAhlu4rL0pHU8"
ADMIN_ID       = 7039652738
LOG_CHANNEL_ID = -1002231034844    # where logs go
GROUP_IDS      = [-1002350016913]                 # list of chat IDs for GBAN

# --------------------- DATABASE ---------------------
conn = sqlite3.connect("bot.db", check_same_thread=False)
c    = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS gban (
        user_id INTEGER PRIMARY KEY
    )
""")
c.execute("""
    CREATE TABLE IF NOT EXISTS afk (
        user_id INTEGER PRIMARY KEY,
        reason  TEXT,
        since   TEXT
    )
""")
c.execute("""
    CREATE TABLE IF NOT EXISTS welcome (
        chat_id INTEGER PRIMARY KEY,
        text    TEXT
    )
""")
conn.commit()

# --------------------- LOGGING ---------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def log_action(context: ContextTypes.DEFAULT_TYPE, text: str):
    try:
        await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=text)
    except:
        pass

# --------------------- FLOOD CONTROL ---------------------
user_times = defaultdict(list)
FLOOD_LIMIT = 5
FLOOD_WINDOW = 10  # seconds

async def flood_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ("group", "supergroup"):
        return
    uid = update.effective_user.id
    now = datetime.utcnow()
    times = [t for t in user_times[uid] if (now - t).seconds < FLOOD_WINDOW]
    times.append(now)
    user_times[uid] = times
    if len(times) > FLOOD_LIMIT:
        await update.effective_chat.restrict_member(
            uid,
            ChatPermissions(can_send_messages=False)
        )
        await update.message.reply_text("🔇 You have been muted for flooding.")
        await log_action(context, f"Flood mute: {uid} in {update.effective_chat.id}")
        user_times[uid].clear()

# --------------------- CORE ---------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Hello! Use /help to see commands.")

async def alive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ I'm alive!")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("Moderation", callback_data="MOD")],
        [InlineKeyboardButton("AFK",        callback_data="AFK")],
        [InlineKeyboardButton("Welcome",    callback_data="WEL")],
        [InlineKeyboardButton("Info",       callback_data="INFO")],
    ]
    await update.message.reply_text(
        "Select a category:", reply_markup=InlineKeyboardMarkup(kb)
    )

async def help_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    sections = {
        "MOD":  "/ban, /unban, /mute, /unmute, /gban, /ungban",
        "AFK":  "/afk [reason], auto-return on your next message",
        "WEL":  "/setwelcome (group only)",
        "INFO": "/info [@user|user_id|reply]",
    }
    await q.edit_message_text(sections.get(q.data, "❓"))

# --------------------- WELCOME ---------------------
async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ("group", "supergroup"):
        return await update.message.reply_text("This works in groups only.")
    if not context.args:
        return await update.message.reply_text("Usage: /setwelcome Welcome {first_name}!")
    text = " ".join(context.args)
    chat_id = update.effective_chat.id
    c.execute("REPLACE INTO welcome (chat_id, text) VALUES (?,?)", (chat_id, text))
    conn.commit()
    await update.message.reply_text("✅ Welcome message set for this group.")

async def greet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    c.execute("SELECT text FROM welcome WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    tmpl = row[0] if row else "Welcome {first_name}!"
    for member in update.message.new_chat_members:
        await update.message.reply_text(tmpl.format(first_name=member.first_name))

# --------------------- MODERATION ---------------------
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: /ban <user_id>")
    uid = int(context.args[0])
    await update.effective_chat.ban_member(uid)
    await update.message.reply_text(f"🚫 Banned {uid}")
    await log_action(context, f"Ban: {uid} in {update.effective_chat.id}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: /unban <user_id>")
    uid = int(context.args[0])
    await update.effective_chat.unban_member(uid)
    await update.message.reply_text(f"✅ Unbanned {uid}")
    await log_action(context, f"Unban: {uid} in {update.effective_chat.id}")

async def gban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or not context.args:
        return
    uid = int(context.args[0])
    c.execute("INSERT OR IGNORE INTO gban (user_id) VALUES (?)", (uid,))
    conn.commit()
    for gid in GROUP_IDS:
        await context.bot.ban_chat_member(gid, uid)
    await update.message.reply_text(f"🌐 Globally banned {uid}")
    await log_action(context, f"GBAN: {uid}")

async def ungban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or not context.args:
        return
    uid = int(context.args[0])
    c.execute("DELETE FROM gban WHERE user_id=?", (uid,))
    conn.commit()
    for gid in GROUP_IDS:
        await context.bot.unban_chat_member(gid, uid)
    await update.message.reply_text(f"🌐 Globally unbanned {uid}")
    await log_action(context, f"UNGBAN: {uid}")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: /mute <user_id>")
    uid = int(context.args[0])
    await update.effective_chat.restrict_member(uid, ChatPermissions(can_send_messages=False))
    await update.message.reply_text(f"🔇 Muted {uid}")
    await log_action(context, f"Mute: {uid}")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: /unmute <user_id>")
    uid = int(context.args[0])
    await update.effective_chat.restrict_member(uid, ChatPermissions(can_send_messages=True))
    await update.message.reply_text(f"🔊 Unmuted {uid}")
    await log_action(context, f"Unmute: {uid}")

# --------------------- AFK ---------------------
async def afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    reason = " ".join(context.args) if context.args else "AFK"
    since = datetime.utcnow().isoformat()
    c.execute("REPLACE INTO afk (user_id,reason,since) VALUES (?,?,?)", (uid, reason, since))
    conn.commit()
    await update.message.reply_text(f"🏖 You are now AFK: {reason}")

async def return_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    c.execute("DELETE FROM afk WHERE user_id=?", (uid,))
    conn.commit()

async def check_mentions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    for row in c.execute("SELECT user_id,reason,since FROM afk"):
        uid, reason, since = row
        if str(uid) in text:
            then = datetime.fromisoformat(since)
            delta = datetime.utcnow() - then
            await update.message.reply_text(f"↩️ {uid} is AFK: {reason} ({delta.seconds}s ago)")
            break

# --------------------- INFO ---------------------
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message.from_user
    # if user passes an ID or replies, fetch that user
    if context.args:
        try:
            target = await context.bot.get_chat(int(context.args[0]))
        except:
            if update.message.reply_to_message:
                target = update.message.reply_to_message.from_user
    uid = target.id
    photos = await context.bot.get_user_profile_photos(uid, limit=1)
    dp = photos.photos[0][0].file_id if photos.total_count else "None"
    c.execute("SELECT 1 FROM gban WHERE user_id=?", (uid,))
    is_gban = bool(c.fetchone())
    text = (
        f"Name: {target.full_name}\n"
        f"Username: @{target.username}\n"
        f"User ID: {uid}\n"
        f"Chat ID: {update.effective_chat.id}\n"
        f"Globally Banned: {is_gban}\n"
        f"Profile Pic File ID: {dp}"
    )
    await update.message.reply_text(text)

# --------------------- RUNNER ---------------------
def main():
    app = Application.builder().token(TOKEN).build()

    # middleware
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, flood_middleware), 0)

    # commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("alive", alive))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(help_btn))

    app.add_handler(CommandHandler("setwelcome", set_welcome))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet))

    for cmd in ("ban","unban","gban","ungban","mute","unmute"):
        app.add_handler(CommandHandler(cmd, globals()[cmd]))

    app.add_handler(CommandHandler("afk", afk))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, return_mention))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_mentions))

    print("Bot is running…")
    app.run_polling()

if __name__ == "__main__":
    main()
