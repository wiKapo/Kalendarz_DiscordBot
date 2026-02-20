from cogs.calendar.classes import EditCalendarModal
from cogs.calendar.util import *


async def calendar_edit(interaction: discord.Interaction):
    if not await check_if_calendar_exists(interaction): return

    print("[INFO]\tEditing calendar")
    try:
        calendar = Calendar()
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
        await interaction.response.send_modal(EditCalendarModal(calendar))
    except Exception as e:
        await interaction.response.send_message('Błąd wewnętrzny Uh Oh', ephemeral=True)
        print(e)
