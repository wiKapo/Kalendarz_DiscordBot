import copy

import discord
from discord import Interaction

from cogs.event.util import create_event_update_message
from g.classes.calendar import Calendar, fetch_calendars_in_guild, format_calendar_options
from g.classes.event import fetch_events_from_guild, Event
from g.classes.logger import LogType, get_logger
from g.discord_classes import SelectEventView
from g.util import check_if_calendar_exists, update_calendar


async def event_edit(interaction: Interaction):
    calendar_id = await check_if_calendar_exists(interaction)

    logger = get_logger(LogType.CALENDAR, -1)  # TODO !!IMPORTANT!! REWORK LOGGER
    logger.info(f"Trying to edit event in [{interaction.guild.name} - {interaction.guild_id}]"
                f" in [{interaction.channel.name} - {interaction.channel_id}]")

    if calendar_id:
        calendar = Calendar()
        calendar.fetch(calendar_id)
        events = calendar.fetch_events()
    else:
        events = fetch_events_from_guild(interaction.guild_id)

    if events:
        logger.info("Showing event select form")
        # TODO if calendar_id: show button to show all remaining events in the guild

        await interaction.response.send_message(
            view=SelectEventView(events, "Wybierz wydarzenie do edytowania", send_event_edit_modal),
            ephemeral=True)
    else:
        logger.info("No events found in this guild")
        await interaction.response.send_message("Brak wydarzeń do edycji na tym serwerze.", ephemeral=True)


async def send_event_edit_modal(interaction: discord.Interaction, events: list[Event], values: list[str]):
    event = events[int(values[0])]
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

        self.event.name = self.name_input.value
        self.event.set_datetime(self.datetime_input.value)
        self.event.team = self.team_input.value
        self.event.place = self.place_input.value
        logger = get_logger(LogType.CALENDAR, -1)  # TODO !!IMPORTANT!! REWORK LOGGER
        logger.debug(f"Old event: {repr(old_event)}")
        logger.debug(f"New event: {repr(self.event)}")

        self.event.update()
        self.event.update_calendar_connections()
        create_event_update_message(self.event, old_event)

        calendars_to_update = []

        modified_calendars_ids = old_event.calendarIds.union(set(map(lambda x: int(x), self.calendar_select.values)))
        for calendar_id in modified_calendars_ids:
            calendar = Calendar()
            calendar.fetch(int(calendar_id))
            calendars_to_update.append(calendar)

            logger.info("Edited this event in the database")

        await interaction.response.send_message(f'Wydarzenie *{self.event.name}* zostało zmienione', ephemeral=True)

        for calendar in calendars_to_update:
            await update_calendar(interaction.guild, calendar, interaction.user.name)
