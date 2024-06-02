import asyncio
import importlib
import os
import re
import subprocess  # nosec # We already know this is dangerous, but it's needed
import sys
from typing import Literal, Optional

import discord
from discord.ext import commands
from discord.ext.commands import Greedy
from libs.utils import RoboContext

from rodhaj import Rodhaj

GIT_PULL_REGEX = re.compile(r"\s+(?P<filename>.*)\b\s+\|\s+[\d]")


class Admin(commands.Cog, command_attrs=dict(hidden=True)):
    """Administrative commands for Rodhaj"""

    def __init__(self, bot: Rodhaj) -> None:
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\U00002699")

    async def cog_check(self, ctx: RoboContext) -> bool:
        return await self.bot.is_owner(ctx.author)

    async def reload_or_load_extension(self, module: str) -> None:
        try:
            await self.bot.reload_extension(module)
        except commands.ExtensionNotLoaded:
            await self.bot.load_extension(module)

    def find_modules_from_git(self, output: str) -> list[tuple[int, str]]:
        files = GIT_PULL_REGEX.findall(output)
        ret: list[tuple[int, str]] = []
        for file in files:
            root, ext = os.path.splitext(file)
            if ext != ".py" or root.endswith("__init__"):
                continue

            true_root = ".".join(root.split("/")[1:])

            if true_root.startswith("cogs") or true_root.startswith("libs"):
                # A subdirectory within these are a part of the codebase

                ret.append((true_root.count(".") + 1, true_root))

        # For reload order, the submodules should be reloaded first
        ret.sort(reverse=True)
        return ret

    async def run_process(self, command: str) -> list[str]:
        process = await asyncio.create_subprocess_shell(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        result = await process.communicate()

        return [output.decode() for output in result]

    def tick(self, opt: Optional[bool], label: Optional[str] = None) -> str:
        lookup = {
            True: "\U00002705",
            False: "\U0000274c",
            None: "\U000023e9",
        }
        emoji = lookup.get(opt, "\U0000274c")
        if label is not None:
            return f"{emoji}: {label}"
        return emoji

    def format_results(self, statuses: list) -> str:
        desc = "\U00002705 - Successful reload | \U0000274c - Failed reload | \U000023e9 - Skipped\n\n"
        status = "\n".join(f"- {status}: `{module}`" for status, module in statuses)
        desc += status
        return desc

    async def reload_exts(self, module: str) -> list[tuple[str, str]]:
        statuses = []
        try:
            await self.reload_or_load_extension(module)
            statuses.append((self.tick(True), module))
        except commands.ExtensionError:
            statuses.append((self.tick(False), module))

        return statuses

    def reload_lib_modules(self, module: str) -> list[tuple[str, str]]:
        statuses = []
        try:
            actual_module = sys.modules[module]
            importlib.reload(actual_module)
            statuses.append((self.tick(True), module))
        except KeyError:
            statuses.append((self.tick(None), module))
        except Exception:
            statuses.append((self.tick(False), module))
        return statuses

    # Umbra's sync command
    # To learn more about it, see the link below (and ?tag ass on the dpy server):
    # https://about.abstractumbra.dev/discord.py/2023/01/29/sync-command-example.html
    @commands.guild_only()
    @commands.command(name="sync", hidden=True)
    async def sync(
        self,
        ctx: RoboContext,
        guilds: Greedy[discord.Object],
        spec: Optional[Literal["~", "*", "^"]] = None,
    ) -> None:
        """Performs a sync of the tree. This will sync, copy globally, or clear the tree."""
        await ctx.defer()
        if not guilds:
            if spec == "~":
                synced = await self.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                self.bot.tree.copy_global_to(guild=ctx.guild)  # type: ignore
                synced = await self.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                self.bot.tree.clear_commands(guild=ctx.guild)
                await self.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await self.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await self.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

    @commands.command(name="reload-all", hidden=True)
    async def reload(self, ctx: RoboContext) -> None:
        """Reloads all cogs and utils"""
        async with ctx.typing():
            stdout, _ = await self.run_process("git pull")

        # progress and stuff is redirected to stderr in git pull
        # however, things like "fast forward" and files
        # along with the text "already up-to-date" are in stdout

        if stdout.startswith("Already up-to-date."):
            await ctx.send(stdout)
            return

        modules = self.find_modules_from_git(stdout)

        mods_text = "\n".join(
            f"{index}. `{module}`" for index, (_, module) in enumerate(modules, start=1)
        )
        prompt_text = (
            f"This will update the following modules, are you sure?\n{mods_text}"
        )

        confirm = await ctx.prompt(prompt_text)
        if not confirm:
            await ctx.send("Aborting....")
            return

        statuses = []
        for is_submodule, module in modules:
            if is_submodule:
                statuses = self.reload_lib_modules(module)
            else:
                statuses = await self.reload_exts(module)

        await ctx.send(self.format_results(statuses))

    @commands.command(name="test")
    async def testing(self, ctx: RoboContext) -> None:
        raise ValueError("hi")


async def setup(bot: Rodhaj) -> None:
    await bot.add_cog(Admin(bot))
