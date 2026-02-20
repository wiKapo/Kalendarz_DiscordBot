from cogs.calendar.util import update_calendar
from cogs.event.classes import DeleteEventsModal
from cogs.event.util import *


async def event_delete(interaction: discord.Interaction, event_id: int | None):
    if not await check_if_calendar_exists(interaction): return

    if event_id is None:
        print("Sending delete events modal")
        events = fetch_events_by_channel(interaction.guild_id, interaction.channel_id)
        await interaction.response.send_modal(DeleteEventsModal(events))
    else:
        print(f"[INFO]\tDeleting event number {event_id} from [{interaction.guild.name} - {interaction.guild.id}]"
              f" [{interaction.channel.name} - {interaction.channel.id}]")

        calendar = Calendar()
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)

        event = Event()
        event.fetch_local(event_id, interaction.guild_id, interaction.channel_id)
        event.delete()

        await update_calendar(interaction, calendar)

        await interaction.response.send_message(f'Wydarzenie numer {event_id} zostało usunięte', ephemeral=True)
