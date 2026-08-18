import discord

from cogs.event.util import create_event_update_message
from g.classes.calendar import fetch_calendars_in_guild, Calendar, fetch_calendars_from_ids
from g.classes.event import Event
from g.classes.logger import get_logger, LogType
from g.discord_classes import format_calendar_options
from g.util import update_calendar, check_if_calendar_exists


async def event_add(interaction: discord.Interaction):
    calendar_id = await check_if_calendar_exists(interaction)
    calendars = fetch_calendars_in_guild(interaction.guild_id)
    for calendar in calendars:
        await calendar.get_additional_data(interaction.guild)

    logger = get_logger(LogType.EVENT)
    logger.info(f"Showing add event modal for {interaction.user.name} "
                f"in {interaction.guild.name} ({interaction.guild_id}) "
                f"in {interaction.channel.name} ({interaction.channel_id})")
    await interaction.response.send_modal(EventAddModal(calendars, calendar_id))


class EventAddModal(discord.ui.Modal):

    def __init__(self, calendars: list[Calendar], selected_calendar_id: int | None):
        super().__init__(title="Dodaj wydarzenie")

        selected_calendar_id = {selected_calendar_id} if selected_calendar_id else None
        self.calendar_select = discord.ui.Select(options=format_calendar_options(calendars, selected_calendar_id), max_values=len(calendars))
        self.add_item(discord.ui.Label(text="Do których kalendarzy przypisać wydarzenie?",
                                       component=self.calendar_select))

        self.name_input = discord.ui.TextInput(placeholder="Podaj nazwę wydarzenia")
        self.add_item(discord.ui.Label(text="Nazwa", component=self.name_input))

        self.datetime_input = discord.ui.TextInput(placeholder="Podaj datę i/lub godzinę")
        self.add_item(discord.ui.Label(text="Data i czas", component=self.datetime_input,
                                       description="Format: `dd.mm(.yyyy)( hh:mm)` Zamiast `:` można wpisać `.`"))

        self.team_input = discord.ui.TextInput(placeholder="Podaj grupę (np. 1, 3B)", required=False)
        self.add_item(discord.ui.Label(text="Grupa", component=self.team_input))

        self.place_input = discord.ui.TextInput(placeholder="Podaj miejsce wydarzenia", required=False)
        self.add_item(discord.ui.Label(text="Miejsce", component=self.place_input))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        event = Event()
        logger = get_logger(LogType.EVENT)

        event.name = self.name_input.value
        event.set_datetime(self.datetime_input.value)
        event.team = self.team_input.value
        event.place = self.place_input.value
        logger.info(f"{interaction.user.name} is creating new event {repr(event)}")

        # Adding new event
        event.insert()
        logger.info("Event was inserted to the database")
        event.calendarIds = set(map(lambda x: int(x), self.calendar_select.values))
        logger.debug(f"Event: {repr(event)}")
        create_event_update_message(event)

        calendars = fetch_calendars_from_ids(event.calendarIds)

        update_message: str
        if len(calendars) == 1:
            update_message = f"kalendarza o numerze {calendars[0].id}"
        else:
            update_message = f"kalendarzy o numerach: {', '.join(map(lambda x: str(x.id), calendars))}"

        await interaction.response.send_message(
            f'Dodano wydarzenie *{event.name}* do {update_message}.\n'
            f'Wydarzenia będą automatycznie usuwane po upłynięciu 1 tygodnia od dnia wydarzenia',
            ephemeral=True)

        logger.info("Sending message to user")
        for calendar in calendars:
            calendar_logger = get_logger(LogType.CALENDAR, calendar.id)
            calendar_logger.info(f"Adding new event {repr(event)}")

            event.connect_to_calendar(calendar.id)
            logger.info(f"Added this event to calendar #{calendar.id}")
            await update_calendar(interaction.guild, calendar, interaction.user.name)
        logger.info("Finished creating new event")
