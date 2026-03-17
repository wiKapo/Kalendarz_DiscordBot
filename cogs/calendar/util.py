from g.util import *
# noinspection PyUnusedImports
from datetime import datetime


async def recreate_calendar(interaction: discord.Interaction, calendar: Calendar):
    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info("Recreating calendar on this channel")
    new_msg = await interaction.channel.send("Nowa wiadomość kalendarza")
    logger.info(f"New calendar message created: {new_msg.id}")
    calendar.messageId = new_msg.id
    calendar.update()
    logger.info("Calendar updated in the database")

    await update_calendar(interaction, calendar)

    await interaction.response.send_message("Odtworzono kalendarz.", ephemeral=True)
    logger.info("Calendar is recreated")


async def update_notification_buttons(bot: Bot, interaction: discord.Interaction, calendar: Calendar):
    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info(f"Updating notification buttons for calendar number {calendar.id}"
                f" in [{interaction.guild.name} - {interaction.guild.id}]"
                f" in [{interaction.channel.name} - {interaction.channel.id}]")

    actions = [send_notification_add, send_notification_list, send_notification_delete]

    from g.discord_classes import NotificationButtonsView
    await (await interaction.channel.fetch_message(calendar.messageId)).edit(view=NotificationButtonsView(bot, actions))
    logger.info("Finished updating notification buttons")
