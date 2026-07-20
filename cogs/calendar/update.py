import discord
from discord.ext.commands import Bot

from cogs.calendar.util import update_notification_buttons
from g.classes.calendar import Calendar
from g.classes.logger import get_logger, LogType
from g.util import check_if_calendar_exists, update_calendar


async def calendar_update(interaction: discord.Interaction, bot: Bot, quiet: bool):
    if not await check_if_calendar_exists(interaction): return

    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info("Updating calendar using slash command")

    await update_calendar(interaction.guild, calendar, interaction.user.name)  # TODO ping -> was 'not quiet'
    await update_notification_buttons(bot, interaction, calendar)

    await interaction.response.send_message('Kalendarz został zaktualizowany', ephemeral=True)
