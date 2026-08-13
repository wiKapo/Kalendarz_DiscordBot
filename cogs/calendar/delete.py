import discord

from g.classes.calendar import Calendar
from g.classes.logger import get_logger, LogType
from g.util import check_if_calendar_exists


async def calendar_delete(interaction: discord.Interaction):
    if not await check_if_calendar_exists(interaction):
        return

    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info(f"Showing delete calendar modal for {interaction.user.name} "
                f"in [{interaction.guild.name} - {interaction.guild.id}] "
                f"in [{interaction.channel.name} - {interaction.channel.id}]")
    await interaction.response.send_modal(DeleteCalendarModal())


class DeleteCalendarModal(discord.ui.Modal, title="Usuń kalendarz"):
    _ = discord.ui.TextDisplay("# Czy na pewno chcesz usunąć ten kalendarz?\n"
                               "Usuwając kalendarz usuniesz również wydarzenia!")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        calendar = Calendar()
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
        logger = get_logger(LogType.CALENDAR, calendar.id)
        logger.info(f"{interaction.user.name} is deleting this calendar")

        channel = await interaction.guild.fetch_channel(calendar.channelId)
        calendar_message = await channel.fetch_message(calendar.messageId)
        await calendar_message.delete()
        logger.info("Removed the calendar message.")

        if calendar.descriptionMessageId:
            await (await channel.fetch_message(calendar.descriptionMessageId)).delete()
            logger.info("Removed the calendar description message.")

        calendar.delete()
        logger.info("The calendar and its events have been removed from the database.")

        await interaction.response.send_message("Kalendarz został usunięty **RAZEM** z wydarzeniami", ephemeral=True)
