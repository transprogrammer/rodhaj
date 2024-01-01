import logging
from pathlib import Path
from typing import Union

import asyncpg
import discord
from aiohttp import ClientSession
from cogs import EXTENSIONS, VERSION
from discord.ext import commands
from libs.utils import RoboContext, RodhajCommandTree, send_error_embed

_fsw = True
try:
    from watchfiles import awatch
except ImportError:
    _fsw = False


class Rodhaj(commands.Bot):
    """Main bot for Rodhaj"""

    def __init__(
        self,
        intents: discord.Intents,
        session: ClientSession,
        pool: asyncpg.Pool,
        dev_mode: bool = False,
        *args,
        **kwargs,
    ):
        super().__init__(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="a game"
            ),
            command_prefix=["r>", "?", "!"],
            help_command=None,  # I need to create one
            intents=intents,
            tree_cls=RodhajCommandTree,
            *args,
            **kwargs,
        )
        self.logger = logging.getLogger("rodhaj")
        self.session = session
        self.pool = pool
        self.version = str(VERSION)
        self._dev_mode = dev_mode

    async def fs_watcher(self) -> None:
        cogs_path = Path(__file__).parent.joinpath("cogs")
        async for changes in awatch(cogs_path):
            changes_list = list(changes)[0]
            if changes_list[0].modified == 2:
                reload_file = Path(changes_list[1])
                self.logger.info(f"Reloading extension: {reload_file.name[:-3]}")
                await self.reload_extension(f"cogs.{reload_file.name[:-3]}")

    async def get_context(
        self, origin: Union[discord.Interaction, discord.Message], /, *, cls=RoboContext
    ) -> RoboContext:
        return await super().get_context(origin, cls=cls)

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        await send_error_embed(ctx, error)

    async def setup_hook(self) -> None:
        for extension in EXTENSIONS:
            await self.load_extension(extension)

        # Load Jishaku during production as this is what Umbra, Jeyy and others do
        # Useful for debugging purposes
        await self.load_extension("jishaku")

        if self._dev_mode is True and _fsw is True:
            self.logger.info("Dev mode is enabled. Loading FSWatcher")
            self.loop.create_task(self.fs_watcher())

    async def on_ready(self):
        if not hasattr(self, "uptime"):
            self.uptime = discord.utils.utcnow()

        curr_user = None if self.user is None else self.user.name
        self.logger.info(f"{curr_user} is fully ready!")
