from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

import asyncpg
import discord
from async_lru import alru_cache

from .structs import PartialTicket, ThreadWithGuild

if TYPE_CHECKING:
    from bot.rodhaj import Rodhaj


async def register_user(
    user_id: int, connection: Union[asyncpg.Pool, asyncpg.Connection]
):
    """Registers the user into the database

    Args:
        user_id (int): ID of the user
        connection (Union[asyncpg.Pool, asyncpg.Connection]): A connection (can be a pool) to the PostgreSQL server (through asyncpg)

    Returns:
        bool: `True` if the user has been successfully registered into the database,
        `False` if the user is already in the database
    """
    query = """
    INSERT INTO user_config (id)
    VALUES ($1) ON CONFLICT (id) DO NOTHING; 
    """
    status = await connection.execute(query, user_id)
    if status[-1] == "0":
        return False
    return True


@alru_cache(maxsize=256)
async def get_partial_ticket(
    bot: Rodhaj, user_id: int, pool: Optional[asyncpg.Pool] = None
) -> PartialTicket:
    """Provides an `PartialTicket` object in order to perform various actions

    The `PartialTicket` represents a partial record of an ticket found in the
    PostgreSQL database.

    If the `PartialTicket` instance has the attribute `id` set to `None`, then this means
    that there is no ticket found. If an ticket is found, then the partial information
    of it is filled.

    Args:
        bot (Rodhaj): An instance of `Rodhaj`
        user_id (int): ID of the user
        pool (asyncpg.Pool): Pool of connections from asyncpg. Defaults to `None`

    Returns:
        PartialTicket: An representation of a "partial" ticket
    """
    query = """
    SELECT id, thread_id, owner_id, location_id, locked
    FROM tickets
    WHERE owner_id = $1;
    """
    pool = pool or bot.pool
    rows = await pool.fetchrow(query, user_id)
    if rows is None:
        # In order to prevent caching invalid tickets, we need to invalidate the cache.
        # By invalidating the cache, we basically "ignore" the invalid
        # ticket. This essentially still leaves us with the performance boosts
        # of the LRU cache, while also properly invalidating invalid tickets
        get_partial_ticket.cache_invalidate(bot, user_id, pool)
        return PartialTicket()
    return PartialTicket(rows)


@alru_cache(maxsize=64)
async def get_cached_thread(
    bot: Rodhaj, user_id: int, connection: Optional[asyncpg.Pool] = None
) -> Optional[ThreadWithGuild]:
    """Obtains an cached thread from the tickets channel

    This has a small LRU cache (size of 64) so the cache is forced to refresh its
    internal data.

    Args:
        bot (Rodhaj): Instance of `RodHaj`
        user_id (int): ID of the user
        connection (Optional[asyncpg.Pool]): Pool of connections from asyncpg. Defaults to `None`

    Returns:
        Optional[ThreadWithGuild]: The thread with the guild the thread belongs to.
        `None` if not found.
    """
    query = """
    SELECT guild_config.ticket_channel_id, tickets.thread_id, tickets.location_id
    FROM tickets
    INNER JOIN guild_config ON guild_config.id = tickets.location_id
    WHERE tickets.owner_id  = $1;
    """
    connection = connection or bot.pool
    record = await connection.fetchrow(query, user_id)
    if record is None:
        return None
    forum_channel = bot.get_channel(record["ticket_channel_id"]) or (
        await bot.fetch_channel(record["ticket_channel_id"])
    )
    if isinstance(forum_channel, discord.ForumChannel):
        thread = forum_channel.get_thread(record["thread_id"])
        if thread is None:
            get_cached_thread.cache_invalidate(bot, user_id, connection)
            return None
        return ThreadWithGuild(thread, thread.guild)


def safe_content(content: str, amount: int = 4000) -> str:
    """Safely sends the content by reducing the length
    to avoid errors

    Args:
        content (str): Content to be sent

    Returns:
        str: A safe version of the content
    """
    if len(content) > amount:
        return content[: amount - 3] + "..."
    return content
