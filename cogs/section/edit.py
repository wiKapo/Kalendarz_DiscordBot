from datetime import datetime, timedelta

import discord

from g.classes.calendar import Calendar, fetch_calendars_in_guild_with_sections
from g.classes.logger import get_logger, LogType
from g.classes.section import Section
from g.discord_classes import UniversalSelectView, format_calendar_options, format_section_options
from g.util import update_calendar, check_if_calendar_exists


async def section_edit(interaction: discord.Interaction, calendar_id: int | None):
    calendar_id = calendar_id or await check_if_calendar_exists(interaction)
    if not calendar_id:
        logger = get_logger(LogType.CALENDAR)
        logger.info(f"{interaction.user.name} is editing sections")
        calendars = fetch_calendars_in_guild_with_sections(interaction.guild_id)
        if not calendars:
            await interaction.response.send_message("Brak kalendarzy z niestandardowymi sekcjami", ephemeral=True)
            return
        for calendar in calendars:
            await calendar.get_additional_data(interaction.guild)
        logger.info("Showing calendar select form")
        await interaction.response.send_message(
            "Wybierz kalendarz, z którego chcesz edytować niestandardową sekcję",
            view=UniversalSelectView(format_calendar_options(calendars), "Wybierz kalendarz",
                                     send_section_select_message),
            ephemeral=True)
    else:
        calendar = Calendar()
        calendar.fetch_in_guild(calendar_id, interaction.guild_id)
        if calendar:
            if not calendar.customSections:
                await interaction.response.send_message("Brak niestandardowych sekcji w tym kalendarzu", ephemeral=True)
            logger = get_logger(LogType.CALENDAR, calendar_id)
            logger.info(f"{interaction.user.name} is editing sections from this calendar")
            logger.info("Showing section select form")
            await interaction.response.send_message(
                "Wybierz sekcję do edycji",
                view=UniversalSelectView(format_section_options(calendar.customSections), "Wybierz sekcję",
                                         send_section_edit_modal), ephemeral=True)
        else:
            await interaction.response.send_message("Kalendarz o tym numerze nie istnieje",
                                                    ephemeral=True)


async def send_section_select_message(interaction: discord.Interaction, values: list[str]):
    calendar = Calendar()
    calendar.fetch(int(values[0]))
    logger = get_logger(LogType.CALENDAR, calendar.id)

    if not len(calendar.customSections):
        logger.info("No custom sections in this calendar")
        await interaction.response.send_message("Wybrany kalendarz nie posiada niestandardowych sekcji", ephemeral=True)
    else:
        logger.info("Showing section select form")
        await interaction.response.send_message(
            "Wybierz sekcję do edycji",
            view=UniversalSelectView(format_section_options(calendar.customSections), "Wybierz sekcję",
                                     send_section_edit_modal), ephemeral=True)


async def send_section_edit_modal(interaction: discord.Interaction, values: list[str]):
    calendar_id, begin_timestamp = map(lambda x: int(x), values[0].split('.'))
    section = Section()
    section.fetch(calendar_id, begin_timestamp)
    await interaction.response.send_modal(SectionEditModal(section))


class SectionEditModal(discord.ui.Modal):
    def __init__(self, section: Section):
        self.section = section

        super().__init__(title="Edytuj niestandardową sekcję")

        self.name_input = discord.ui.TextInput(placeholder="Podaj nazwę", default=self.section.name)
        self.add_item(discord.ui.Label(text="Podaj nazwę sekcji", component=self.name_input))

        self.begin_date_input = discord.ui.TextInput(placeholder="Podaj datę rozpoczęcia",
                                                     default=self.section.begin_date)
        self.add_item(discord.ui.Label(text="Podaj datę rozpoczęcia sekcji", component=self.begin_date_input))

        self.end_date_input = discord.ui.TextInput(placeholder="Podaj datę zakończenia",
                                                   default=self.section.end_date, required=False)
        self.add_item(discord.ui.Label(text="Podaj datę zakończenia sekcji", component=self.end_date_input,
                                       description="Domyślnie dwa tygodnie od daty rozpoczęcia"))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        calendar = Calendar()
        calendar.fetch(self.section.calendarId)
        logger = get_logger(LogType.CALENDAR, calendar.id)
        logger.info(f"{interaction.user.name} is editing section {self.section.name}")

        calendar.customSections.remove(self.section)
        logger.info("Removed section from list")

        old_section_name = self.section.name
        self.section.name = self.name_input.value
        self.section.begin_date = self.begin_date_input.value
        self.section.end_date = self.end_date_input.value
        if self.section.endTimestamp:
            if self.section.beginTimestamp > self.section.endTimestamp:
                logger.error("Section begin date is after end date")
                raise ValueError("Section begin date is after end date")

            if self.section.endTimestamp < datetime.now().timestamp():
                logger.error("Section end date is in the past")
                raise ValueError("Section end date is in the past")
        else:
            self.section.endTimestamp = int(
                (datetime.fromtimestamp(self.section.beginTimestamp) + timedelta(weeks=2)).timestamp())

        self.section.calendarId = calendar.id
        logger.info(f"Read section: {repr(self.section)}")

        calendar.customSections.append(self.section)
        logger.info("Added section to list")

        calendar.update_sections()
        logger.info("Updated calendar sections in database")

        await interaction.response.send_message(f"Zmieniono sekcję `{old_section_name}`", ephemeral=True)
        logger.info("Finished editing section")

        await update_calendar(interaction.guild, calendar, interaction.user.name)
        logger.info("Updated calendar")
