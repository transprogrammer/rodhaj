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
    async def show(self, ctx, *args):
        await ctx.send("placeholder for snippet show")

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
