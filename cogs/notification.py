import re
from datetime import time, timedelta

import discord
from discord.ext import tasks, commands

from cogs.event import SelectEventView, format_event
from util import *

UPDATE_TIMES = [time(hour=i) for i in range(0, 24)]


def hour_rounder(t: datetime) -> datetime:
    # Rounds to the nearest hour by adding a timedelta hour if minute >= 30
    return t.replace(second=0, microsecond=0, minute=0, hour=t.hour) + timedelta(hours=t.minute // 30)


def get_time_from_tag(time_tag: str) -> int:
    times = re.findall(r"\d+\w?", time_tag)
    result = 0

    for t in times:
        if t[-1] == "d":
            result += int(t[:-1]) * 24
        elif t[-1] == "w":
            result += int(t[:-1]) * 168
        elif t[-1] == "h":
            result += int(t[:-1])
        else:
            result += int(t)

    return result


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


class NotificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_loop.start()

    def cog_unload(self):
        self.update_loop.cancel()

    @tasks.loop(time=UPDATE_TIMES)
    async def update_loop(self):
        ID = 0
        USER = 1
        EVENT = 2
        TIMESTAMP = 3
        DESCRIPTION = 4

        current_time = hour_rounder(datetime.now()).timestamp()
        print(f"[INFO]\tChecking for notifications to send at {current_time}")

        notifications = Db().fetch_all("SELECT Id, UserId, EventId, Timestamp, Description FROM notifications")
        if len(notifications) == 0:
            return
        print(len(notifications))
        for notification in notifications:
            print(f"Checking notification: {notification} |{notification[TIMESTAMP] <= current_time}|")
            if notification[TIMESTAMP] <= current_time:
                user = await self.bot.fetch_user(notification[USER])
                print(f"Sending notification to [{user} {notification[USER]}]")
                event_name, calendar_id = Db().fetch_one("SELECT Name, CalendarId FROM events WHERE Id = ?",
                                                         (notification[EVENT],))
                guild_id, channel_id, message_id = Db().fetch_one(
                    "SELECT GuildId, ChannelId, MessageId FROM calendars WHERE Id = ?", (calendar_id,))
                await user.send(f"Powiadomienie o wydarzeniu \"{event_name}\"\n"
                                f"Link do wiadomości: https://discord.com/channels/{guild_id}/{channel_id}/{message_id}\n"
                                f"{notification[DESCRIPTION] if notification[DESCRIPTION] else None}")
                # TODO make better notification message
                Db().execute("DELETE FROM notifications WHERE Id = ?", (notification[ID],))
        print("DONE checking notifications")

    notify_group = discord.app_commands.Group(name="notification", description="Polecenia powiadomień")

    @notify_group.command(name="add", description="Dodaje lub edytuje powiadomienia do wybranego wydarzenia")
    @discord.app_commands.describe(event_id="Numer wydarzenia (od najstarszego / od góry)")
    async def add(self, interaction: discord.Interaction, event_id: int | None):
        if not await check_if_calendar_exists(interaction): return

        print(f"[INFO]\tModifying notifications in [{interaction.guild.name} - {interaction.guild.id}]"
              f" in [{interaction.channel.name} - {interaction.channel.id}] for [{interaction.user.name} - {interaction.user.id}]")

        if event_id is None:
            await interaction.response.send_message(
                view=SelectEventView(interaction, "Wybierz wydarzenie", AddNotificationModal), ephemeral=True)
        else:
            await interaction.response.send_modal(AddNotificationModal(interaction, event_id))

    @notify_group.command(name="edit", description="Edytuje powiadomienia do wybranego wydarzenia")
    @discord.app_commands.describe(event_id="Numer wydarzenia (od najstarszego / od góry)")
    async def edit(self, interaction: discord.Interaction, event_id: int | None):
        await interaction.response.send_message("Not yet implemented", ephemeral=True)
        pass

    @notify_group.command(name="delete", description="Usuwa wszystkie powiadomienia związane z wybranym wydarzeniem")
    @discord.app_commands.describe(event_id="Numer wydarzenia (od najstarszego / od góry)")
    async def delete(self, interaction: discord.Interaction, event_id: int | None):
        if not await check_if_calendar_exists(interaction): return

        print(f"[INFO]\tDeleting notifications in [{interaction.guild.name} - {interaction.guild.id}]"
              f"in [{interaction.channel.name} - {interaction.channel.id}] from [{interaction.user.name} - {interaction.user.id}]")

        if event_id is None:
            await interaction.response.send_message(
                view=SelectEventView(interaction, "Wybierz wydarzenie", DeleteNotificationModal), ephemeral=True)
        else:
            await interaction.response.send_modal(DeleteNotificationModal(interaction, event_id))

    @notify_group.command(name="test", description="DEBUG ONLY")
    @discord.app_commands.check(check_admin)
    async def test(self, interaction: discord.Interaction):
        print("Testing notification loop")
        try:
            await self.update_loop()
        except Exception as e:
            print(e)
        await interaction.response.send_message("Done", ephemeral=True)


async def setup(bot):
    await bot.add_cog(NotificationCog(bot))
