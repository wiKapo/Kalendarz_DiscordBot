from cogs.calendar.classes import DeleteCalendarModal
from cogs.calendar.util import *


async def calendar_delete(interaction: discord.Interaction):
    if not await check_if_calendar_exists(interaction): return

    print("[INFO]\tDeleting calendar")
    await interaction.response.send_modal(DeleteCalendarModal())
