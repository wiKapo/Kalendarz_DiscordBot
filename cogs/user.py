import discord
from discord.ext import commands

from global_functions import *


class UserCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    user_group = discord.app_commands.Group(name='user', description='Komendy do zarządzania menedżerami')

    @user_group.command(name="add", description="Dodaj menedżera do bota na tym serwerze")
    @discord.app_commands.describe(user="Użytkownik do dodania jako menedżer")
    @discord.app_commands.check(check_admin)
    async def add(self, interaction: discord.Interaction, user: discord.User):
        print(f"[INFO]\tAdding user {user.name}")
        connection, cursor = db_connect()
        cursor.execute("SELECT * FROM users WHERE UserId = ? AND  GuildId = ?", (user.id, interaction.guild.id))
        if cursor.fetchone():
            print(f"[INFO]\tUser {user.name} is already added in {interaction.guild.name}")
            await interaction.response.send_message(f"Użytkownik {user.name} jest już dodany na tym serwerze.",
                                                    ephemeral=True)
            return
        cursor.execute("INSERT INTO users (UserId, Name, GuildId) VALUES (?, ?, ?)",
                       (user.id, user.name, interaction.guild.id))
        connection.commit()
        db_disconnect(connection, cursor)
        await interaction.response.send_message(
            f'Dodano użytkownika *{user.name}* jako menedżera kalendarza na tym serwerze', ephemeral=True)

    @add.error
    async def add_error(self, interaction: discord.Interaction, error):
        if await check_manager(interaction) and isinstance(error, discord.app_commands.CheckFailure):
            print(f"[INFO]\tUser {interaction.user.name} doesn't have permissions to use that function")
            await interaction.response.send_message("Brak uprawnień", ephemeral=True)

    @user_group.command(name="remove", description="Usuń menedżera z tego serwera")
    @discord.app_commands.describe(user="Użytkownik do usunięcia")
    @discord.app_commands.check(check_admin)
    async def remove(self, interaction: discord.Interaction, user: discord.User):
        connection, cursor = db_connect()
        cursor.execute("SELECT * FROM users WHERE UserId = ? AND GuildId = ?", (user.id, interaction.guild.id))
        if cursor.fetchone():
            print(f"[INFO]\tRemoving user {user.name}")
            cursor.execute("DELETE FROM users WHERE UserId = ? AND GuildId = ?", (user.id, interaction.guild.id))
            connection.commit()
            await interaction.response.send_message(f'Usunięto menedżera *{user.name}* z tego serwera', ephemeral=True)
        else:
            print(f"[INFO]\tUser {user.name} not found in {interaction.guild.name}")
            await interaction.response.send_message(f'Nie znaleziono menedżera *{user.name}* na tym serwerze', ephemeral=True)
        db_disconnect(connection, cursor)

    @remove.error
    async def remove_error(self, interaction: discord.Interaction, error):
        if await check_manager(interaction) and isinstance(error, discord.app_commands.CheckFailure):
            print(f"[INFO]\tUser {interaction.user.name} doesn't have permissions to use that function")
            await interaction.response.send_message("Brak uprawnień", ephemeral=True)


async def setup(bot):
    await bot.add_cog(UserCog(bot))
