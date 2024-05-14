from __future__ import annotations

import platform
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks

try:

    from prometheus_async.aio.web import start_http_server
    from prometheus_client import Counter, Enum, Gauge, Info, Summary
except ImportError:
    raise RuntimeError(
        "Prometheus libraries are required to be installed. "
        "Either install those libraries or disable Prometheus extension"
    )

if TYPE_CHECKING:
    from bot.rodhaj import Rodhaj

METRIC_PREFIX = "discord_"


class FeatureCollector:
    __slots__ = (
        "bot",
        "active_tickets",
        "closed_tickets",
        "locked_tickets",
        "blocked_users",
    )

    def __init__(self, bot: Rodhaj):
        self.bot = bot
        self.active_tickets = Gauge(
            f"{METRIC_PREFIX}active_tickets", "Amount of active tickets"
        )
        self.closed_tickets = Counter(
            f"{METRIC_PREFIX}closed_tickets", "Number of closed tickets in this session"
        )
        self.locked_tickets = Gauge(
            f"{METRIC_PREFIX}locked_tickets",
            "Number of soft locked tickets in this session",
        )
        self.blocked_users = Gauge(
            f"{METRIC_PREFIX}blocked_users", "Number of currently blocked users"
        )


# Maybe load all of these from an json file next time
class Metrics:
    __slots__ = ("bot", "connected", "latency", "commands", "version", "features")

    def __init__(self, bot: Rodhaj):
        self.bot = bot
        self.connected = Enum(
            f"{METRIC_PREFIX}connected",
            "Connected to Discord",
            ["shard"],
            states=["connected", "disconnected"],
        )
        self.latency = Gauge(f"{METRIC_PREFIX}latency", "Latency to Discord", ["shard"])
        self.commands = Summary(f"{METRIC_PREFIX}commands", "Total commands executed")
        self.version = Info(f"{METRIC_PREFIX}version", "Versions of the bot")
        self.features = FeatureCollector(self.bot)

    def get_commands(self) -> int:
        total_commands = 0
        for _ in self.bot.walk_commands():
            # As some of the commands are parents,
            # Grouped commands are also counted here
            total_commands += 1

        return total_commands

    def fill(self) -> None:
        self.version.info(
            {
                "build_version": self.bot.version,
                "dpy_version": discord.__version__,
                "python_version": platform.python_version(),
            }
        )
        self.commands.observe(self.get_commands())

    async def start(self, host: str, port: int) -> None:
        await start_http_server(addr=host, port=port)


class Prometheus(commands.Cog):
    """Prometheus exporter extension for Rodhaj"""

    def __init__(self, bot: Rodhaj):
        self.bot = bot
        self._connected_label = self.bot.metrics.connected.labels(None)

    async def cog_load(self) -> None:
        self.latency_loop.start()

    async def cog_unload(self) -> None:
        self.latency_loop.stop()

    @tasks.loop(seconds=5)
    async def latency_loop(self) -> None:
        self.bot.metrics.latency.labels(None).set(self.bot.latency)

    @commands.Cog.listener()
    async def on_connect(self) -> None:
        self._connected_label.state("connected")

    @commands.Cog.listener()
    async def on_resumed(self) -> None:
        self._connected_label.state("connected")

    @commands.Cog.listener()
    async def on_disconnect(self) -> None:
        self._connected_label.state("disconnected")


async def setup(bot: Rodhaj) -> None:
    await bot.add_cog(Prometheus(bot))
