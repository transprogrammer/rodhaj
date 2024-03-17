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
    async def remove(self, ctx, *args):
        await ctx.send("placeholder for snippet remove")

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

    @commands.guild_only()
    @snippet_cmd.command()
    async def edit(self, ctx, *args):
        await ctx.send("placeholder for snippet edit")


async def setup(bot: Rodhaj):
    await bot.add_cog(Snippets(bot))
