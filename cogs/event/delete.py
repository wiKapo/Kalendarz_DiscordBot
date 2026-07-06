from cogs.event.util import *


async def event_delete(interaction: discord.Interaction):
    if not await check_if_calendar_exists(interaction): return

    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
    logger = get_logger(LogType.CALENDAR, calendar.id)

    events = fetch_events_by_channel(interaction.guild_id, interaction.channel_id)
    if events:
        logger.info(f"Sending delete events modal in [{interaction.guild.name} - {interaction.guild.id}]"
                    f" in [{interaction.channel.name} - {interaction.channel.id}]")
        await interaction.response.send_modal(DeleteEventsModal(events))
    else:
        logger.info(f"No available events found in the calendar")
        await interaction.response.send_message("Brak dostępnych wydarzeń w tym kalendarzu.", ephemeral=True)


class DeleteEventsModal(discord.ui.Modal):
    def __init__(self, events: list[Event]):
        super().__init__(title="Usuń wydarzenia")

        options = format_event_options(events)
        self.event_select = discord.ui.Select(options=options, max_values=len(options), required=True)
        self.add_item(discord.ui.Label(text="Wybierz wydarzenia do usunięcia", component=self.event_select))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        calendar = Calendar()
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
        logger = get_logger(LogType.CALENDAR, calendar.id)
        events = fetch_events_from_calendar(calendar.id)

        events_to_delete = [events[int(i)] for i in self.event_select.values]
        logger.info(f"Deleting events {events_to_delete}")

        for event in events_to_delete:
            create_event_delete_message(event)
            event.delete()

        await update_calendar(interaction.guild, calendar, interaction.user.name)
        logger.info(f"Deleted events")

        if self.event_select.values:
            await interaction.response.send_message(f'Wydarzenia zostały usunięte', ephemeral=True)
        else:
            await interaction.response.send_message(f'Wydarzenie zostało usunięte', ephemeral=True)
