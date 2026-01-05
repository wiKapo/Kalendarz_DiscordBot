import discord

from g.classes import Db


async def user_add(interaction: discord.Interaction, user: discord.User):
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
