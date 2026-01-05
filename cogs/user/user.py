import discord
from discord.ext import commands

from cogs.user.add import user_add
from cogs.user.list import user_list
from cogs.user.remove import user_remove
from g.util import *


class UserCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    user_group = discord.app_commands.Group(name='user', description='Komendy do zarządzania menedżerami')

    @user_group.command(name="add",
                        description="Dodaj menedżera do kalendarza na tym serwerze. Wybrana osoba dostanie wiadomość o dodaniu")
    @discord.app_commands.describe(user="Użytkownik do dodania jako menedżer")
    @discord.app_commands.check(check_admin)
    async def add(self, interaction: discord.Interaction, user: discord.User):
        await user_add(interaction, user)

    @add.error
    async def add_error(self, interaction: discord.Interaction, error):
        if await check_manager(interaction) and isinstance(error, discord.app_commands.CheckFailure):
            print(f"[INFO]\tUser {interaction.user.name} doesn't have permissions to add users")
            await interaction.response.send_message("Brak uprawnień", ephemeral=True)

    @user_group.command(name="remove", description="Usuń menedżera z tego serwera. Dostanie wiadomość o usunięciu")
    @discord.app_commands.describe(user="Użytkownik do usunięcia")
    @discord.app_commands.check(check_admin)
    async def remove(self, interaction: discord.Interaction, user: discord.User):
        await user_remove(interaction, user)

    @remove.error
    async def remove_error(self, interaction: discord.Interaction, error):
        if await check_manager(interaction) and isinstance(error, discord.app_commands.CheckFailure):
            print(f"[INFO]\tUser {interaction.user.name} doesn't have permissions to delete users")
            await interaction.response.send_message("Brak uprawnień", ephemeral=True)

    @user_group.command(name="list", description="Pokaż menedżerów dodanych do tego serwera")
    @discord.app_commands.check(check_admin)
    async def list(self, interaction: discord.Interaction):
        await user_list(interaction)

    @list.error
    async def list_error(self, interaction: discord.Interaction, error):
        if isinstance(error, discord.app_commands.CheckFailure):
            print(f"[INFO]\tUser {interaction.user.name} doesn't have permissions to show the list of users")
            await interaction.response.send_message("Brak uprawnień", ephemeral=True)
        else:
            print("XD")
            await interaction.response.send_message("Inny błąd", ephemeral=True)


async def setup(bot):
    await bot.add_cog(UserCog(bot))
