import traceback

import discord

from .embeds import ErrorEmbed


def produce_error_embed(error: Exception) -> ErrorEmbed:
    error_traceback = "\n".join(traceback.format_exception_only(type(error), error))
    embed = ErrorEmbed()
    desc = f"""
    Uh oh! It seems like there was an issue. Ask the devs for help.
    
    **Error**:
    ```{error_traceback}```
    """
    embed.description = desc
    embed.set_footer(text="Happened At")
    embed.timestamp = discord.utils.utcnow()
    return embed
