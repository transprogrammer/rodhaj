import traceback

import discord
from discord.ext import commands

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


def create_premade_embed(title: str, description: str) -> ErrorEmbed:
    embed = ErrorEmbed()
    embed.timestamp = discord.utils.utcnow()
    embed.title = title
    embed.description = description
    return embed


async def send_error_embed(ctx: commands.Context, error: commands.CommandError) -> None:
    if isinstance(error, commands.CommandInvokeError) or isinstance(
        error, commands.HybridCommandError
    ):
        await ctx.send(embed=produce_error_embed(error))
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(
            embed=create_premade_embed(
                "Command not found",
                "The command you were looking for could not be found",
            )
        )
    elif isinstance(error, commands.NotOwner):
        # Basically completely silence it making people not know what happened
        return
    elif isinstance(error, commands.MissingPermissions):
        missing_perms = ", ".join(error.missing_permissions).rstrip(",")
        await ctx.send(
            embed=create_premade_embed(
                "Missing Permissions",
                f"You are missing the following permissions: {missing_perms}",
            )
        )
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            embed=create_premade_embed(
                "Missing Required Argument",
                f"You are missing the following argument(s): {error.param.name}",
            )
        )
    else:
        await ctx.send(embed=produce_error_embed(error))
