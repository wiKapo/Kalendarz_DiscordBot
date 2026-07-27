from datetime import datetime

import discord

from cogs.notification.classes import send_add_notification_modal
from g.classes.calendar import Calendar
from g.classes.event import remove_old_events
from g.classes.logger import LogType, get_logger
from g.discord_classes import SelectEventView
from g.util import check_if_calendar_exists


async def notification_add(interaction: discord.Interaction):
    if not await check_if_calendar_exists(interaction):
        return

    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)

    logger = get_logger(LogType.USER, interaction.user.id)
    logger.info(f"Modifying notifications in [{interaction.guild.name} - {interaction.guild_id}]"
                f" in [{interaction.channel.name} - {interaction.channel_id}]")

    events = remove_old_events(calendar.events, int(datetime.now().timestamp()))

    if events:
        logger.info(f"Showing event select form")
        await interaction.response.send_message(
            view=SelectEventView(events, "Wybierz wydarzenie", send_add_notification_modal), ephemeral=True)
    else:
        logger.info(f"No available events found in the calendar")
        await interaction.response.send_message("Brak dostępnych wydarzeń w tym kalendarzu.", ephemeral=True)
