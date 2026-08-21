import discord

from g.classes.calendar import Calendar, fetch_calendars_in_guild_with_sections
from g.classes.logger import get_logger, LogType
from g.classes.message import Message
from g.classes.section import Section
from g.discord_classes import UniversalSelectView, UniversalSelect, format_calendar_options, \
    format_section_options
from g.util import update_calendar, check_if_calendar_exists


async def section_delete(interaction: discord.Interaction, calendar_id: int | None):
    calendar_id = calendar_id or await check_if_calendar_exists(interaction)

    if not calendar_id:
        logger = get_logger(LogType.CALENDAR)
        logger.info(f"{interaction.user.name} is trying to delete sections")

        calendars = fetch_calendars_in_guild_with_sections(interaction.guild_id)
        if not calendars:
            await interaction.response.send_message("Brak kalendarzy z niestandardowymi sekcjami", ephemeral=True)
            return
        for calendar in calendars:
            await calendar.get_additional_data(interaction.guild)

        logger.info("Showing calendar select form")
        await interaction.response.send_message(
            "Wybierz kalendarz, z którego chcesz usunąć niestandardową sekcję",
            view=UniversalSelectView(format_calendar_options(calendars), "Wybierz kalendarz",
                                     send_section_delete_modal),
            ephemeral=True)
    else:
        calendar = Calendar()
        calendar.fetch_in_guild(calendar_id, interaction.guild_id)

        if calendar:
            if not calendar.customSections:
                await interaction.response.send_message("Brak niestandardowych sekcji w tym kalendarzu", ephemeral=True)
            logger = get_logger(LogType.CALENDAR, calendar_id)
            logger.info(f"{interaction.user.name} is deleting sections from this calendar")

            await interaction.response.send_modal(SectionDeleteModal(calendar))
        else:
            await interaction.response.send_message("Kalendarz o tym numerze nie istnieje",
                                                    ephemeral=True)


async def send_section_delete_modal(interaction: discord.Interaction, values: list[str]):
    calendar = Calendar()
    calendar.fetch(int(values[0]))
    await interaction.response.send_modal(SectionDeleteModal(calendar))


class SectionDeleteModal(discord.ui.Modal):
    def __init__(self, calendar: Calendar):
        self.calendar = calendar

        super().__init__(title="Usuń niestandardowe sekcje")

        self.section_select = UniversalSelect(format_section_options(self.calendar.customSections), "Wybierz sekcje",
                                              max_values=len(self.calendar.customSections))
        self.add_item(discord.ui.Label(text="Wybierz sekcje do usunięcia", component=self.section_select))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        logger = get_logger(LogType.CALENDAR, self.calendar.id)
        sections_to_delete: list[Section] = [self._fetch_section(x) for x in self.section_select.values]
        logger.info(f"{interaction.user.name} is deleting sections {sections_to_delete}")

        for section in sections_to_delete:
            self.calendar.customSections.remove(section)
            section.delete()
            create_section_delete_message(section)
            logger.info(f"Deleted section {section.name}")
        logger.info("Removed all selected sections")
        self.calendar.update_sections()
        logger.info("Updated calendar sections in database")
        await interaction.response.send_message(f"Usunięto wybrane sekcje", ephemeral=True)

        await update_calendar(interaction.guild, self.calendar, interaction.user.name)

    @staticmethod
    def _fetch_section(combined_primary_key: str) -> Section:
        calendar_id, section_id = map(int, combined_primary_key.split("."))
        section = Section()
        section.fetch(calendar_id, section_id)
        return section


def create_section_delete_message(section: Section):
    message = Message()
    message.calendarId = section.calendarId
    message.message = f"Usunięto sekcję {section.name}"
    message.insert()
