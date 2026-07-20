from datetime import datetime

from discord import Interaction

from cogs.notification.classes import send_delete_notification_modal
from g.classes.event import remove_old_events, fetch_events_by_channel
from g.classes.logger import LogType, get_logger
from g.discord_classes import SelectEventView
from g.util import check_if_calendar_exists


async def notification_delete(interaction: Interaction):
    if not await check_if_calendar_exists(interaction): return

    logger = get_logger(LogType.USER, interaction.user.id)
    logger.info(f"Deleting notifications in [{interaction.guild.name} - {interaction.guild.id}]"
                f"in [{interaction.channel.name} - {interaction.channel.id}]")

    events = remove_old_events(fetch_events_by_channel(interaction.guild_id, interaction.channel_id),
                               int(datetime.now().timestamp()))
    if events:
        logger.info(f"Showing event select form")
        await interaction.response.send_message(
            view=SelectEventView(events, "Wybierz wydarzenie", send_delete_notification_modal), ephemeral=True)
    else:
        logger.info(f"No available events found in the calendar")
        await interaction.response.send_message("Brak dostępnych wydarzeń w tym kalendarzu.", ephemeral=True)
