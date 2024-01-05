# This cog is unloaded as I (Noelle)
# don't want to delete this. More than likely
# it will stay here as what I'll do is use my implementation
# of the ticket system instead. This is now here for reference
# purposes
# - Noelle

from discord import Message
from discord.ext import commands
from libs.utils import RoboContext

from rodhaj import Rodhaj


class DmCommunications(commands.Cog):
    def __init__(self, bot: Rodhaj):
        self._bot = bot
        self._pool = bot.pool

    async def handle_user_no_thread(self, context: RoboContext):
        result = await context.prompt(
            "Seems like you do not have an active thread. "
            + "Would you want to create one?",
            timeout=600,
            delete_after=True,
        )

        # Code to create thread here
        if result:
            await context.send(
                "Thread created; please use the following "
                + "thread for all further communications."
            )
        else:
            await context.send("No worries!")

    async def handle_dm(self, message: Message):
        query = """
        SELECT id
        FROM tickets
        WHERE owner_id = $1
        """
        row = await self._pool.fetchrow(query, message.author.id)

        message_ctx = await self._bot.get_context(message)
        if row is None:
            await self.handle_user_no_thread(message_ctx)

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.guild is None:
            if not message.author.bot:
                # private DM not from bot
                await self.handle_dm(message)


async def setup(bot: Rodhaj):
    await bot.add_cog(DmCommunications(bot))
