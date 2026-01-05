from cogs.calendar.util import update_calendar
from cogs.event.classes import DeleteEventsModal
from cogs.event.util import *

async def event_delete(interaction: discord.Interaction, event_id: int | None):
    if not await check_if_calendar_exists(interaction): return

    if event_id is None:
        print("Sending delete events modal")
        await interaction.response.send_modal(DeleteEventsModal(interaction))
    else:
        print(f"[INFO]\tDeleting event number {event_id} from [{interaction.guild.name} - {interaction.guild.id}]"
              f" [{interaction.channel.name} - {interaction.channel.id}]")
        calendar_id = Db().fetch_one("SELECT Id FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                                     (interaction.guild.id, interaction.channel.id))[0]

        Db().execute(
            "DELETE FROM events WHERE Id = (SELECT Id FROM events WHERE CalendarId = ? "
            "ORDER BY Timestamp LIMIT 1 OFFSET ?)", (calendar_id, event_id - 1))

        await update_calendar(interaction, calendar_id)

        await interaction.response.send_message(f'Wydarzenie numer {event_id} zostało usunięte', ephemeral=True)
