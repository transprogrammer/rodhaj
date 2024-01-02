from typing import Literal, Optional

import discord
from cogs import EXTENSIONS
from discord.ext import commands
from discord.ext.commands import Greedy
from libs.utils import RoboContext

from rodhaj import Rodhaj


class Admin(commands.Cog, command_attrs=dict(hidden=True)):
    """Administrative commands for Rodhaj"""

    def __init__(self, bot: Rodhaj) -> None:
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\U00002699")

    async def cog_check(self, ctx: RoboContext) -> bool:
        return await self.bot.is_owner(ctx.author)

    # Umbra's sync command
    # To learn more about it, see the link below (and ?tag ass on the dpy server):
    # https://about.abstractumbra.dev/discord.py/2023/01/29/sync-command-example.html
    @commands.guild_only()
    @commands.command(name="sync")
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

    @commands.command(name="reload-all")
    async def reload_all(self, ctx: RoboContext) -> None:
        """Reloads all cogs. Used in production to not produce any downtime"""
        if not hasattr(self.bot, "uptime"):
            await ctx.send("Bot + exts must be up and loaded before doing this")
            return

        for extension in EXTENSIONS:
            await self.bot.reload_extension(extension)
        await ctx.send("Successfully reloaded all extensions live")


async def setup(bot: Rodhaj) -> None:
    await bot.add_cog(Admin(bot))
