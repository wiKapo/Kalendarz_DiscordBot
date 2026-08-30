import copy

import discord
from discord import Interaction

from g.classes.calendar import Calendar, fetch_calendars_in_guild, fetch_calendars_from_ids
from g.classes.event import fetch_events_from_guild, Event
from g.classes.logger import LogType, get_logger
from g.classes.message import Message
from g.discord_classes import format_calendar_options, UniversalSelectView, format_event_options
from g.util import check_if_calendar_exists, update_calendar


async def event_edit(interaction: Interaction, calendar_id: int | None):
    calendar_id = calendar_id or await check_if_calendar_exists(interaction)

    logger = get_logger(LogType.EVENT)
    logger.info(f"{interaction.user.name} is trying to edit event "
                f"in [{interaction.guild.name} - {interaction.guild_id}] "
                f"in [{interaction.channel.name} - {interaction.channel_id}]")

    if calendar_id:
        calendar = Calendar()
        calendar.fetch_in_guild(calendar_id, interaction.guild_id)
        if not calendar:
            await interaction.response.send_message("Kalendarz o tym numerze nie istnieje", ephemeral=True)
            logger.warning(f"Tried to delete events from calendar #{calendar_id} that does not exist in this guild")
            return
        logger.info(f"Fetching events from calendar #{calendar_id}")
        events = calendar.fetch_events()
        if not events:
            logger.info("No events found in this calendar")
            await interaction.response.send_message("Brak wydarzeń w tym kalendarzu", ephemeral=True)
            return
        events_source = f"z kalendarza #{calendar_id}"
    else:
        logger.info(f"Fetching events from guild")
        events = fetch_events_from_guild(interaction.guild_id)
        if not events:
            logger.info("No events found in this guild")
            await interaction.response.send_message("Brak wydarzeń do edycji na tym serwerze.", ephemeral=True)
            return
        events_source = "z całego serwera"

    logger.info("Showing event select form")
    await interaction.response.send_message(
        f"Wydarzenia {events_source}, posortowane od najbliższego do najdalszego",
        view=UniversalSelectView(format_event_options(events), "Wybierz wydarzenie do edytowania",
                                 send_event_edit_modal), ephemeral=True)


async def send_event_edit_modal(interaction: discord.Interaction, values: list[str]):
    event = Event()
    event.fetch(int(values[0]))
    guild_id = event.get_guild_id()
    calendars = fetch_calendars_in_guild(guild_id)
    for calendar in calendars:
        await calendar.get_additional_data(interaction.guild)

    await interaction.response.send_modal(EventEditModal(event, calendars))


class EventEditModal(discord.ui.Modal):
    event: Event

    def __init__(self, event: Event, calendars: list[Calendar]):
        self.event = event
        super().__init__(title="Edytuj wydarzenie")

        self.calendar_select = discord.ui.Select(options=format_calendar_options(calendars, self.event.calendarIds),
                                                 max_values=len(calendars))
        self.add_item(discord.ui.Label(text="Do których kalendarzy przypisać wydarzenie?",
                                       component=self.calendar_select))

        self.name_input = discord.ui.TextInput(default=event.name, placeholder="Podaj nazwę wydarzenia")
        self.add_item(discord.ui.Label(text="Nazwa", component=self.name_input))

        self.datetime_input = discord.ui.TextInput(default=event.datetime, placeholder="Podaj datę i/lub godzinę")
        self.add_item(discord.ui.Label(text="Data i czas", component=self.datetime_input,
                                       description="Format: `dd.mm(.yyyy)( hh:mm)` Zamiast `:` można wpisać `.`"))

        self.team_input = discord.ui.TextInput(default=event.team, placeholder="Podaj grupę (np. 1, 3B)",
                                               required=False)
        self.add_item(discord.ui.Label(text="Grupa", component=self.team_input))

        self.place_input = discord.ui.TextInput(default=event.place, placeholder="Podaj miejsce wydarzenia",
                                                required=False)
        self.add_item(discord.ui.Label(text="Miejsce", component=self.place_input))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        old_event = copy.deepcopy(self.event)
        user_loggers = get_logger(LogType.USER, interaction.user.name)
        user_loggers.info(f"Editing event {self.event.id}")
        logger = get_logger(LogType.EVENT, self.event.id)
        logger.info(f"{interaction.user.name} is editing this event")

        self.event.name = self.name_input.value
        self.event.set_datetime(self.datetime_input.value)
        self.event.team = self.team_input.value
        self.event.place = self.place_input.value
        logger.debug(f"Old event: {repr(old_event)}")
        logger.debug(f"New event: {repr(self.event)}")

        if old_event == self.event:
            logger.info("No changes were made to the event")
            await interaction.response.send_message("Nie wprowadzono zmian do wydarzenia", ephemeral=True)
            return

        self.event.update()

        self.event.calendarIds = set(map(lambda x: int(x), self.calendar_select.values))
        self.event.update_calendar_connections()
        create_event_update_message(self.event, old_event)

        modified_calendars_ids = old_event.calendarIds.union(self.event.calendarIds)
        logger.info(f"Affected calendars: {modified_calendars_ids}")
        calendars = fetch_calendars_from_ids(modified_calendars_ids)

        await interaction.response.send_message(f"Wydarzenie *{self.event.name}* zostało zmienione", ephemeral=True)

        for calendar in calendars:
            await update_calendar(interaction.guild, calendar, interaction.user.name)


def create_event_update_message(new_event: Event, old_event: Event):
    message = Message()

    for calendar_id in new_event.calendarIds.intersection(old_event.calendarIds):
        logger = get_logger(LogType.CALENDAR, calendar_id)
        logger.info(f"Changed event from {repr(old_event)} to {repr(new_event)}")
        message.calendarId = calendar_id
        message.message = compare_event_changes(new_event, old_event)
        message.insert()

    for calendar_id in old_event.calendarIds.difference(new_event.calendarIds):
        logger = get_logger(LogType.CALENDAR, calendar_id)
        logger.info(f"Deleted event {repr(old_event)}")
        message.calendarId = calendar_id
        message.message = f"Wydarzenie {old_event} zostało usunięte z tego kalendarza"
        message.insert()

    for calendar_id in new_event.calendarIds.difference(old_event.calendarIds):
        logger = get_logger(LogType.CALENDAR, calendar_id)
        logger.info(f"Added event {repr(new_event)}")
        message.calendarId = calendar_id
        message.message = f"Wydarzenie {new_event} zostało dodane do tego kalendarza"
        message.insert()


def compare_event_changes(new_event: Event, old_event: Event) -> str | None:
    if new_event == old_event:
        return None
    message = f"Zmiany w wydarzeniu **{old_event.name}**: "

    if new_event.name != old_event.name:
        message += f"| *Nazwa*: `{old_event.name}` -> `{new_event.name}` "

    if new_event.time != old_event.time:
        message += f"| *Godzina*: `{old_event.time if old_event.time else "-"}` -> `{new_event.time if new_event.time else "-"}` "

    if new_event.date != old_event.date:
        message += f"| *Data*: `{old_event.date}` -> `{new_event.date}` "

    if new_event.team != old_event.team:
        message += f"| *Grupa*: `{old_event.team if old_event.team else "-"}` -> `{new_event.team if new_event.team else "-"}` "

    if new_event.place != old_event.place:
        message += f"| *Miejsce*: `{old_event.place if old_event.place else "-"}` -> `{new_event.place if new_event.place else "-"}` "

    message += "|"

    return message
