import discord

from cogs.event.util import create_event_delete_message
from g.classes.calendar import Calendar
from g.classes.event import Event, fetch_events_from_guild
from g.discord_classes import format_event_options
from g.classes.logger import LogType, get_logger
from g.util import check_if_calendar_exists, update_calendar


async def event_delete(interaction: discord.Interaction):
    calendar_id = await check_if_calendar_exists(interaction)

    logger = get_logger(LogType.CALENDAR, -1)  # TODO !!IMPORTANT!! REWORK LOGGER
    logger.info(f"Trying to delete events in [{interaction.guild.name} - {interaction.guild_id}]"
                f" in [{interaction.channel.name} - {interaction.channel_id}]")

    if calendar_id:
        calendar = Calendar()
        calendar.fetch(calendar_id)
        events = calendar.fetch_events()
    else:
        events = fetch_events_from_guild(interaction.guild_id)

    if events:
        # TODO if calendar_id: show button to show all remaining events in the guild
        logger.info(f"Sending delete events modal in [{interaction.guild.name} - {interaction.guild.id}]"
                    f" in [{interaction.channel.name} - {interaction.channel.id}]")
        await interaction.response.send_modal(DeleteEventsModal(events))
    else:
        logger.info(f"No events found in this guild")
        await interaction.response.send_message("Brak wydarzeń na tym serwerze.", ephemeral=True)


class DeleteEventsModal(discord.ui.Modal):
    def __init__(self, events: list[Event]):
        super().__init__(title="Usuń wydarzenia")

        options = format_event_options(events)
        self.event_select = discord.ui.Select(options=options, max_values=len(options), required=True)
        self.add_item(discord.ui.Label(text="Wybierz wydarzenia do usunięcia", component=self.event_select))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        calendar = Calendar()
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
        logger = get_logger(LogType.CALENDAR, calendar.id)

        events = calendar.fetch_events()
        events_to_delete = [events[int(i)] for i in self.event_select.values]
        logger.info(f"Deleting events {events_to_delete}")

        for event in events_to_delete:
            create_event_delete_message(event)
            event.delete()

        await update_calendar(interaction.guild, calendar, interaction.user.name)
        logger.info(f"Deleted events")

        if self.event_select.values:
            await interaction.response.send_message(f'Wydarzenia zostały usunięte', ephemeral=True)
        else:
            await interaction.response.send_message(f'Wydarzenie zostało usunięte', ephemeral=True)
