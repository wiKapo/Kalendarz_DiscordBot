import discord

from cogs.event.util import create_event_delete_message
from g.classes.calendar import Calendar, fetch_calendars_from_ids
from g.classes.event import Event, fetch_events_from_guild
from g.classes.logger import LogType, get_logger
from g.discord_classes import format_event_options, UniversalSelectView
from g.util import check_if_calendar_exists, update_calendar


async def event_delete(interaction: discord.Interaction, calendar_id: int | None):
    calendar_id = calendar_id or await check_if_calendar_exists(interaction)

    logger = get_logger(LogType.EVENT)
    logger.info(f"{interaction.user.name} is trying to delete events "
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
        logger.info("Fetching events from guild")
        events = fetch_events_from_guild(interaction.guild_id)
        if not events:
            logger.info("No events found in this guild")
            await interaction.response.send_message("Brak wydarzeń na tym serwerze", ephemeral=True)
            return
        events_source = "z całego serwera"

    if len(events) <= 25:
        logger.info("Sending delete events modal")
        await interaction.response.send_modal(DeleteEventsModal(events))
    else:
        logger.info("Sending select event range form")
        options = []
        for i in range(0, len(events), 25):
            options.append(discord.SelectOption(
                label=f"Od {i} do {min(i + 25, len(events))}",
                description=f"Od {events[i].date} do {events[min(i + 25, len(events)) - 1].date}",
                value=f"{calendar_id if calendar_id else ""}.{i}.{min(i + 25, len(events))}", ))
        await interaction.response.send_message(
            f"Wybierz przedział wydarzeń {events_source}",
            view=UniversalSelectView(options, "Wybierz przedział", send_event_delete_modal),
            ephemeral=True)


async def send_event_delete_modal(interaction: discord.Interaction, values: list[str]):
    calendar_id, begin, end = list(map(lambda x: int(x), values[0].split(".")))
    if calendar_id:
        calendar = Calendar()
        calendar.fetch(calendar_id)
        events = calendar.fetch_events()[begin:end]
    else:
        events = fetch_events_from_guild(interaction.guild_id)[begin:end]
    await interaction.response.send_modal(DeleteEventsModal(events))


class DeleteEventsModal(discord.ui.Modal):
    def __init__(self, events: list[Event]):
        super().__init__(title="Usuń wydarzenia")

        self.add_item(discord.ui.TextDisplay(
            "Usuwa wydarzenia, ze **wszystkich** kalendarzy.\n"
            "Użyj `/event edit`, aby usunąć wydarzenia tylko z tego kalendarza"))

        options = format_event_options(events)  # TODO handle having more than 25 events
        self.event_select = discord.ui.Select(options=options[:25], max_values=min(len(options), 25), required=True)
        self.add_item(discord.ui.Label(text="Wybierz wydarzenia do usunięcia", component=self.event_select,
                                       description="Najbliższe 25 wydarzeń w polu wyboru" if len(
                                           options) > 25 else ""))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        logger = get_logger(LogType.EVENT)

        events = fetch_events_from_guild(interaction.guild_id)
        events_to_delete = list(filter(lambda e: e.id in list(map(lambda x: int(x), self.event_select.values)), events))
        logger.info(f"{interaction.user.name} is deleting events {events_to_delete}")

        calendar_ids = set().union(*(event.calendarIds for event in events_to_delete))
        logger.info(f"Affected calendars: {calendar_ids}")

        for event in events_to_delete:
            create_event_delete_message(event)
            event.delete()

        if self.event_select.values:
            await interaction.response.send_message(f"Wydarzenia zostały usunięte", ephemeral=True)
        else:
            await interaction.response.send_message(f"Wydarzenie zostało usunięte", ephemeral=True)

        calendars = fetch_calendars_from_ids(calendar_ids)
        for calendar in calendars:
            calendar_logger = get_logger(LogType.CALENDAR, calendar.id)
            calendar_logger.info(f"Deleted events {calendar.eventIds.intersection(events_to_delete)}")
            await update_calendar(interaction.guild, calendar, interaction.user.name)
        logger.info(f"Deleted events")
