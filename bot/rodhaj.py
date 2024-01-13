from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

import asyncpg
import discord
from aiohttp import ClientSession
from cogs import EXTENSIONS, VERSION
from cogs.config import GuildWebhookDispatcher
from discord.ext import commands
from libs.tickets.structs import PartialConfig, ReservedTags, StatusChecklist
from libs.tickets.utils import get_cached_thread, get_partial_ticket
from libs.tickets.views import TicketConfirmView
from libs.utils import (
    RoboContext,
    RodhajCommandTree,
    RodhajHelp,
    send_error_embed,
)
from libs.utils.config import RodhajConfig

if TYPE_CHECKING:
    from cogs.tickets import Tickets

_fsw = True
try:
    from watchfiles import awatch
except ImportError:
    _fsw = False


class Rodhaj(commands.Bot):
    """Main bot for Rodhaj"""

    def __init__(
        self,
        config: RodhajConfig,
        intents: discord.Intents,
        session: ClientSession,
        pool: asyncpg.Pool,
        *args,
        **kwargs,
    ):
        super().__init__(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="a game"
            ),
            command_prefix=["r>", "?", "!"],
            help_command=RodhajHelp(),
            intents=intents,
            tree_cls=RodhajCommandTree,
            *args,
            **kwargs,
        )
        self.logger = logging.getLogger("rodhaj")
        self.session = session
        self.partial_config: Optional[PartialConfig] = None
        self.pool = pool
        self.transprogrammer_guild_id = config.get("guild_id", 1183302385020436480)
        self.version = str(VERSION)
        self._dev_mode = config.get("dev_mode", False)

    ### Ticket related utils
    async def fetch_partial_config(self) -> Optional[PartialConfig]:
        query = """
        SELECT id, ticket_channel_id, logging_channel_id
        FROM guild_config
        WHERE id = $1;
        """
        rows = await self.pool.fetchrow(query, self.transprogrammer_guild_id)
        if rows is None:
            return None
        return PartialConfig(rows)

    ### Bot-related overrides

    async def get_context(
        self, origin: Union[discord.Interaction, discord.Message], /, *, cls=RoboContext
    ) -> RoboContext:
        return await super().get_context(origin, cls=cls)

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        await send_error_embed(ctx, error)

    ### Ticket processing and handling

    async def process_commands(
        self, message: discord.Message, /, ctx: RoboContext
    ) -> None:
        # Probably will not get fired but just in case
        if message.author.bot:
            return

        whitelist_commands = [
            "close",
            "solved",
            "resolved",
            "is_active",
            "is-active",
            "ticket-info",
            "tinfo",
        ]
        if (
            message.guild is None
            and ctx.command is not None
            and ctx.invoked_with in whitelist_commands
        ):
            await self.invoke(ctx)
            return

        await self.invoke(ctx)

    async def on_message(self, message: discord.Message) -> None:
        # Ignore all messages from the bot
        if message.author.bot:
            return

        # Since we are already using an RoboContext to deal with process commands,
        # and it's used in both instances of an DM or an guild command,
        # It's more efficient to go ahead and fetch it first since we need it later anyways
        ctx = await self.get_context(message)

        # Handle all DMs from here
        if message.guild is None:
            # We only will process the "close" command
            if ctx.command is not None:
                await self.process_commands(message, ctx)
                return

            author = message.author
            potential_ticket = await get_partial_ticket(self, author.id, self.pool)

            # Represents that there is no active ticket
            if potential_ticket.id is None:
                # We might want to validate the content type here...
                if len(message.attachments) > 10:
                    over_msg = (
                        "There are more than 10 attachments linked. "
                        "Please remove some and try again"
                    )
                    await author.send(over_msg)
                    return

                tickets_cog: Tickets = self.get_cog("Tickets")  # type: ignore
                default_tags = ReservedTags(
                    question=False, serious=False, private=False
                )
                status_checklist = StatusChecklist()
                tickets_cog.add_in_progress_tag(author.id, default_tags)
                tickets_cog.add_status_checklist(author.id, status_checklist)
                guild = self.get_guild(self.transprogrammer_guild_id) or (
                    await self.fetch_guild(self.transprogrammer_guild_id)
                )

                embed = discord.Embed(
                    title="Ready to create a ticket?",
                    color=discord.Color.from_rgb(124, 252, 0),
                )
                embed.description = (
                    "Are you ready to create a ticket? "
                    "Before you click the `Confirm` button, please select the tags found in the dropdown menu. "
                    "Doing this step is crucial as these tags are used in order to help better sort tickets for the staff team. "
                    "In addition, please set the title of your ticket using the `Set Title` button. "
                    "This will also help identify your ticket and streamline the process."
                    "\n\nNote: Once you have created your ticket, this prompt will not show up again"
                )

                view = TicketConfirmView(
                    message.attachments, self, ctx, tickets_cog, message.content, guild
                )
                view.message = await author.send(embed=embed, view=view)
                return

            # The thread is cached within an LRU cache to heavily speedup performance
            cached_thread = await get_cached_thread(self, author.id, self.pool)

            if cached_thread is not None:
                dispatcher = GuildWebhookDispatcher(self, cached_thread.source_guild.id)
                webhook = await dispatcher.get_ticket_webhook()
                if webhook is not None:
                    await webhook.send(
                        message.content,
                        username=f"[RESPONSE] {author.display_name}",
                        avatar_url=author.display_avatar.url,
                        thread=cached_thread.thread,
                    )

            return
        await self.process_commands(message, ctx)

    ### Dev related utils

    async def fs_watcher(self) -> None:
        cogs_path = Path(__file__).parent.joinpath("cogs")
        async for changes in awatch(cogs_path):
            changes_list = list(changes)[0]
            if changes_list[0].modified == 2:
                reload_file = Path(changes_list[1])
                self.logger.info(f"Reloading extension: {reload_file.name[:-3]}")
                await self.reload_extension(f"cogs.{reload_file.name[:-3]}")

    ### Internal core overrides

    async def setup_hook(self) -> None:
        for extension in EXTENSIONS:
            await self.load_extension(extension)

        # Load Jishaku during production as this is what Umbra, Jeyy and others do
        # Useful for debugging purposes
        await self.load_extension("jishaku")

        self.partial_config = await self.fetch_partial_config()

        if self._dev_mode is True and _fsw is True:
            self.logger.info("Dev mode is enabled. Loading FSWatcher")
            self.loop.create_task(self.fs_watcher())

    async def on_ready(self):
        if not hasattr(self, "uptime"):
            self.uptime = discord.utils.utcnow()

        curr_user = None if self.user is None else self.user.name
        self.logger.info(f"{curr_user} is fully ready!")
