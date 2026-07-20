import discord
from discord.ext import commands

from cogs.event.add import event_add
from cogs.event.delete import event_delete
from cogs.event.edit import event_edit
from g.util import send_error_message, check_user


class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    event_group = discord.app_commands.Group(name="event.py", description="Komendy do zarządzania wydarzeniami")

    @event_group.command(name="add", description="Dodaje nowe wydarzenie")
    @discord.app_commands.check(check_user)
    async def add(self, interaction: discord.Interaction):
        await event_add(interaction)

    @add.error
    async def add_error(self, interaction: discord.Interaction, error):
        await send_error_message(interaction, error)

    @event_group.command(name="edit", description="Zmienia wydarzenie")
    @discord.app_commands.check(check_user)
    async def edit(self, interaction: discord.Interaction):
        await event_edit(interaction)

    @edit.error
    async def edit_error(self, interaction: discord.Interaction, error):
        await send_error_message(interaction, error)

    @event_group.command(name="delete", description="Usuwa wydarzenia")
    @discord.app_commands.check(check_user)
    async def delete(self, interaction: discord.Interaction):
        await event_delete(interaction)

    @delete.error
    async def delete_error(self, interaction: discord.Interaction, error):
        await send_error_message(interaction, error)


async def setup(bot):
    await bot.add_cog(EventCog(bot))
