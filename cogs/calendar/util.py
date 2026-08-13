from collections.abc import Callable

import discord

from g.classes.calendar import Calendar
from g.classes.logger import get_logger, LogType


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

    if has_notification:
        calendar.delete_notification(interaction.user.id)
        await interaction.response.send_message(
            "Nie będziesz już otrzymywać powiadomień o nadchodzących wydarzeniach z tego kalendarza", ephemeral=True)
    else:
        calendar.add_notification(interaction.user.id)
        await interaction.response.send_message(
            "Będziesz otrzymywał powiadomienia o nadchodzących wydarzeniach z tego kalendarza\n"
            "Powiadomienia będą wysyłane w dniu lub dzień przed wydarzeniem.\n"
            "W niedzielę będzie wysłane większe powiadomienie, które zawierać będzie również wydarzenia z najbliższego i następnego tygodnia\n"
            "Powiadomienia będą wykonywane jako wiadomość prywatna od kalendarza, które będą przychodzić o godzinie 7:00",
            ephemeral=True)


class NotificationButton(discord.ui.Button):

    def __init__(self, label: str, style: discord.ButtonStyle, action: Callable):
        super().__init__(label=label, style=style)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.action(interaction)
        except Exception as e:
            await interaction.response.send_message(f"Błąd przy wykonywaniu akcji", ephemeral=True)
            logger = get_logger(LogType.USER, interaction.user.name)
            logger.error(f"in callback of NotificationButton in [{interaction.guild.name} - {interaction.guild.id}] "
                         f"in [{interaction.channel.name} - {interaction.channel.id}]: {e}", exc_info=True)


class NotificationButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            NotificationButton(label="Otrzymuj powiadomienia o nadchodzących wydarzeniach",
                               style=discord.ButtonStyle.primary, action=update_notification))
