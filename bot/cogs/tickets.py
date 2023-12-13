from __future__ import annotations

import random
import uuid
from typing import TYPE_CHECKING, NamedTuple, Optional, Union

import asyncpg
import discord
from discord.ext import commands
from libs.tickets.structs import ReservedTags, TicketThread
from libs.tickets.utils import get_cached_thread, get_partial_ticket

from .config import GuildWebhookDispatcher

if TYPE_CHECKING:
    from libs.utils import RoboContext
    from rodhaj import Rodhaj

STAFF_ROLE_ID = 1184257456419913798
TICKET_CHANNEL = 1183305410304806922  # maybe fetch it from the DB? probably not needed


def is_ticket_or_dm():
    def pred(ctx: RoboContext) -> bool:
        return (
            isinstance(ctx.channel, discord.Thread)
            and ctx.channel.parent_id == TICKET_CHANNEL
        ) or ctx.guild is None

    return commands.check(pred)


class TicketOutput(NamedTuple):
    status: bool
    ticket: discord.channel.ThreadWithMessage
    msg: str


class Tickets(commands.Cog):
    """The main central ticket management hub"""

    def __init__(self, bot: Rodhaj) -> None:
        self.bot = bot
        self.pool = self.bot.pool
        self.logger = self.bot.logger
        self.reserved_tags: dict[int, ReservedTags] = {}

    def is_tag_selected(self, user_id: int, type: str) -> Optional[bool]:
        conf = self.reserved_tags.get(user_id)

        if conf is None:
            return
        return conf[type]

    async def lock_ticket(
        self, thread: discord.Thread, reason: Optional[str] = None
    ) -> discord.Thread:
        locked_thread = await thread.edit(archived=True, locked=True, reason=reason)
        return locked_thread

    def determine_active_mod(self, guild: discord.Guild) -> Optional[discord.Member]:
        mod_role = guild.get_role(STAFF_ROLE_ID)
        if mod_role is None:
            return None

        active_members = [
            member
            for member in mod_role.members
            if member.status == discord.Status.online
            or member.status == discord.Status.dnd
        ]
        # Ideally this needs to be weighted but I'm not so sure how to implement that
        selected_mod = random.choice(active_members)  # nosec
        return selected_mod

    async def create_ticket(self, ticket: TicketThread) -> Optional[TicketOutput]:
        query = """
        SELECT ticket_channel_id
        FROM guild_config
        WHERE id = $1;
        """
        ticket_query = """
        INSERT INTO tickets (thread_id, owner_id, location_id)
        VALUES ($1, $2, $3);
        """
        ticket_channel_id = await self.pool.fetchval(query, ticket.location_id)
        if ticket_channel_id is None:
            self.logger.error(
                "No tickets channel found for server with ID %d. Cannot make ticket",
                ticket.location_id,
            )
            return

        # Should fetch channel and add to cache if not found
        tc = self.bot.get_channel(ticket_channel_id) or await self.bot.fetch_channel(
            ticket_channel_id
        )

        # It should be a forum channel....
        if not isinstance(tc, discord.ForumChannel):
            return

        # TODO: Add file attachment support later

        thread_display_id = uuid.uuid4()
        thread_name = f"{ticket.user.display_name} | {thread_display_id}"
        content = f"({ticket.user.display_name}, {discord.utils.format_dt(ticket.created_at)})\n\n{ticket.content}"
        created_ticket = await tc.create_thread(
            name=thread_name,
            content=content,
            reason=f"Ticket submitted by {ticket.user.global_name} (ID: {ticket.user.id})",
        )

        async with self.pool.acquire() as conn:
            tr = conn.transaction()
            await tr.start()

            try:
                await conn.execute(
                    ticket_query,
                    created_ticket[0].id,
                    ticket.user.id,
                    ticket.location_id,
                )
            except asyncpg.UniqueViolationError:
                await tr.rollback()
                await self.lock_ticket(
                    created_ticket[0],
                    reason=f"Attempted to create duplicate ticket (User ID: {ticket.user.id})",
                )
                return TicketOutput(
                    status=False,
                    ticket=created_ticket,
                    msg="You already have an ticket. Please ensure that you have closed all tickets before creating a new one.",
                )
            except Exception:
                await tr.rollback()
                await self.lock_ticket(
                    created_ticket[0],
                    reason=f"Failed to create ticket (User ID: {ticket.user.id})",
                )
                return TicketOutput(
                    status=False, ticket=created_ticket, msg="Could not create ticket"
                )
            else:
                await tr.commit()
                get_partial_ticket.cache_invalidate(ticket.user.id, self.pool)
                get_cached_thread.cache_invalidate(self.bot, ticket.user.id)
                return TicketOutput(
                    status=True,
                    ticket=created_ticket,
                    msg="Ticket successfully created. In order to use this ticket, please continue sending messages to Rodhaj. The messages will be directed towards the appropriate ticket.",
                )

    @is_ticket_or_dm()
    @commands.hybrid_command(name="close", aliases=["solved", "closed", "resolved"])
    async def close(self, ctx: RoboContext) -> None:
        """Closes the thread"""
        # I'll finish this later - Noelle
        await ctx.send("Sending close msg")

    @commands.Cog.listener()
    async def on_ticket_create(
        self,
        guild: discord.Guild,
        user: Union[discord.User, discord.Member],
        ticket: discord.channel.ThreadWithMessage,
        init_message: str,
    ):
        selected_mod = self.determine_active_mod(guild)
        dispatcher = GuildWebhookDispatcher(self.bot, guild.id)
        webhook = await dispatcher.get_webhook()

        select_mod_mention = f"{selected_mod.mention}, " if selected_mod else ""

        if webhook is not None:
            msg = (
                f"{select_mod_mention}{user.display_name} has created a ticket at {ticket.thread.mention}. The initial message has been provided below:\n\n"
                f"{init_message}"
            )
            await webhook.send(content=msg)


async def setup(bot: Rodhaj) -> None:
    await bot.add_cog(Tickets(bot))
