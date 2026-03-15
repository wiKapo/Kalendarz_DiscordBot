from cogs.event.classes import EventEditModal, send_event_edit_modal
from cogs.event.util import *
from g.discord_classes import SelectEventView


async def event_edit(interaction: discord.Interaction, event_id: int | None):
    if not await check_if_calendar_exists(interaction): return

    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info(f"Trying to edit event in [{interaction.guild.name} - {interaction.guild.id}]"
                f" in [{interaction.channel.name} - {interaction.channel.id}]")

    if event_id is not None:
        if not await check_if_event_id_exists(interaction, event_id): return

        logger.info(f"Editing event number {event_id}")
        event = Event()
        event.fetch_local(event_id, interaction.guild_id, interaction.channel_id)
        await interaction.response.send_modal(EventEditModal(event))
    else:
        events = fetch_events_by_channel(interaction.guild_id, interaction.channel_id)
        if len(events) > 0:
            logger.info("Showing event select form")
            await interaction.response.send_message(
                view=SelectEventView(events, "Wybierz wydarzenie do edytowania", send_event_edit_modal),
                ephemeral=True)
        else:
            logger.info("No events found in the calendar")
            await interaction.response.send_message("Brak wydarzeń do edycji w tym kalendarzu.", ephemeral=True)
