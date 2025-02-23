import os
import signal
from pathlib import Path

import asyncpg
from aiohttp import ClientSession
from rodhaj import KeyboardInterruptHandler, Rodhaj, RodhajLogger, init
from utils.config import RodhajConfig

if os.name == "nt":
    from winloop import run
else:
    from uvloop import run

config_path = Path(__file__).parent / "config.yml"
config = RodhajConfig(config_path)

TOKEN = config["rodhaj"]["token"]
POSTGRES_URI = config["postgres_uri"]


async def main() -> None:
    async with (
        ClientSession() as session,
        asyncpg.create_pool(
            dsn=POSTGRES_URI,
            min_size=25,
            max_size=25,
            init=init,
            command_timeout=30,
        ) as pool,
    ):
        async with Rodhaj(config=config, session=session, pool=pool) as bot:
            bot.loop.add_signal_handler(signal.SIGTERM, KeyboardInterruptHandler(bot))
            bot.loop.add_signal_handler(signal.SIGINT, KeyboardInterruptHandler(bot))
            await bot.start(TOKEN)


if __name__ == "__main__":
    with RodhajLogger():
        run(main())
