from cogs.event.util import *
from cogs.event.classes import EventEditModal
from cogs.event.classes import SelectEventView

async def event_edit(interaction: discord.Interaction, event_id: int | None):
    if not await check_if_calendar_exists(interaction): return

    print(f"[INFO]\tTrying to edit events in [{interaction.guild.name} - {interaction.guild.id}]"
          f" in [{interaction.channel.name} - {interaction.channel.id}]")
    try:
        if event_id is not None:
            if not await check_if_event_id_exists(interaction, event_id): return

            print(f"[INFO]\tEditing event number {event_id}")
            await interaction.response.send_modal(EventEditModal(interaction, event_id))
        else:
            if Db().fetch_one(
                    "SELECT COUNT(events.Id) FROM events JOIN calendars ON events.CalendarId = calendars.Id "
                    "WHERE GuildId = ? AND ChannelId = ?", (interaction.guild.id, interaction.channel.id))[0] > 0:
                print("[INFO]\tShowing event select form")
                await interaction.response.send_message(
                    view=SelectEventView(interaction, "Wybierz wydarzenie do edytowania", EventEditModal),
                    ephemeral=True)
            else:
                print("[INFO]\tNo events found in the calendar")
                await interaction.response.send_message("Brak wydarzeń do edycji w tym kalendarzu.", ephemeral=True)
    except Exception as e:
        print(f"[ERROR]\tInternal error: {e}")
        await interaction.response.send_message('Błąd wewnętrzny Uh Oh', ephemeral=True)
