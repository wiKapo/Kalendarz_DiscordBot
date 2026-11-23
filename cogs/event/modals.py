import copy
from collections.abc import Callable

import discord

from g.classes.calendar import Calendar
from g.classes.event import Event
from g.discord_classes import format_calendar_options


class EventModal(discord.ui.Modal):

    def __init__(self, calendars: list[Calendar], action: Callable, event: Event | None = None,
                 selected_calendar_id: int | None = None):
        self.event = event or None
        self.action = action
        super().__init__(title="Dodaj wydarzenie")
        selected_calendar_id = self.event.calendarIds if self.event else \
            {selected_calendar_id} if selected_calendar_id else None
        self.calendar_select = discord.ui.Select(options=format_calendar_options(calendars, selected_calendar_id),
                                                 max_values=len(calendars))
        self.add_item(discord.ui.Label(text="Do których kalendarzy przypisać wydarzenie?",
                                       component=self.calendar_select))

        self.name_input = discord.ui.TextInput(placeholder="Podaj nazwę wydarzenia",
                                               default=self.event.name if self.event else None)
        self.add_item(discord.ui.Label(text="Nazwa", component=self.name_input))

        self.datetime_input = discord.ui.TextInput(placeholder="Podaj datę i/lub godzinę",
                                                   default=self.event.datetime if self.event else None)
        self.add_item(discord.ui.Label(text="Data i czas", component=self.datetime_input,
                                       description="Format: `dd.mm<.yyyy> <hh:mm>`"))

        self.team_input = discord.ui.TextInput(placeholder="Podaj grupę (np. 1, 3B)", required=False,
                                               default=self.event.team if self.event else None)
        self.add_item(discord.ui.Label(text="Grupa", component=self.team_input))

        self.place_input = discord.ui.TextInput(placeholder="Podaj miejsce wydarzenia", required=False,
                                                default=self.event.place if self.event else None)
        self.add_item(discord.ui.Label(text="Miejsce", component=self.place_input,
                                       description="Umieść link w <>, aby nie dołączać embedu do wiadomości kalendarza"))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        new_event = copy.deepcopy(self.event) if self.event else Event()

        new_event.name = self.name_input.value
        new_event.set_datetime(self.datetime_input.value)
        new_event.team = self.team_input.value
        new_event.place = self.place_input.value
        new_event.calendarIds = set(map(lambda x: int(x), self.calendar_select.values))

        await self.action(interaction=interaction, new_event=new_event, old_event=self.event)
