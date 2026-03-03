from cogs.calendar.util import *


async def calendar_delete(interaction: discord.Interaction):
    if not await check_if_calendar_exists(interaction): return

    print("[INFO]\tDeleting calendar")
    await interaction.response.send_modal(DeleteCalendarModal())


class DeleteCalendarModal(discord.ui.Modal, title="Usuń kalendarz"):
    _ = discord.ui.TextDisplay(
        "# Czy na pewno chcesz usunąć ten kalendarz?\nUsuwając kalendarz usuniesz również wydarzenia!")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        calendar = Calendar()
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
        print(
            f"[INFO]\tDeleting calendar from server [{interaction.guild.name}] from channel [{interaction.channel.name}]")
        calendar_message = await (await interaction.guild.fetch_channel(calendar.channelId)).fetch_message(
            calendar.messageId)
        await calendar_message.delete()
        print("[INFO] Removed the calendar message.")
        calendar.delete()
        print("[INFO] The calendar and its events have been removed from the database.")

        await interaction.response.send_message("Kalendarz został usunięty RAZEM z wydarzeniami", ephemeral=True)
