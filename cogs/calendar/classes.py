from g.util import *


class EditCalendarModal(discord.ui.Modal):
    calendar: Calendar

    def __init__(self, calendar: Calendar, ping_role: Role | None) -> None:
        self.calendar = calendar
        super().__init__(title="Edytuj kalendarz")

        self.add_item(discord.ui.Label(text="Tytuł",
                                       description="Podaj tytuł kalendarza lub zostaw puste, aby ustawić wartość domyślną",
                                       component=discord.ui.TextInput(required=False, default=calendar.title,
                                                                      placeholder=DEFAULT_TITLE)))
        self.add_item(discord.ui.Label(text="Pokaż sekcje", component=discord.ui.Select(
            options=[discord.SelectOption(label="Nie", value="0", default=calendar.showSections == 0),
                     discord.SelectOption(label="Tak", value="1", default=calendar.showSections == 1)])))
        self.add_item(
            discord.ui.Label(text="Wybierz rolę do powiadomień",
                             description="Będzie wysyłana przy zmianie w kalendarzu",
                             component=discord.ui.RoleSelect(placeholder="Rola do powiadomień",
                                                             default_values=[ping_role] if ping_role else [])))
        # TODO dynamic sections

    async def on_submit(self, interaction: discord.Interaction) -> None:
        data = []
        for child in self.walk_children():
            if type(child) is discord.ui.TextInput:
                data.append(str(child))
            if type(child) is discord.ui.Select:
                data.append(child.values[0])
            if type(child) is discord.ui.RoleSelect:
                if len(child.values) > 0:
                    data.append(child.values[0].id)
                else:
                    data.append(None)

        # TODO Refactor all modals
        send_ping = self.calendar.pingRoleId != data[2]  # Send a ping message only when the ping role is changed

        self.calendar.title, self.calendar.showSections, self.calendar.pingRoleId = data
        if self.calendar.title == "": self.calendar.title = None

        try:
            print(self.calendar)
            self.calendar.update()
            await update_calendar(interaction, self.calendar, send_ping)
        except Exception as e:
            print(e)
        await interaction.response.send_message("Kalendarz został zmieniony", ephemeral=True)
