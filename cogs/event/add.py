import discord

from cogs.event.util import create_event_update_message
from g.classes.calendar import fetch_calendars_in_guild, format_calendar_options, Calendar
from g.classes.event import Event
from g.classes.logger import get_logger, LogType
from g.util import update_calendar


async def event_add(interaction: discord.Interaction):
    calendars = []
    for calendar in fetch_calendars_in_guild(interaction.guild_id):
        calendar.channelName = (await interaction.guild.fetch_channel(calendar.channelId)).name
        calendars.append(calendar)

    event = Event()
    await interaction.response.send_modal(EventAddModal(event, calendars))


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
                                       description="Format: `dd.mm(.yyyy)( hh:mm)` Zamiast `:` można wpisać `.`"))

        self.team_input = discord.ui.TextInput(default=event.team, placeholder="Podaj grupę (np. 1, 3B)",
                                               required=False)
        self.add_item(discord.ui.Label(text="Grupa", component=self.team_input))

        self.place_input = discord.ui.TextInput(default=event.place, placeholder="Podaj miejsce wydarzenia",
                                                required=False)
        self.add_item(discord.ui.Label(text="Miejsce", component=self.place_input))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.event.name = self.name_input.value
        self.event.set_datetime(self.datetime_input.value)
        self.event.team = self.team_input.value
        self.event.place = self.place_input.value
        logger = get_logger(LogType.CALENDAR, -1)  # TODO !!IMPORTANT!! REWORK LOGGER
        logger.info("Got all data from modal")
        logger.debug(f"Event: {repr(self.event)}")

        # Adding new event
        self.event.insert()
        logger.info("Event was inserted to the database")
        self.event.fetch_id_using_raw()
        logger.info("Event id was fetched")
        create_event_update_message(self.event)
        logger.info("Created event update message")

        calendars_to_update: list[Calendar] = []

        for calendar_id in self.calendar_select.values:
            calendar = Calendar()
            calendar.fetch(int(calendar_id))

            logger.info(f"Adding new event {repr(self.event)} to calendar {repr(calendar)}")
            calendars_to_update.append(calendar)
            logger.debug(f"Calendar saved to be updated")

            self.event.connect_to_calendar(calendar.id)
            logger.info("Added this event to this calendar")

        update_message: str
        if len(calendars_to_update) == 1:
            update_message = f"kalendarza o numerze {calendars_to_update[0].id}"
        else:
            update_message = f"kalendarzy o numerach: {', '.join(map(lambda x: str(x.id), calendars_to_update))}"

        await interaction.response.send_message(
            f'Dodano wydarzenie *{self.event.name}* do {update_message}.\n'
            f'Wydarzenia będą automatycznie usuwane po upłynięciu 3 tygodni od dnia wydarzenia',
            ephemeral=True)

        for calendar in calendars_to_update:
            await update_calendar(interaction.guild, calendar, interaction.user.name)
