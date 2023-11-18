from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

from .errors import produce_error_embed

if TYPE_CHECKING:
    from bot.rodhaj import Rodhaj

NO_CONTROL_MSG = "This view cannot be controlled by you, sorry!"


class RoboView(discord.ui.View):
    """Subclassed `discord.ui.View` that includes sane default configs"""

    def __init__(self, ctx: commands.Context[Rodhaj]):
        super().__init__()
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
        self.clear_items()
        self.stop()
