from discord import DMChannel, Message
from discord.ext import commands
from rodhaj import Rodhaj


class DmCommunications(commands.Cog):
    def __init__(self, bot: Rodhaj):
        self._bot = bot
        self._pool = bot.pool

    async def handle_user_no_thread(self, message: Message):
        channel = message.channel
        context = await self._bot.get_context(message)
        result = await context.prompt(
            "Seems like you do not have an active thread. "
            + "Would you want to create one?",
            timeout=600,
            delete_after=True,
        )

        # Code to create thread here
        if result:
            await channel.send(
                "Thread created; please use the following "
                + "thread for all further communications."
            )
        else:
            await channel.send("No worries!")

    async def handle_dm(self, message: Message):
        query = """
        SELECT id
        FROM tickets
        WHERE owner_id = $1
        """
        row = await self._pool.fetchrow(query, message.author.id)
        if row is None:
            await self.handle_user_no_thread(message)

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if isinstance(message.channel, DMChannel):
            if not self._bot.user_is_this_bot(message.author):
                await self.handle_dm(message)


async def setup(bot: Rodhaj):
    await bot.add_cog(DmCommunications(bot))
