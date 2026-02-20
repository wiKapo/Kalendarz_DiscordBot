from cogs.event.classes import EventEditModal, send_event_edit_modal
from cogs.event.util import *
from g.discord_classes import SelectEventView


async def event_edit(interaction: discord.Interaction, event_id: int | None):
    if not await check_if_calendar_exists(interaction): return

    print(f"[INFO]\tTrying to edit events in [{interaction.guild.name} - {interaction.guild.id}]"
          f" in [{interaction.channel.name} - {interaction.channel.id}]")
    try:
        if event_id is not None:
            if not await check_if_event_id_exists(interaction, event_id): return

            print(f"[INFO]\tEditing event number {event_id}")
            event = Event()
            event.fetch_local(event_id, interaction.guild_id, interaction.channel_id)
            await interaction.response.send_modal(EventEditModal(event))
        else:
            events = fetch_events_by_channel(interaction.guild_id, interaction.channel_id)
            if len(events) > 0:
                print("[INFO]\tShowing event select form")

                await interaction.response.send_message(
                    view=SelectEventView(events, "Wybierz wydarzenie do edytowania", send_event_edit_modal),
                    ephemeral=True)
            else:
                print("[INFO]\tNo events found in the calendar")
                await interaction.response.send_message("Brak wydarzeń do edycji w tym kalendarzu.", ephemeral=True)
    except Exception as e:
        print(f"[ERROR]\tInternal error: {e}")
        await interaction.response.send_message('Błąd wewnętrzny Uh Oh', ephemeral=True)
