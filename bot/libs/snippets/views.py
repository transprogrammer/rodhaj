from libs.utils import RoboView, GuildContext
import discord.ui

from rodhaj import Rodhaj


class SnippetCreationModal(discord.ui.Modal, title="Editing Snippet"):
    content = discord.ui.TextInput(
        label="Snippet message",
        placeholder="Call me Ishmael. Some years ago—never mind "
                    + "how long precisely...",
        style=discord.TextStyle.paragraph,
    )

    def __init__(self, bot: Rodhaj, context: GuildContext, name: str):
        super().__init__(timeout=12 * 3600)
        self._bot = bot
        self._ctx = context
        self._snippet_name = name
        self.title = f"Creating Snippet {name}"

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self._bot.dispatch(
            "snippet_create",
            self._ctx.guild,
            self._ctx.author,
            self._snippet_name,
            self.content.value,
            self._ctx,
        )
        self.stop()


class SnippetPreCreationConfirmationView(discord.ui.View):
    def __init__(self, bot: Rodhaj, ctx: GuildContext, snippet_name: str, timeout=15):
        super().__init__(timeout=timeout)
        self._bot = bot
        self._ctx = ctx
        self._snippet_name = snippet_name

    @discord.ui.button(label="Create Snippet", style=discord.ButtonStyle.green)
    async def create_snippet(
            self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self._ctx.author.id:
            return
        button.disabled = True
        modal = SnippetCreationModal(self._bot, self._ctx, self._snippet_name)
        await interaction.response.send_modal(modal)
        await interaction.edit_original_response(
            content="Creating Snippet...", view=None
        )
        await modal.wait()
        await interaction.delete_original_response()
        self.stop()

    async def on_timeout(self):
        self.clear_items()
        self.stop()


class SnippetInfoView(RoboView):
    pass
