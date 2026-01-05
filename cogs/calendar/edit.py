from cogs.calendar.classes import EditCalendarModal
from cogs.calendar.util import *


async def calendar_edit(interaction: discord.Interaction):
    if not await check_if_calendar_exists(interaction): return

    print("[INFO]\tEditing calendar")
    try:
        await interaction.response.send_modal(EditCalendarModal(interaction))
    except Exception as e:
        await interaction.response.send_message('Błąd wewnętrzny Uh Oh', ephemeral=True)
        print(e)
