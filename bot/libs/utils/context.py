from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from .views import RoboView

if TYPE_CHECKING:
    from bot.rodhaj import Rodhaj


class ConfirmationView(RoboView):
    def __init__(self, ctx, timeout: float, delete_after: bool):
        super().__init__(ctx, timeout=timeout)
        self.value: Optional[bool] = None
        self.delete_after = delete_after
        self.message: Optional[discord.Message] = None

    async def on_timeout(self) -> None:
        if self.delete_after and self.message:
            await self.message.delete()
        elif self.message:
            await self.message.edit(view=None)

    async def delete_response(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_response()

        self.stop()

    @discord.ui.button(
        label="Confirm",
        style=discord.ButtonStyle.green,
        emoji="<:greenTick:596576670815879169>",
    )
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.value = True
        await self.delete_response(interaction)

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.red,
        emoji="<:redTick:596576672149667840>",
    )
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.value = False
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


class RoboContext(commands.Context):
    bot: Rodhaj

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.partial_config = self.bot.partial_config

    async def prompt(
        self, message: str, *, timeout: float = 60.0, delete_after: bool = False
    ) -> Optional[bool]:
        view = ConfirmationView(ctx=self, timeout=timeout, delete_after=delete_after)
        view.message = await self.send(message, view=view, ephemeral=delete_after)
        await view.wait()
        return view.value


class GuildContext(RoboContext):
    guild: discord.Guild
