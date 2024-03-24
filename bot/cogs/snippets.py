from typing import Optional

import discord
from discord.ext import commands
from libs.utils import GuildContext
from rodhaj import Rodhaj


class Snippets(commands.Cog):
    """
    Cog for snippet-related commands (#21)
    """

    def __init__(self, bot: Rodhaj):
        self._bot = bot

    @commands.guild_only()
    @commands.group(name="snippet")
    async def snippet_cmd(self, ctx: GuildContext):
        if ctx.invoked_subcommand is None:
            await ctx.send("placeholder for base command")

    @commands.guild_only()
    @snippet_cmd.command()
    async def remove(self, ctx: GuildContext, name: str):
        query = """
        DELETE FROM snippets
        WHERE guild_id = $1 AND name = $2
        RETURNING name
        """
        result = await self._bot.pool.fetchrow(query, ctx.guild.id, name)
        if result is None:
            await ctx.reply(
                embed=discord.Embed(
                    title="Deletion failed",
                    colour=discord.Colour.red(),
                    description=f"Snippet `{name}` was not found and "
                    + "hence was not deleted.",
                ),
                ephemeral=True,
            )
        else:
            await ctx.reply(
                embed=discord.Embed(
                    title="Deletion successful",
                    colour=discord.Colour.green(),
                    description=f"Snippet `{name}` was deleted successfully",
                ),
                ephemeral=True,
            )

    @commands.guild_only()
    @snippet_cmd.command()
    async def new(self, ctx, *args):
        await ctx.send("placeholder for snippet new")

    @commands.guild_only()
    @snippet_cmd.command()
    async def show(self, ctx: GuildContext, name: str):
        query = """
        SELECT content FROM snippets
        WHERE guild_id = $1 AND name = $2
        """
        data = await self._bot.pool.fetchrow(query, ctx.guild.id, name)
        if data is None:
            ret_embed = discord.Embed(
                title="Oops...",
                colour=discord.Colour.red(),
                description=f"The snippet `{name}` was not found. "
                + "To create a new snippet with this name, "
                + f"please run `snippet create {name} <content>`",
            )
            await ctx.reply(embed=ret_embed, ephemeral=True)
        else:
            ret_data = discord.Embed(
                title=f"Snippet information for `{name}`",
                colour=discord.Colour.green(),
                description=data[0],
            )
            await ctx.reply(embed=ret_data, ephemeral=True)

    @commands.guild_only()
    @snippet_cmd.command()
    async def list(self, ctx, *args):
        await ctx.send("placeholder for snippet list")

    async def edit_prompt_user(self, ctx: GuildContext, name: str):
        raise NotImplementedError("TODO: Add prompt for editing snippet.")

    @commands.guild_only()
    @snippet_cmd.command()
    async def edit(self, ctx: GuildContext, name: str, content: Optional[str]):
        if content is None:
            await self.edit_prompt_user(ctx, name)
            return
        query = """
        UPDATE snippets
        SET content = $3
        WHERE guild_id = $1 AND name = $2
        RETURNING name
        """

        result = await self._bot.pool.fetchrow(query, ctx.guild.id, name, content)
        if result is None:
            await ctx.reply(
                embed=discord.Embed(
                    title="Oops...",
                    colour=discord.Colour.red(),
                    description=f"Cannot edit snippet `{name}` as there is no such "
                    + "snippet. To create a new snippet with the corresponding "
                    + f"name, please run `snippet new {name} <snippet text>`.",
                ),
                ephemeral=True,
            )
        else:
            await ctx.reply(
                embed=discord.Embed(
                    title="Snippet changed",
                    colour=discord.Colour.green(),
                    description=f"The contents of snippet {result[0]} has been "
                    + f"changed to \n\n{content}",
                ),
                ephemeral=True,
            )


async def setup(bot: Rodhaj):
    await bot.add_cog(Snippets(bot))
