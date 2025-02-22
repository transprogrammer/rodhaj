from __future__ import annotations

import asyncio
import datetime
import uuid
from typing import TYPE_CHECKING, Annotated, Optional, TypedDict, Union

import asyncpg
import discord
import msgspec
from async_lru import alru_cache
from discord.ext import commands
from discord.utils import format_dt, utcnow
from libs.utils import ErrorEmbed
from libs.utils.checks import bot_check_permissions
from libs.utils.embeds import CooldownEmbed, Embed, LoggingEmbed
from libs.utils.modals import RoboModal
from libs.utils.views import RoboView

from .config import GuildWebhookDispatcher

if TYPE_CHECKING:
    from libs.utils import GuildContext, RoboContext
    from rodhaj import Rodhaj

    from .config import Config


TICKET_EMOJI = "\U0001f3ab"  # U+1F3AB Ticket

### Command checks


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


### Public ticket utilities


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


### Typed Structs and Slotted Classes


class ReservedTags(TypedDict):
    question: bool
    serious: bool
    private: bool


class TicketOutput(msgspec.Struct, frozen=True):
    status: bool
    ticket: discord.channel.ThreadWithMessage
    msg: str


class ThreadWithGuild(msgspec.Struct, frozen=True):
    thread: discord.Thread
    source_guild: discord.Guild


class StatusChecklist(msgspec.Struct, frozen=True):
    title: asyncio.Event = asyncio.Event()
    tags: asyncio.Event = asyncio.Event()


class TicketThread(msgspec.Struct, frozen=True):
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


### Embeds


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


### UI Components (Views, Modals and Selects)


# Note that these emoji codepoints appear a lot:
# \U00002705 - U+2705 White Heavy Check Mark
# \U0000274c - U+274c Cross Mark
class TicketTitleModal(RoboModal, title="Ticket Title"):
    def __init__(self, ctx: RoboContext, ticket_cog: Tickets, *args, **kwargs):
        super().__init__(ctx=ctx, *args, **kwargs)

        self.title_input = discord.ui.TextInput(
            label="Title",
            style=discord.TextStyle.long,
            placeholder="Input a title...",
            min_length=20,
            max_length=100,
        )
        self.input: Optional[str] = None
        self.ticket_cog = ticket_cog
        self.add_item(self.title_input)

    async def on_submit(
        self, interaction: discord.Interaction[Rodhaj]
    ) -> Optional[str]:
        self.input = self.title_input.value
        self.ticket_cog.in_progress_tickets[interaction.user.id].title.set()
        await interaction.response.send_message(
            f"The title of the ticket is set to:\n`{self.title_input.value}`",
            ephemeral=True,
        )
        return self.input


