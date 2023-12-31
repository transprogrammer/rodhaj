import os
import signal

import asyncpg
import discord
from aiohttp import ClientSession
from environs import Env
from libs.utils import KeyboardInterruptHandler, RodhajLogger
from rodhaj import Rodhaj

if os.name == "nt":
    from winloop import run
else:
    from uvloop import run

# Hope not to trip pyright
env = Env()
env.read_env()

TOKEN = env("TOKEN")
DEV_MODE = env.bool("DEV_MODE", False)
POSTGRES_URI = env("POSTGRES_URI")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


async def main() -> None:
    async with ClientSession() as session, asyncpg.create_pool(
        dsn=POSTGRES_URI, min_size=25, max_size=25, command_timeout=30
    ) as pool:
        async with Rodhaj(
            intents=intents, session=session, pool=pool, dev_mode=DEV_MODE
        ) as bot:
            bot.loop.add_signal_handler(signal.SIGTERM, KeyboardInterruptHandler(bot))
            bot.loop.add_signal_handler(signal.SIGINT, KeyboardInterruptHandler(bot))
            await bot.start(TOKEN)


def launch() -> None:
    with RodhajLogger():
        run(main())


if __name__ == "__main__":
    launch()
