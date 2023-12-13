import asyncio
import os

import asyncpg
import discord
from aiohttp import ClientSession
from environs import Env
from libs.utils import RodhajLogger
from rodhaj import Rodhaj

if os.name == "nt":
    from winloop import install
else:
    from uvloop import install

# Hope not to trip pyright
env = Env()
env.read_env()

TOKEN = env("TOKEN")
DEV_MODE = env.bool("DEV_MODE", False)
POSTGRES_URI = env("POSTGRES_URI")

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True


async def main() -> None:
    async with ClientSession() as session, asyncpg.create_pool(
        dsn=POSTGRES_URI, min_size=25, max_size=25, command_timeout=30
    ) as pool:
        async with Rodhaj(
            intents=intents, session=session, pool=pool, dev_mode=DEV_MODE
        ) as bot:
            await bot.start(TOKEN)


def launch() -> None:
    with RodhajLogger():
        install()
        asyncio.run(main())


if __name__ == "__main__":
    try:
        launch()
    except KeyboardInterrupt:
        pass
