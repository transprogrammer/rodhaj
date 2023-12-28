from __future__ import annotations

import datetime
from typing import NamedTuple, Optional, TypedDict, Union

import asyncpg
import discord
import msgspec


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
