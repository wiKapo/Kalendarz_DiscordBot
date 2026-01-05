from cogs.calendar.util import *


async def calendar_update(interaction: discord.Interaction):
    calendar_id = await check_if_calendar_exists(interaction)
    if calendar_id is None: return

    await update_calendar(interaction, calendar_id)

    await interaction.response.send_message('Kalendarz został zaktualizowany', ephemeral=True)
