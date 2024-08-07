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
    mention: str
    content: str
    tags: list[str]
    files: list[discord.File]
    created_at: datetime.datetime


class PartialTicket:
    __slots__ = ("id", "thread_id", "owner_id", "location_id", "locked")

    def __init__(self, record: Optional[asyncpg.Record] = None):
        self.id = None

        if record:
            self.id = record["id"]
            self.thread_id = record["thread_id"]
            self.owner_id = record["owner_id"]
            self.location_id = record["location_id"]
            self.locked = record["locked"]


class PartialConfig:
    __slots__ = ("id", "ticket_channel_id", "logging_channel_id")

    def __init__(self, record: Optional[asyncpg.Record] = None):
        self.id = None

        if record:
            self.id = record["id"]
            self.ticket_channel_id = record["ticket_channel_id"]
            self.logging_channel_id = record["logging_channel_id"]
