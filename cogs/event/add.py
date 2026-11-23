import discord

from cogs.event.modals import EventModal
from g.classes.calendar import fetch_calendars_in_guild, fetch_calendars_from_ids
from g.classes.event import Event
from g.classes.logger import get_logger, LogType
from g.classes.message import Message
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
    await interaction.response.send_modal(EventModal(calendars, add_event, selected_calendar_id=calendar_id))


async def add_event(interaction: discord.Interaction, new_event: Event, old_event) -> None:
    logger = get_logger(LogType.EVENT)
    logger.info(repr(new_event))

    new_event.insert()
    logger.info(f"Event {new_event.id} created")
    event_logger = get_logger(LogType.EVENT, new_event.id)
    event_logger.info(f"Event created in {interaction.guild.name}")
    event_logger.info(repr(new_event))
    create_event_add_message(new_event)

    calendars = fetch_calendars_from_ids(new_event.calendarIds)

    update_message: str
    if len(calendars) == 1:
        update_message = f"kalendarza o numerze {calendars[0].id}"
    else:
        update_message = f"kalendarzy o numerach: {", ".join(map(lambda x: str(x.id), calendars))}"

    await interaction.response.send_message(
        f"Dodano wydarzenie *{new_event.name}* do {update_message}.\n"
        f"Wydarzenia będą automatycznie usuwane po upłynięciu 1 tygodnia od dnia wydarzenia",
        ephemeral=True)

    logger.info("Sending message to user")
    for calendar in calendars:
        calendar_logger = get_logger(LogType.CALENDAR, calendar.id)
        calendar_logger.info(f"Adding new event {repr(new_event)}")

        new_event.connect_to_calendar(calendar.id)
        logger.info(f"Added this event to calendar #{calendar.id}")
        await update_calendar(interaction.guild, calendar, interaction.user.name)
    logger.info("Finished creating new event")


def create_event_add_message(event: Event):
    message = Message()

    for calendar_id in event.calendarIds:
        logger = get_logger(LogType.CALENDAR, calendar_id)
        logger.info(f"Added new event {repr(event)}")
        message.calendarId = calendar_id
        message.message = f"Utworzono nowe wydarzenie: {event}"
        message.insert()
