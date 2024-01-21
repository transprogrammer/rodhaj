from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Annotated, NamedTuple, Optional, Union

import asyncpg
import discord
from async_lru import alru_cache
from discord.ext import commands
from discord.utils import format_dt, utcnow
from libs.tickets.structs import ReservedTags, StatusChecklist, TicketThread
from libs.tickets.utils import (
    get_cached_thread,
    get_partial_ticket,
    safe_content,
)
from libs.utils.embeds import Embed, LoggingEmbed

from .config import GuildWebhookDispatcher

if TYPE_CHECKING:
    from libs.utils import GuildContext, RoboContext
    from rodhaj import Rodhaj


STAFF_ROLE = 1184257456419913798
TICKET_EMOJI = "\U0001f3ab"  # U+1F3AB Ticket


def is_ticket_or_dm():
    def pred(ctx: RoboContext) -> bool:
        partial_config = ctx.partial_config
        return (
            isinstance(ctx.channel, discord.Thread)
            and partial_config is not None
            and ctx.channel.parent_id == partial_config.ticket_channel_id
        ) or ctx.guild is None

    return commands.check(pred)


def is_ticket_thread():
    def pred(ctx: RoboContext) -> bool:
        partial_config = ctx.partial_config
        return (
            isinstance(ctx.channel, discord.Thread)
            and ctx.guild is not None
            and partial_config is not None
            and ctx.channel.parent_id == partial_config.ticket_channel_id
        )

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


class ReplyEmbed(discord.Embed):
    def __init__(self, author: Union[discord.User, discord.Member], **kwargs):
        kwargs.setdefault("color", discord.Color.from_rgb(246, 194, 255))
        kwargs.setdefault("timestamp", discord.utils.utcnow())
        super().__init__(**kwargs)
        self.set_footer(text="Sent at")
        self.set_author(name=author.global_name, icon_url=author.display_avatar.url)


