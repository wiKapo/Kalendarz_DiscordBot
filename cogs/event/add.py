from cogs.event.classes import EventAddModal
from cogs.event.util import *


async def event_add(interaction: discord.Interaction):
    calendars = []
    for calendar in fetch_calendars_in_guild(interaction.guild_id):
        calendar.channelName = (await interaction.guild.fetch_channel(calendar.channelId)).name
        calendars.append(calendar)

    event = Event()
    await interaction.response.send_modal(EventAddModal(event, calendars))
