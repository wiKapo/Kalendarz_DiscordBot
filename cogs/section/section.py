import discord
from discord.ext import commands

from cogs.section.add import section_add
from cogs.section.delete import section_delete
from cogs.section.edit import section_edit
from g.util import check_user, send_error_message


class SectionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    section_group = discord.app_commands.Group(name="section", description="Polecenia niestandardowych sekcji")

    @section_group.command(name="add", description="Stwórz niestandardową sekcję do kalendarza")
    @discord.app_commands.describe(calendar_id="Numer id kalendarza")
    @discord.app_commands.check(check_user)
    async def add(self, interaction: discord.Interaction, calendar_id: int | None):
        await section_add(interaction, calendar_id)

    @add.error
    async def add_error(self, interaction: discord.Interaction, error):
        await send_error_message(interaction, error)

    @section_group.command(name="edit", description="Edytuj niestandardową sekcję")
    @discord.app_commands.describe(calendar_id="Numer id kalendarza")
    @discord.app_commands.check(check_user)
    async def edit(self, interaction: discord.Interaction, calendar_id: int | None):
        await section_edit(interaction, calendar_id)

    @edit.error
    async def edit_error(self, interaction: discord.Interaction, error):
        await send_error_message(interaction, error)

    @section_group.command(name="delete", description="Usuń niestandardową sekcję z kalendarza")
    @discord.app_commands.describe(calendar_id="Numer id kalendarza")
    @discord.app_commands.check(check_user)
    async def delete(self, interaction: discord.Interaction, calendar_id: int | None):
        await section_delete(interaction, calendar_id)

    @delete.error
    async def delete_error(self, interaction: discord.Interaction, error):
        await send_error_message(interaction, error)


async def setup(bot):
    await bot.add_cog(SectionCog(bot))
