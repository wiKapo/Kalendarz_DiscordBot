import discord

from cogs.event.classes import EventAddModal
from g.classes.calendar import fetch_calendars_in_guild
from g.classes.event import Event


async def event_add(interaction: discord.Interaction):
    calendars = []
    for calendar in fetch_calendars_in_guild(interaction.guild_id):
        calendar.channelName = (await interaction.guild.fetch_channel(calendar.channelId)).name
        calendars.append(calendar)

    event = Event()
    await interaction.response.send_modal(EventAddModal(event, calendars))