class TicketTagsSelect(discord.ui.Select):
    def __init__(self, tickets_cog: Tickets):
        options = [
            discord.SelectOption(
                label="Question",
                value="question",
                description="Represents one or more question",
                emoji=discord.PartialEmoji(name="\U00002753"),
            ),
            discord.SelectOption(
                label="Serious",
                value="serious",
                description="Represents a serious concern or question(s)",
                emoji=discord.PartialEmoji(name="\U0001f610"),
            ),
            discord.SelectOption(
                label="Private",
                value="private",
                description="Represents a private concern or matter",
                emoji=discord.PartialEmoji(name="\U0001f512"),
            ),
        ]
        super().__init__(
            placeholder="Select a tag...",
            min_values=1,
            max_values=3,
            options=options,
            row=0,
        )
        self.tickets_cog = tickets_cog
        self.prev_selected: Optional[set] = None

    def tick(self, status) -> str:
        if status is True:
            return "\U00002705"
        return "\U0000274c"

    async def callback(self, interaction: discord.Interaction[Rodhaj]) -> None:
        values = self.values
        in_progress_tag = self.tickets_cog.reserved_tags.get(interaction.user.id)
        if in_progress_tag is None:
            await interaction.response.send_message(
                "Are there really any tags cached?", ephemeral=True
            )
            return

        output_tag = ReservedTags(question=False, serious=False, private=False)

        if interaction.user.id in self.tickets_cog.reserved_tags:
            output_tag = in_progress_tag

        current_selected = set(self.values)

        if self.prev_selected is not None:
            missing = self.prev_selected - current_selected
            added = current_selected - self.prev_selected

            combined = missing.union(added)

            for tag in combined:
                output_tag[tag] = not in_progress_tag[tag]
        else:
            for tag in values:
                output_tag[tag] = not in_progress_tag[tag]

        self.tickets_cog.reserved_tags[interaction.user.id] = output_tag
        self.tickets_cog.in_progress_tickets[interaction.user.id].tags.set()
        self.prev_selected = set(self.values)
        formatted_str = "\n".join(
            f"{self.tick(v)} - {k.title()}" for k, v in output_tag.items()
        )
        result = f"The following have been modified:\n\n{formatted_str}"

        embed = Embed(title="Modified Tags")
        embed.description = result
        embed.set_footer(text="\U00002705 = Selected | \U0000274c = Unselected")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class TicketConfirmView(RoboView):
    def __init__(
        self,
        attachments: list[discord.Attachment],
        bot: Rodhaj,
        ctx: RoboContext,
        cog: Tickets,
        config_cog: Config,
        content: str,
        guild: discord.Guild,
        delete_after: bool = True,
    ) -> None:
        super().__init__(ctx=ctx, timeout=300.0)
        self.attachments = attachments
        self.bot = bot
        self.ctx = ctx
        self.cog = cog
        self.config_cog = config_cog
        self.content = content
        self.guild = guild
        self.delete_after = delete_after
        self.triggered = asyncio.Event()
        self.pool = self.bot.pool
        self._modal = None
        self.add_item(TicketTagsSelect(cog))

    def tick(self, status) -> str:
        if status is True:
            return "\U00002705"
        return "\U0000274c"

    async def delete_response(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_response()

        self.stop()

    async def get_or_fetch_member(self, member_id: int) -> Optional[discord.Member]:
        member = self.guild.get_member(member_id)
        if member is not None:
            return member

        members = await self.guild.query_members(
            limit=1, user_ids=[member_id], cache=True
        )
        if not members:
            return None
        return members[0]

    @discord.ui.button(
        label="Checklist",
        style=discord.ButtonStyle.primary,
        emoji=discord.PartialEmoji(name="\U00002753"),
        row=1,
    )
    async def see_checklist(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        status = self.cog.in_progress_tickets.get(interaction.user.id)

        if status is None:
            await interaction.response.send_message(
                "Unable to view checklist", ephemeral=True
            )
            return

        dict_status = {"title": status.title, "tags": status.tags}
        formatted_status = "\n".join(
            f"{self.tick(v.is_set())} - {k.title()}" for k, v in dict_status.items()
        )

        embed = Embed()
        embed.title = "\U00002753 Status Checklist"
        embed.description = f"The current status is shown below:\n\n{formatted_status}"
        embed.set_footer(text="\U00002705 = Completed | \U0000274c = Incomplete")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Set Title",
        style=discord.ButtonStyle.primary,
        emoji=discord.PartialEmoji(name="\U0001f58b"),
        row=1,
    )
    async def set_title(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self._modal = TicketTitleModal(self.ctx, self.cog)
        await interaction.response.send_modal(self._modal)

    @discord.ui.button(
        label="Confirm",
        style=discord.ButtonStyle.green,
        emoji="<:greenTick:596576670815879169>",
        row=1,
    )
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await register_user(self.ctx.author.id, self.pool)
        author = self.ctx.author

        thread_display_id = uuid.uuid4()
        thread_name = f"{author.display_name} | {thread_display_id}"
        title = self._modal.input if self._modal and self._modal.input else thread_name

        tags = self.cog.reserved_tags.get(interaction.user.id)
        status = self.cog.in_progress_tickets.get(interaction.user.id)
        if tags is None or status is None:
            await interaction.response.send_message(
                "Unable to obtain reserved tags and in progress tags",
                ephemeral=True,
            )
            return

        applied_tags = [k for k, v in tags.items() if v is True]

        guild_settings = await self.config_cog.get_guild_settings(self.guild.id)
        potential_member = await self.get_or_fetch_member(author.id)

        if not guild_settings:
            await interaction.response.send_message(
                "Unable to find guild settings", ephemeral=True
            )
            return

        if (self.guild.created_at - interaction.created_at) < guild_settings.guild_age:
            await interaction.response.send_message(
                "The guild is too young in order to utilize Rodhaj.",
                ephemeral=True,
            )
            return
        elif potential_member:  # Since we are checking join times, if we don't have the proper member, we can only skip it.
            joined_at = potential_member.joined_at or discord.utils.utcnow()
            if (joined_at - interaction.created_at) < guild_settings.account_age:
                await interaction.response.send_message(
                    "This account joined the server too soon in order to utilize Rodhaj.",
                    ephemeral=True,
                )
            return

        if not status.title.is_set() or not status.tags.is_set():
            dict_status = {"title": status.title, "tags": status.tags}
            formatted_status = "\n".join(
                f"{self.tick(v.is_set())} - {k.title()}" for k, v in dict_status.items()
            )

            embed = ErrorEmbed()
            embed.title = "\U00002757 Unfinished Ticket"
            embed.description = (
                "Hold up! It seems like you have an unfinished ticket! "
                "It's important to have a finished ticket "
                "as it allows staff to work more efficiently. "
                "Please refer to the checklist given below for which parts "
                "that are incomplete.\n\n"
                f"{formatted_status}"
                "\n\nNote: In order to know, refer to the status checklist. "
                'This can be found by clicking the "See Checklist" button. '
            )
            embed.set_footer(text="\U00002705 = Complete | \U0000274c = Incomplete")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        files = [await attachment.to_file() for attachment in self.attachments]
        ticket = TicketThread(
            title=title,
            user=author,
            location_id=self.guild.id,
            mention=guild_settings.mention,
            content=self.content,
            tags=applied_tags,
            files=files,
            created_at=discord.utils.utcnow(),
        )
        created_ticket = await self.cog.create_ticket(ticket)

        if created_ticket is None:
            await interaction.response.send_message(
                "Rodhaj is not set up yet. Please contact the admin or staff",
                ephemeral=True,
            )
            return

        self.bot.dispatch(
            "ticket_create",
            self.guild,
            self.ctx.author,
            created_ticket.ticket,
            safe_content(self.content),
        )

        self.cog.reserved_tags.pop(self.ctx.author.id, None)
        self.cog.in_progress_tickets.pop(self.ctx.author.id, None)

        if self.message:
            self.triggered.set()

            embed = discord.Embed(
                title="\U0001f3ab Ticket created",
                color=discord.Color.from_rgb(124, 252, 0),
            )
            embed.description = "The ticket has been successfully created. Please continue to DM Rodhaj in order to send the message to the ticket, where an assigned staff will help you."
            await self.message.edit(embed=embed, view=None, delete_after=15.0)

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.red,
        emoji="<:redTick:596576672149667840>",
        row=1,
    )
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()

    async def on_timeout(self) -> None:
        # This is the only way you can really edit the original message
        # There is a bug here, where the message first gets edited and the timeout gets called
        # thus editing an unknown message
        # ---
        # In order to fix the issue with the invalid message,
        # an event called triggered is used. This asyncio.Event
        # is used in order to determine whether the event was triggered
        # and if it is not, that means that it truly is an actual timeout that caused it
        # not the user confirming and then the timeout being called later
        if self.message and self.triggered.is_set() is False:
            embed = ErrorEmbed()
            embed.title = "\U00002757 Timed Out"
            embed.description = (
                "Timed out waiting for a response. Not creating a ticket. "
                "In order to create a ticket, please resend your message and properly confirm"
            )
            await self.message.edit(embed=embed, view=None, delete_after=15.0)
            return


### Actual cog


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
        # More than likely it will be closed through the threads
        # That means, it must be done in a guild. Thus, we know that
        # it will always be discord.Member
        perms = ctx.channel.permissions_for(ctx.author)  # type: ignore
        from_ticket_channel = (
            isinstance(ctx.channel, discord.Thread)
            and ctx.partial_config is not None
            and ctx.channel.parent_id == ctx.partial_config.ticket_channel_id
        )

        if perms.manage_threads and from_ticket_channel is True:
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

    async def soft_lock_ticket(
        self, thread: discord.Thread, reason: Optional[str] = None
    ) -> discord.Thread:
        self.bot.metrics.features.locked_tickets.inc()
        tags = thread.applied_tags
        locked_tag = self.get_locked_tag(thread.parent)

        if locked_tag is not None and not any(tag.id == locked_tag.id for tag in tags):
            tags.insert(0, locked_tag)

        return await thread.edit(applied_tags=tags, locked=True, reason=reason)

    async def soft_unlock_ticket(
        self, thread: discord.Thread, reason: Optional[str] = None
    ) -> discord.Thread:
        self.bot.metrics.features.locked_tickets.dec()
        tags = thread.applied_tags
        locked_tag = self.get_locked_tag(thread.parent)

        if locked_tag is not None and any(tag.id == locked_tag.id for tag in tags):
            tags.remove(locked_tag)

        return await thread.edit(applied_tags=tags, locked=False, reason=reason)

    async def close_ticket(
        self,
        user: Union[discord.User, discord.Member, int],
        connection: Union[asyncpg.Pool, asyncpg.Connection],
        author: Optional[Union[discord.User, discord.Member]] = None,
    ) -> Optional[discord.Thread]:
        self.bot.metrics.features.closed_tickets.inc()
        self.bot.metrics.features.active_tickets.dec()
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

        content = f"({ticket.mention} - {ticket.user.display_name}, {discord.utils.format_dt(ticket.created_at)})\n\n{ticket.content}"
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
                    status=False,
                    ticket=created_ticket,
                    msg="Could not create ticket",
                )
            else:
                self.bot.metrics.features.active_tickets.inc()
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
        self,
        channel: Optional[Union[discord.ForumChannel, discord.TextChannel]],
    ):
        if not isinstance(channel, discord.ForumChannel):
            return None

        all_tags = channel.available_tags

        solved_tag = discord.utils.get(all_tags, name="Resolved")
        if solved_tag is None:
            return None
        return solved_tag

    def get_locked_tag(
        self,
        channel: Optional[Union[discord.ForumChannel, discord.TextChannel]],
    ):
        if not isinstance(channel, discord.ForumChannel):
            return None

        all_tags = channel.available_tags

        locked_tag = discord.utils.get(all_tags, name="Locked")
        if locked_tag is None:
            return None
        return locked_tag

    ### Feature commands

    # This command requires the manage_threads permissions for the bot
    @is_ticket_or_dm()
    @bot_check_permissions(manage_threads=True)
    @commands.cooldown(1, 20, commands.BucketType.channel)
    @commands.hybrid_command(name="close", aliases=["solved", "closed", "resolved"])
    async def close(self, ctx: RoboContext) -> None:
        """Closes a ticket

        If someone requests to close the ticket
        and has Manage Threads permissions, then they can
        also close the ticket.
        """
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
        self,
        ctx: GuildContext,
        *,
        message: Annotated[str, commands.clean_content],
    ) -> None:
        """Replies back to the owner of the active ticket with a message"""
        ticket_owner = await self.get_ticket_owner_id(ctx.channel.id)

        if ticket_owner is None:
            await ctx.send("No owner could be found for the current ticket")
            return
        partial_ticket_owner = await get_partial_ticket(self.bot, ticket_owner.id)

        dispatcher = GuildWebhookDispatcher(self.bot, ctx.guild.id)
        tw = await dispatcher.get_ticket_webhook()
        if tw is None:
            await ctx.send("Could not find webhook")
            return

        # We might want to have these as a chain of embeds but eh
        embed = ReplyEmbed(author=ctx.author)
        embed.description = safe_content(message)

        if isinstance(ctx.channel, discord.Thread):
            if (
                partial_ticket_owner.id
                and partial_ticket_owner.locked
                and ctx.channel.locked
            ):
                await ctx.send("This ticket is locked. You cannot reply in this ticket")
                return

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
            name="Associated Guild",
            value=ticket.source_guild.name,
            inline=False,
        )
        embed.add_field(
            name="Created At",
            value=format_dt(ticket.thread.created_at),  # type: ignore
            inline=False,
        )
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

    @reply.error
    async def on_reply_error(
        self, ctx: GuildContext, error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            embed = CooldownEmbed(error.retry_after)
            await ctx.send(embed=embed)


async def setup(bot: Rodhaj) -> None:
    await bot.add_cog(Tickets(bot))
