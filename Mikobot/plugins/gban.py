""" Global Ban Handler for Telegram Bot
This module manages banning and unbanning users across all connected groups.
"""

import html
import asyncio
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, ContextTypes

from Exon import application, DRAGONS, DEV_USERS, SUPPORT_CHAT
from Exon.modules.sql import gban_sql as sql
from Exon.modules.helper_funcs.chat_status import dev_plus, user_admin
from Exon.modules.helper_funcs.extraction import extract_user_and_text
from Exon.modules.helper_funcs.alternate import typing_action

# Helper Function: Try to ban user in a specific chat
async def try_ban_user_in_chat(chat_id: int, user_id: int):
    try:
        await application.bot.ban_chat_member(chat_id, user_id)
    except BadRequest as err:
        if err.message not in ["User not found", "User_id_invalid"]:
            print(f"Error banning in chat {chat_id}: {err}")

# Command: /gban
@dev_plus
@user_admin
@typing_action
async def gban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, reason = await extract_user_and_text(update, context)

    if not user_id:
        await update.effective_message.reply_text("Couldn't find the user to ban.")
        return

    if int(user_id) in DEV_USERS:
        await update.effective_message.reply_text("You can't ban a developer!")
        return

    if sql.is_user_gbanned(user_id):
        await update.effective_message.reply_text("User is already globally banned.")
        return

    sql.gban_user(user_id, reason or "No reason provided.")
    await update.effective_message.reply_text("Globally banned! Starting ban process...")

    # Send DM to banned user
    try:
        user_obj = sql.get_gbanned_user(user_id)
        await context.bot.send_message(
            user_id,
            text=(
                "#EVENT\nYou have been marked as Malicious and banned from any future groups we manage."
                f"\n<b>Reason:</b> <code>{html.escape(user_obj.reason)}</code>"
                f"\n<b>Appeal Chat:</b> @{SUPPORT_CHAT}"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass  # User may have blocked the bot

    # Apply ban across all chats
    for chat_id in sql.get_all_chat_ids():
        await try_ban_user_in_chat(chat_id, user_id)
        await asyncio.sleep(0.1)  # Prevent flood

    await update.effective_message.reply_text("Global ban applied in all groups.")

# Command: /ungban
@dev_plus
@user_admin
@typing_action
async def ungban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, _ = await extract_user_and_text(update, context)

    if not user_id:
        await update.effective_message.reply_text("Couldn't find the user to unban.")
        return

    if not sql.is_user_gbanned(user_id):
        await update.effective_message.reply_text("User is not globally banned.")
        return

    sql.ungban_user(user_id)
    await update.effective_message.reply_text("User has been globally unbanned.")

# Command: /gbanlist
@dev_plus
async def gbanlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gbanned_users = sql.get_gbanned_list()
    reply = "<b>Globally Banned Users:</b>\n\n"

    if not gbanned_users:
        reply += "No users are currently globally banned."
    else:
        for user in gbanned_users:
            reply += f"• <code>{user.user_id}</code> - {html.escape(user.reason)}\n"

    await update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)

# Register handlers
gban_handler = CommandHandler("gban", gban, block=False)
ungban_handler = CommandHandler("ungban", ungban, block=False)
gbanlist_handler = CommandHandler("gbanlist", gbanlist, block=False)

handlers = [gban_handler, ungban_handler, gbanlist_handler]