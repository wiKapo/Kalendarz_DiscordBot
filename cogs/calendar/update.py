import discord

from cogs.calendar.util import update_calendar_buttons
from g.classes.calendar import Calendar
from g.classes.logger import get_logger, LogType
from g.util import check_if_calendar_exists, update_calendar


async def calendar_update(interaction: discord.Interaction, calendar_id: int | None, quiet: bool):
    calendar_id = calendar_id or await check_if_calendar_exists(interaction)
    if not calendar_id:
        await interaction.response.send_message("Kalendarz nie istnieje na tym kanale", ephemeral=True)
        return

    calendar = Calendar()
    calendar.fetch_in_guild(calendar_id, interaction.guild_id)
    if calendar:
        logger = get_logger(LogType.CALENDAR, calendar.id)
        logger.info(f"{interaction.user.name} is updating calendar using slash command")

        await interaction.response.send_message(f"Kalendarz jest aktualizowany {"po cichu" if quiet else ""}",
                                                ephemeral=True)

        await update_calendar(interaction.guild, calendar, interaction.user.name, quiet)
        await update_calendar_buttons(interaction.guild, calendar)

        await interaction.followup.send(f"Kalendarz #{calendar_id} został zaktualizowany", ephemeral=True)
    else:
        await interaction.response.send_message(f"Kalendarz o numerze {calendar_id} nie istnieje", ephemeral=True)
