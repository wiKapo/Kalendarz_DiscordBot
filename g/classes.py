import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta
from enum import Enum

from discord import Role, Guild, SelectOption

DEFAULT_TITLE = "Kalendarz by wiKapo"

DEFAULT_SECTIONS_RULES: dict[int, Callable[[datetime, datetime], bool]] = {
    1: lambda now, check: now.day == check.day and now.month == check.month and now.year == check.year,
    2: lambda now, check: now.day + 1 == check.day and now.month == check.month and now.year == check.year,
    3: lambda now, check: now.isocalendar()[1] == check.isocalendar()[1] and now.year == check.year,
    4: lambda now, check: now.isocalendar()[1] + 1 == check.isocalendar()[1] and now.year == check.year,
    5: lambda now, check: now.month == check.month and now.year == check.year,
    6: lambda now, check: now.month + 1 == check.month and now.year == check.year,
    99: lambda now, check: True
}


class Db:
    connection: sqlite3.Connection = None
    cursor: sqlite3.Cursor = None

    def fetch_one(self, query: str, data=None):
        self.connect()
        if data is not None:
            self.cursor.execute(query, data)
        else:
            self.cursor.execute(query)
        result = self.cursor.fetchone()
        self.disconnect()
        return result

    def fetch_all(self, query: str, data=None) -> list:
        self.connect()
        if data is not None:
            self.cursor.execute(query, data)
        else:
            self.cursor.execute(query)
        result = self.cursor.fetchall()
        self.disconnect()
        return result

    def fetch_many(self, query: str, amount: int, data=None) -> list:
        self.connect()
        if data is not None:
            self.cursor.execute(query, data)
        else:
            self.cursor.execute(query)
        result = self.cursor.fetchmany(amount)
        self.disconnect()
        return result

    def execute(self, query: str, data=None):
        self.connect()
        if data is not None:
            self.cursor.execute(query, data)
        else:
            self.cursor.execute(query)
        self.commit_disconnect()

    def connect(self) -> sqlite3.Cursor:
        self.connection = sqlite3.connect('calendar_database.db')
        self.cursor = self.connection.cursor()
        return self.cursor

    def commit(self):
        self.connection.commit()

    def commit_disconnect(self):
        self.connection.commit()
        self.disconnect()

    def disconnect(self):
        self.cursor.close()
        self.connection.close()


