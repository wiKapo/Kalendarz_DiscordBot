import discord

from cogs.calendar.util import update_calendar_buttons
from g.classes.calendar import Calendar, fetch_calendars_in_guild_with_additional_data
from g.classes.logger import get_logger, LogType
from g.discord_classes import UniversalSelectView, format_calendar_options
from g.util import check_if_calendar_exists, update_calendar


async def calendar_update(interaction: discord.Interaction, calendar_id: int | None, quiet: bool):
    calendar_id = calendar_id or await check_if_calendar_exists(interaction)

    if calendar_id:
        calendar = Calendar()
        calendar.fetch_in_guild(calendar_id, interaction.guild_id)
        if not calendar:
            await interaction.response.send_message(f"Kalendarz o numerze {calendar_id} nie istnieje", ephemeral=True)
        else:
            logger = get_logger(LogType.CALENDAR, calendar.id)
            logger.info(f"{interaction.user.name} is updating calendar using slash command")

            await interaction.response.send_message(f"Kalendarz jest aktualizowany {"po cichu" if quiet else ""}",
                                                    ephemeral=True)

            await update_calendar(interaction.guild, calendar, interaction.user.name, quiet)
            await update_calendar_buttons(interaction.guild, calendar)

            await interaction.followup.send(f"Kalendarz #{calendar_id} został zaktualizowany", ephemeral=True)
    else:
        logger = get_logger(LogType.CALENDAR)
        logger.info(f"{interaction.user.name} is trying to update calendar using slash command")
        calendars = await fetch_calendars_in_guild_with_additional_data(interaction.guild)

        if calendars:
            logger.info("Showing select form")
            await interaction.response.send_message(
                "Wybierz kalendarz do zaktualizowania po cichu",
                view=UniversalSelectView(format_calendar_options(calendars), "Wybierz kalendarz", finally_update_calendar),
                ephemeral=True)
        else:
            logger.info("There are no calendars in this guild")
            await interaction.response.send_message("Nie ma kalendarzy na tym serwerze", ephemeral=True)


async def finally_update_calendar(interaction: discord.Interaction, values: list[str]):
    calendar = Calendar()
    calendar.fetch(int(values[0]))
    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info(f"{interaction.user.name} is updating calendar using slash command")
    await interaction.response.send_message(f"Kalendarz jest aktualizowany po cichu", ephemeral=True)

    await update_calendar(interaction.guild, calendar, interaction.user.name, True)
    await update_calendar_buttons(interaction.guild, calendar)

    await interaction.followup.send(f"Kalendarz #{calendar.id} został zaktualizowany", ephemeral=True)
