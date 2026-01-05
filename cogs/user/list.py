import discord

from g.classes import Db


async def user_list(interaction: discord.Interaction):
    users = Db().fetch_all("SELECT UserId FROM users WHERE GuildId = ?", (interaction.guild.id,))

    print(f"[INFO]\tShowing all users in [{interaction.guild.name} - {interaction.guild.id}]")
    message = f"## Menedżerowie serwera {interaction.guild.name}"

    if users:
        for user in users:
            message += f"\n - <@{user[0]}>"
    else:
        message += "\nBrak"

    await interaction.response.send_message(message, ephemeral=True)