class Tickets(commands.Cog):
    """The main central ticket management hub"""

    def __init__(self, bot: Rodhaj) -> None:
        self.bot = bot
        self.pool = self.bot.pool
        self.logger = self.bot.logger
        self.reserved_tags: dict[int, ReservedTags] = {}
        self.in_progress_tickets: dict[int, StatusChecklist] = {}

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\U0001f3ab")

    ### Tag selection utils

    def add_in_progress_tag(self, author_id: int, tags: ReservedTags) -> ReservedTags:
        reserved = self.reserved_tags.setdefault(author_id, tags)
        return reserved

    def add_status_checklist(
        self, author_id: int, status: StatusChecklist
    ) -> StatusChecklist:
        return self.in_progress_tickets.setdefault(author_id, status)

    #### Determining staff

    @lru_cache(maxsize=64)
    def get_staff(self, guild: discord.Guild) -> Optional[list[discord.Member]]:
        mod_role = guild.get_role(STAFF_ROLE)
        if mod_role is None:
            return None
        return [member for member in mod_role.members]

    ### Conditions for closing tickets

    async def can_close_ticket(self, ctx: RoboContext):
        partial_ticket = await get_partial_ticket(self.bot, ctx.author.id)

        if partial_ticket.id is None:
            return False

        if (
            ctx.guild is None
            and partial_ticket.owner_id == ctx.author.id
            or await self.can_admin_close_ticket(ctx)
        ):
            return True

        return False

    async def can_admin_close_ticket(self, ctx: RoboContext) -> bool:
        guild_id = self.bot.transprogrammer_guild_id
        guild = self.bot.get_guild(guild_id) or (await self.bot.fetch_guild(guild_id))
        staff_members = self.get_staff(guild)

        if staff_members is None:
            return False

        # TODO: Add the hierarchy system here
        staff_ids = [member.id for member in staff_members]
        from_ticket_channel = (
            isinstance(ctx.channel, discord.Thread)
            and ctx.partial_config is not None
            and ctx.channel.parent_id == ctx.partial_config.ticket_channel_id
        )

        if ctx.author.id in staff_ids and from_ticket_channel is True:
            return True
        return False

    ### CLosing and locking tickets

    async def lock_ticket(
        self, thread: discord.Thread, reason: Optional[str] = None
    ) -> discord.Thread:
        tags = thread.applied_tags
        solved_tag = self.get_solved_tag(thread.parent)

        if solved_tag is not None and not any(tag.id == solved_tag.id for tag in tags):
            tags.append(solved_tag)

        locked_thread = await thread.edit(
            applied_tags=tags, archived=True, locked=True, reason=reason
        )
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

    async def notify_finished_ticket(self, ctx: RoboContext, owner_id: int):
        # We know that an admin must have closed it
        if await self.can_admin_close_ticket(ctx):
            user = self.bot.get_user(owner_id) or (await self.bot.fetch_user(owner_id))
            user_description = f"The ticket is now closed. In order to make a new one, please DM Rodhaj with a new message to make a new ticket. (Hint: You can check if you have an active ticket by using the `{ctx.prefix}is_active` command)"
            await user.send(embed=ClosedEmbed(description=user_description))
            return
        closed_embed = ClosedEmbed(description="You have closed the ticket")
        closed_embed.set_footer(
            text="In order to make a new one, please DM Rodhaj with a new message to make a new ticket."
        )
        await ctx.author.send(embed=closed_embed)

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

        all_tags = tc.available_tags
        applied_tags = [
            discord.utils.get(all_tags, name=tag.title()) for tag in ticket.tags
        ]
        processed_tags = [tag for tag in applied_tags if tag is not None]

        content = f"({ticket.user.display_name}, {discord.utils.format_dt(ticket.created_at)})\n\n{ticket.content}"
        created_ticket = await tc.create_thread(
            applied_tags=processed_tags,
            name=ticket.title,
            content=content,
            files=ticket.files,
            reason=f"Ticket submitted by {ticket.user.global_name} (ID: {ticket.user.id})",
        )

        async with self.pool.acquire() as conn:
            tr = conn.transaction()
            await tr.start()

            try:
                await conn.execute(
                    ticket_query,
                    created_ticket.thread.id,
                    ticket.user.id,
                    ticket.location_id,
                )
            except asyncpg.UniqueViolationError:
                await tr.rollback()
                await self.lock_ticket(
                    created_ticket.thread,
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
                    created_ticket.thread,
                    reason=f"Failed to create ticket (User ID: {ticket.user.id})",
                )
                return TicketOutput(
                    status=False, ticket=created_ticket, msg="Could not create ticket"
                )
            else:
                await tr.commit()
                return TicketOutput(
                    status=True,
                    ticket=created_ticket,
                    msg="Ticket successfully created. In order to use this ticket, please continue sending messages to Rodhaj. The messages will be directed towards the appropriate ticket.",
                )

    ### Obtaining owner of tickets
    @alru_cache()
    async def get_ticket_owner_id(self, thread_id: int) -> Optional[discord.User]:
        query = """
        SELECT owner_id
        FROM tickets
        WHERE thread_id = $1;
        """
        owner_id = await self.pool.fetchval(query, thread_id)
        if owner_id is None:
            self.get_ticket_owner_id.cache_invalidate(thread_id)
            return None
        user = self.bot.get_user(owner_id) or (await self.bot.fetch_user(owner_id))
        return user

    ### Misc Utils

    async def obtain_webhook(self, guild_id: int) -> Optional[discord.Webhook]:
        dispatcher = GuildWebhookDispatcher(self.bot, guild_id)
        return await dispatcher.get_webhook()

    async def tick_post(self, ctx: RoboContext) -> None:
        await ctx.message.add_reaction(discord.PartialEmoji(name="\U00002705"))

    def get_solved_tag(
        self, channel: Optional[Union[discord.ForumChannel, discord.TextChannel]]
    ):
        if not isinstance(channel, discord.ForumChannel):
            return None

        all_tags = channel.available_tags

        solved_tag = discord.utils.get(all_tags, name="Resolved")
        if solved_tag is None:
            return None
        return solved_tag

    ### Feature commands

    @is_ticket_or_dm()
    @commands.cooldown(1, 20, commands.BucketType.channel)
    @commands.hybrid_command(name="close", aliases=["solved", "closed", "resolved"])
    async def close(self, ctx: RoboContext) -> None:
        """Closes the thread"""
        query = """
        DELETE FROM tickets
        WHERE thread_id = $1 AND owner_id = $2;
        """
        get_owner_id_query = """
        SELECT owner_id
        FROM tickets
        WHERE thread_id = $1 AND location_id = $2;
        """

        async with self.pool.acquire() as conn:
            if await self.can_close_ticket(ctx):
                owner_id = ctx.author.id
                if await self.can_admin_close_ticket(ctx):
                    owner_id = await conn.fetchval(
                        get_owner_id_query,
                        ctx.channel.id,
                        self.bot.transprogrammer_guild_id,
                    )

                await self.tick_post(ctx)
                closed_ticket = await self.close_ticket(ctx.author, conn)
                if closed_ticket is None:
                    await ctx.send(
                        "The ticket can not be found. Are you sure you have an open ticket?"
                    )
                    return
                await conn.execute(query, closed_ticket.id, owner_id)
                get_cached_thread.cache_invalidate(self.bot, owner_id, self.pool)
                get_partial_ticket.cache_invalidate(self.bot, owner_id, self.pool)
                self.get_ticket_owner_id.cache_invalidate(closed_ticket.id)
                await self.notify_finished_ticket(ctx, owner_id)

    # 10 command invocations per 12 seconds for each member
    # These values should not be tripped unless someone is spamming
    # https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/mod.py#L524C9-L524C74
    @is_ticket_thread()
    @commands.cooldown(10, 12, commands.BucketType.member)
    @commands.command(name="reply", aliases=["r"])
    async def reply(
        self, ctx: GuildContext, *, message: Annotated[str, commands.clean_content]
    ) -> None:
        """Replies back to the owner of the active ticket with a message"""
        ticket_owner = await self.get_ticket_owner_id(ctx.channel.id)

        if ticket_owner is None:
            await ctx.send("No owner could be found for the current ticket")
            return

        dispatcher = GuildWebhookDispatcher(self.bot, ctx.guild.id)
        tw = await dispatcher.get_ticket_webhook()
        if tw is None:
            await ctx.send("Could not find webhook")
            return

        # We might want to have these as a chain of embeds but eh
        embed = ReplyEmbed(author=ctx.author)
        embed.description = safe_content(message)

        if isinstance(ctx.channel, discord.Thread):
            # May hit the ratelimit hard. Note this
            await ctx.message.delete(delay=30.0)
            await tw.send(
                content=message,
                username=f"[REPLY] {ctx.author.display_name}",
                avatar_url=ctx.author.display_avatar.url,
                thread=ctx.channel,
            )
        await ticket_owner.send(embed=embed)

    ### Ticket information

    @is_ticket_or_dm()
    @commands.hybrid_command(name="is-active", aliases=["is_active"])
    async def is_active(self, ctx: RoboContext) -> None:
        """Determines whether the current ticket is active"""
        ticket = await get_cached_thread(self.bot, ctx.author.id, self.pool)
        is_thread_active = ticket is not None
        format_str = "Active" if is_thread_active else "Not Active"
        await ctx.send(f"The current ticket is: {format_str}")

    @is_ticket_or_dm()
    @commands.hybrid_command(name="ticket-info", aliases=["tinfo"])
    async def ticket_info(self, ctx: RoboContext) -> None:
        """Provides information about the current ticket"""
        ticket = await get_cached_thread(self.bot, ctx.author.id, self.pool)
        partial_ticket = await get_partial_ticket(self.bot, ctx.author.id, self.pool)
        if ticket is None or partial_ticket.id is None:
            await ctx.send(
                "You have no active tickets. Please send a message to Rodhaj to get started"
            )
            return

        formatted_tags = ", ".join(
            tag.name for tag in ticket.thread.applied_tags
        ).rstrip(",")
        ticket_owner = self.bot.get_user(partial_ticket.owner_id) or (
            await self.bot.fetch_user(partial_ticket.owner_id)
        )
        embed = Embed()
        embed.title = f"{TICKET_EMOJI} {ticket.thread.name}"
        embed.description = formatted_tags
        embed.add_field(name="Is Active", value=ticket is not None, inline=False)
        embed.add_field(
            name="Is Closed",
            value=ticket.thread.archived and ticket.thread.locked,
            inline=False,
        )
        embed.add_field(name="Ticket Owner", value=ticket_owner.mention, inline=False)
        embed.add_field(
            name="Associated Guild", value=ticket.source_guild.name, inline=False
        )
        embed.add_field(name="Created At", value=format_dt(ticket.thread.created_at), inline=False)  # type: ignore
        await ctx.send(embed=embed)

    # As the guild has an entry in the cache,
    # we need to invalidate it if a guild goes
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        dispatcher = GuildWebhookDispatcher(self.bot, guild.id)
        dispatcher.get_config.cache_invalidate()

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
            embed = LoggingEmbed(title=f"{TICKET_EMOJI} New Ticket")
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
            embed = LoggingEmbed(
                title="\U0001f512 Ticket Closed",
                color=discord.Color.from_rgb(194, 163, 255),
            )
            embed.description = f"The ticket has closed at {format_dt(utcnow())}"
            if author is not None:
                embed.add_field(name="Closed By", value=author.mention)
            embed.add_field(name="Owner", value=user.mention)
            embed.add_field(name="Link", value=ticket.mention)
            await webhook.send(embed=embed)


async def setup(bot: Rodhaj) -> None:
    await bot.add_cog(Tickets(bot))
