import discord
from discord.ext import commands

from util import *


class UserCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    user_group = discord.app_commands.Group(name='user', description='Komendy do zarządzania menedżerami')

    @user_group.command(name="add", description="Dodaj menedżera do kalendarza na tym serwerze. Wybrana osoba dostanie wiadomość o dodaniu")
    @discord.app_commands.describe(user="Użytkownik do dodania jako menedżer")
    @discord.app_commands.check(check_admin)
    async def add(self, interaction: discord.Interaction, user: discord.User):
        print(f"[INFO]\tAdding user [{user.name} - {user.id}] in [{interaction.guild.name} - {interaction.guild.id}]")
        manager = Db().fetch_one("SELECT * FROM users WHERE UserId = ? AND  GuildId = ?", (user.id, interaction.guild.id))
        if manager:
            print(f"[INFO]\tUser [{user.name} - {user.id}] is already added in {interaction.guild.name}")
            await interaction.response.send_message(f"Użytkownik {user.name} jest już dodany na tym serwerze.",
                                                    ephemeral=True)
            return

        Db().execute("INSERT INTO users (UserId, GuildId) VALUES (?, ?)", (user.id, interaction.guild.id))
        await user.send(f"Dodano ciebie do listy menedżerów kalendarza na serwerze \"{interaction.guild.name}\"")

        await interaction.response.send_message(
            f'Dodano użytkownika *{user.name}* jako menedżera kalendarza na tym serwerze', ephemeral=True)

    @add.error
    async def add_error(self, interaction: discord.Interaction, error):
        if await check_manager(interaction) and isinstance(error, discord.app_commands.CheckFailure):
            print(f"[INFO]\tUser {interaction.user.name} doesn't have permissions to add users")
            await interaction.response.send_message("Brak uprawnień", ephemeral=True)

    @user_group.command(name="remove", description="Usuń menedżera z tego serwera. Dostanie wiadomość o usunięciu")
    @discord.app_commands.describe(user="Użytkownik do usunięcia")
    @discord.app_commands.check(check_admin)
    async def remove(self, interaction: discord.Interaction, user: discord.User):
        manager = Db().fetch_one("SELECT * FROM users WHERE UserId = ? AND GuildId = ?", (user.id, interaction.guild.id))
        if manager:
            print(f"[INFO]\tRemoving user [{user.name} - {user.id}] from [{interaction.guild.name} - {interaction.guild.id}]")
            Db().execute("DELETE FROM users WHERE UserId = ? AND GuildId = ?", (user.id, interaction.guild.id))
            await user.send(
                f"Usunięto ciebie z listy menedżerów kalendarza na serwerze \"{interaction.guild.name}\"")

            await interaction.response.send_message(f'Usunięto menedżera *{user.name}* z tego serwera', ephemeral=True)
        else:
            print(f"[INFO]\tUser [{user.name} - {user.id}] not found in [{interaction.guild.name} - {interaction.guild.id}]")
            await interaction.response.send_message(f'Nie znaleziono menedżera *{user.name}* na tym serwerze',
                                                    ephemeral=True)

    @remove.error
    async def remove_error(self, interaction: discord.Interaction, error):
        if await check_manager(interaction) and isinstance(error, discord.app_commands.CheckFailure):
            print(f"[INFO]\tUser {interaction.user.name} doesn't have permissions to delete users")
            await interaction.response.send_message("Brak uprawnień", ephemeral=True)

    @user_group.command(name="list", description="Pokaż menedżerów dodanych do tego serwera")
    @discord.app_commands.check(check_admin)
    async def list(self, interaction: discord.Interaction):
        users = Db().fetch_all("SELECT UserId FROM users WHERE GuildId = ?", (interaction.guild.id,))

        print(f"[INFO]\tShowing all users in [{interaction.guild.name} - {interaction.guild.id}]")
        message = f"## Menedżerowie serwera {interaction.guild.name}"

        if users:
            for user in users:
                message += f"\n - <@{user[0]}>"
        else:
            message += "\nBrak"

        await interaction.response.send_message(message, ephemeral=True)

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
