import discord

from cogs.notification.list import SelectCalendarView
from g.classes.calendar import Calendar, fetch_calendars_in_guild
from g.classes.section import Section
from g.util import update_calendar


async def section_add(interaction: discord.Interaction, calendar_id: int | None):
    if not calendar_id:
        calendars = fetch_calendars_in_guild(interaction.guild_id)
        for calendar in calendars:
            await calendar.get_additional_data(interaction.guild)

        await interaction.response.send_message("Wybierz kalendarz, do którego chcesz dodać niestandardową sekcję",
                                                view=SelectCalendarView(calendars, send_section_add_modal),
                                                ephemeral=True)
    else:
        calendar = Calendar()
        calendar.fetch(calendar_id)
        await interaction.response.send_modal(SectionAddModal(calendar))


async def send_section_add_modal(interaction: discord.Interaction, values: list[str]):
    calendar = Calendar()
    calendar.fetch(int(values[0]))
    await interaction.response.send_modal(SectionAddModal(calendar))


class SectionAddModal(discord.ui.Modal):
    def __init__(self, calendar: Calendar):
        self.calendar = calendar

        super().__init__(title="Stwórz niestandardową sekcję")

        self.name_input = discord.ui.TextInput(placeholder="Podaj nazwę")
        self.add_item(discord.ui.Label(text="Podaj nazwę sekcji", component=self.name_input))

        self.begin_date_input = discord.ui.TextInput(placeholder="Podaj datę rozpoczęcia")
        self.add_item(discord.ui.Label(text="Podaj datę rozpoczęcia sekcji", component=self.begin_date_input))

        self.end_date_input = discord.ui.TextInput(placeholder="Podaj datę zakończenia", required=False)
        self.add_item(discord.ui.Label(text="Podaj datę zakończenia sekcji", component=self.end_date_input))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        section = Section()

        section.name = self.name_input.value
        section.begin_date = self.begin_date_input.value
        section.end_date = self.end_date_input.value
        section.calendarId = self.calendar.id

        self.calendar.customSections.append(section)

        self.calendar.update_sections()

        try:
            await update_calendar(interaction.guild, self.calendar, interaction.user.name)
        except Exception as e:
            await interaction.response.send_message(f"ERROR: {e}", ephemeral=True)
            return

        await interaction.response.send_message(f"Stworzono sekcję {section.name}", ephemeral=True)
