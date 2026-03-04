from g.util import *


class EditCalendarModal(discord.ui.Modal):
    calendar: Calendar

    def __init__(self, calendar: Calendar, ping_role: Role | None) -> None:
        self.calendar = calendar
        super().__init__(title="Edytuj kalendarz")

        self.title_input = discord.ui.TextInput(required=False, default=calendar.title, placeholder=DEFAULT_TITLE)
        self.add_item(discord.ui.Label(text="Tytuł",
                                       description="Podaj tytuł kalendarza lub zostaw puste, aby ustawić wartość domyślną",
                                       component=self.title_input))

        self.section_select = discord.ui.Select(  # TODO dynamic sections
            options=[discord.SelectOption(label="Nie", value="0", default=calendar.showSections == 0),
                     discord.SelectOption(label="Tak", value="1", default=calendar.showSections == 1)])
        self.add_item(discord.ui.Label(text="Pokaż sekcje", component=self.section_select))

        self.ping_role_select = discord.ui.RoleSelect(placeholder="Rola do powiadomień",
                                                      default_values=[ping_role] if ping_role else [])
        self.add_item(discord.ui.Label(text="Wybierz rolę do powiadomień",
                                       description="Będzie wysyłana przy zmianie w kalendarzu",
                                       component=self.ping_role_select))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        send_ping = self.calendar.pingRoleId != self.ping_role_select.values[0].id  # Send a ping message only when the ping role is changed

        self.calendar.title = self.title_input.value
        self.calendar.showSections = self.section_select.values[0] == "1"
        self.calendar.pingRoleId = self.ping_role_select.values[0].id
        if self.calendar.title == "": self.calendar.title = None

        try:
            self.calendar.update()
            await update_calendar(interaction, self.calendar, send_ping)
        except Exception as e:
            print(e)
        await interaction.response.send_message("Kalendarz został zmieniony", ephemeral=True)