class Section:
    calendarId: int = None
    timestamp: int | None = None
    name: str = None

    def __init__(self, data: list = None):
        """
        :param data: for parsing fields from the database.
        """
        if data:
            self.calendarId, self.timestamp, self.name = data

    def __repr__(self):
        return f"Section[{self.calendarId}] Timestamp:{self.timestamp} Name:{self.name}"

    def __str__(self):
        return f"---==[  {self.name}  ]==---"

    def double_str(self, other):
        return f"---==[  {self.name}  ][  {other.name}  ]==---"

    def __eq__(self, other):
        return (isinstance(other, Section) and self.timestamp == other.timestamp
                and self.name == other.name and self.calendarId == other.calendarId)

    def timestamp_to_text(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%d.%m.%Y")

    def text_to_timestamp(self, date: str):
        if len(date.split(".")) == 2:
            date += f".{datetime.now().year}"

        self.timestamp = int(datetime.strptime(date, "%d.%m.%Y").timestamp())

    def create_modal_text(self):
        return f"{self.timestamp_to_text()}-{self.name}"

    def insert(self):
        Db().execute("INSERT INTO sections (CalendarId, Timestamp, Name) VALUES (?, ?, ?)",
                     (self.calendarId, self.timestamp, self.name))


DEFAULT_SECTIONS = [Section([0, 1, "Dzisiaj"]),
                    Section([0, 2, "Jutro"]),
                    Section([0, 3, "W tym tygodniu"]),
                    Section([0, 4, "Za tydzień"]),
                    Section([0, 5, "W tym miesiącu"]),
                    Section([0, 6, "Za miesiąc"]),
                    Section([0, 99, "W przyszłości"])]


def delete_all_sections(calendar_id: int):
    Db().execute("DELETE FROM sections WHERE CalendarId = ?", (calendar_id,))


def select_section(custom_sections: list[Section], timestamp: int) -> tuple[Section | None, Section | None]:
    now = datetime.now()
    check = datetime.fromtimestamp(timestamp)

    selected_custom_section = selected_section = None

    if check.date() >= now.date():
        if custom_sections:
            custom_sections.sort(key=lambda s: s.timestamp, reverse=True)
            for section in custom_sections:
                if timestamp >= section.timestamp:
                    selected_custom_section = section
                    break

        for section in DEFAULT_SECTIONS:
            rule = DEFAULT_SECTIONS_RULES.get(section.timestamp)
            if rule(now, check):
                selected_section = section
                break
    return selected_section, selected_custom_section


class Calendar:
    id: int = None
    title: str | None = None
    showSections: bool = None
    custom_sections: list[Section] = []
    guildId: int = None
    channelId: int = None
    messageId: int = None
    pingRoleId: int | None = None
    pingMessageId: int | None = None
    guildName: str = None
    """
    Only for displaying in notifications
    """
    channelName: str = None
    """
    Only for displaying in notifications
    """

    def __init__(self, data: list = None):
        """
        :param data: for parsing fields from the database.
        """
        if data is not None:
            self.id, self.title, self.showSections, self.guildId, self.channelId, self.messageId, \
                self.pingRoleId, self.pingMessageId = data

    def __repr__(self):
        event_amount = Db().fetch_one("SELECT COUNT(*) FROM events WHERE CalendarId=?", (self.id,))[0]
        event_amount_text = f"{event_amount if event_amount else "No"} event{"s" if event_amount != 1 else ""}"
        return (f"Calendar[{self.id}] Title:{self.title} ({event_amount_text}) "
                f"ShowSections:{self.showSections} (GuildId:{self.guildId}, ChannelId:{self.channelId}, "
                f"MessageId:{self.messageId}) (PingRoleId:{self.pingRoleId} PingMessageId:{self.pingMessageId})")

    def __str__(self):
        events: list[Event] = fetch_events_by_calendar(self.id)
        message = f":calendar:\t{self.title if self.title else DEFAULT_TITLE}\t:calendar:"
        if not events:
            message += "\nPUSTE"
        else:
            current_section = None
            current_custom_section = None
            for event in events:
                message += "\n"
                new_section, new_custom_section = select_section(self.custom_sections, event.timestamp)
                if self.showSections:
                    if new_section != current_section and new_custom_section != current_custom_section:
                        message += f"\n\t{new_section.double_str(new_custom_section)}\n"
                    elif new_custom_section != current_custom_section:
                        message += f"\n\t{new_custom_section}\n"
                    elif new_section != current_section:
                        message += f"\n\t{new_section}\n"

                current_section = new_section
                current_custom_section = new_custom_section

                if not current_section:
                    message += "-# ~~"

                message += str(event)

                if not current_section:
                    message += "~~"

        message += "\n\nZarządzaj powiadomieniami przyciskami poniżej"

        return message

    def fetch(self, calendar_id: int):
        data = Db().fetch_one("SELECT * FROM calendars WHERE id=?", (calendar_id,))
        if data is not None:
            (self.id, self.title, self.showSections, self.guildId, self.channelId, self.messageId,
             self.pingRoleId, self.pingMessageId) = data
            self.fetch_sections()

    def fetch_by_channel(self, guild_id: int, channel_id: int):
        data = Db().fetch_one("SELECT * FROM calendars WHERE GuildId=? AND ChannelId=?", (guild_id, channel_id))
        if data is not None:
            (self.id, self.title, self.showSections, self.guildId, self.channelId, self.messageId,
             self.pingRoleId, self.pingMessageId) = data
            self.fetch_sections()

    def insert(self):
        Db().execute(
            "INSERT INTO calendars (Title, ShowSections, GuildId, ChannelId, MessageId) VALUES (?, ?, ?, ?, ?)",
            (self.title, self.showSections, self.guildId, self.channelId, self.messageId))

    def update(self):
        Db().execute(
            "UPDATE calendars SET Title=?, ShowSections=?, MessageId=?, PingRoleId=?, PingMessageId=? WHERE id=?",
            (self.title, self.showSections, self.messageId, self.pingRoleId, self.pingMessageId, self.id))

    def delete(self):
        # TODO remove notifications connected with those events
        Db().execute("DELETE FROM events WHERE CalendarId = ?", (self.id,))
        Db().execute("DELETE FROM calendars WHERE GuildId = ? AND ChannelId = ?", (self.guildId, self.channelId))

    def fetch_sections(self):
        data = Db().fetch_all("SELECT * FROM sections WHERE calendarId=?", (self.id,))
        self.custom_sections = [Section(x) for x in data]

    def update_sections(self):
        delete_all_sections(self.id)
        for section in self.custom_sections:
            section.insert()


def fetch_all_calendars() -> list[Calendar]:
    data = Db().fetch_all("SELECT * FROM calendars")
    calendars = [Calendar(x) for x in data]
    for calendar in calendars:
        calendar.fetch_sections()
    return calendars


class Event:
    id: int = None
    calendarId: int = None
    timestamp: int = None
    wholeDay: bool = None
    name: str = None
    team: str | None = None
    place: str | None = None

    def __init__(self, data: list = None):
        """
        :param data: for parsing fields from the database.
        """
        if data is not None:
            self.id, self.calendarId, self.timestamp, self.wholeDay, self.name, self.team, self.place = data

    def __repr__(self):
        return f"Event[{self.id}]: calendar[{self.calendarId}] {self.name} team[{self.team}] place[{self.place}] {self.timestamp} {self.wholeDay}"

    def __str__(self):
        message = ""

        # Timestamp
        message += f"<t:{str(self.timestamp)}"
        if self.wholeDay:
            message += ":D"
        message += "> "

        # Team
        if self.team:
            message += f"[{self.team}] "
        # Name
        message += f"**{self.name}"
        # Place
        if self.place:
            message += f" @ {self.place}"
        message += " **"

        return message

    def timestamp_to_text(self) -> tuple[str, str]:
        """
        :return: time, date
        """
        dt = datetime.fromtimestamp(self.timestamp)

        if self.wholeDay:
            time = ""
        else:
            time = dt.strftime("%H:%M")

        date = dt.strftime("%d.%m.%Y")

        return time, date

    def text_to_timestamp(self, time: str, date: str):
        if len(date.split(".")) == 2:
            date += f".{datetime.now().year}"

        if not time:
            dt = datetime.strptime(date, "%d.%m.%Y")
            self.wholeDay = True
        else:
            dt = datetime.strptime(f"{date} {time.replace(".", ":")}", "%d.%m.%Y %H:%M")
            self.wholeDay = False
        self.timestamp = int(dt.timestamp())

    def fetch(self, event_id: int):
        data = Db().fetch_one("SELECT * FROM events WHERE Id=?", (event_id,))
        if data is not None:
            self.id, self.calendarId, self.timestamp, self.wholeDay, self.name, self.team, self.place = data

    def fetch_local(self, event_local_id: int, guild_id: int, channel_id: int):
        data = Db().fetch_one(
            "SELECT events.Id FROM events JOIN calendars ON events.CalendarId = calendars.Id "
            "WHERE GuildId = ? AND ChannelId = ? ORDER BY Timestamp LIMIT 1 OFFSET ?",
            (guild_id, channel_id, event_local_id - 1))
        self.fetch(data[0])

    def insert(self):
        Db().execute(
            "INSERT INTO events (CalendarId, Timestamp, WholeDay, Name, Team, Place) VALUES (?, ?, ?, ?, ?, ?)",
            (self.calendarId, self.timestamp, self.wholeDay, self.name, self.team, self.place))

    def update(self):
        Db().execute("UPDATE events SET Timestamp=?, WholeDay=?, Name=?, Team=?, Place=? WHERE Id=?",
                     (self.timestamp, self.wholeDay, self.name, self.team, self.place, self.id))

    def delete(self):
        Db().execute("DELETE FROM events WHERE Id=?", (self.id,))

    def get_guild_and_channel_id(self):
        return Db().fetch_one("SELECT GuildId, ChannelId FROM events "
                              "JOIN calendars ON events.CalendarId = calendars.Id WHERE events.Id=?", (self.id,))


def fetch_events_by_channel(guild_id: int, channel_id: int) -> list[Event]:
    data = Db().fetch_all("SELECT events.* FROM events INNER JOIN calendars ON events.CalendarId = calendars.Id "
                          "WHERE guildId=? AND channelId=? ORDER BY Timestamp", (guild_id, channel_id))
    return [Event(x) for x in data]


def fetch_events_by_calendar(calendar_id: int) -> list[Event]:
    data = Db().fetch_all("SELECT events.* FROM events WHERE CalendarId=? ORDER BY Timestamp", (calendar_id,))
    return [Event(x) for x in data]


def fetch_outdated_events(cutoff_timestamp: int) -> list[Event]:
    data = Db().fetch_all("SELECT * FROM events WHERE Timestamp<? ORDER BY Timestamp", (cutoff_timestamp,))
    return [Event(x) for x in data]


def delete_events(events: list[Event]):
    for event in events: event.delete()


def remove_old_events(events: list[Event], cutoff_timestamp: int) -> list[Event]:
    good_events = []
    for event in events:
        if event.timestamp > cutoff_timestamp:
            good_events.append(event)
    return good_events


def format_event_entries(events: list[Event], selected_event: int | None = None) -> list[SelectOption]:
    options = []
    for i, event in enumerate(events):
        time, date = event.timestamp_to_text()
        if time: date = f"{date} {time}"

        description = ""
        if event.team:
            description += f'[{event.team}] '
        if event.place:
            description += event.place

        options.append(
            SelectOption(
                label=f"{date} {event.name}",
                description=description,
                value=f"{i}",
                default=i == selected_event
            )
        )

    return options


class Notification:
    id: int = None
    userId: int = None
    eventId: int = None
    timestamp: int = None
    timeTag: str = None
    description: str = None

    def __init__(self, data: list = None):
        """
        :param data: for parsing fields from the database.
        """
        if data is not None:
            self.id, self.userId, self.eventId, self.timestamp, self.timeTag, self.description = data

    def __repr__(self):
        return f"Notification[{self.id}]: user[{self.userId}] event[{self.eventId}] {self.timestamp} {self.timeTag} {self.description}"

    def __str__(self):
        event = Event()
        event.fetch(self.eventId)
        calendar = Calendar()
        calendar.fetch(event.calendarId)

        return (f"Powiadomienie o wydarzeniu [{event}]\n"
                f"Odbędzie się <t:{event.timestamp}:R>\n"
                f"Z kalendarza: https://discord.com/channels/{calendar.guildId}/{calendar.channelId}/{calendar.messageId}\n"
                f"{self.description if self.description else ""}")

    def get_guild_and_channel_id(self):
        return Db().fetch_one(
            "SELECT GuildId, ChannelId FROM notifications JOIN events ON notifications.EventId = events.Id "
            "JOIN calendars ON events.CalendarId = calendars.Id WHERE notifications.Id=?",
            (self.eventId,))

    def fetch(self, notification_id: int):
        data = Db().fetch_one("SELECT * FROM notifications WHERE Id=?", (notification_id,))
        if data is not None:
            self.id, self.userId, self.eventId, self.timestamp, self.timeTag, self.description = data

    def insert(self):
        Db().execute(
            "INSERT INTO notifications (UserId, EventId, Timestamp, TimeTag, Description) VALUES (?, ?, ?, ?, ?)",
            (self.userId, self.eventId, self.timestamp, self.timeTag, self.description))

    def update(self):
        Db().execute("UPDATE notifications SET Timestamp=?, TimeTag=?, Description=? WHERE Id=?",
                     (self.timestamp, self.timeTag, self.description, self.id))

    def delete(self):
        Db().execute("DELETE FROM notifications WHERE Id=?", (self.id,))


def fetch_all_notifications() -> list[Notification]:
    data = Db().fetch_all("SELECT * FROM notifications")
    return [Notification(x) for x in data]


def fetch_all_ready_notifications() -> list[Notification]:
    data = Db().fetch_all("SELECT * FROM notifications WHERE Timestamp<?", (datetime.now().timestamp(),))
    return [Notification(x) for x in data]


def fetch_notifications_by_user(user_id: int) -> list[Notification]:
    data = Db().fetch_all("SELECT * FROM notifications WHERE UserId=?", (user_id,))
    return [Notification(x) for x in data]


def fetch_notifications_by_event(user_id: int, event_id: int) -> list[Notification]:
    data = Db().fetch_all("SELECT * FROM notifications WHERE UserId=? AND EventId=?", (user_id, event_id))
    return [Notification(x) for x in data]


def fetch_notifications_by_calendar(user_id: int, calendar_id: int) -> list[Notification]:
    data = Db().fetch_all("SELECT notifications.* FROM notifications JOIN events ON notifications.EventId = events.Id "
                          "WHERE UserId=? AND CalendarId=?", (user_id, calendar_id))
    return [Notification(x) for x in data]


def fetch_events_with_notifications(user_id: int) -> list[Event]:
    return [Event(x) for x in Db().fetch_all(
        "SELECT DISTINCT events.* FROM events JOIN notifications ON events.Id = notifications.EventId WHERE UserId=?",
        (user_id,))]


def fetch_events_with_notifications_by_calendar(user_id: int, calendar_id: int) -> list[Event]:
    return [Event(x) for x in Db().fetch_all(
        "SELECT DISTINCT events.* FROM events JOIN notifications ON events.Id = notifications.EventId WHERE UserId=? AND CalendarId=?",
        (user_id, calendar_id))]


class Message:
    id: int = None
    calendarId: int = None
    timestamp: int = None
    deleteBy: int = None
    message: str = None

    def __init__(self, data: list = None):
        """
        :param data: for parsing fields from the database.
        """
        if data is not None:
            self.id, self.calendarId, self.timestamp, self.deleteBy, self.message = data

    def __repr__(self):
        return f"Message [{self.id}]: Event[{self.calendarId}] {self.timestamp} {self.deleteBy} {self.message}"

    def set_time(self, delay_in_days: int = 1):
        current_time = datetime.now()
        self.timestamp = int(current_time.timestamp())
        self.deleteBy = int((current_time + timedelta(days=delay_in_days)).timestamp())

    def insert_with_check(self):
        if not self.check_if_duplicate():
            self.insert()

    def insert(self):
        Db().execute("INSERT INTO messages (CalendarId, Timestamp, DeleteBy, Message) VALUES (?, ?, ?, ?)",
                     (self.calendarId, self.timestamp, self.deleteBy, self.message))

    def delete(self):
        Db().execute("DELETE FROM messages WHERE Id=?", (self.id,))

    def check_if_duplicate(self) -> bool:
        data = Db().fetch_one("SELECT * FROM messages WHERE CalendarId=? AND Message=?",
                              (self.calendarId, self.message))
        return data is not None


def fetch_outdated_update_messages(calendar_id: int, cutoff_timestamp: int) -> list[Message]:
    data = Db().fetch_all("SELECT * FROM messages WHERE CalendarId=? AND DeleteBy<?",
                          (calendar_id, cutoff_timestamp))
    return [Message(x) for x in data]


def delete_messages(messages: list[Message]):
    for message in messages: message.delete()


def fetch_messages_for_calendar(calendar_id: int) -> list[Message]:
    data = Db().fetch_all("SELECT * FROM messages WHERE CalendarId=?", (calendar_id,))
    return [Message(x) for x in data]


def fetch_manager_roles_for_guild(guild: Guild) -> list[Role]:
    role_ids = Db().fetch_all("SELECT RoleId FROM managerRoles WHERE GuildId=?", (guild.id,))
    return [guild.get_role(r[0]) for r in role_ids] if role_ids else []


def update_manager_roles_for_guild(guild_id: int, roles: list[Role]):
    Db().execute("DELETE FROM managerRoles WHERE GuildId=?", (guild_id,))  # remove all old roles

    if roles:  # if there are any roles, add them
        for role in roles:
            Db().execute("INSERT INTO managerRoles (GuildId, RoleId) VALUES (?, ?)", (guild_id, role.id))


class LogType(Enum):  # when adding something that will need a new folder, add it to init_logger()
    ALL = ""
    CALENDAR = "calendar"
    USER = "user"
    NOTIFICATION = "notification"
