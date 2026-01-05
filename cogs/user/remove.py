import discord

from g.classes import Db


async def user_remove(interaction: discord.Interaction, user: discord.User):
    manager = Db().fetch_one("SELECT * FROM users WHERE UserId = ? AND GuildId = ?", (user.id, interaction.guild.id))
    if manager:
        print(
            f"[INFO]\tRemoving user [{user.name} - {user.id}] from [{interaction.guild.name} - {interaction.guild.id}]")
        Db().execute("DELETE FROM users WHERE UserId = ? AND GuildId = ?", (user.id, interaction.guild.id))
        await user.send(
            f"Usunięto ciebie z listy menedżerów kalendarza na serwerze \"{interaction.guild.name}\"")

        await interaction.response.send_message(f'Usunięto menedżera *{user.name}* z tego serwera', ephemeral=True)
    else:
        print(
            f"[INFO]\tUser [{user.name} - {user.id}] not found in [{interaction.guild.name} - {interaction.guild.id}]")
        await interaction.response.send_message(f'Nie znaleziono menedżera *{user.name}* na tym serwerze',
                                                ephemeral=True)
