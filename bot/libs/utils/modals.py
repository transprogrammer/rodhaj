from __future__ import annotations

import discord

from .context import RoboContext
from .embeds import FullErrorEmbed

NO_CONTROL_MSG = "This modal cannot be controlled by you, sorry!"


class RoboModal(discord.ui.Modal):
    """Subclassed `discord.ui.Modal` that includes sane default configs"""

    def __init__(self, ctx: RoboContext, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        if interaction.user and interaction.user.id in (
            self.ctx.bot.application.owner.id,  # type: ignore
            self.ctx.author.id,
        ):
            return True
        await interaction.response.send_message(NO_CONTROL_MSG, ephemeral=True)
        return False

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, /
    ) -> None:
        await interaction.response.send_message(
            embed=FullErrorEmbed(error), ephemeral=True
        )
        self.stop()
