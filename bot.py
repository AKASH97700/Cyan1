import json
import logging
from telegram import Update, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load configuration
with open('config.json') as f:
    config = json.load(f)

TOKEN = config['token']
GBAN_FILE = 'gbans.json'
SETTINGS_FILE = 'group_settings.json'

# Load initial data
try:
    with open(GBAN_FILE, 'r') as f:
        GBANS = json.load(f)
except FileNotFoundError:
    GBANS = {'users': []}

try:
    with open(SETTINGS_FILE, 'r') as f:
        GROUP_SETTINGS = json.load(f)
except FileNotFoundError:
    GROUP_SETTINGS = {}

def save_gbans():
    with open(GBAN_FILE, 'w') as f:
        json.dump(GBANS, f)

def save_settings():
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(GROUP_SETTINGS, f)

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = await update.get_chat_member(update.effective_chat.id, update.effective_user.id)
    return user.status in ['administrator', 'creator']

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👮 Group Management Bot Ready!")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    🛠️ Available Commands:
    /start - Start the bot
    /help - Show this help
    /warn <user> - Warn a user
    /ban <user> - Ban a user
    /unban <user> - Unban a user
    /kick <user> - Kick a user
    /mute <user> - Mute a user
    /unmute <user> - Unmute a user
    /gban <user> - Globally ban a user
    /ungban <user> - Remove global ban
    /setwelcome <text> - Set welcome message
    /delete - Delete command message
    """
    await update.message.reply_text(help_text)

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("You need to be admin to use this command!")
        return

    user_id = update.message.reply_to_message.from_user.id
    await context.bot.ban_chat_member(
        chat_id=update.effective_chat.id,
        user_id=user_id
    )
    await update.message.reply_text(f"🚫 User {user_id} has been banned!")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("You need to be admin to use this command!")
        return

    user_id = update.message.reply_to_message.from_user.id
    await context.bot.unban_chat_member(
        chat_id=update.effective_chat.id,
        user_id=user_id
    )
    await update.message.reply_text(f"✅ User {user_id} has been unbanned!")

async def gban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("You need to be admin to use this command!")
        return

    user_id = update.message.reply_to_message.from_user.id
    if user_id not in GBANS['users']:
        GBANS['users'].append(user_id)
        save_gbans()
    await update.message.reply_text(f"🌍 User {user_id} has been globally banned!")

async def ungban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("You need to be admin to use this command!")
        return

    user_id = update.message.reply_to_message.from_user.id
    if user_id in GBANS['users']:
        GBANS['users'].remove(user_id)
        save_gbans()
    await update.message.reply_text(f"🌏 User {user_id} has been removed from global bans!")

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("You need to be admin to use this command!")
        return

    welcome_text = ' '.join(context.args)
    chat_id = str(update.effective_chat.id)
    GROUP_SETTINGS[chat_id] = {'welcome': welcome_text}
    save_settings()
    await update.message.reply_text("✅ Welcome message updated!")

async def welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if chat_id not in GROUP_SETTINGS:
        return

    welcome_text = GROUP_SETTINGS[chat_id].get('welcome', '')
    for member in update.message.new_chat_members:
        formatted_welcome = welcome_text.format(
            name=member.full_name,
            mention=member.mention_markdown()
        )
        await update.message.reply_text(formatted_welcome)

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update, context):
        await update.message.delete()

async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) not in GROUP_SETTINGS:
        return
    
    if update.effective_user.id in GBANS['users']:
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id
        )
        await update.message.reply_text("🚫 Globally banned user detected and banned!")

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("gban", gban))
    application.add_handler(CommandHandler("ungban", ungban))
    application.add_handler(CommandHandler("setwelcome", set_welcome))
    application.add_handler(CommandHandler("delete", delete_command))

    # Event handlers
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_message))
    application.add_handler(MessageHandler(filters.ALL & filters.ChatType.GROUPS, anti_spam))

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
    
