import discord

from g.classes.calendar import Calendar, fetch_calendars_in_guild
from g.classes.logger import get_logger, LogType
from g.classes.section import Section
from g.discord_classes import SelectSection, SelectCalendarView
from g.util import update_calendar


async def section_delete(interaction: discord.Interaction, calendar_id: int | None):
    if not calendar_id:
        logger = get_logger(LogType.CALENDAR)
        logger.info(f"{interaction.user.name} is deleting sections")

        calendars = fetch_calendars_in_guild(interaction.guild_id)
        for calendar in calendars:
            await calendar.get_additional_data(interaction.guild)

        logger.info("Showing calendar select form")
        await interaction.response.send_message("Wybierz kalendarz, z którego chcesz edytować niestandardową sekcję",
                                                view=SelectCalendarView(calendars, send_section_delete_modal),
                                                ephemeral=True)
    else:
        logger = get_logger(LogType.CALENDAR, calendar_id)
        logger.info(f"{interaction.user.name} is deleting sections from this calendar")

        calendar = Calendar()
        calendar.fetch(calendar_id)
        await interaction.response.send_modal(SectionDeleteModal(calendar))


async def send_section_delete_modal(interaction: discord.Interaction, values: list[str]):
    calendar = Calendar()
    calendar.fetch(int(values[0]))
    await interaction.response.send_modal(SectionDeleteModal(calendar))


class SectionDeleteModal(discord.ui.Modal):
    def __init__(self, calendar: Calendar):
        self.calendar = calendar

        super().__init__(title="Usuń niestandardowe sekcje")

        self.section_select = SelectSection("Wybierz sekcje", None, self.calendar.customSections,
                                            max_values=len(self.calendar.customSections))
        self.add_item(discord.ui.Label(text="Wybierz sekcje do usunięcia", component=self.section_select))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        logger = get_logger(LogType.CALENDAR, self.calendar.id)
        sections_to_delete: list[Section] = [self._fetch_section(x) for x in self.section_select.values]
        logger.info(f"{interaction.user.name} is deleting sections {sections_to_delete}")

        for section in sections_to_delete:
            self.calendar.customSections.remove(section)
            section.delete()
            logger.info(f"Deleted section {section.name}")
        logger.info("Removed all selected sections")
        self.calendar.update_sections()
        logger.info("Updated calendar sections in database")
        await update_calendar(interaction.guild, self.calendar, interaction.user.name)

        await interaction.response.send_message(f"Usunięto wybrane sekcje")

    @staticmethod
    def _fetch_section(combined_primary_key: str) -> Section:
        calendar_id, section_id = map(int, combined_primary_key.split("."))
        section = Section()
        section.fetch(calendar_id, section_id)
        return section
