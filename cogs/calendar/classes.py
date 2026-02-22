from discord.role import Role

from cogs.calendar.util import *


class DeleteCalendarModal(discord.ui.Modal, title="Usuń kalendarz"):
    _ = discord.ui.TextDisplay(
        "# Czy na pewno chcesz usunąć ten kalendarz?\nUsuwając kalendarz usuniesz również wydarzenia!")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        calendar = Calendar()
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
        print(
            f"[INFO]\tDeleting calendar from server [{interaction.guild.name}] from channel [{interaction.channel.name}]")
        calendar_message = await (await interaction.guild.fetch_channel(calendar.channelId)).fetch_message(
            calendar.messageId)
        await calendar_message.delete()
        print("[INFO] Removed the calendar message.")
        calendar.delete()
        print("[INFO] The calendar and its events have been removed from the database.")

        await interaction.response.send_message("Kalendarz został usunięty RAZEM z wydarzeniami", ephemeral=True)


class EditCalendarModal(discord.ui.Modal):
    calendar: Calendar

    def __init__(self, calendar: Calendar, ping_role: Role | None, user_role: Role | None) -> None:
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
        self.add_item(
            discord.ui.Label(text="Wybierz rolę dla menedżerów kalendarza",
                             description="Osoby z tą rolą będą mogły edytować kalendarz (Zastępuje wszystko związane z `/user`)",
                             component=discord.ui.RoleSelect(placeholder="[WIP] Rola menedżerów kalendarza",
                                                             default_values=[user_role] if user_role else [])))
        self.add_item(discord.ui.TextDisplay("-# Rola dla menedżerów nic obecnie nie robi :)"))
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
        self.calendar.title, self.calendar.showSections, self.calendar.pingRoleId, self.calendar.userRoleId = data
        if self.calendar.title == "": self.calendar.title = None

        try:
            self.calendar.update()
            await update_calendar(interaction, self.calendar)
        except Exception as e:
            print(e)
        await interaction.response.send_message("Kalendarz został zmieniony", ephemeral=True)
