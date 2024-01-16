import os
import signal
from pathlib import Path

import asyncpg
import discord
from aiohttp import ClientSession
from libs.utils import KeyboardInterruptHandler, RodhajLogger
from libs.utils.config import RodhajConfig

from rodhaj import Rodhaj

if os.name == "nt":
    from winloop import run
else:
    from uvloop import run

config_path = Path(__file__).parent / "config.yml"
config = RodhajConfig(config_path)

TOKEN = config["rodhaj"]["token"]
POSTGRES_URI = config["postgres_uri"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


async def main() -> None:
    async with ClientSession() as session, asyncpg.create_pool(
        dsn=POSTGRES_URI, min_size=25, max_size=25, command_timeout=30
    ) as pool:
        async with Rodhaj(
            config=config, intents=intents, session=session, pool=pool
        ) as bot:
            bot.loop.add_signal_handler(signal.SIGTERM, KeyboardInterruptHandler(bot))
            bot.loop.add_signal_handler(signal.SIGINT, KeyboardInterruptHandler(bot))
            await bot.start(TOKEN)


def launch() -> None:
    with RodhajLogger():
        run(main())


if __name__ == "__main__":
    launch()
