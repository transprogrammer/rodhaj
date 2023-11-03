from typing import Any

import discord

from .errors import produce_error_embed

NO_CONTROL_MSG = "This view cannot be controlled by you, sorry!"


class RoboView(discord.ui.View):
    """Subclassed `discord.ui.View` that includes sane default configs"""

    def __init__(self, interaction: discord.Interaction):
        super().__init__()
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
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[Any],
        /,
    ) -> None:
        await interaction.response.send_message(
            embed=produce_error_embed(error), ephemeral=True
        )
        self.stop()

    async def on_timeout(self) -> None:
        if self.interaction.response.is_done():
            await self.interaction.edit_original_response(view=None)
