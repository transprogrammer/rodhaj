from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING, Optional

import discord
from libs.tickets.structs import ReservedTags, TicketThread
from libs.utils import Embed, ErrorEmbed, RoboModal, RoboView

from .utils import register_user, safe_content

if TYPE_CHECKING:
    from libs.utils.context import RoboContext

    from bot.cogs.config import Config
    from bot.cogs.tickets import Tickets
    from bot.rodhaj import Rodhaj


# Note that these emoji codepoints appear a lot:
# \U00002705 - U+2705 White Heavy Check Mark
# \U0000274c - U+274c Cross Mark
class TicketTitleModal(RoboModal, title="Ticket Title"):
    def __init__(self, ctx: RoboContext, ticket_cog: Tickets, *args, **kwargs):
        super().__init__(ctx=ctx, *args, **kwargs)

        self.title_input = discord.ui.TextInput(
            label="Title",
            style=discord.TextStyle.long,
            placeholder="Input a title...",
            min_length=20,
            max_length=100,
        )
        self.input: Optional[str] = None
        self.ticket_cog = ticket_cog
        self.add_item(self.title_input)

    async def on_submit(
        self, interaction: discord.Interaction[Rodhaj]
    ) -> Optional[str]:
        self.input = self.title_input.value
        self.ticket_cog.in_progress_tickets[interaction.user.id].title.set()
        await interaction.response.send_message(
            f"The title of the ticket is set to:\n`{self.title_input.value}`",
            ephemeral=True,
        )
        return self.input


