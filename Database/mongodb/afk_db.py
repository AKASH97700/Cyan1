from typing import Tuple, Union
from Database.mongodb.db import dbname

usersdb = dbname.users
cleandb = dbname.cleanmode
cleanmode = {}


async def is_cleanmode_on(chat_id: int) -> bool:
    mode = cleanmode.get(chat_id)
    if mode is not None:
        return mode

    user = await cleandb.find_one({"chat_id": chat_id})
    cleanmode[chat_id] = not bool(user)
    return cleanmode[chat_id]


async def cleanmode_on(chat_id: int):
    cleanmode[chat_id] = True
    if await cleandb.find_one({"chat_id": chat_id}):
        await cleandb.delete_one({"chat_id": chat_id})


async def cleanmode_off(chat_id: int):
    cleanmode[chat_id] = False
    if not await cleandb.find_one({"chat_id": chat_id}):
        await cleandb.insert_one({"chat_id": chat_id})


async def is_afk(user_id: int) -> Tuple[bool, Union[str, dict]]:
    user = await usersdb.find_one({"user_id": user_id})
    return (True, user["reason"]) if user else (False, {})


async def add_afk(user_id: int, reason: Union[str, dict]):
    await usersdb.update_one(
        {"user_id": user_id}, {"$set": {"reason": reason}}, upsert=True
    )


async def remove_afk(user_id: int):
    if await usersdb.find_one({"user_id": user_id}):
        await usersdb.delete_one({"user_id": user_id})


async def get_afk_users() -> list:
    cursor = usersdb.find({"user_id": {"$gt": 0}})
    return await cursor.to_list(length=None)
