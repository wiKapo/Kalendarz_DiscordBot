import discord

from cogs.calendar.util import update_calendar_buttons
from g.classes.calendar import Calendar
from g.classes.logger import get_logger, LogType
from g.util import check_if_calendar_exists, update_calendar


async def calendar_update(interaction: discord.Interaction, quiet: bool):
    if not await check_if_calendar_exists(interaction):
        return

    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info(f"{interaction.user.name} is updating calendar using slash command")

    await interaction.response.send_message(f'Kalendarz jest aktualizowany {"po cichu" if quiet else ""}', ephemeral=True)

    await update_calendar(interaction.guild, calendar, interaction.user.name, quiet)
    await update_calendar_buttons(interaction.guild, calendar)

    await interaction.followup.send('Kalendarz został zaktualizowany', ephemeral=True)
