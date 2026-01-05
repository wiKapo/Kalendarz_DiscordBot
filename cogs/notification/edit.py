import discord


async def notification_edit(interaction: discord.Interaction, event_id: int | None):
    await interaction.response.send_message("Not yet implemented", ephemeral=True)
    pass
