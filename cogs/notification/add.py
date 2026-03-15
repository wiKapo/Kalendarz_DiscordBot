from datetime import datetime

from cogs.notification.classes import AddNotificationModal, send_add_notification_modal
from g.discord_classes import SelectEventView
from g.util import *


async def notification_add(interaction: discord.Interaction, event_id: int | None):
    if not await check_if_calendar_exists(interaction): return

    logger = get_logger(LogType.USER, interaction.user.id)
    logger.info(f"Modifying notifications in [{interaction.guild.name} - {interaction.guild.id}]"
                f" in [{interaction.channel.name} - {interaction.channel.id}]")

    if event_id is None:
        events = remove_old_events(fetch_events_by_channel(interaction.guild_id, interaction.channel_id),
                                   int(datetime.now().timestamp()))

        if events:
            logger.info(f"Showing event select form")
            await interaction.response.send_message(
                view=SelectEventView(events, "Wybierz wydarzenie", send_add_notification_modal), ephemeral=True)
        else:
            logger.info(f"No available events found in the calendar")
            await interaction.response.send_message("Brak dostępnych wydarzeń w tym kalendarzu.", ephemeral=True)
    else:
        event = Event()
        event.fetch_local(event_id, interaction.guild_id, interaction.channel_id)
        logger.info(f"Showing notification edit modal for event {repr(event)}")
        await interaction.response.send_modal(AddNotificationModal(event, interaction.user.id))
