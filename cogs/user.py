import discord
from discord.ext import commands

from global_functions import *


class UserCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    user_group = discord.app_commands.Group(name='user', description='Komendy do zarządzania menedżerami')

    @user_group.command(name="add", description="Dodaj menedżera do bota na tym serwerze")
    @discord.app_commands.describe(user="Użytkownik do dodania jako menedżer")
    async def add(self, interaction: discord.Interaction, user: discord.User):
        if not await check_user(interaction): return

        print(f"[INFO]\tAdding user {user.name}")
        connection, cursor = db_connect()
        cursor.execute("INSERT INTO users (UserId, Name, GuildId) VALUES (?, ?, ?)",
                       (user.id, user.name, interaction.guild.id))
        connection.commit()
        db_disconnect(connection, cursor)
        await interaction.response.send_message(
            f'Dodano użytkownika *{user.name}* jako menedżera kalendarza na tym serwerze', ephemeral=True)

    @user_group.command(name="remove", description="Usuń menedżera z tego serwera")
    @discord.app_commands.describe(user="Użytkownik do usunięcia")
    async def remove(self, interaction: discord.Interaction, user: discord.User):
        if not await check_user(interaction): return

        connection, cursor = db_connect()
        cursor.execute("SELECT * FROM users WHERE UserId = ? AND GuildId = ?", (user.id, interaction.guild.id))
        if cursor.fetchone():
            print(f"[INFO]\tRemoving user {user.name}")
            cursor.execute("DELETE FROM users WHERE UserId = ? AND GuildId = ?", (user.id, interaction.guild.id))
            connection.commit()
            await interaction.response.send_message(f'Usunięto użytkownika *{user.name}*', ephemeral=True)
        else:
            await interaction.response.send_message(f'Nie znaleziono użytkownika *{user.name}*', ephemeral=True)
        db_disconnect(connection, cursor)
        return


async def setup(bot):
    await bot.add_cog(UserCog(bot))
