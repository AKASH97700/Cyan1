# Advanced Telegram Group Management Bot
# Supports: Welcome per-group, Ban/Gban, Mute/Unmute, AFK, Google Search, Font Styling, Flood Control,
# Lock/Unlock Restrictions, Command Help Menu, Logging, /info command

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
TOKEN = "7737679888:AAGWAHt0-eBn1K3Mo9dOKISAhlu4rL0pHU8"
ADMIN_ID = 7039652738  # your Telegram ID
GROUP_IDS = []  # for GBAN target groups
LOG_CHANNEL_ID = -1002231034844  # your log channel

# ---------------------------- Database Setup ----------------------------
conn = sqlite3.connect("bot_data.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS gban (user_id INTEGER PRIMARY KEY)")
c.execute("CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT, since TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS welcome (chat_id INTEGER PRIMARY KEY, text TEXT)")
conn.commit()

# ---------------------------- Logging Setup ----------------------------
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

async def log_action(context: ContextTypes.DEFAULT_TYPE, action: str):
    await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=action)

# ---------------------------- Flood Control ----------------------------
user_times = defaultdict(list)
FLOOD_LIMIT = 5
FLOOD_TIME = 10  # seconds

async def flood_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        return
    uid = update.effective_user.id
    now = datetime.now()
    user_times[uid] = [t for t in user_times[uid] if (now - t).seconds < FLOOD_TIME]
    user_times[uid].append(now)
    if len(user_times[uid]) > FLOOD_LIMIT:
        await update.message.chat.restrict_member(uid, ChatPermissions())
        await update.message.reply_text("Muted for flooding.")
        await log_action(context, f"Flood mute {uid} in {update.effective_chat.id}")
        user_times[uid].clear()

# ---------------------------- Core Commands ----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Use /help")

async def alive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("I am alive")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton(cat, callback_data=cat)] for cat in ["mod","afk","search_font","flood_welcome","info"]]
    await update.message.reply_text("Choose:", reply_markup=InlineKeyboardMarkup(kb))

async def help_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sec = update.callback_query.data
    texts = {
        'mod':'/ban /unban /mute /unmute /gban /ungban /lock /unlock',
        'afk':'/afk /info',
        'search_font':'/google /font',
        'flood_welcome':'/setwelcome (in group) FloodControl active',
        'info':'/info <reply or id>'
    }
    await update.callback_query.edit_message_text(texts.get(sec,'-'))

# ---------------------------- Welcome per-group ----------------------------
async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group","supergroup"]: return
    if not context.args: return await update.message.reply_text("Usage: /setwelcome text")
    text = ' '.join(context.args)
    cid = update.effective_chat.id
    c.execute("REPLACE INTO welcome VALUES(?,?)", (cid, text))
    conn.commit()
    await update.message.reply_text("Welcome set.")

async def greet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    c.execute("SELECT text FROM welcome WHERE chat_id=?", (cid,))
    row = c.fetchone()
    txt = row[0] if row else "Welcome {first}!"
    for u in update.message.new_chat_members:
        await update.message.reply_text(txt.format(first=u.first_name))

