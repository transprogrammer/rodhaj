from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from libs.tickets.structs import TicketThread
from libs.utils import ErrorEmbed, RoboView

from .utils import register_user, safe_content

if TYPE_CHECKING:
    from libs.utils.context import RoboContext

    from bot.cogs.tickets import Tickets
    from bot.rodhaj import Rodhaj


class TicketConfirmView(RoboView):
    def __init__(
        self,
        bot: Rodhaj,
        ctx: RoboContext,
        cog: Tickets,
        content: str,
        guild: discord.Guild,
        delete_after: bool = True,
    ) -> None:
        super().__init__(ctx=ctx, timeout=300.0)
        self.bot = bot
        self.ctx = ctx
        self.cog = cog
        self.content = content
        self.guild = guild
        self.delete_after = delete_after
        self.pool = self.bot.pool

    async def delete_response(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_response()

        self.stop()

    @discord.ui.button(
        label="Confirm",
        style=discord.ButtonStyle.green,
        emoji="<:greenTick:596576670815879169>",
        row=1,
    )
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await register_user(self.ctx.author.id, self.pool)
        author = self.ctx.author
        ticket = TicketThread(
            user=author,
            location_id=self.guild.id,
            content=self.content,
            created_at=discord.utils.utcnow(),
        )
        created_ticket = await self.cog.create_ticket(ticket)

        if created_ticket is None:
            await interaction.response.send_message(
                "Rodhaj is not set up yet. Please contact the admin or staff",
                ephemeral=True,
            )
            return

        self.bot.dispatch(
            "ticket_create",
            self.guild,
            self.ctx.author,
            created_ticket.ticket,
            safe_content(self.content),
        )
        embed = discord.Embed(
            title="\U0001f3ab Ticket created", color=discord.Color.from_rgb(124, 252, 0)
        )
        embed.description = "The ticket has been successfully created. Please continue to DM Rodhaj in order to send the message to the ticket, where an assigned staff will help you."

        if self.message:
            await self.message.edit(
                content=None, embed=embed, view=None, delete_after=5.0
            )

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.red,
        emoji="<:redTick:596576672149667840>",
        row=1,
    )
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()

    async def on_timeout(self) -> None:
        # This is the only way you can really edit the original message
        if self.message:
            embed = ErrorEmbed()
            embed.title = "\U00002757 Timed Out"
            embed.description = (
                "Timed out waiting for a response. Not creating a ticket. "
                "In order to create a ticket, please resend your message and properly confirm"
            )
            await self.message.edit(embed=embed, view=None)
            return
