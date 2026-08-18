import copy

import discord
from discord import Interaction

from cogs.event.util import create_event_update_message
from g.classes.calendar import Calendar, fetch_calendars_in_guild, fetch_calendars_from_ids
from g.classes.event import fetch_events_from_guild, Event
from g.classes.logger import LogType, get_logger
from g.discord_classes import format_calendar_options, UniversalSelectView, format_event_options
from g.util import check_if_calendar_exists, update_calendar


async def event_edit(interaction: Interaction):
    calendar_id = await check_if_calendar_exists(interaction)

    logger = get_logger(LogType.EVENT)
    logger.info(f"{interaction.user.name} is trying to edit event "
                f"in [{interaction.guild.name} - {interaction.guild_id}] "
                f"in [{interaction.channel.name} - {interaction.channel_id}]")

    if calendar_id:
        logger.info(f"Fetching events from calendar #{calendar_id}")
        calendar = Calendar()
        calendar.fetch(calendar_id)
        events = calendar.fetch_events()
    else:
        logger.info(f"Fetching events from guild")
        events = fetch_events_from_guild(interaction.guild_id)

    if events:
        logger.info("Showing event select form")
        # TODO if calendar_id: show button to show all remaining events in the guild

        await interaction.response.send_message(
            "Wydarzenia posortowane od najbliższego do najdalszego",
            view=UniversalSelectView(format_event_options(events), "Wybierz wydarzenie do edytowania",
                                     send_event_edit_modal), ephemeral=True)
    else:
        logger.info("No events found in this guild")
        await interaction.response.send_message("Brak wydarzeń do edycji na tym serwerze.", ephemeral=True)


async def send_event_edit_modal(interaction: discord.Interaction, values: list[str]):
    events = fetch_events_from_guild(interaction.guild_id)
    event = next(event for event in events if event.id == int(values[0]))
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
        logger = get_logger(LogType.EVENT, self.event.id)
        logger.info(f"{interaction.user.name} is editing event {self.event.name}")

        self.event.name = self.name_input.value
        self.event.set_datetime(self.datetime_input.value)
        self.event.team = self.team_input.value
        self.event.place = self.place_input.value
        logger.debug(f"Old event: {repr(old_event)}")
        logger.debug(f"New event: {repr(self.event)}")

        self.event.update()
        self.event.update_calendar_connections()
        create_event_update_message(self.event, old_event)

        modified_calendars_ids = old_event.calendarIds.intersection(
            set(map(lambda x: int(x), self.calendar_select.values)))
        logger.info(f"Affected calendars: {modified_calendars_ids}")
        calendars = fetch_calendars_from_ids(modified_calendars_ids)

        await interaction.response.send_message(f'Wydarzenie *{self.event.name}* zostało zmienione', ephemeral=True)

        for calendar in calendars:
            await update_calendar(interaction.guild, calendar, interaction.user.name)
