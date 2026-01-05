from cogs.event.classes import EventEditModal
from cogs.event.util import *


async def event_add(interaction: discord.Interaction):
    if not await check_if_calendar_exists(interaction): return

    print(f"[INFO]\tAdding event in [{interaction.guild.name} - {interaction.guild.id}]"
          f" in [{interaction.channel.name} - {interaction.channel.id}]")
    try:
        await interaction.response.send_modal(EventEditModal(interaction))
    except Exception as e:
        await interaction.response.send_message('Błąd przy wysyłaniu modala', ephemeral=True)
        print(f"ERROR {e}")
