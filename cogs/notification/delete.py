from datetime import datetime

import discord
from discord import Interaction

from g.classes.calendar import Calendar
from g.classes.db import Db
from g.classes.event import Event
from g.classes.logger import LogType, get_logger
from g.classes.notification import fetch_notifications_by_event
from g.discord_classes import SelectEventView
from g.util import check_if_calendar_exists


async def notification_delete(interaction: Interaction):
    if not await check_if_calendar_exists(interaction):
        return

    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)

    logger = get_logger(LogType.USER, interaction.user.id)
    logger.info(f"Deleting notifications in [{interaction.guild.name} - {interaction.guild_idid}]"
                f"in [{interaction.channel.name} - {interaction.channel_id}]")

    events = [event for event in calendar.fetch_events() if event.timestamp > datetime.now().timestamp()]  # TODO check me
    if events:
        logger.info(f"Showing event select form")
        await interaction.response.send_message(
            view=SelectEventView(events, "Wybierz wydarzenie", send_delete_notification_modal), ephemeral=True)
    else:
        logger.info(f"No available events found in the calendar")
        await interaction.response.send_message("Brak dostępnych wydarzeń w tym kalendarzu.", ephemeral=True)


async def send_delete_notification_modal(interaction: discord.Interaction, events: list[Event], values: list[str]):
    event = events[int(values[0])]
    notifications = fetch_notifications_by_event(interaction.user.id, event.id)
    if notifications:
        await interaction.response.send_modal(DeleteNotificationModal(events[int(values[0])], interaction.user.id))
    else:
        await interaction.response.send_message("Nie masz żadnych powiadomień dotyczących tego wydarzenia",
                                                ephemeral=True)


class DeleteNotificationModal(discord.ui.Modal):
    event: Event

    def __init__(self, event: Event, user_id: int):
        self.event = event
        super().__init__(title="Usuń powiadomienia")
        amount_of_notifications = Db().fetch_one("SELECT COUNT(*) FROM notifications WHERE EventId = ? AND UserId = ?",
                                                 (event.id, user_id))[0]
        if amount_of_notifications == 1:
            text = "Usuwasz 1 powiadomienie"
        elif 1 < amount_of_notifications < 5:
            text = f"Usuwasz {amount_of_notifications} powiadomienia"
        else:
            text = f"Usuwasz {amount_of_notifications} powiadomień"

        self.add_item(discord.ui.TextDisplay(f"{text} z wydarzenia:\n{event}\n\n"
                                             "Potwierdź wybierając przycisk `Wyślij`"))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        logger = get_logger(LogType.USER, interaction.user.id)
        logger.info(f"Deleting notifications for event id {self.event.id}")
        Db().execute("DELETE FROM notifications WHERE UserId = ? AND EventId = ?", (interaction.user.id, self.event.id))
