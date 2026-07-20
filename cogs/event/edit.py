from discord import Interaction

from cogs.event.classes import send_event_edit_modal
from g.classes.logger import LogType, get_logger
from g.classes.calendar import Calendar
from g.classes.event import fetch_events_by_channel
from g.discord_classes import SelectEventView
from g.util import check_if_calendar_exists


async def event_edit(interaction: Interaction):
    if not await check_if_calendar_exists(interaction): return

    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info(f"Trying to edit event.py in [{interaction.guild.name} - {interaction.guild.id}]"
                f" in [{interaction.channel.name} - {interaction.channel.id}]")

    events = fetch_events_by_channel(interaction.guild_id, interaction.channel_id)
    if events:
        logger.info("Showing event.py select form")
        await interaction.response.send_message(
            view=SelectEventView(events, "Wybierz wydarzenie do edytowania", send_event_edit_modal),
            ephemeral=True)
    else:
        logger.info("No events found in the calendar")
        await interaction.response.send_message("Brak wydarzeń do edycji w tym kalendarzu.", ephemeral=True)
