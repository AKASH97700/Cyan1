from typing import Tuple, Union
from Database.mongodb.db import dbname
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database collections
usersdb = dbname.users
cleandb = dbname.cleanmode
cleanmode = {}

# Error handling for database operations
async def is_cleanmode_on(chat_id: int) -> bool:
    try:
        mode = cleanmode.get(chat_id)
        if mode is not None:
            return mode

        user = await cleandb.find_one({"chat_id": chat_id})
        cleanmode[chat_id] = not bool(user)
        return cleanmode[chat_id]
    except Exception as e:
        logger.error(f"Error in is_cleanmode_on: {e}")
        return False

async def cleanmode_on(chat_id: int):
    try:
        cleanmode[chat_id] = True
        if await cleandb.find_one({"chat_id": chat_id}):
            await cleandb.delete_one({"chat_id": chat_id})
    except Exception as e:
        logger.error(f"Error in cleanmode_on: {e}")

async def cleanmode_off(chat_id: int):
    try:
        cleanmode[chat_id] = False
        if not await cleandb.find_one({"chat_id": chat_id}):
            await cleandb.insert_one({"chat_id": chat_id})
    except Exception as e:
        logger.error(f"Error in cleanmode_off: {e}")

async def is_afk(user_id: int) -> Tuple[bool, Union[str, dict]]:
    try:
        user = await usersdb.find_one({"user_id": user_id})
        return (True, user["reason"]) if user else (False, {})
    except Exception as e:
        logger.error(f"Error in is_afk: {e}")
        return (False, {})

async def add_afk(user_id: int, reason: Union[str, dict]):
    try:
        await usersdb.update_one(
            {"user_id": user_id}, {"$set": {"reason": reason}}, upsert=True
        )
    except Exception as e:
        logger.error(f"Error in add_afk: {e}")

async def remove_afk(user_id: int):
    try:
        if await usersdb.find_one({"user_id": user_id}):
            await usersdb.delete_one({"user_id": user_id})
    except Exception as e:
        logger.error(f"Error in remove_afk: {e}")

async def get_afk_users() -> list:
    try:
        cursor = usersdb.find({"user_id": {"$gt": 0}})
        return await cursor.to_list(length=None)
    except Exception as e:
        logger.error(f"Error in get_afk_users: {e}")
        return []
