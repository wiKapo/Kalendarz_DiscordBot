from cogs.calendar.util import *


async def calendar_edit(interaction: discord.Interaction):
    if not await check_if_calendar_exists(interaction): return
    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)

    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info(f"Showing edit calendar modal in [{interaction.guild.name} - {interaction.guild.id}]")

    await interaction.response.send_modal(
        EditCalendarModal(calendar, interaction.guild.get_role(calendar.pingRoleId)))


class EditCalendarModal(discord.ui.Modal):
    calendar: Calendar

    def __init__(self, calendar: Calendar, ping_role: Role | None) -> None:
        self.calendar = calendar
        super().__init__(title="Edytuj kalendarz")

        self.title_input = discord.ui.TextInput(required=False, default=calendar.title, placeholder=DEFAULT_TITLE)
        self.add_item(discord.ui.Label(text="Tytuł",
                                       description="Podaj tytuł kalendarza lub zostaw puste, aby ustawić wartość domyślną",
                                       component=self.title_input))

        self.show_section = discord.ui.Checkbox(default=calendar.showSections)
        self.add_item(discord.ui.Label(text="Pokaż sekcje w wiadomości kalendarza", component=self.show_section))

        self.add_item(discord.ui.TextDisplay("Format niestandardowych sekcji: `dd.mm(.yyyy)-nazwa`\n"
                                             "`()`- opcjonalne, wstawi obecny rok. Kolejne sekcje rozdziej `,`"))

        self.custom_sections = discord.ui.TextInput(required=False,
                                                    default=", ".join([s.create_modal_text() for s in self.calendar.custom_sections]))
        self.add_item(discord.ui.Label(text="Dodaj niestandardowe sekcje", component=self.custom_sections))

        self.ping_role_select = discord.ui.RoleSelect(placeholder="Rola do powiadomień",
                                                      default_values=[ping_role] if ping_role else [])
        self.add_item(discord.ui.Label(text="Wybierz rolę do powiadomień",
                                       description="Będzie wysyłana przy zmianie w kalendarzu",
                                       component=self.ping_role_select))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        selected_ping_role = self.ping_role_select.values[0].id if self.ping_role_select.values else None

        logger = get_logger(LogType.CALENDAR, self.calendar.id)
        logger.info(f"Editing calendar number {self.calendar.id}")
        logger.debug(
            f"Title: {self.calendar.title} -> {self.title_input.value if self.title_input.value != '' else None}")
        logger.debug(f"Show sections: {self.calendar.showSections == 1} -> {self.show_section.value}")
        logger.debug(f"Custom sections: {self.calendar.custom_sections} -> {self.custom_sections.value}")
        logger.debug(f"Ping role: {self.calendar.pingRoleId} -> {selected_ping_role}")

        ping_role_changed = self.calendar.pingRoleId != selected_ping_role

        self.calendar.title = self.title_input.value if self.title_input.value != "" else None
        self.calendar.showSections = self.show_section.value
        self.calendar.custom_sections = format_custom_sections(self.calendar.id, self.custom_sections.value)
        self.calendar.update_sections()
        self.calendar.pingRoleId = selected_ping_role
        # Send a ping message only when the ping role is changed
        self.calendar.update()
        logger.info("Calendar updated in the database")
        await update_calendar(interaction, self.calendar, ping_role_changed)

        await interaction.response.send_message("Kalendarz został zmieniony", ephemeral=True)
        logger.info("Finished editing calendar")
