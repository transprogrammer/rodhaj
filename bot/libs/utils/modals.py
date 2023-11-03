import discord

from .errors import produce_error_embed

NO_CONTROL_MSG = "This modal cannot be controlled by you, sorry!"


class RoboModal(discord.ui.Modal):
    """Subclassed `discord.ui.Modal` that includes sane default configs"""

    def __init__(self, interaction: discord.Interaction, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interaction = interaction

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        if interaction.user and interaction.user.id in (
            self.interaction.client.application.owner.id,  # type: ignore
            self.interaction.user.id,
        ):
            return True
        await interaction.response.send_message(NO_CONTROL_MSG, ephemeral=True)
        return False

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, /
    ) -> None:
        await interaction.response.send_message(
            embed=produce_error_embed(error), ephemeral=True
        )
        self.stop()