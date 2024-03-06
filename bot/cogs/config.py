from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Annotated, Any, Optional, Union, overload

import asyncpg
import discord
import msgspec
from async_lru import alru_cache
from discord import app_commands
from discord.ext import commands
from discord.utils import format_dt, utcnow
from libs.utils import GuildContext
from libs.utils.checks import bot_check_permissions, check_permissions
from libs.utils.embeds import Embed
from libs.utils.errors import create_premade_embed
from libs.utils.pages import SimplePages
from libs.utils.prefix import get_prefix
from libs.utils.time import FriendlyTimeResult, UserFriendlyTime

if TYPE_CHECKING:
    from rodhaj import Rodhaj

UNKNOWN_ERROR_MESSAGE = (
    "An unknown error happened. Please contact the dev team for assistance"
)


class BlocklistEntity(msgspec.Struct, frozen=True):
    bot: Rodhaj
    guild_id: int
    entity_id: int
    expires: datetime.datetime
    created: datetime.datetime = utcnow()
    event: str = "on_blocklist_timer"

    def format(self) -> str:
        user = self.bot.get_user(self.entity_id)
        name = user.global_name if user else "Unknown"
        return f"{name} (ID: {self.entity_id} | Expires: {format_dt(self.expires)})"


class BlocklistPages(SimplePages):
    def __init__(self, entries: list[BlocklistEntity], *, ctx: GuildContext):
        converted = [entry.format() for entry in entries]
        super().__init__(converted, ctx=ctx)


class Blocklist:
    def __init__(self, bot: Rodhaj):
        self.bot = bot
        self._blocklist: dict[int, BlocklistEntity] = {}

    async def _load(self):
        query = """
        SELECT guild_id, entity_id, expires, created
        FROM blocklist;
        """
        rows = await self.bot.pool.fetch(query)
        return {
            row["entity_id"]: BlocklistEntity(bot=self.bot, **dict(row)) for row in rows
        }

    async def load(self):
        try:
            self._blocklist = await self._load()
        except Exception:
            self._blocklist = {}

    @overload
    def get(self, key: int) -> Optional[BlocklistEntity]: ...

    @overload
    def get(self, key: int) -> BlocklistEntity: ...

    def get(self, key: int, default: Any = None) -> Optional[BlocklistEntity]:
        return self._blocklist.get(key, default)

    def pop(self, key: int) -> BlocklistEntity:
        return self._blocklist.pop(key)

    def put(self, key: int, value: BlocklistEntity) -> None:
        self._blocklist[key] = value

    def __contains__(self, item: int) -> bool:
        return item in self._blocklist

    def __getitem__(self, item: int) -> BlocklistEntity:
        return self._blocklist[item]

    def __len__(self) -> int:
        return len(self._blocklist)

    def all(self) -> dict[int, BlocklistEntity]:
        return self._blocklist


# Msgspec Structs are usually extremely fast compared to slotted classes
class GuildConfig(msgspec.Struct):
    bot: Rodhaj
    id: int
    category_id: int
    ticket_channel_id: int
    logging_channel_id: int
    logging_broadcast_url: str
    ticket_broadcast_url: str

    @property
    def category_channel(self) -> Optional[discord.CategoryChannel]:
        guild = self.bot.get_guild(self.id)
        return guild and guild.get_channel(self.category_id)  # type: ignore

    @property
    def logging_channel(self) -> Optional[discord.TextChannel]:
        guild = self.bot.get_guild(self.id)
        return guild and guild.get_channel(self.logging_channel_id)  # type: ignore

    @property
    def ticket_channel(self) -> Optional[discord.ForumChannel]:
        guild = self.bot.get_guild(self.id)
        return guild and guild.get_channel(self.ticket_channel_id)  # type: ignore


class GuildWebhookDispatcher:
    def __init__(self, bot: Rodhaj, guild_id: int):
        self.bot = bot
        self.guild_id = guild_id
        self.session = self.bot.session
        self.pool = self.bot.pool

    async def get_webhook(self) -> Optional[discord.Webhook]:
        conf = await self.get_config()
        if conf is None:
            return None
        return discord.Webhook.from_url(
            url=conf.logging_broadcast_url, session=self.session
        )

    async def get_ticket_webhook(self) -> Optional[discord.Webhook]:
        conf = await self.get_config()
        if conf is None:
            return None
        return discord.Webhook.from_url(
            url=conf.ticket_broadcast_url, session=self.session
        )

    @alru_cache()
    async def get_config(self) -> Optional[GuildConfig]:
        query = """
        SELECT id, category_id, ticket_channel_id, logging_channel_id, logging_broadcast_url, ticket_broadcast_url
        FROM guild_config
        WHERE id = $1;
        """
        rows = await self.pool.fetchrow(query, self.guild_id)
        if rows is None:
            return None

        config = GuildConfig(bot=self.bot, **dict(rows))
        return config


