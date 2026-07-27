import copy

import discord

from cogs.event.util import create_event_update_message
from g.classes.calendar import Calendar, format_calendar_options
from g.classes.event import Event
from g.classes.logger import LogType, get_logger
from g.util import update_calendar


class EventEditLabel(discord.ui.Label):
    def __init__(self, text: str, required: bool, default: str, placeholder: str):
        super().__init__(text=text,
                         component=discord.ui.TextInput(required=required, default=default, placeholder=placeholder))


class EventAddModal(discord.ui.Modal):
    event: Event

    def __init__(self, event: Event, calendars: list[Calendar]):
        self.event = event
        super().__init__(title="Dodaj wydarzenie")

        self.calendar_select = discord.ui.Select(options=format_calendar_options(calendars), max_values=len(calendars))
        self.add_item(discord.ui.Label(text="Do których kalendarzy przypisać wydarzenie?",
                                       component=self.calendar_select))

        self.name_input = discord.ui.TextInput(default=event.name, placeholder="Podaj nazwę wydarzenia")
        self.add_item(discord.ui.Label(text="Nazwa", component=self.name_input))

        self.datetime_input = discord.ui.TextInput(default="", placeholder="Podaj datę i/lub godzinę")
        self.add_item(discord.ui.Label(text="Data i czas", component=self.datetime_input,
                                       description="Format: `dd.mm(.yyyy) hh:mm` Zamiast `:` przy godzinie można wpisać `.`"))

        self.team_input = discord.ui.TextInput(default=event.team, placeholder="Podaj grupę (np. 1, 3B)",
                                               required=False)
        self.add_item(discord.ui.Label(text="Grupa", component=self.team_input))

        self.place_input = discord.ui.TextInput(default=event.place, placeholder="Podaj miejsce wydarzenia",
                                                required=False)
        self.add_item(discord.ui.Label(text="Miejsce", component=self.place_input))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.event.name = self.name_input.value
        datetime_text = self.datetime_input.value.split(" ")
        self.event.text_to_timestamp(datetime_text[1], datetime_text[0])
        self.event.team = self.team_input.value
        self.event.place = self.place_input.value
        logger = get_logger(LogType.CALENDAR, self.event.calendarId)  # TODO change to guild logger or smth

        calendars_to_update = []

        for calendar_id in self.calendar_select.values:
            calendar = Calendar()
            calendar.fetch(int(calendar_id))
            calendars_to_update.append(calendar)

            self.event.calendarId = calendar.id

            # Adding new event
            logger.info(f"Adding new event {repr(self.event)} to calendar {repr(calendar)}")

            self.event.insert()
            create_event_update_message(self.event)
            logger.info("Added this event to the database")

        await interaction.response.send_message(
            f'Dodano wydarzenie *{self.event.name}* do kalendarzy {self.calendar_select.values}.\n'
            f'Wydarzenia będą automatycznie usuwane po upłynięciu 3 tygodni od dnia wydarzenia',
            ephemeral=True)

        for calendar in calendars_to_update:
            await update_calendar(interaction.guild, calendar, interaction.user.name)


class EventEditModal(discord.ui.Modal):
    event: Event

    def __init__(self, event: Event):
        self.event = event
        super().__init__(title="Edytuj wydarzenie")

        self.name_input = discord.ui.TextInput(default=event.name, placeholder="Podaj nazwę wydarzenia")
        self.add_item(discord.ui.Label(text="Nazwa", component=self.name_input))

        if event.id is None:
            time = date = ""
        else:
            time, date = event.timestamp_to_text()
        self.date_input = discord.ui.TextInput(default=date,
                                               placeholder="Podaj datę (np. 1.12.2025 lub 6.02 [doda obecny rok])")
        self.add_item(discord.ui.Label(text="Data", component=self.date_input))

        self.time_input = discord.ui.TextInput(default=time, placeholder="Podaj godzinę (np. 12:35)", required=False)
        self.add_item(discord.ui.Label(text="Godzina", component=self.time_input))

        self.team_input = discord.ui.TextInput(default=event.team, placeholder="Podaj grupę (np. 1, 3B)",
                                               required=False)
        self.add_item(discord.ui.Label(text="Grupa", component=self.team_input))

        self.place_input = discord.ui.TextInput(default=event.place, placeholder="Podaj miejsce wydarzenia",
                                                required=False)
        self.add_item(discord.ui.Label(text="Miejsce", component=self.place_input))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        old_event = copy.deepcopy(self.event)

        self.event.name = self.name_input.value
        self.event.text_to_timestamp(self.time_input.value, self.date_input.value)
        self.event.team = self.team_input.value
        self.event.place = self.place_input.value
        logger = get_logger(LogType.CALENDAR, self.event.calendarId)
        logger.debug(f"Old event: {repr(old_event)}")
        logger.debug(f"New event: {repr(self.event)}")

        # Event exists already
        logger.info(f"Editing event {repr(self.event)}")
        self.event.update()
        create_event_update_message(self.event, old_event)
        logger.info("Edited this event in the database")
        await interaction.response.send_message(f'Wydarzenie *{self.event.name}* zostało zmienione', ephemeral=True)

        calendar = Calendar()
        calendar.fetch(self.event.calendarId)
        await update_calendar(interaction.guild, calendar, interaction.user.name)


async def send_event_edit_modal(interaction: discord.Interaction, events: list[Event], values: list[str]):
    await interaction.response.send_modal(EventEditModal(events[int(values[0])]))
