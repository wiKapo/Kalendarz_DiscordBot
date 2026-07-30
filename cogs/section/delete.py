import discord

from cogs.calendar import update
from cogs.notification.list import SelectCalendarView
from g.classes.calendar import Calendar, fetch_calendars_in_guild
from g.classes.section import Section
from g.discord_classes import SelectSection
from g.util import update_calendar


async def section_delete(interaction: discord.Interaction, calendar_id: int | None):
    if not calendar_id:
        calendars = fetch_calendars_in_guild(interaction.guild_id)
        await interaction.response.send_message("Wybierz kalendarz, z którego chcesz edytować niestandardową sekcję",
                                                view=SelectCalendarView(calendars, send_section_delete_modal),
                                                ephemeral=True)
    else:
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

        self.section_select = SelectSection("Wybierz sekcje", None, calendar.customSections)
        self.add_item(discord.ui.Label(text="Wybierz sekcje do usunięcia", component=self.section_select))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        sections_to_delete = [self._fetch_section(x) for x in self.section_select.values]
        for section in sections_to_delete:
            section.delete()
        self.calendar.update_sections()
        await update_calendar(interaction.guild, self.calendar, interaction.user.name)

    @staticmethod
    def _fetch_section(combined_primary_key: str):
        calendar_id, section_id = map(int, combined_primary_key.split("."))
        return Section().fetch(calendar_id, section_id)
