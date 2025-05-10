from threading import RLock
from time import perf_counter, time
from typing import List, Tuple, Union

from cachetools import TTLCache
from pyrogram.enums import ChatMembersFilter
from pyrogram.types import CallbackQuery, Message
from Mikobot import LOGGER

THREAD_LOCK = RLock()

# Cache settings
ADMIN_CACHE = TTLCache(maxsize=512, ttl=(60 * 30), timer=perf_counter)
TEMP_ADMIN_CACHE_BLOCK = TTLCache(maxsize=512, ttl=(60 * 10), timer=perf_counter)


async def admin_cache_reload(m: Union[Message, CallbackQuery], status=None) -> List[Tuple[int, str, bool]]:
    start = time()
    with THREAD_LOCK:
        if isinstance(m, CallbackQuery):
            m = m.message

        if not m or not hasattr(m, "chat"):
            LOGGER.warning("Invalid message object passed to admin_cache_reload")
            return []

        if status is not None:
            TEMP_ADMIN_CACHE_BLOCK[m.chat.id] = status

        if m.chat.id in TEMP_ADMIN_CACHE_BLOCK and TEMP_ADMIN_CACHE_BLOCK[m.chat.id] in ("autoblock", "manualblock"):
            return []

        try:
            admins = [
                (
                    member.user.id,
                    f"@{member.user.username}" if member.user.username else member.user.first_name,
                    member.privileges.is_anonymous,
                )
                async for member in m._client.get_chat_members(m.chat.id, filter=ChatMembersFilter.ADMINISTRATORS)
                if not member.user.is_deleted
            ]
        except Exception as e:
            LOGGER.exception(f"Failed to fetch admins for {m.chat.id}: {e}")
            return []

        ADMIN_CACHE[m.chat.id] = admins
        TEMP_ADMIN_CACHE_BLOCK[m.chat.id] = "autoblock"

        LOGGER.info(
            f"Loaded admins for chat {m.chat.id} in {round((time() - start), 3)}s due to '{status}'"
        )

        return admins
# <================================================ END =======================================================>
