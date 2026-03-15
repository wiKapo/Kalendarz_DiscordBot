from cogs.event.util import *


async def event_delete(interaction: discord.Interaction, event_id: int | None):
    if not await check_if_calendar_exists(interaction): return

    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
    logger = get_logger(LogType.CALENDAR, calendar.id)

    if event_id is None:
        events = fetch_events_by_channel(interaction.guild_id, interaction.channel_id)
        if events:
            logger.info(f"Sending delete events modal in [{interaction.guild.name} - {interaction.guild.id}]"
                        f" in [{interaction.channel.name} - {interaction.channel.id}]")
            await interaction.response.send_modal(DeleteEventsModal(events))
        else:
            logger.info(f"No available events found in the calendar")
            await interaction.response.send_message("Brak dostępnych wydarzeń w tym kalendarzu.", ephemeral=True)
    else:
        logger.info(f"Deleting event number {event_id} from [{interaction.guild.name} - {interaction.guild.id}]"
              f" [{interaction.channel.name} - {interaction.channel.id}]")

        calendar = Calendar()
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)

        event = Event()
        event.fetch_local(event_id, interaction.guild_id, interaction.channel_id)
        logger.info(f"Deleting event {repr(event)}")
        event.delete()
        logger.info("Deleted this event from the database")

        await update_calendar(interaction, calendar)

        await interaction.response.send_message(f'Wydarzenie numer {event_id} zostało usunięte', ephemeral=True)


class DeleteEventsModal(discord.ui.Modal):
    def __init__(self, events: list[Event]):
        super().__init__(title="Usuń wydarzenia")

        options = format_event_entries(events)
        self.event_select = discord.ui.Select(options=options, max_values=len(options), required=True)
        self.add_item(discord.ui.Label(text="Wybierz wydarzenia do usunięcia", component=self.event_select))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        calendar = Calendar()
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
        logger = get_logger(LogType.CALENDAR, calendar.id)
        events = fetch_events_by_calendar(calendar.id)

        events_to_delete = [events[int(i)] for i in self.event_select.values]
        logger.info(f"Deleting events {events_to_delete}")

        for event in events_to_delete:
            create_event_delete_message(event)
            event.delete()

        await update_calendar(interaction, calendar)
        logger.info(f"Deleted events")

        if len(self.event_select.values) > 1:
            await interaction.response.send_message(f'Wydarzenia zostały usunięte', ephemeral=True)
        else:
            await interaction.response.send_message(f'Wydarzenie zostało usunięte', ephemeral=True)
