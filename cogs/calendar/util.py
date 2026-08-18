import discord

from g.classes.calendar import Calendar, remove_all_notifications_from_user
from g.classes.logger import get_logger, LogType
from g.discord_classes import UniversalButton


async def update_calendar_buttons(guild: discord.Guild, calendar: Calendar):
    channel = await guild.fetch_channel(calendar.channelId)

    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info(f"Updating calendar buttons for calendar number {calendar.id} "
                f"in [{guild.name} - {guild.id}] "
                f"in [{channel.name} - {channel.id}]")

    await (await channel.fetch_message(calendar.messageId)).edit(view=NotificationButtonsView())
    logger.info("Finished updating calendar buttons")


async def update_notification(interaction: discord.Interaction):
    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
    has_notification = calendar.get_notification(interaction.user.id)
    logger = get_logger(LogType.USER, interaction.user.name)

    if has_notification:
        logger.info(f"Removing notifications for calendar #{calendar.id}")
        calendar.delete_notification(interaction.user.id)
        await interaction.response.send_message(
            "Nie będziesz już otrzymywać powiadomień o nadchodzących wydarzeniach z tego kalendarza", ephemeral=True)
    else:
        logger.info(f"Adding notifications for calendar #{calendar.id}")
        calendar.add_notification(interaction.user.id)
        await interaction.response.send_message(
            "Będziesz otrzymywał powiadomienia o nadchodzących wydarzeniach z tego kalendarza\n"
            "Powiadomienia będą wysyłane w dniu lub dzień przed wydarzeniem.\n"
            "W niedzielę będzie wysłane większe powiadomienie, które zawierać będzie również wydarzenia z najbliższego i następnego tygodnia\n"
            "Powiadomienia będą wykonywane jako wiadomość prywatna od kalendarza, które będą przychodzić o godzinie 7:00",
            ephemeral=True)


class NotificationButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            UniversalButton(label="Otrzymuj powiadomienia o nadchodzących wydarzeniach",
                            style=discord.ButtonStyle.primary, action=update_notification))


async def remove_notification(interaction: discord.Interaction):
    logger = get_logger(LogType.USER, interaction.user.name)
    logger.info("Removing notifications for all calendars")
    remove_all_notifications_from_user(interaction.user.id)
    logger.info("Removed all notifications")
    await interaction.response.send_message("Nie będziesz już otrzymywać powiadomień z kalendarzy", ephemeral=True)


class DMNotificationButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(UniversalButton(label="Zrezygnuj z powiadomień kalendarza", style=discord.ButtonStyle.secondary,
                                      action=remove_notification))
