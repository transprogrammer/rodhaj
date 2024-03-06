from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands

from .errors import produce_error_embed

if TYPE_CHECKING:
    from rodhaj import Rodhaj


# Later on if we needed global interaction checks, we can do it here
class RodhajCommandTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        bot: Rodhaj = interaction.client  # type: ignore # Correct subclass type
        if interaction.user.id in bot.blocklist:
            await interaction.response.send_message(
                "You have been blocked from using this bot", ephemeral=True
            )
            return False
        return True

    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        await interaction.response.send_message(embed=produce_error_embed(error))
