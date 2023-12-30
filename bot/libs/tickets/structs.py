from __future__ import annotations

import asyncio
import datetime
from typing import NamedTuple, Optional, TypedDict, Union

import asyncpg
import discord
import msgspec


class StatusChecklist(msgspec.Struct):
    title: asyncio.Event = asyncio.Event()
    tags: asyncio.Event = asyncio.Event()


class ReservedTags(TypedDict):
    question: bool
    serious: bool
    private: bool


class ThreadWithGuild(NamedTuple):
    thread: discord.Thread
    source_guild: discord.Guild


class TicketThread(msgspec.Struct):
    title: str
    user: Union[discord.User, discord.Member]
    location_id: int
    content: str
    tags: list[str]
    created_at: datetime.datetime


class PartialTicket:
    __slots__ = ("id", "thread_id", "owner_id", "location_id")

    def __init__(self, record: Optional[asyncpg.Record] = None):
        self.id = None

        if record:
            self.id = record["id"]
            self.thread_id = record["thread_id"]
            self.owner_id = record["owner_id"]
            self.location_id = record["location_id"]

    # For debugging purposes
    def __repr__(self):
        if self.id is None:
            return f"<PartialTicket id={self.id}>"
        return f"<PartialTicket id={self.id} thread_id={self.thread_id} owner_id={self.owner_id} location_id={self.location_id}>"
