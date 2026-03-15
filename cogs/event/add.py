from cogs.event.classes import EventEditModal
from cogs.event.util import *


async def event_add(interaction: discord.Interaction):
    if not await check_if_calendar_exists(interaction): return

    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)

    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info(f"Sending Add event modal in [{interaction.guild.name} - {interaction.guild.id}]"
                f" in [{interaction.channel.name} - {interaction.channel.id}]")

    event = Event()
    event.calendarId = calendar.id
    await interaction.response.send_modal(EventEditModal(event))
