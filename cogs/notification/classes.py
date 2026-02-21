from cogs.notification.util import *
from g.util import *


class DeleteNotificationModal(discord.ui.Modal):
    event: Event

    def __init__(self, event: Event, user_id: int):
        self.event = event
        super().__init__(title="Usuń powiadomienia")
        amount_of_notifications = Db().fetch_one("SELECT COUNT(*) FROM notifications WHERE EventId = ? AND UserId = ?",
                                                 (event.id, user_id))[0]
        if amount_of_notifications == 1:
            text = "Usuwasz 1 powiadomienie"
        elif 1 < amount_of_notifications < 5:
            text = f"Usuwasz {amount_of_notifications} powiadomienia"
        else:
            text = f"Usuwasz {amount_of_notifications} powiadomień"

        self.add_item(discord.ui.TextDisplay(f"{text} z wydarzenia:\n{format_event(event)}\n\n"
                                             "Potwierdź wybierając przycisk `Wyślij`"))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        print(f"[INFO]\tDeleting notifications from user [{interaction.user.name} = {interaction.user.id}] "
              f"for event id {self.event.id}")
        try:
            Db().execute("DELETE FROM notifications WHERE UserId = ? AND EventId = ?",
                         (interaction.user.id, self.event.id))
        except Exception as e:
            print(e)


class AddNotificationModal(discord.ui.Modal):
    event: Event
    notifications: list[Notification]
    default_time_tags = ["0", "1", "2", "1d", "1w"]

    def __init__(self, event: Event, user_id: int):
        self.event = event
        super().__init__(title="Dodaj powiadomienie")
        self.add_item(discord.ui.TextDisplay(f"Do wydarzenia: {format_event(event)}"))

        self.notifications = fetch_notifications_by_event(user_id, event.id)
        selected_time_tags = [n.timeTag for n in self.notifications]
        selected_custom_time_tags = [tag for tag in selected_time_tags if tag not in self.default_time_tags]
        time_options = [
            discord.SelectOption(label="W godzinie wydarzenia", value="0", default="0" in selected_time_tags),
            discord.SelectOption(label="1 godzina wcześniej", value="1", default="1" in selected_time_tags),
            discord.SelectOption(label="2 godziny wcześniej", value="2", default="2" in selected_time_tags),
            discord.SelectOption(label="1 dzień wcześniej", value="1d", default="1d" in selected_time_tags),
            discord.SelectOption(label="1 tydzień wcześniej", value="1w", default="1w" in selected_time_tags),
            discord.SelectOption(label="Niestandardowe", value="_", default=len(selected_custom_time_tags) > 0)]
        self.add_item(discord.ui.Label(
            text="Wybierz czas", description="Powiadomienia są sprawdzane co godzinę (czyli o 12:00, 13:00, itd.)",
            component=discord.ui.Select(options=time_options, max_values=len(time_options), required=True)))

        self.add_item(discord.ui.Label(text="Opis powiadomień", component=discord.ui.TextInput(
            required=False, placeholder="Dodaj opcjonalny opis do nowych powiadomień")))

        self.add_item(discord.ui.Label(
            text="Dodaj niestandardowe powiadomienia",
            description="Każdą kolejną wartość oddziel przecinkiem [,]",
            component=discord.ui.TextInput(
                placeholder="Zaznacz [Niestandardowe] w polu wyboru czasu",
                required=False,
                default=", ".join(selected_custom_time_tags) if selected_custom_time_tags else None)))

        self.add_item(discord.ui.TextDisplay(
            "-# Np.: `3h`=3 godziny, `3d`=3 dni, `2w`=2 tygodnie, `1d5`=dzień i 5 godzin"))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        data = []
        for child in self.walk_children():
            if type(child) is discord.ui.TextInput:
                data.append(str(child))
            if type(child) is discord.ui.Select:
                data.append(child.values)

        TIME = 0
        TEXT = 1
        CUSTOM = 2

        try:
            print(f"[INFO]\tAdding notifications for event id {self.event.id}"
                  f" at {'time' if len(data[TIME]) == 1 else 'times'} {data[TIME]}"
                  f"{f' and text {data[TEXT]}' if data[TEXT] else ''}")
        except Exception as e:
            print(e)
            return

        print(f"Event {self.event.name} @ {self.event.timestamp} ")
        event_time = hour_rounder(datetime.fromtimestamp(self.event.timestamp))

        print(f"Event time: {event_time}")
        if "_" in data[TIME]:
            data[TIME].remove("_")
            if data[CUSTOM] != "":
                data[TIME].extend(data[CUSTOM].replace(" ", "").split(','))
            else:
                print("Did not receive custom times, skipping")

        print(data[TIME])
        selected_time_tags = [n.timeTag for n in self.notifications]
        for time_tag in data[TIME]:
            if time_tag in selected_time_tags:  # do not add duplicates
                selected_time_tags.remove(time_tag)
                continue

            notify_time = event_time - timedelta(hours=get_time_from_tag(time_tag))
            print(f"Notify time: {notify_time}")
            Db().execute(
                "INSERT INTO notifications (UserId, EventId, Timestamp, TimeTag, Description) VALUES (?, ?, ?, ?, ?)",
                (interaction.user.id, self.event.id, notify_time.timestamp(), time_tag,
                 data[TEXT][0] if data[TEXT] else None))

        if len(selected_time_tags) > 0:  # if there are times left, remove them from the database
            print(f"Removing {selected_time_tags} from database")
            for time_tag in selected_time_tags:
                Db().execute("DELETE FROM notifications WHERE UserId = ? AND EventId = ? AND TimeTag = ?",
                             (interaction.user.id, self.event.id, time_tag))

        print("DONE")
        await interaction.response.send_message(f"Dodano powiadomienia do wydarzenia \"{self.event.name}\"",
                                                ephemeral=True)


async def send_add_notification_modal(interaction: discord.Interaction, events: list[Event], values: list[str]):
    await interaction.response.send_modal(AddNotificationModal(events[int(values[0])], interaction.user.id))


async def send_delete_notification_modal(interaction: discord.Interaction, events: list[Event], values: list[str]):
    event = events[int(values[0])]
    notifications = fetch_notifications_by_event(interaction.user.id, event.id)
    if len(notifications) > 0:
        await interaction.response.send_modal(DeleteNotificationModal(events[int(values[0])], interaction.user.id))
    else:
        await interaction.response.send_message("Nie masz żadnych powiadomień dotyczących tego wydarzenia",
                                                ephemeral=True)
