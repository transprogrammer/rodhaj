import discord
from discord import DMChannel, Interaction, Message
from discord.ext import commands
from discord.ui import Button, button
from rodhaj import Rodhaj


class StubView(discord.ui.View):
    def __init__(self, base_message: Message):
        super().__init__(timeout=30)
        self._base_msg = base_message
        self._replied = False

    async def on_timeout(self) -> None:
        if not self._replied:
            await self._base_msg.reply("You have not responded within 30 seconds")

    @button(label="Create Thread")
    async def create_thread_btn(self, interaction: Interaction, btn: Button):
        if not self._replied:
            self._replied = True
            btn.disabled = True
            # thread code creation goes to here
            await interaction.message.edit(content="Thread created!", view=self)
            await interaction.response.send_message("Thread created")


class DmCommunications(commands.Cog):
    def __init__(self, bot: Rodhaj):
        self._bot = bot
        self._pool = bot.pool

    @staticmethod
    async def handle_user_no_thread(message: Message):
        await message.reply(
            "Seems like you do not have an active thread. "
            + "Would you want to create one?",
            view=StubView(message),
        )

    async def handle_dm(self, message: Message):
        query = """
        select threadid
        from active_user_threads
        where userid = $1
        """
        row = await self._pool.fetchrow(query, message.author.id)
        if row is None:
            await self.handle_user_no_thread(message)

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if isinstance(message.channel, DMChannel):
            if message.author not in self._bot.users:
                await self.handle_dm(message)


async def setup(bot: Rodhaj):
    await bot.add_cog(DmCommunications(bot))
