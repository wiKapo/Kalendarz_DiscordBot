from datetime import datetime, timedelta

import discord

from cogs.notification.util import hour_rounder, get_hours_from_tag
from g.classes.calendar import Calendar
from g.classes.db import Db
from g.classes.event import Event
from g.classes.logger import LogType, get_logger
from g.classes.notification import Notification, fetch_notifications_by_event
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

    events = [event for event in calendar.fetch_events() if event.timestamp > datetime.now().timestamp()]

    if events:
        logger.info(f"Showing event select form")
        await interaction.response.send_message(
            view=SelectEventView(events, "Wybierz wydarzenie", send_add_notification_modal), ephemeral=True)
    else:
        logger.info(f"No available events found in the calendar")
        await interaction.response.send_message("Brak dostępnych wydarzeń w tym kalendarzu.", ephemeral=True)


async def send_add_notification_modal(interaction: discord.Interaction, events: list[Event], values: list[str]):
    await interaction.response.send_modal(AddNotificationModal(events[int(values[0])], interaction.user.id))


class AddNotificationModal(discord.ui.Modal):
    event: Event
    notifications: list[Notification]
    default_time_tags = ["0", "1", "2", "1d", "1w"]

    def __init__(self, event: Event, user_id: int):
        self.event = event
        super().__init__(title="Dodaj powiadomienie")
        self.add_item(discord.ui.TextDisplay(f"Do wydarzenia: {event}"))

        self.notifications = fetch_notifications_by_event(user_id, event.id)
        selected_time_tags = [n.timeTag for n in self.notifications]
        selected_custom_time_tags = [tag for tag in selected_time_tags if tag not in self.default_time_tags]
        time_options = [
            discord.SelectOption(label="W godzinie wydarzenia", value="0", default="0" in selected_time_tags),
            discord.SelectOption(label="1 godzina wcześniej", value="1", default="1" in selected_time_tags),
            discord.SelectOption(label="2 godziny wcześniej", value="2", default="2" in selected_time_tags),
            discord.SelectOption(label="1 dzień wcześniej", value="1d", default="1d" in selected_time_tags),
            discord.SelectOption(label="1 tydzień wcześniej", value="1w", default="1w" in selected_time_tags),
            discord.SelectOption(label="Niestandardowe", value="_", default=bool(selected_custom_time_tags))]

        self.time_select = discord.ui.Select(options=time_options, max_values=len(time_options), required=True)
        self.add_item(discord.ui.Label(
            text="Wybierz czas", description="Powiadomienia są sprawdzane co godzinę (czyli o 12:00, 13:00, itd.)",
            component=self.time_select))

        self.description_input = discord.ui.TextInput(required=False,
                                                      placeholder="Dodaj opcjonalny opis do nowych powiadomień")
        self.add_item(discord.ui.Label(text="Opis powiadomień", component=self.description_input))

        self.custom_input = discord.ui.TextInput(
            placeholder="Zaznacz [Niestandardowe] w polu wyboru czasu",
            required=False,
            default=", ".join(selected_custom_time_tags) if selected_custom_time_tags else None)
        self.add_item(discord.ui.Label(
            text="Dodaj niestandardowe powiadomienia",
            description="Każdą kolejną wartość oddziel przecinkiem [,]",
            component=self.custom_input))

        self.add_item(discord.ui.TextDisplay(
            "-# Np.: `3h`=3 godziny, `3d`=3 dni, `2w`=2 tygodnie, `1d5`=dzień i 5 godzin"))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        logger = get_logger(LogType.USER, interaction.user.id)
        logger.info(f"Adding notifications for event {repr(self.event)}")
        logger.debug(f"Selected times: {self.time_select.values} | Description: {self.description_input.value}")

        event_time = hour_rounder(datetime.fromtimestamp(self.event.timestamp))
        logger.debug(f"Event time: {event_time}")

        if "_" in self.time_select.values:
            self.time_select.values.remove("_")
            if self.custom_input.value:
                self.time_select.values.extend(self.custom_input.value.replace(" ", "").split(','))
            else:
                logger.info("Did not receive custom times, skipping")

        selected_time_tags = [n.timeTag for n in self.notifications]
        for time_tag in self.time_select.values:
            if time_tag in selected_time_tags:  # do not add duplicates
                selected_time_tags.remove(time_tag)
                continue
            notification = Notification()
            notification.userId = interaction.user.id
            notification.eventId = self.event.id

            notify_time = event_time - timedelta(hours=get_hours_from_tag(time_tag))
            logger.debug(f"Notify time: {notify_time}")
            notification.timestamp = int(notify_time.timestamp())
            notification.timeTag = time_tag
            notification.description = self.description_input.value if self.description_input.value else None

        if selected_time_tags:  # if there are time tags left, remove them from the database
            logger.info(f"Removing {selected_time_tags} from database")
            for time_tag in selected_time_tags:
                notification = Notification()
                notification.userId = interaction.user.id
                notification.eventId = self.event.id
                notification.timeTag = time_tag
                notification.delete()

        logger.info("DONE")
        await interaction.response.send_message(f"Dodano powiadomienia do wydarzenia \"{self.event.name}\"",
                                                ephemeral=True)
