from cogs.calendar.util import update_calendar
from cogs.event.util import *

NAME = 0
DATE = TIMESTAMP = 1
TIME = WHOLE_DAY = 2
TEAM = 3
PLACE = 4


class DeleteEventsModal(discord.ui.Modal):
    def __init__(self, interaction: discord.Interaction):
        options = format_event_entries(interaction)
        super().__init__(title="Usuń wydarzenia")

        self.add_item(discord.ui.Label(text="Wybierz wydarzenia do usunięcia",
                                       component=discord.ui.Select(options=options, max_values=len(options),
                                                                   required=True)))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        event_ids = []
        for child in self.walk_children():
            print(f"-> {child}")
            if type(child) is discord.ui.Select:
                event_ids = sorted(list(map(int, child.values)))

        print(f"[INFO]\t{event_ids}")

        calendar_id = Db().fetch_one("SELECT Id FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                                     (interaction.guild.id, interaction.channel.id))[0]
        events = Db().fetch_all("SELECT events.Id FROM events WHERE CalendarId = ? ORDER BY Timestamp", (calendar_id,))

        events_to_delete = [events[i][0] for i in event_ids]
        for e_id in events_to_delete:
            Db().execute("DELETE FROM events WHERE Id = ?", (e_id,))

        await update_calendar(interaction, calendar_id)
        print(f"[INFO]\tDeleted events {events_to_delete}")

        if len(event_ids) > 1:
            await interaction.response.send_message(f'Wydrzenia zostały usunięte', ephemeral=True)
        else:
            await interaction.response.send_message(f'Wydarzenie zostało usunięte', ephemeral=True)


class EventEditLabel(discord.ui.Label):
    def __init__(self, text: str, required: bool, default: str, placeholder: str):
        super().__init__(text=text,
                         component=discord.ui.TextInput(required=required, default=default, placeholder=placeholder))


class EventEditModal(discord.ui.Modal):
    db_event_id: int = None

    def __init__(self, interaction: discord.Interaction, event_id: int | None = None):
        if event_id is None:
            title = "Dodaj wydarzenie"
        else:
            title = "Edytuj wydarzenie"
        super().__init__(title=title)

        if event_id is None:
            event = [""] * 5
        else:
            self.db_event_id = \
                Db().fetch_one("SELECT events.Id FROM events JOIN calendars ON events.CalendarId = calendars.Id "
                               "WHERE GuildId = ? AND ChannelId = ? ORDER BY events.Timestamp LIMIT 1 OFFSET ?",
                               (interaction.guild.id, interaction.channel.id, event_id))[0]
            event = Db().fetch_one("SELECT Name, Timestamp, WholeDay, Team, Place FROM events WHERE Id = ?",
                                   (self.db_event_id,))

        print(f"Event [DB ID {self.db_event_id}]: {event}")

        self.add_item(EventEditLabel("Nazwa", True, event[NAME], "Podaj nazwę wydarzenia"))
        if event_id is None:
            time = ""
            date = ""
        else:
            time, date = timestamp_to_text(int(event[TIMESTAMP]), bool(int(event[WHOLE_DAY])))
        self.add_item(EventEditLabel("Data", True, date, "Podaj datę (na przykład 1.12.2025)"))
        self.add_item(EventEditLabel("Godzina", False, time, "Podaj godzinę (np. 12:35)"))
        self.add_item(EventEditLabel("Grupa", False, event[TEAM], "Podaj grupę (np. 1, 3B)"))
        self.add_item(EventEditLabel("Miejsce", False, event[PLACE], "Podaj miejsce wydarzenia"))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        data = []
        for child in self.walk_children():
            if type(child) is discord.ui.TextInput:
                data.append(str(child))

        timestamp, whole_day = text_to_timestamp(data[TIME], data[DATE])

        calendar_id = Db().fetch_one("SELECT Id FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                                     (interaction.guild.id, interaction.channel.id))[0]

        if self.db_event_id is None:  # Adding new event
            print(
                f"[INFO]\tAdding new event [Name = {data[NAME]}, Date = {data[DATE]}, Time = {data[TIME]}, "
                f"Group = {data[TEAM]}, Place = {data[PLACE]}]")

            Db().execute(
                "INSERT INTO events (CalendarId, Timestamp, WholeDay, Name, Team, Place) VALUES (?, ?, ?, ?, ?, ?)",
                (calendar_id, timestamp, whole_day, data[NAME], data[TEAM], data[PLACE]))
            print("[INFO]\tAdded this event")
            await interaction.response.send_message(
                f'Dodano wydarzenie *{data[NAME]}* do kalendarza.\nWydarzenia będą automatycznie usuwane po upłynięciu 3 tygodni od dnia wydarzenia',
                ephemeral=True)
        else:  # Event exists already
            print(
                f"[INFO]\tEditing event [DB ID {self.db_event_id}] with values [Name = {data[NAME]}, Date = {data[DATE]}, "
                f"Time = {data[TIME]}, Group = {data[TEAM]}, Place = {data[PLACE]}]")

            Db().execute(
                "UPDATE events SET Timestamp = ?, WholeDay = ?, Name = ?, Team = ?, Place = ? WHERE Id = ?",
                (timestamp, whole_day, data[NAME], data[TEAM], data[PLACE], self.db_event_id))

            print("[INFO]\tEdited this event")

            await interaction.response.send_message(f'Wydarzenie zostało zmienione', ephemeral=True)

        await update_calendar(interaction, calendar_id)


class SelectEvent(discord.ui.Select):
    result_modal: type

    def __init__(self, interaction: discord.Interaction, placeholder: str, result_modal: type):
        options = format_event_entries(interaction)
        super().__init__(placeholder=placeholder, options=options, max_values=1)
        self.result_modal = result_modal

    async def callback(self, interaction: discord.Interaction):
        try:
            print(f"Recieved value from select: {self.values}")
            await interaction.response.send_modal(self.result_modal(interaction, int(self.values[0])))
        except Exception as e:
            await interaction.response.send_message(f"Błąd przy wysyłaniu Modala", ephemeral=True)
            print(e)


class SelectEventView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, placeholder: str, result_modal: type):
        super().__init__()
        self.add_item(SelectEvent(interaction, placeholder, result_modal))
        print("[INFO]\tSent event selection form")
