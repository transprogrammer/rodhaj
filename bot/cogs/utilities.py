from __future__ import annotations

import datetime
import itertools
import platform
from time import perf_counter
from typing import TYPE_CHECKING

import discord
import psutil
import pygit2
from discord.ext import commands
from discord.utils import format_dt
from pygit2.enums import SortMode
from utils import Embed, human_timedelta, is_docker

if TYPE_CHECKING:
    from utils import RoboContext

    from bot.rodhaj import Rodhaj


# A cog houses a category of commands
# Unlike djs, think of commands being stored as a category,
# which the cog is that category
class Utilities(commands.Cog):
    def __init__(self, bot: Rodhaj) -> None:
        self.bot = bot
        self.process = psutil.Process()

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\U0001f9f0")

    def get_bot_uptime(self, *, brief: bool = False) -> str:
        return human_timedelta(
            self.bot.uptime, accuracy=None, brief=brief, suffix=False
        )

    def format_commit(self, commit: pygit2.Commit) -> str:
        short, _, _ = commit.message.partition("\n")
        short_sha2 = str(commit.id)[0:6]
        commit_tz = datetime.timezone(
            datetime.timedelta(minutes=commit.commit_time_offset)
        )
        commit_time = datetime.datetime.fromtimestamp(commit.commit_time).astimezone(
            commit_tz
        )

        # [`hash`](url) message (offset)
        offset = format_dt(commit_time.astimezone(datetime.timezone.utc), "R")
        commit_id = str(commit.id)
        return f"[`{short_sha2}`](https://github.com/transprogrammer/rodhaj/commit/{commit_id}) {short} ({offset})"

    def get_last_commits(self, count: int = 5):
        repo = pygit2.Repository(".git")  # type: ignore # It technically is
        commits = list(
            itertools.islice(repo.walk(repo.head.target, SortMode.TOPOLOGICAL), count)
        )
        return "\n".join(self.format_commit(c) for c in commits)

    def get_current_branch(
        self,
    ) -> str:
        repo = pygit2.Repository(".git")  # type: ignore
        return repo.head.shorthand

    async def fetch_num_active_tickets(self) -> int:
        query = "SELECT COUNT(*) FROM tickets;"
        value = await self.bot.pool.fetchval(query)
        if value is None:
            return 0
        return value

    @commands.hybrid_command(name="about")
    async def about(self, ctx: RoboContext) -> None:
        """Shows some stats for Rodhaj"""
        total_members = 0
        total_unique = len(self.bot.users)

        guilds = 0
        for guild in self.bot.guilds:
            guilds += 1
            if guild.unavailable:
                continue

            total_members += guild.member_count or 0

        # For Kumiko, it's done differently
        # R. Danny's way of doing it is probably close enough anyways
        memory_usage = self.process.memory_full_info().uss / 1024**2
        cpu_usage = self.process.cpu_percent() / psutil.cpu_count()  # type: ignore
        bot_user: discord.ClientUser = self.bot.user  # type: ignore

        revisions = "See [GitHub](https://github.com/transprogrammer/rodhaj)"
        working_branch = "Docker"

        if not is_docker():
            revisions = self.get_last_commits()
            working_branch = self.get_current_branch()

        footer_text = (
            "Developed by Noelle and the Transprogrammer dev team\n"
            f"Made with discord.py v{discord.__version__} | Running Python {platform.python_version()}"
        )
        embed = Embed()
        embed.set_author(name=bot_user.name, icon_url=bot_user.display_avatar.url)
        embed.title = "Rodhaj"
        embed.description = (
            "Rodhaj is a modern, improved ModMail bot designed exclusively for "
            "the transprogrammer community. By creating a shared inbox, "
            "it allows for users and staff to seamlessly communicate safely, securely, and privately. "
            "In order to start using Rodhaj, please DM Rodhaj to make a ticket. "
            f"\n\nLatest Changes ({working_branch}):\n {revisions}"
        )
        embed.set_footer(
            text=footer_text,
            icon_url="https://cdn.discordapp.com/emojis/596577034537402378.png",
        )
        embed.add_field(name="Servers", value=guilds)
        embed.add_field(
            name="User", value=f"{total_members} total\n{total_unique} unique"
        )
        embed.add_field(
            name="Process",
            value=f"{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU",
        )
        embed.add_field(
            name="Active Tickets", value=await self.fetch_num_active_tickets()
        )
        embed.add_field(name="Version", value=str(self.bot.version))
        embed.add_field(name="Uptime", value=self.get_bot_uptime(brief=True))
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="ping")
    async def ping(self, ctx: RoboContext) -> None:
        """Obtains ping information"""
        start = perf_counter()
        await self.bot.pool.fetchrow("SELECT 1")
        end = perf_counter()
        db_ping = end - start

        embed = Embed()
        embed.add_field(
            name="DB Latency",
            value=f"```{db_ping * 1000:.2f}ms```",
            inline=False,
        )
        embed.add_field(
            name="Websocket Latency",
            value=f"```{self.bot.latency * 1000:.2f}ms```",
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="uptime")
    async def uptime(self, ctx: RoboContext) -> None:
        """Displays the bot's uptime"""
        uptime_message = f"Uptime: {self.get_bot_uptime()}"
        await ctx.send(uptime_message)

    @commands.hybrid_command(name="version")
    async def version(self, ctx: RoboContext) -> None:
        """Displays the current build version"""
        version_message = f"Version: {self.bot.version}"
        await ctx.send(version_message)


async def setup(bot: Rodhaj) -> None:
    await bot.add_cog(Utilities(bot))
