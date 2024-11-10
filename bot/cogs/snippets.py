from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

import asyncpg.exceptions
import discord
from discord.ext import commands
from libs.snippets.model import create_snippet, get_snippet
from libs.snippets.views import SnippetPreCreationConfirmationView

if TYPE_CHECKING:
    from libs.utils.context import GuildContext
    from rodhaj import Rodhaj


class Snippets(commands.Cog):
    """Send or display pre-written text to users"""

    def __init__(self, bot: Rodhaj):
        self.bot = bot
        self.pool = self.bot.pool

    # Editing Utilities

    async def edit_prompt_user(self, ctx: GuildContext, name: str):
        raise NotImplementedError("TODO: Add prompt for editing snippet.")

    @commands.guild_only()
    @commands.hybrid_group(name="snippets", alias=["snippet"], fallback="get")
    async def snippet(self, ctx: GuildContext, *, name: str):
        """Allows for use snippets of text for later retrieval or for quicker responses

        If an subcommand is not called, then this will search
        the database for the requested snippet
        """
        await ctx.send("Implement getting snippets here")

    @commands.guild_only()
    @snippet.command()
    async def remove(self, ctx: GuildContext, name: str):
        query = """
        DELETE FROM snippets
        WHERE name = $2
        RETURNING id
        """
        result = await self.pool.fetchrow(query, ctx.guild.id, name)
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

    # TODO: Run all str inputs through custom converters
    @commands.guild_only()
    @snippet.command()
    async def new(
        self,
        ctx: GuildContext,
        name: str,
        *,
        content: Optional[str] = None,
    ):
        if (
            await get_snippet(self.pool, ctx.guild.id, ctx.message.author.id, name)
            is not None
        ):
            await ctx.send(
                content=f"Snippet `{name}` already exists!",
            )
            return

        if not content:
            timeout = 15
            confirmation_view = SnippetPreCreationConfirmationView(
                self.bot, ctx, name, timeout
            )
            await ctx.reply(
                content=f"Create snippet with id `{name}`?",
                view=confirmation_view,
                delete_after=timeout,
            )
        else:
            self.bot.dispatch(
                "snippet_create",
                ctx.guild,
                ctx.message.author,
                name,
                content,
                ctx,
            )

    @commands.guild_only()
    @snippet.command(name="list")
    async def snippets_list(
        self, ctx: GuildContext, json: Optional[bool] = False
    ) -> None:
        await ctx.send("list snippets")

    @commands.guild_only()
    @snippet.command()
    async def show(self, ctx: GuildContext, name: str):
        query = """
        SELECT content FROM snippets
        WHERE name = $1
        """
        data = await self.pool.fetchrow(query, name)
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
    @snippet.command()
    async def edit(self, ctx: GuildContext, name: str, content: Optional[str]):
        if content is None:
            await self.edit_prompt_user(ctx, name)
            return
        query = """
        UPDATE snippets
        SET content = $2
        WHERE name = $1
        RETURNING name
        """
        result = await self.pool.fetchrow(query, name, content)
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

    @commands.Cog.listener()
    async def on_snippet_create(
        self,
        guild: discord.Guild,
        creator: Union[discord.User, discord.Member],
        snippet_name: str,
        snippet_text: str,
        response_context: GuildContext,
    ):
        try:
            await create_snippet(
                self.pool, guild.id, creator.id, snippet_name, snippet_text
            )
            if response_context:
                await response_context.send(
                    "Snippet created successfully", delete_after=5
                )
        except asyncpg.exceptions.UniqueViolationError:
            if response_context:
                await response_context.send("Snippet already exists", delete_after=5)


async def setup(bot: Rodhaj):
    await bot.add_cog(Snippets(bot))
