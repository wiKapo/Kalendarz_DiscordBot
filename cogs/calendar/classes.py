from cogs.calendar.util import *

TITLE = 0
SHOW_SECTIONS = 1


class DeleteCalendarModal(discord.ui.Modal, title="Usuń kalendarz"):
    _ = discord.ui.TextDisplay(
        "# Czy na pewno chcesz usunąć ten kalendarz?\nUsuwając kalendarz usuniesz również wydarzenia!")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        calendar_id, calendar_message_id = Db().fetch_one(
            "SELECT Id, MessageId FROM calendars WHERE GuildId = ? AND ChannelId = ?",
            (interaction.guild.id, interaction.channel.id))
        print(
            f"[INFO]\tDeleting calendar from server [{interaction.guild.name}] from channel [{interaction.channel.name}]")
        calendar_message = await (await interaction.guild.fetch_channel(interaction.channel.id)).fetch_message(
            calendar_message_id)
        await calendar_message.delete()
        print("[INFO] Removed the calendar message.")
        Db().execute("DELETE FROM events WHERE CalendarId = ?", (calendar_id,))
        Db().execute("DELETE FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                     (interaction.guild.id, interaction.channel.id))
        print("[INFO] The calendar and its events have been removed from the database.")

        await interaction.response.send_message("Kalendarz został usunięty RAZEM z wydarzeniami", ephemeral=True)


class EditCalendarModal(discord.ui.Modal):
    def __init__(self, interaction: discord.Interaction):
        calendar = Db().fetch_one("SELECT Title, ShowSections  FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                                  (interaction.guild.id, interaction.channel.id))
        calendar = list(calendar)
        super().__init__(title="Edytuj kalendarz")

        self.add_item(discord.ui.Label(text="Tytuł",
                                       description="Podaj tytuł kalendarza lub zostaw puste, aby ustawić wartość domyślną",
                                       component=discord.ui.TextInput(required=False, default=calendar[TITLE],
                                                                      placeholder=DEFAULT_TITLE)))
        self.add_item(discord.ui.Label(text="Pokaż sekcje", component=discord.ui.Select(
            options=[discord.SelectOption(label="Nie", value="0", default=calendar[SHOW_SECTIONS] == 0),
                     discord.SelectOption(label="Tak", value="1", default=calendar[SHOW_SECTIONS] == 1)])))
        # TODO dynamic sections

    async def on_submit(self, interaction: discord.Interaction) -> None:
        data = []
        for child in self.walk_children():
            if type(child) is discord.ui.TextInput:
                data.append(str(child))
            if type(child) is discord.ui.Select:
                data.append(child.values[0])

        print(data)
        try:
            calendar_id = Db().fetch_one("SELECT Id FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                                         (interaction.guild.id, interaction.channel.id))[0]
            Db().execute("UPDATE calendars SET Title = ?, ShowSections = ? WHERE Id = ?",
                         (data[TITLE] if data[TITLE] != "" else None, data[SHOW_SECTIONS], calendar_id))
            await update_calendar(interaction, calendar_id)
        except Exception as e:
            print(e)
        await interaction.response.send_message("Kalendarz został zmieniony", ephemeral=True)
