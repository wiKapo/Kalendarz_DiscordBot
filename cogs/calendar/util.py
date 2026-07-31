import discord
from discord.ext.commands import Bot

from g.classes.calendar import Calendar
from g.classes.logger import get_logger, LogType
from g.util import send_notification_add, send_notification_list, send_notification_delete


async def update_notification_buttons(bot: Bot, interaction: discord.Interaction, calendar: Calendar):
    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info(f"Updating notification buttons for calendar number {calendar.id}"
                f" in [{interaction.guild.name} - {interaction.guild.id}]"
                f" in [{interaction.channel.name} - {interaction.channel.id}]")

    actions = [send_notification_add, send_notification_list, send_notification_delete]

    from g.discord_classes import NotificationButtonsView
    await (await interaction.channel.fetch_message(calendar.messageId)).edit(view=NotificationButtonsView(bot, actions))
    logger.info("Finished updating notification buttons")