class TicketTagsSelect(discord.ui.Select):
    def __init__(self, tickets_cog: Tickets):
        options = [
            discord.SelectOption(
                label="Question",
                value="question",
                description="Represents one or more question",
                emoji=discord.PartialEmoji(name="\U00002753"),
            ),
            discord.SelectOption(
                label="Serious",
                value="serious",
                description="Represents a serious concern or question(s)",
                emoji=discord.PartialEmoji(name="\U0001f610"),
            ),
            discord.SelectOption(
                label="Private",
                value="private",
                description="Represents a private concern or matter",
                emoji=discord.PartialEmoji(name="\U0001f512"),
            ),
        ]
        super().__init__(
            placeholder="Select a tag...",
            min_values=1,
            max_values=3,
            options=options,
            row=0,
        )
        self.tickets_cog = tickets_cog
        self.prev_selected: Optional[set] = None

    def tick(self, status) -> str:
        if status is True:
            return "\U00002705"
        return "\U0000274c"

    async def callback(self, interaction: discord.Interaction[Rodhaj]) -> None:
        values = self.values
        in_progress_tag = self.tickets_cog.reserved_tags.get(interaction.user.id)
        if in_progress_tag is None:
            await interaction.response.send_message(
                "Are there really any tags cached?", ephemeral=True
            )
            return

        output_tag = ReservedTags(question=False, serious=False, private=False)

        if interaction.user.id in self.tickets_cog.reserved_tags:
            output_tag = in_progress_tag

        current_selected = set(self.values)

        if self.prev_selected is not None:
            missing = self.prev_selected - current_selected
            added = current_selected - self.prev_selected

            combined = missing.union(added)

            for tag in combined:
                output_tag[tag] = not in_progress_tag[tag]
        else:
            for tag in values:
                output_tag[tag] = not in_progress_tag[tag]

        self.tickets_cog.reserved_tags[interaction.user.id] = output_tag
        self.tickets_cog.in_progress_tickets[interaction.user.id].tags.set()
        self.prev_selected = set(self.values)
        formatted_str = "\n".join(
            f"{self.tick(v)} - {k.title()}" for k, v in output_tag.items()
        )
        result = f"The following have been modified:\n\n{formatted_str}"

        embed = Embed(title="Modified Tags")
        embed.description = result
        embed.set_footer(text="\U00002705 = Selected | \U0000274c = Unselected")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class TicketConfirmView(RoboView):
    def __init__(
        self,
        attachments: list[discord.Attachment],
        bot: Rodhaj,
        ctx: RoboContext,
        cog: Tickets,
        config_cog: Config,
        content: str,
        guild: discord.Guild,
        delete_after: bool = True,
    ) -> None:
        super().__init__(ctx=ctx, timeout=300.0)
        self.attachments = attachments
        self.bot = bot
        self.ctx = ctx
        self.cog = cog
        self.config_cog = config_cog
        self.content = content
        self.guild = guild
        self.delete_after = delete_after
        self.triggered = asyncio.Event()
        self.pool = self.bot.pool
        self._modal = None
        self.add_item(TicketTagsSelect(cog))

    def tick(self, status) -> str:
        if status is True:
            return "\U00002705"
        return "\U0000274c"

    async def delete_response(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.delete_after:
            await interaction.delete_original_response()

        self.stop()

    async def get_or_fetch_member(self, member_id: int) -> Optional[discord.Member]:
        member = self.guild.get_member(member_id)
        if member is not None:
            return member

        members = await self.guild.query_members(
            limit=1, user_ids=[member_id], cache=True
        )
        if not members:
            return None
        return members[0]

    @discord.ui.button(
        label="Checklist",
        style=discord.ButtonStyle.primary,
        emoji=discord.PartialEmoji(name="\U00002753"),
        row=1,
    )
    async def see_checklist(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        status = self.cog.in_progress_tickets.get(interaction.user.id)

        if status is None:
            await interaction.response.send_message(
                "Unable to view checklist", ephemeral=True
            )
            return

        dict_status = {"title": status.title, "tags": status.tags}
        formatted_status = "\n".join(
            f"{self.tick(v.is_set())} - {k.title()}" for k, v in dict_status.items()
        )

        embed = Embed()
        embed.title = "\U00002753 Status Checklist"
        embed.description = f"The current status is shown below:\n\n{formatted_status}"
        embed.set_footer(text="\U00002705 = Completed | \U0000274c = Incomplete")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Set Title",
        style=discord.ButtonStyle.primary,
        emoji=discord.PartialEmoji(name="\U0001f58b"),
        row=1,
    )
    async def set_title(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self._modal = TicketTitleModal(self.ctx, self.cog)
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

        thread_display_id = uuid.uuid4()
        thread_name = f"{author.display_name} | {thread_display_id}"
        title = self._modal.input if self._modal and self._modal.input else thread_name

        tags = self.cog.reserved_tags.get(interaction.user.id)
        status = self.cog.in_progress_tickets.get(interaction.user.id)
        if tags is None or status is None:
            await interaction.response.send_message(
                "Unable to obtain reserved tags and in progress tags",
                ephemeral=True,
            )
            return

        applied_tags = [k for k, v in tags.items() if v is True]

        guild_settings = await self.config_cog.get_guild_settings(self.guild.id)
        potential_member = await self.get_or_fetch_member(author.id)

        if not guild_settings:
            await interaction.response.send_message(
                "Unable to find guild settings", ephemeral=True
            )
            return

        if (self.guild.created_at - interaction.created_at) < guild_settings.guild_age:
            await interaction.response.send_message(
                "The guild is too young in order to utilize Rodhaj.",
                ephemeral=True,
            )
            return
        elif potential_member:  # Since we are checking join times, if we don't have the proper member, we can only skip it.
            joined_at = potential_member.joined_at or discord.utils.utcnow()
            if (joined_at - interaction.created_at) < guild_settings.account_age:
                await interaction.response.send_message(
                    "This account joined the server too soon in order to utilize Rodhaj.",
                    ephemeral=True,
                )
            return

        if not status.title.is_set() or not status.tags.is_set():
            dict_status = {"title": status.title, "tags": status.tags}
            formatted_status = "\n".join(
                f"{self.tick(v.is_set())} - {k.title()}" for k, v in dict_status.items()
            )

            embed = ErrorEmbed()
            embed.title = "\U00002757 Unfinished Ticket"
            embed.description = (
                "Hold up! It seems like you have an unfinished ticket! "
                "It's important to have a finished ticket "
                "as it allows staff to work more efficiently. "
                "Please refer to the checklist given below for which parts "
                "that are incomplete.\n\n"
                f"{formatted_status}"
                "\n\nNote: In order to know, refer to the status checklist. "
                'This can be found by clicking the "See Checklist" button. '
            )
            embed.set_footer(text="\U00002705 = Complete | \U0000274c = Incomplete")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        files = [await attachment.to_file() for attachment in self.attachments]
        ticket = TicketThread(
            title=title,
            user=author,
            location_id=self.guild.id,
            mention=guild_settings.mention,
            content=self.content,
            tags=applied_tags,
            files=files,
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

        self.cog.reserved_tags.pop(self.ctx.author.id, None)
        self.cog.in_progress_tickets.pop(self.ctx.author.id, None)

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
