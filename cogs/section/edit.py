from datetime import datetime

import discord

from cogs.notification.list import SelectCalendarView
from g.classes.calendar import Calendar, fetch_calendars_in_guild
from g.classes.logger import get_logger, LogType
from g.classes.section import Section
from g.discord_classes import SelectSectionView
from g.util import update_calendar


async def section_edit(interaction: discord.Interaction, calendar_id: int | None):
    if not calendar_id:
        calendars = fetch_calendars_in_guild(interaction.guild_id)
        for calendar in calendars:
            await calendar.get_additional_data(interaction.guild)
        await interaction.response.send_message("Wybierz kalendarz, z którego chcesz edytować niestandardową sekcję",
                                                view=SelectCalendarView(calendars, send_section_select_message),
                                                ephemeral=True)
    else:
        calendar = Calendar()
        calendar.fetch(calendar_id)
        await interaction.response.send_message("Wybierz sekcję do edycji",
                                                view=SelectSectionView(calendar.customSections,
                                                                       send_section_edit_modal),
                                                ephemeral=True)


async def send_section_select_message(interaction: discord.Interaction, values: list[str]):
    calendar = Calendar()
    calendar.fetch(int(values[0]))
    if not len(calendar.customSections):
        await interaction.response.send_message("Wybrany kalendarz nie posiada niestandardowych sekcji", ephemeral=True)
    else:
        await interaction.response.send_message("Wybierz sekcję do edycji",
                                                view=SelectSectionView(calendar.customSections,
                                                                       send_section_edit_modal),
                                                ephemeral=True)


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
        self.add_item(discord.ui.Label(text="Podaj datę zakończenia sekcji", component=self.end_date_input))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        calendar = Calendar()
        calendar.fetch(self.section.calendarId)
        logger = get_logger(LogType.CALENDAR, calendar.id)
        logger.info(f"{interaction.user.name} is editing section {self.section.name}")

        calendar.customSections.remove(self.section)
        logger.info("Removed section from list")


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

        self.section.calendarId = calendar.id
        logger.info(f"Read section: {repr(self.section)}")

        calendar.customSections.append(self.section)
        logger.info("Added section to list")

        calendar.update_sections()
        logger.info("Updated calendar sections in database")

        await update_calendar(interaction.guild, calendar, interaction.user.name)

        await interaction.response.send_message(f"Zmieniono sekcję {self.section.name}", ephemeral=True)
