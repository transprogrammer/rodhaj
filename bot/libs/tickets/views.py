from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING, Optional

import discord
from libs.tickets.structs import TicketThread
from libs.utils import ErrorEmbed, RoboModal, RoboView

from .utils import register_user, safe_content

if TYPE_CHECKING:
    from libs.utils.context import RoboContext

    from bot.cogs.tickets import Tickets
    from bot.rodhaj import Rodhaj


class TicketTitleModal(RoboModal, title="Ticket Title"):
    def __init__(self, ctx: RoboContext, *args, **kwargs):
        super().__init__(ctx=ctx, *args, **kwargs)

        self.title_input = discord.ui.TextInput(
            label="Title",
            style=discord.TextStyle.long,
            placeholder="Input a title...",
            min_length=20,
            max_length=100,
        )
        self.input: Optional[str] = None
        self.add_item(self.title_input)

    async def on_submit(
        self, interaction: discord.Interaction[Rodhaj]
    ) -> Optional[str]:
        self.input = self.title_input.value
        await interaction.response.send_message(
            f"The title of the ticket is set to: `{self.title_input.value}`",
            ephemeral=True,
        )
        return self.input


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
        self.triggered = asyncio.Event()
        self.pool = self.bot.pool
        self._modal = None

    async def delete_response(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_response()

        self.stop()

    @discord.ui.button(label="Set Title", style=discord.ButtonStyle.blurple, row=1)
    async def set_title(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self._modal = TicketTitleModal(self.ctx)
        await interaction.response.send_modal(self._modal)

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

        # TODO: Probably add user config defaults instead
        thread_display_id = uuid.uuid4()
        thread_name = f"{author.display_name} | {thread_display_id}"
        title = self._modal.input if self._modal and self._modal.input else thread_name
        ticket = TicketThread(
            title=title,
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

        if self.message:
            self.triggered.set()

            embed = discord.Embed(
                title="\U0001f3ab Ticket created",
                color=discord.Color.from_rgb(124, 252, 0),
            )
            embed.description = "The ticket has been successfully created. Please continue to DM Rodhaj in order to send the message to the ticket, where an assigned staff will help you."
            await self.message.edit(embed=embed, view=None, delete_after=15.0)

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
        # There is a bug here, where the message first gets edited and the timeout gets called
        # thus editing an unknown message
        # ---
        # In order to fix the issue with the invalid message,
        # an event called triggered is used. This asyncio.Event
        # is used in order to determine whether the event was triggered
        # and if it is not, that means that it truly is an actual timeout that caused it
        # not the user confirming and then the timeout being called later
        if self.message and self.triggered.is_set() is False:
            embed = ErrorEmbed()
            embed.title = "\U00002757 Timed Out"
            embed.description = (
                "Timed out waiting for a response. Not creating a ticket. "
                "In order to create a ticket, please resend your message and properly confirm"
            )
            await self.message.edit(embed=embed, view=None, delete_after=15.0)
            return
