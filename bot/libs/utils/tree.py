import discord
from discord import app_commands

from .errors import produce_error_embed


# Later on if we needed global interaction checks, we can do it here
class RodhajCommandTree(app_commands.CommandTree):
    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        await interaction.response.send_message(embed=produce_error_embed(error))
