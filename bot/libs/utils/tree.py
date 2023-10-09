import traceback

import discord
from discord import app_commands
from discord.utils import utcnow
from libs.utils import ErrorEmbed


class RodhajCommandTree(app_commands.CommandTree):
    def build_error_embed(self, error: app_commands.AppCommandError) -> ErrorEmbed:
        error_traceback = "\n".join(traceback.format_exception_only(type(error), error))
        embed = ErrorEmbed()
        embed.description = f"""
        Uh oh! It seems like the command ran into an issue!
        
        **Error**:
        ```
        {error_traceback}
        ```
        """
        embed.set_footer(text="Happened At")
        embed.timestamp = utcnow()
        return embed

    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        await interaction.response.send_message(embed=self.build_error_embed(error))
