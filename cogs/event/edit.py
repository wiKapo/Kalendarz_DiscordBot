from discord import Interaction

from cogs.event.classes import send_event_edit_modal
from g.classes.calendar import Calendar
from g.classes.event import fetch_events_from_guild
from g.classes.logger import LogType, get_logger
from g.discord_classes import SelectEventView
from g.util import check_if_calendar_exists


async def event_edit(interaction: Interaction):
    calendar_id = await check_if_calendar_exists(interaction)

    logger = get_logger(LogType.CALENDAR, -1)  # TODO !!IMPORTANT!! REWORK LOGGER
    logger.info(f"Trying to edit event in [{interaction.guild.name} - {interaction.guild_id}]"
                f" in [{interaction.channel.name} - {interaction.channel_id}]")

    if calendar_id:
        calendar = Calendar()
        calendar.fetch(calendar_id)
        events = calendar.fetch_events()
    else:
        events = fetch_events_from_guild(interaction.guild_id)

    if events:
        logger.info("Showing event select form")
        # TODO if calendar_id: show button to show all remaining events in the guild

        await interaction.response.send_message(
            view=SelectEventView(events, "Wybierz wydarzenie do edytowania", send_event_edit_modal),
            ephemeral=True)
    else:
        logger.info("No events found in this guild")
        await interaction.response.send_message("Brak wydarzeń do edycji na tym serwerze.", ephemeral=True)
