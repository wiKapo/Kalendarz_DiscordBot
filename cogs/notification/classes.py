import discord

from cogs.event.util import format_event
from g.util import *
from cogs.notification.util import *


class DeleteNotificationModal(discord.ui.Modal):
    db_event_id: int

    def __init__(self, interaction: discord.Interaction, event_id: int | None = None):
        self.db_event_id = Db().fetch_one(
            "SELECT events.Id FROM events JOIN calendars ON events.CalendarId = calendars.Id "
            "WHERE GuildId = ? AND ChannelId = ? ORDER BY events.Timestamp LIMIT 1 OFFSET ?",
            (interaction.guild.id, interaction.channel.id, event_id))[0]

        event = Db().fetch_one("SELECT Name, Timestamp, WholeDay, Team, Place FROM events WHERE Id = ?",
                               (self.db_event_id,))
        amount_of_notifications = Db().fetch_one("SELECT COUNT(*) FROM notifications WHERE EventId = ?",
                                                 (self.db_event_id,))[0]
        if amount_of_notifications == 1:
            title = "Usuwasz 1 powiadomienie"
        elif 1 < amount_of_notifications < 5:
            title = f"Usuwasz {amount_of_notifications} powiadomienia"
        else:
            title = f"Usuwasz {amount_of_notifications} powiadomień"
        super().__init__(title=title)
        self.add_item(discord.ui.TextDisplay(f"Z wydarzenia: {format_event(event)}\n"
                                             "Potwierdź wybierając przycisk `Wyślij`"))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        print(f"[INFO]\tDeleting notifications from user [{interaction.user.name} = {interaction.user.id}] "
              f"for event id {self.db_event_id}")
        Db().execute("DELETE FROM notifications WHERE UserId = ? AND EventId = ?",
                     (interaction.user.id, self.db_event_id))


class AddNotificationModal(discord.ui.Modal):
    db_event_id: int
    selected_time_tags: list[str]
    default_time_tags = ["0", "1", "2", "1d", "1w"]

    def __init__(self, interaction: discord.Interaction, event_id: int | None = None):
        super().__init__(title="Dodaj powiadomienie")
        self.db_event_id = Db().fetch_one(
            "SELECT events.Id FROM events JOIN calendars ON events.CalendarId = calendars.Id "
            "WHERE GuildId = ? AND ChannelId = ? ORDER BY events.Timestamp LIMIT 1 OFFSET ?",
            (interaction.guild.id, interaction.channel.id, event_id))[0]

        event = Db().fetch_one("SELECT Name, Timestamp, WholeDay, Team, Place FROM events WHERE Id = ?",
                               (self.db_event_id,))
        self.add_item(discord.ui.TextDisplay(f"Do wydarzenia: {format_event(event)}"))

        selected_time_tags = Db().fetch_all("SELECT TimeTag FROM notifications WHERE EventId = ?", (self.db_event_id,))
        self.selected_time_tags = [x[0] for x in selected_time_tags]
        selected_custom_time_tags = [x for x in self.selected_time_tags if x not in self.default_time_tags]
        time_options = [
            discord.SelectOption(label="W godzinie wydarzenia", value="0", default="0" in self.selected_time_tags),
            discord.SelectOption(label="1 godzina wcześniej", value="1", default="1" in self.selected_time_tags),
            discord.SelectOption(label="2 godziny wcześniej", value="2", default="2" in self.selected_time_tags),
            discord.SelectOption(label="1 dzień wcześniej", value="1d", default="1d" in self.selected_time_tags),
            discord.SelectOption(label="1 tydzień wcześniej", value="1w", default="1w" in self.selected_time_tags),
            discord.SelectOption(label="Niestandardowe", value="_", default=len(selected_custom_time_tags) > 0)]
        self.add_item(discord.ui.Label(
            text="Wybierz czas", description="Powiadomienia są sprawdzane co godzinę (czyli o 12:00, 13:00, itd.)",
            component=discord.ui.Select(options=time_options, max_values=len(time_options), required=True)))

        self.add_item(discord.ui.Label(text="Opis powiadomień", component=discord.ui.TextInput(
            required=False, placeholder="Dodaj opis do nowych powiadomień")))

        self.add_item(discord.ui.Label(
            text="Dodaj niestandardowe powiadomienia",
            description="Każdą kolejną wartość oddziel przecinkiem [,]",
            component=discord.ui.TextInput(
                placeholder="Zaznacz [Niestandardowe] w polu wyboru czasu",
                required=False,
                default=", ".join(selected_custom_time_tags) if selected_custom_time_tags else None)))

        self.add_item(discord.ui.TextDisplay(
            "-# Np.: `3` = 3 godziny, `3d` = 3 dni, `2w` = 2 tygodnie, `1d5` = dzień i 5 godzin"))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        data = []
        for child in self.walk_children():
            if type(child) is discord.ui.TextInput:
                data.append(str(child))
            if type(child) is discord.ui.Select:
                data.append(child.values)
        print(data)

        TIME = 0
        TEXT = 1
        CUSTOM = 2

        print(f"[INFO]\tAdding notifications for event id {self.db_event_id}"
              f" at {'time' if len(data[TIME]) == 1 else 'times'} {data[TIME]}"
              f"{f' and text {data[TEXT]}' if data[TEXT] else ''}")

        event_name, event_timestamp = Db().fetch_one("SELECT Name, Timestamp FROM events WHERE Id = ?",
                                                     (self.db_event_id,))
        print(f"Event {event_name} @ {event_timestamp} ")
        event_time = hour_rounder(datetime.fromtimestamp(event_timestamp))

        print(f"Event time: {event_time}")
        if "_" in data[TIME]:
            data[TIME].remove("_")
            if data[CUSTOM] != "":
                data[TIME].extend(data[CUSTOM].replace(" ", "").split(','))
            else:
                print("Did not receive custom times, skipping")

        print(data[TIME])
        for time_tag in data[TIME]:
            if time_tag in self.selected_time_tags:  # do not add duplicates
                self.selected_time_tags.remove(time_tag)
                continue

            notify_time = event_time - timedelta(hours=get_time_from_tag(time_tag))
            print(f"Notify time: {notify_time}")
            Db().execute(
                "INSERT INTO notifications (UserId, EventId, Timestamp, TimeTag, Description) VALUES (?, ?, ?, ?, ?)",
                (interaction.user.id, self.db_event_id, notify_time.timestamp(), time_tag,
                 data[TEXT][0] if data[TEXT] else None))

        if len(self.selected_time_tags) > 0:  # if there are times left, remove them from the database
            print(f"Removing {self.selected_time_tags} from database")
            for time_tag in self.selected_time_tags:
                Db().execute("DELETE FROM notifications WHERE UserId = ? AND EventId = ? AND TimeTag = ?",
                             (interaction.user.id, self.db_event_id, time_tag))

        print("DONE")
        await interaction.response.send_message(f"Dodano powiadomienia do wydarzenia \"{event_name}\"", ephemeral=True)
