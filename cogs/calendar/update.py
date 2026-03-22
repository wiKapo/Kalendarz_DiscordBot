from cogs.calendar.util import *


async def calendar_update(interaction: discord.Interaction, bot: Bot, quiet: bool):
    if not await check_if_calendar_exists(interaction): return

    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info("Updating calendar using slash command")

    await update_calendar(interaction, calendar, not quiet)
    await update_notification_buttons(bot, interaction, calendar)

    await interaction.response.send_message('Kalendarz został zaktualizowany', ephemeral=True)
