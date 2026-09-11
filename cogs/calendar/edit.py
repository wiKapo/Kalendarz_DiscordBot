import discord
from discord import Role

from g.classes.calendar import DEFAULT_TITLE_RAW, Calendar, fetch_calendars_in_guild_with_additional_data
from g.classes.logger import get_logger, LogType
from g.discord_classes import UniversalSelectView, format_calendar_options
from g.util import check_if_calendar_exists, update_calendar


async def calendar_edit(interaction: discord.Interaction, calendar_id: int | None):
    calendar_id = calendar_id or await check_if_calendar_exists(interaction)

    if calendar_id:
        calendar = Calendar()
        calendar.fetch(calendar_id)
        if not calendar:
            await interaction.response.send_message(f"Kalendarz o numerze {calendar_id} nie istnieje", ephemeral=True)
        else:
            logger = get_logger(LogType.CALENDAR, calendar.id)
            logger.info(f"Showing edit calendar modal for {interaction.user.name} "
                        f"in [{interaction.guild.name} - {interaction.guild_id}]")

            await interaction.response.send_modal(
                EditCalendarModal(calendar, interaction.guild.get_role(calendar.pingRoleId)))
    else:
        logger = get_logger(LogType.CALENDAR)
        logger.info(f"{interaction.user.name} is trying to edit calendar")

        calendars = await fetch_calendars_in_guild_with_additional_data(interaction.guild)
        if calendars:
            logger.info("Showing select form")
            await interaction.response.send_message(
                "Wybierz kalendarz do edycji",
                view=UniversalSelectView(format_calendar_options(calendars), "Wybierz kalendarz", send_edit_calendar_modal),
                ephemeral=True)
        else:
            logger.info("There are no calendars in this guild")
            await interaction.response.send_message("Nie ma kalendarzy na tym serwerze", ephemeral=True)


async def send_edit_calendar_modal(interaction: discord.Interaction, values: list[str]):
    calendar = Calendar()
    calendar.fetch(int(values[0]))
    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info(f"Showing edit calendar modal for {interaction.user.name} "
                f"in [{interaction.guild.name} - {interaction.guild_id}]")

    await interaction.response.send_modal(
        EditCalendarModal(calendar, interaction.guild.get_role(calendar.pingRoleId)))


class EditCalendarModal(discord.ui.Modal):
    calendar: Calendar

    def __init__(self, calendar: Calendar, ping_role: Role | None) -> None:
        self.calendar = calendar
        super().__init__(title="Edytuj kalendarz")

        self.title_input = discord.ui.TextInput(required=False, default=calendar.title, placeholder=DEFAULT_TITLE_RAW)
        self.add_item(discord.ui.Label(text="Tytuł",
                                       description="Podaj tytuł kalendarza lub zostaw puste, aby ustawić wartość domyślną",
                                       component=self.title_input))

        self.ping_role_select = discord.ui.RoleSelect(placeholder="Rola do powiadomień",
                                                      default_values=[ping_role] if ping_role else [])
        self.add_item(discord.ui.Label(text="Wybierz rolę do powiadomień",
                                       description="Będzie wysyłana przy zmianie w kalendarzu",
                                       component=self.ping_role_select))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        selected_ping_role = self.ping_role_select.values[0].id if self.ping_role_select.values else None

        logger = get_logger(LogType.CALENDAR, self.calendar.id)
        logger.info(f"Editing calendar number {self.calendar.id}")
        logger.debug(f"Title: {self.calendar.title} -> {self.title_input.value if self.title_input.value else None}")
        logger.debug(f"Ping role: {self.calendar.pingRoleId} -> {selected_ping_role}")

        if self.calendar.pingRoleId != selected_ping_role or self.calendar.title != self.title_input.value:
            self.calendar.title = self.title_input.value if self.title_input.value else None
            self.calendar.pingRoleId = selected_ping_role
            self.calendar.update()
            logger.info("Calendar updated in the database")
            logger.debug(repr(self.calendar))

            await interaction.response.send_message("Kalendarz został zmieniony", ephemeral=True)
            logger.info("Finished editing calendar")

            await update_calendar(interaction.guild, self.calendar, interaction.user.name)
        else:
            await interaction.response.send_message("Nie wprowadzono żadnych zmian", ephemeral=True)
            logger.info("Calendar was not edited")