class SetupFlags(commands.FlagConverter):
    ticket_name: Optional[str] = commands.flag(
        name="ticket_name",
        default="tickets",
        description="The name of the ticket forum. Defaults to tickets",
    )
    log_name: Optional[str] = commands.flag(
        name="log_name",
        default="rodhaj-logs",
        description="The name of the logging channel. Defaults to rodhaj-logs",
    )


class PrefixConverter(commands.Converter):
    async def convert(self, ctx: GuildContext, argument: str):
        user_id = ctx.bot.user.id  # type: ignore # Already logged in by this time
        if argument.startswith((f"<@{user_id}>", f"<@!{user_id}>")):
            raise commands.BadArgument("That is a reserved prefix already in use.")
        if len(argument) > 100:
            raise commands.BadArgument("That prefix is too long.")
        return argument


class EntityConverter(commands.MemberConverter):
    async def convert(self, ctx: GuildContext, argument: str) -> discord.Member:
        member = await super().convert(ctx, argument)
        # TODO: Implement hierarchy checks here
        if member.id == ctx.author.id:
            raise commands.BadArgument("You can't block yourself")
        if ctx.bot.user and member.id == ctx.bot.user.id:
            raise commands.BadArgument("You can't block the bot")

        return member


class Config(commands.Cog):
    """Config and setup commands for Rodhaj"""

    def __init__(self, bot: Rodhaj) -> None:
        self.bot = bot
        self.pool = self.bot.pool

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\U0001f6e0")

    @alru_cache()
    async def get_guild_config(self, guild_id: int) -> Optional[GuildConfig]:
        # Normally using the star is bad practice but...
        # Since I don't want to write out every single column to select,
        # we are going to use the star
        # The guild config roughly maps to it as well
        query = "SELECT * FROM guild_config WHERE id = $1;"
        rows = await self.pool.fetchrow(query, guild_id)
        if rows is None:
            return None
        config = GuildConfig(bot=self.bot, **dict(rows))
        return config

    def clean_prefixes(self, prefixes: Union[str, list[str]]) -> str:
        if isinstance(prefixes, str):
            return f"`{prefixes}`"

        return ", ".join(f"`{prefix}`" for prefix in prefixes[2:])

    ### Blocklist Utilities

    async def add_to_blocklist(
        self, guild_id: int, id: int, expires: datetime.datetime
    ) -> None:
        query = """
        INSERT INTO blocklist (guild_id, entity_id, expires, event)
        VALUES ($1, $2, $3, $4);
        """
        # Strip out timezone as the db doesn't need it
        expires = expires.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        await self.bot.pool.execute(query, guild_id, id, expires, "on_blocklist_timer")
        await self.bot.blocklist.load()

    async def remove_from_blocklist(self, guild_id: int, id: int) -> None:
        query = """
        DELETE FROM blocklist
        WHERE guild_id = $1 AND entity_id = $2;
        """
        await self.bot.pool.execute(query, guild_id, id)
        await self.bot.blocklist.load()

    async def blocklist_error(
        self, ctx: GuildContext, error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.BadArgument):
            await ctx.send(
                embed=create_premade_embed(
                    "Invalid Argument",
                    str(error),
                )
            )

    @check_permissions(manage_guild=True)
    @bot_check_permissions(manage_channels=True, manage_webhooks=True)
    @commands.guild_only()
    @commands.hybrid_group(name="config")
    async def config(self, ctx: GuildContext) -> None:
        """Commands to configure, setup, or delete Rodhaj"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @commands.cooldown(1, 20, commands.BucketType.guild)
    @config.command(name="setup", usage="ticket_name: <str> log_name: <str>")
    async def setup(self, ctx: GuildContext, *, flags: SetupFlags) -> None:
        """First-time setup for Rodhaj

        You only need to run this once
        """
        await ctx.defer()
        guild_id = ctx.guild.id

        dispatcher = GuildWebhookDispatcher(self.bot, guild_id)
        config = await dispatcher.get_config()

        if (
            config is not None
            and config.logging_channel is not None
            and config.ticket_channel is not None
        ):
            msg = (
                "It seems like there the channels are set up already\n"
                "If you want to delete it, please run"
            )
            await ctx.send(msg)
            return

        perms = ctx.channel.permissions_for(ctx.guild.me)

        if not perms.manage_webhooks or not perms.manage_channels:
            await ctx.send(
                "\N{NO ENTRY SIGN} I do not have proper permissions (Manage Webhooks and Manage Channel)"
            )
            return

        # LGC stands for Logging Channel
        avatar_bytes = await self.bot.user.display_avatar.read()  # type: ignore # The bot should be logged in order to run this command
        rodhaj_overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(
                read_messages=False,
                send_messages=False,
                create_public_threads=False,
            ),
            ctx.guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_webhooks=True,
                create_public_threads=True,
                manage_threads=True,
            ),
        }
        lgc_reason = (
            f"{ctx.author} (ID: {ctx.author.id}) has created the Rodhaj logs channel"
        )

        # The rationale behind the restriction of posts is to make sure that
        # people don't create posts of their own, thus messing up the code for the bot
        # These perms can be changed later....
        forums_reason = f"{ctx.author} (ID: {ctx.author.id}) has created the Rodhaj ticket forum channel"

        # Using a docstring created some weird discord formatting
        forum_description_content = (
            "This forum is the main forum where tickets get created and resolved.",
            "Unlike ModMail, which uses channels to achieve this, Rodhaj employs a more modern approach to ticket threads.",
            "This channel doesn't allow new posts from users, as the posts (or tickets) are created by Rodhaj directly.",
            "**Please do not edit, delete, or make your own post, and if you wish to, please use the appropriate command to do so.**",
        )
        forum_description = "\n".join(forum_description_content)
        forum_tags = [
            discord.ForumTag(
                name="Question",
                emoji=discord.PartialEmoji(
                    name="\U00002753"
                ),  # U+2753 Black Question Mark Ornament
            ),
            discord.ForumTag(
                name="Serious",
                emoji=discord.PartialEmoji(name="\U0001f610"),  # U+1F610 Neutral Face
            ),
            discord.ForumTag(
                name="Private",
                emoji=discord.PartialEmoji(name="\U0001f512"),  # U+1F512 Lock
            ),
            discord.ForumTag(
                name="Resolved",
                emoji=discord.PartialEmoji(
                    name="\U00002705"
                ),  # U+2705 White Heavy Check Mark
                moderated=True,
            ),
        ]

        delete_reason = "Failed to create channel due to existing config"

        try:
            # This is like ratelimiting hell
            rodhaj_category = await ctx.guild.create_category(
                name="rodhaj", overwrites=rodhaj_overwrites, position=0
            )
            logging_channel = await rodhaj_category.create_text_channel(
                name=flags.log_name or "rodhaj-logs", reason=lgc_reason, position=0
            )
            lgc_webhook = await logging_channel.create_webhook(
                name="Rodhaj Ticket Logs", avatar=avatar_bytes
            )
            ticket_channel = await rodhaj_category.create_forum(
                name=flags.ticket_name or "tickets",
                topic=forum_description,
                position=1,
                reason=forums_reason,
                default_auto_archive_duration=4320,
                default_sort_order=discord.ForumOrderType.latest_activity,
                default_layout=discord.ForumLayoutType.list_view,
                available_tags=forum_tags,
            )
            tc_webhook = await ticket_channel.create_webhook(
                name="Rodhaj User Proxy Webhook", avatar=avatar_bytes
            )
        except discord.Forbidden:
            await ctx.send(
                "\N{NO ENTRY SIGN} Rodhaj is missing permissions: Manage Channels and Manage Webhooks"
            )
            return
        except discord.HTTPException:
            await ctx.send(UNKNOWN_ERROR_MESSAGE)
            return

        query = """
        INSERT INTO guild_config (id, category_id, ticket_channel_id, logging_channel_id, logging_broadcast_url, ticket_broadcast_url, prefix)
        VALUES ($1, $2, $3, $4, $5, $6, $7);
        """
        try:
            await self.pool.execute(
                query,
                guild_id,
                rodhaj_category.id,
                ticket_channel.id,
                logging_channel.id,
                lgc_webhook.url,
                tc_webhook.url,
                [],
            )
        except asyncpg.UniqueViolationError:
            await ticket_channel.delete(reason=delete_reason)
            await logging_channel.delete(reason=delete_reason)
            await rodhaj_category.delete(reason=delete_reason)
            await ctx.send(
                "Failed to create the channels. Please contact Noelle to figure out why (it's more than likely that the channels exist and bypassed checking the lru cache for some reason)"
            )
        else:
            # Invalidate LRU cache just to clear it out
            dispatcher.get_config.cache_invalidate()
            msg = f"Rodhaj channels successfully created! The ticket channel can be found under {ticket_channel.mention}"
            await ctx.send(msg)

    @commands.cooldown(1, 20, commands.BucketType.guild)
    @config.command(name="delete")
    async def delete(self, ctx: GuildContext) -> None:
        """Permanently deletes Rodhaj channels and tickets."""
        await ctx.defer()
        guild_id = ctx.guild.id

        dispatcher = GuildWebhookDispatcher(self.bot, guild_id)
        guild_config = await self.get_guild_config(guild_id)

        msg = "Are you really sure that you want to delete the Rodhaj channels?"
        confirm = await ctx.prompt(msg, timeout=300.0, delete_after=True)
        if confirm:
            if guild_config is None:
                msg = (
                    "Could not find the guild config. Perhaps Rodhaj is not set up yet?"
                )
                await ctx.send(msg)
                return

            reason = f"Requested by {ctx.author.name} (ID: {ctx.author.id}) to purge Rodhaj channels"

            if (
                guild_config.logging_channel is not None
                and guild_config.ticket_channel is not None
                and guild_config.category_channel is not None
            ):
                try:
                    await guild_config.logging_channel.delete(reason=reason)
                    await guild_config.ticket_channel.delete(reason=reason)
                    await guild_config.category_channel.delete(reason=reason)
                except discord.Forbidden:
                    await ctx.send(
                        "\N{NO ENTRY SIGN} Rodhaj is missing permissions: Manage Channels"
                    )
                    return
                except discord.HTTPException:
                    await ctx.send(UNKNOWN_ERROR_MESSAGE)
                    return

            query = """
            DELETE FROM guild_config WHERE id = $1;
            """
            await self.pool.execute(query, guild_id)
            dispatcher.get_config.cache_invalidate()
            self.get_guild_config.cache_invalidate(guild_id)
            await ctx.send("Successfully deleted channels")
        elif confirm is None:
            await ctx.send("Not removing Rodhaj channels. Canceling.")
        else:
            await ctx.send("Cancelling.")

    @check_permissions(manage_guild=True)
    @commands.guild_only()
    @config.group(name="prefix", fallback="info")
    async def prefix(self, ctx: GuildContext) -> None:
        """Shows and manages custom prefixes for the guild

        Passing in no subcommands will effectively show the currently set prefixes.
        """
        prefixes = await get_prefix(self.bot, ctx.message)
        embed = Embed()
        embed.add_field(
            name="Prefixes", value=self.clean_prefixes(prefixes), inline=False
        )
        embed.add_field(name="Total", value=len(prefixes) - 2, inline=False)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url)  # type: ignore
        await ctx.send(embed=embed)

    @prefix.command(name="add")
    @app_commands.describe(prefix="The new prefix to add")
    async def prefix_add(
        self, ctx: GuildContext, prefix: Annotated[str, PrefixConverter]
    ) -> None:
        """Adds an custom prefix"""
        prefixes = await get_prefix(self.bot, ctx.message)

        # 2 are the mention prefixes, which are always prepended on the list of prefixes
        if isinstance(prefixes, list) and len(prefixes) > 12:
            await ctx.send(
                "You can not have more than 10 custom prefixes for your server"
            )
            return
        elif prefix in prefixes:
            await ctx.send("The prefix you want to set already exists")
            return

        query = """
            UPDATE guild_config
            SET prefix = ARRAY_APPEND(prefix, $1)
            WHERE id = $2;
        """
        await self.pool.execute(query, prefix, ctx.guild.id)
        get_prefix.cache_invalidate(self.bot, ctx.message)
        await ctx.send(f"Added prefix: `{prefix}`")

    @prefix.command(name="edit")
    @app_commands.describe(
        old="The prefix to edit", new="A new prefix to replace the old"
    )
    @app_commands.rename(old="old_prefix", new="new_prefix")
    async def prefix_edit(
        self,
        ctx: GuildContext,
        old: Annotated[str, PrefixConverter],
        new: Annotated[str, PrefixConverter],
    ) -> None:
        """Edits and replaces a prefix"""
        query = """
            UPDATE guild_config
            SET prefix = ARRAY_REPLACE(prefix, $1, $2)
            WHERE id = $3;
        """
        prefixes = await get_prefix(self.bot, ctx.message)

        guild_id = ctx.guild.id
        if old in prefixes:
            await self.pool.execute(query, old, new, guild_id)
            get_prefix.cache_invalidate(self.bot, ctx.message)
            await ctx.send(f"Prefix updated to from `{old}` to `{new}`")
        else:
            await ctx.send("The prefix is not in the list of prefixes for your server")

    @prefix.command(name="delete")
    @app_commands.describe(prefix="The prefix to delete")
    async def prefix_delete(
        self, ctx: GuildContext, prefix: Annotated[str, PrefixConverter]
    ) -> None:
        """Deletes a set prefix"""
        query = """
        UPDATE guild_config
        SET prefix = ARRAY_REMOVE(prefix, $1)
        WHERE id=$2;
        """
        msg = f"Do you want to delete the following prefix: {prefix}"
        confirm = await ctx.prompt(msg, timeout=120.0, delete_after=True)
        if confirm:
            await self.pool.execute(query, prefix, ctx.guild.id)
            get_prefix.cache_invalidate(self.bot, ctx.message)
            await ctx.send(f"The prefix `{prefix}` has been successfully deleted")
        elif confirm is None:
            await ctx.send("Confirmation timed out. Cancelled deletion...")
        else:
            await ctx.send("Confirmation cancelled. Please try again")

    # In order to prevent abuse, 4 checks must be performed:
    # 1. Permissions check
    # 2. Is the selected entity higher than the author's current hierarchy? (in terms of role and members)
    # 3. Is the bot itself the entity getting blocklisted?
    # 4. Is the author themselves trying to get blocklisted?
    # This system must be addressed with care as it is extremely dangerous
    @check_permissions(manage_messages=True, manage_roles=True, moderate_members=True)
    @commands.guild_only()
    @config.group(name="blocklist", fallback="info")
    async def blocklist(self, ctx: GuildContext) -> None:
        """Manages and views the current blocklist"""
        blocklist = self.bot.blocklist.all()
        pages = BlocklistPages([entry for entry in blocklist.values()], ctx=ctx)
        await pages.start()

    @blocklist.command(name="add")
    @app_commands.describe(
        entity="The user or role to add to the blocklist",
        until="The date or time that the user or role is removed from the blocklist",
    )
    async def blocklist_add(
        self,
        ctx: GuildContext,
        entity: Annotated[discord.Member, EntityConverter],
        *,
        until: Annotated[
            FriendlyTimeResult, UserFriendlyTime(commands.clean_content, default="…")
        ],
    ) -> None:
        """Adds an user or role into the blocklist"""
        # TODO: Remove any active tickets
        await self.add_to_blocklist(ctx.guild.id, entity.id, until.dt)
        await ctx.send(f"{entity.mention} has been blocked until {format_dt(until.dt)}")

    @blocklist.command(name="remove")
    @app_commands.describe(entity="The user or role to remove from the blocklist")
    async def blocklist_remove(
        self, ctx: GuildContext, entity: Annotated[discord.Member, EntityConverter]
    ) -> None:
        """Removes an user or role from the blocklist"""
        # TODO: Check if the command executed at < expiration date
        await self.remove_from_blocklist(ctx.guild.id, entity.id)
        await ctx.send(f"{entity.mention} has been unblocked")

    @blocklist_add.error
    async def on_blocklist_add_error(
        self, ctx: GuildContext, error: commands.CommandError
    ) -> None:
        await self.blocklist_error(ctx, error)

    @blocklist_remove.error
    async def on_blocklist_remove_error(
        self, ctx: GuildContext, error: commands.CommandError
    ) -> None:
        await self.blocklist_error(ctx, error)


async def setup(bot: Rodhaj) -> None:
    await bot.add_cog(Config(bot))
