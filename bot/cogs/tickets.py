from __future__ import annotations

import random
import uuid
from functools import lru_cache
from typing import TYPE_CHECKING, NamedTuple, Optional, Union

import asyncpg
import discord
from discord.ext import commands
from discord.utils import format_dt, utcnow
from libs.tickets.structs import ReservedTags, TicketThread
from libs.tickets.utils import get_cached_thread, get_partial_ticket
from libs.utils.embeds import LoggingEmbed

from .config import GuildWebhookDispatcher

if TYPE_CHECKING:
    from libs.utils import RoboContext
    from rodhaj import Rodhaj

from rodhaj import TRANSPROGRAMMER_SERVER_ID

STAFF_ROLE = 1184257456419913798
MOD_ROLE = 1  # later this is the correct one
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


class ClosedEmbed(discord.Embed):
    def __init__(self, **kwargs):
        kwargs.setdefault("color", discord.Color.from_rgb(138, 255, 157))
        kwargs.setdefault("title", "\U00002705 Ticket Closed")
        kwargs.setdefault("timestamp", discord.utils.utcnow())
        super().__init__(**kwargs)
        self.set_footer(text="Ticket closed at")


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

    #### Determining active mods

    @lru_cache(maxsize=64)
    def get_staff(self, guild: discord.Guild) -> Optional[list[discord.Member]]:
        mod_role = guild.get_role(
            STAFF_ROLE
        )  # TODO: change the STAFF_ROLE_ID to the correct one
        if mod_role is None:
            return None
        return [member for member in mod_role.members]

    def determine_active_mod(self, guild: discord.Guild) -> Optional[discord.Member]:
        mod_role = guild.get_role(STAFF_ROLE)
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

    ### Conditions for closing tickets

    async def can_close_ticket(
        self, ctx: RoboContext, connection: Union[asyncpg.Pool, asyncpg.Connection]
    ):
        connection = connection or self.pool
        partial_ticket = await get_partial_ticket(ctx.author.id, connection)

        if (
            ctx.guild is None
            and partial_ticket.id is not None
            and partial_ticket.owner_id == ctx.author.id
        ):
            return True

        return False

    async def can_admin_close_ticket(self, ctx: RoboContext) -> bool:
        guild = self.bot.get_guild(TRANSPROGRAMMER_SERVER_ID) or (
            await self.bot.fetch_guild(TRANSPROGRAMMER_SERVER_ID)
        )
        staff_members = self.get_staff(guild)

        if staff_members is None:
            return False

        # TODO: Add the hierarchy system here
        staff_ids = [member.id for member in staff_members]
        from_ticket_channel = (
            isinstance(ctx.channel, discord.Thread)
            and ctx.channel.parent_id == TICKET_CHANNEL
        )

        if ctx.author.id in staff_ids and from_ticket_channel is True:
            return True
        return False

    ### CLosing and locking tickets

    async def lock_ticket(
        self, thread: discord.Thread, reason: Optional[str] = None
    ) -> discord.Thread:
        # TODO: Add the solved tag in here
        locked_thread = await thread.edit(archived=True, locked=True, reason=reason)
        return locked_thread

    async def close_ticket(
        self,
        user: Union[discord.User, discord.Member, int],
        connection: Union[asyncpg.Pool, asyncpg.Connection],
        author: Optional[Union[discord.User, discord.Member]] = None,
    ) -> Optional[discord.Thread]:
        if isinstance(user, int):
            user = self.bot.get_user(user) or (await self.bot.fetch_user(user))

        connection = connection or self.pool
        owned_ticket = await get_cached_thread(self.bot, user.id, connection)
        if owned_ticket is None:
            return None
        thread = owned_ticket.thread

        reason = f"Ticket closed by {user.name} (ID: {user.id})"
        await self.lock_ticket(thread, reason)
        self.bot.dispatch("ticket_close", thread.guild, user, thread, author)

        return thread

    async def admin_close_ticket(
        self, ctx: RoboContext, thread_id: int, pool: asyncpg.Pool
    ):
        get_owner_id_query = """
        SELECT owner_id
        FROM tickets
        WHERE thread_id = $1 AND location_id = $2;
        """

        delete_query = """
        DELETE FROM tickets
        WHERE thread_id = $1 AND owner_id = $2;
        """

        async with pool.acquire() as conn:
            owner_id = await conn.fetchval(
                get_owner_id_query, thread_id, TRANSPROGRAMMER_SERVER_ID
            )

            if owner_id is None:
                await ctx.send("Failed to close the ticket. Is there a ticket at all?")
                return

            await self.close_ticket(owner_id, conn, ctx.author)

            await conn.execute(delete_query, thread_id, owner_id)
            get_cached_thread.cache_invalidate(self.bot, ctx.author.id, conn)
            get_partial_ticket.cache_invalidate(ctx.author.id, conn)

            user = self.bot.get_user(owner_id) or (await self.bot.fetch_user(owner_id))

            ticket_description = "This ticket is now closed. Reopening and messaging in the thread will have no effect."
            user_description = f"The ticket is now closed. In order to make a new one, please DM Rodhaj with a new message to make a new ticket. (Hint: You can check if you have an active ticket by using the `{ctx.prefix}is_active` command)"
            await user.send(embed=ClosedEmbed(description=user_description))
            await ctx.send(embed=ClosedEmbed(description=ticket_description))

    ### Creation of tickets

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
                get_partial_ticket.cache_invalidate()
                get_cached_thread.cache_invalidate()
                return TicketOutput(
                    status=True,
                    ticket=created_ticket,
                    msg="Ticket successfully created. In order to use this ticket, please continue sending messages to Rodhaj. The messages will be directed towards the appropriate ticket.",
                )

    ### Misc Utils

    async def obtain_webhook(self, guild_id: int) -> Optional[discord.Webhook]:
        dispatcher = GuildWebhookDispatcher(self.bot, guild_id)
        return await dispatcher.get_webhook()

    async def tick_post(self, ctx: RoboContext) -> None:
        await ctx.message.add_reaction(discord.PartialEmoji(name="\U00002705"))

    @is_ticket_or_dm()
    @commands.hybrid_command(name="close", aliases=["solved", "closed", "resolved"])
    async def close(self, ctx: RoboContext) -> None:
        """Closes the thread"""
        query = """
        DELETE FROM tickets
        WHERE thread_id = $1 AND owner_id = $2;
        """

        if await self.can_admin_close_ticket(ctx):
            await self.admin_close_ticket(ctx, ctx.channel.id, self.pool)
            return

        async with self.pool.acquire() as conn:
            if await self.can_close_ticket(ctx, conn):
                await self.tick_post(ctx)
                closed_ticket = await self.close_ticket(ctx.author, conn)

                if closed_ticket is None:
                    await ctx.send(
                        "The ticket can not be found. Are you sure you have an open ticket?"
                    )
                    return

                await conn.execute(query, closed_ticket.id, ctx.author.id)
                get_cached_thread.cache_invalidate(self.bot, ctx.author.id, conn)
                get_partial_ticket.cache_invalidate(ctx.author.id, conn)

    @commands.Cog.listener()
    async def on_ticket_create(
        self,
        guild: discord.Guild,
        user: Union[discord.User, discord.Member],
        ticket: discord.channel.ThreadWithMessage,
        init_message: str,
    ) -> None:
        webhook = await self.obtain_webhook(guild.id)

        if webhook is not None:
            embed = LoggingEmbed(title="\U0001f3ab New Ticket")
            embed.description = init_message
            embed.add_field(name="Owner", value=user.mention)
            embed.add_field(name="Link", value=ticket.thread.mention)
            await webhook.send(embed=embed)

    @commands.Cog.listener()
    async def on_ticket_close(
        self,
        guild: discord.Guild,
        user: Union[discord.User, discord.Member],
        ticket: discord.Thread,
        author: Optional[Union[discord.User, discord.Member]] = None,
    ) -> None:
        webhook = await self.obtain_webhook(guild.id)

        if webhook is not None:
            embed = LoggingEmbed(title="\U0001f512 Ticket Closed")
            embed.description = f"The ticket has closed at {format_dt(utcnow())}"
            if author is not None:
                embed.add_field(name="Closed By", value=author.mention)
            embed.add_field(name="Owner", value=user.mention)
            embed.add_field(name="Link", value=ticket.mention)
            await webhook.send(embed=embed)


async def setup(bot: Rodhaj) -> None:
    await bot.add_cog(Tickets(bot))
