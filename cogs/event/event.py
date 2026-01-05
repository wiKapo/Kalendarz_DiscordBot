import discord
from discord.ext import commands

from cogs.event.add import event_add
from cogs.event.delete import event_delete
from cogs.event.edit import event_edit
from g.util import *


# TODO add error handling
class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    event_group = discord.app_commands.Group(name="event", description="Komendy do zarządzania wydarzeniami")

    @event_group.command(name="add", description="Dodaje nowe wydarzenie")
    @discord.app_commands.check(check_user)
    async def add(self, interaction: discord.Interaction):
        await event_add(interaction)

    @event_group.command(name="edit", description="Zmienia wydarzenie")
    @discord.app_commands.describe(event_id="Numer wydarzenia do edycji (od najstarszego / od góry)")
    @discord.app_commands.check(check_user)
    async def edit(self, interaction: discord.Interaction, event_id: int | None):
        await event_edit(interaction, event_id)

    @event_group.command(name="delete", description="Usuwa wydarzenia")
    @discord.app_commands.describe(event_id="Numer wydarzenia do usunięcia (od najstarszego / od góry)")
    @discord.app_commands.check(check_user)
    async def delete(self, interaction: discord.Interaction, event_id: int | None):
        await event_delete(interaction, event_id)


async def setup(bot):
    await bot.add_cog(EventCog(bot))