# ---------------------------- Moderation ----------------------------
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    target=int(context.args[0])
    await update.effective_chat.ban_member(target)
    await update.message.reply_text(f"Banned {target}")
    await log_action(context,f"ban {target} in {update.effective_chat.id}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    t=int(context.args[0])
    await update.effective_chat.unban_member(t)
    await update.message.reply_text(f"Unbanned {t}")
    await log_action(context,f"unban {t} in {update.effective_chat.id}")

async def gban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID or not context.args: return
    u=int(context.args[0])
    c.execute("INSERT OR IGNORE INTO gban VALUES(?)",(u,));conn.commit()
    for gid in GROUP_IDS:
        await context.bot.ban_chat_member(gid,u)
    await update.message.reply_text(f"Globally banned {u}")
    await log_action(context,f"gban {u}")

async def ungban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID or not context.args: return
    u=int(context.args[0])
    c.execute("DELETE FROM gban WHERE user_id=?",(u,));conn.commit()
    for gid in GROUP_IDS:
        await context.bot.unban_chat_member(gid,u)
    await update.message.reply_text(f"Globally unbanned {u}")
    await log_action(context,f"ungban {u}")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    u=int(context.args[0]);await update.effective_chat.restrict_member(u,ChatPermissions())
    await update.message.reply_text(f"Muted {u}")
    await log_action(context,f"mute {u}")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    u=int(context.args[0]);await update.effective_chat.restrict_member(u,ChatPermissions(can_send_messages=True))
    await update.message.reply_text(f"Unmuted {u}")
    await log_action(context,f"unmute {u}")

# ---------------------------- Lock/Unlock ----------------------------
locks={'media':{'can_send_photos':False,'can_send_videos':False,'can_send_documents':False},
       'links':{'can_add_web_page_previews':False},
       'stickers':{'can_send_other_messages':False},
       'polls':{'can_send_polls':False}}

async def lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    t=context.args[0].lower()
    if t in locks:
        await context.bot.set_chat_permissions(update.effective_chat.id, **locks[t])
        await update.message.reply_text(f"Locked {t}")

async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    t=context.args[0].lower()
    if t in locks:
        perms=ChatPermissions(**{k:True for k in locks[t]})
        await context.bot.set_chat_permissions(update.effective_chat.id, perms)
        await update.message.reply_text(f"Unlocked {t}")

# ---------------------------- AFK & Info ----------------------------
async def afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id;r=' '.join(context.args) or 'AFK'
    c.execute("REPLACE INTO afk VALUES(?,?,?)",(uid,r,datetime.now().isoformat()));conn.commit()
    await update.message.reply_text(f"AFK: {r}")

async def return_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id;c.execute("DELETE FROM afk WHERE user_id=?",(uid,));conn.commit()

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user=update.message.from_user
    target=user if not context.args else await context.bot.get_chat(int(context.args[0]))
    uid=target.id;chatid=update.effective_chat.id
    # dp
    photo = (await context.bot.get_user_profile_photos(uid, limit=1)).photos
    dp = photo[0][0].file_id if photo else None
    # statuses
    c.execute("SELECT 1 FROM gban WHERE user_id=?",(uid,));isg=bool(c.fetchone())
    # can't check realtime mute/ban easily
    text=(f"Name: {target.full_name}\nUsername: @{target.username}\nID: {uid}\nChat: {chatid}\nGBAN: {isg}\nProfilePicID: {dp}")
    await update.message.reply_text(text)

# ---------------------------- Search & Font ----------------------------
async def google(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        q='+'.join(context.args)
        await update.message.reply_text(f"https://google.com/search?q={q}")

async def font(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args)<2: return
    st,txt=context.args[0], ' '.join(context.args[1:])
    if st=='bold': out=''.join(chr(0x1D400+ord(c)-65) if c.isupper() else c for c in txt)
    else: out=txt
    await update.message.reply_text(out)

# ---------------------------- Runner ----------------------------
def main():
    app=Application.builder().token(TOKEN).build()
    # core
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("alive",alive))
    app.add_handler(CommandHandler("help",help_command))
    app.add_handler(CallbackQueryHandler(help_button))
    # welcome
    app.add_handler(CommandHandler("setwelcome",set_welcome))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS,greet))
    # moderation
    for cmd in [ban,unban,gban,ungban,mute,unmute,lock,unlock]:
        app.add_handler(CommandHandler(cmd.__name__,cmd))
    # afk/info
    app.add_handler(CommandHandler("afk",afk))
    app.add_handler(CommandHandler("info",info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,return_afk))
    # flood, search,font
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS,flood_control))
    app.add_handler(CommandHandler("google",google))
    app.add_handler(CommandHandler("font",font))
    print("Running...")
    app.run_polling()

if __name__=='__main__':
    main()
    
