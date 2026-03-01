import sqlite3


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


class Calendar:
    id: int = None
    title: str | None = None
    showSections: bool = None
    guildId: int = None
    channelId: int = None
    messageId: int = None
    guildName: str = None
    userRoleId: int | None = None
    pingRoleId: int | None = None
    pingMessageId: int | None = None
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
                self.userRoleId, self.pingRoleId, self.pingMessageId = data

    def __repr__(self):
        return (f"Calendar[{self.id}] Title:{self.title} ShowSections:{self.showSections} "
                f"(GuildId:{self.guildId}, ChannelId:{self.channelId}, MessageId:{self.messageId}) "
                f"userRoleId:{self.userRoleId} (PingRoleId:{self.pingRoleId} PingMessageId:{self.pingMessageId}) ")

    def prepare_calendar_base(self, data: list):
        """
        :param data: title, showSections, guildId, channelId, messageId
        """
        self.set_base(data)
        self.insert()
        self.fetch_by_channel(self.guildId, self.channelId)

    def set_base(self, data: list):
        """
        :param data: title, showSections, guildId, channelId, messageId
        """
        self.title, self.showSections, self.guildId, self.channelId, self.messageId = data

    def fetch(self, calendar_id: int):
        data = Db().fetch_one("SELECT * FROM calendars WHERE id=?", (calendar_id,))
        if data is not None:
            (self.id, self.title, self.showSections, self.guildId, self.channelId, self.messageId,
             self.userRoleId, self.pingRoleId, self.pingMessageId) = data

    def fetch_by_channel(self, guild_id: int, channel_id: int):
        data = Db().fetch_one("SELECT * FROM calendars WHERE GuildId=? AND ChannelId=?", (guild_id, channel_id))
        if data is not None:
            (self.id, self.title, self.showSections, self.guildId, self.channelId, self.messageId,
             self.userRoleId, self.pingRoleId, self.pingMessageId) = data

    def insert(self):
        Db().execute(
            "INSERT INTO calendars (Title, ShowSections, GuildId, ChannelId, MessageId) VALUES (?, ?, ?, ?, ?)",
            (self.title, self.showSections, self.guildId, self.channelId, self.messageId))

    def update(self):
        Db().execute(
            "UPDATE calendars SET Title=?, ShowSections=?, MessageId=?, UserRoleId=?, PingRoleId=?, PingMessageId=? WHERE id=?",
            (self.title, self.showSections, self.messageId, self.userRoleId, self.pingRoleId, self.pingMessageId,
             self.id))

    def delete(self):
        Db().execute("DELETE FROM events WHERE CalendarId = ?", (self.id,))
        Db().execute("DELETE FROM calendars WHERE GuildId = ? AND ChannelId = ?", (self.guildId, self.channelId))


def fetch_all_calendars() -> list[Calendar]:
    data = Db().fetch_all("SELECT * FROM calendars")
    return [Calendar(x) for x in data]


class Event:
    id: int = None
    calendarId: int = None
    timestamp: int = None
    wholeDay: bool = None
    name: str = None
    team: str = None
    place: str = None

    def __init__(self, data: list = None):
        """
        :param data: for parsing fields from the database.
        """
        if data is not None:
            self.id, self.calendarId, self.timestamp, self.wholeDay, self.name, self.team, self.place = data

    def __repr__(self):
        return f"Event[{self.id}]: calendar[{self.calendarId}] {self.name} team[{self.team}] place[{self.place}] {self.timestamp} {self.wholeDay}"

    def set_and_update(self, data: list):
        """
        :param data: name, date, time, team, place
        """
        self.set(data)
        self.update()

    def set_and_insert(self, data: list):
        """
        :param data: name, date, time, team, place
        """
        self.set(data)
        self.insert()

    def set(self, data: list):
        """
        :param data: name, date, time, team, place
        """
        self.text_to_timestamp(data[2], data[1])
        self.name, _, _, self.team, self.place = data

    def timestamp_to_text(self) -> tuple[str, str]:
        from datetime import datetime
        dt = datetime.fromtimestamp(self.timestamp)

        if self.wholeDay:
            time = ""
        else:
            time = dt.strftime("%H:%M")

        date = dt.strftime("%d.%m.%Y")

        return time, date

    def text_to_timestamp(self, time: str, date: str):
        from datetime import datetime
        if len(date.split(".")) == 2:
            date += f".{datetime.now().year}"

        if time == "":
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


class User:  # TODO Change to role managers
    pass


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


def fetch_all_notifications() -> list[Notification]:
    data = Db().fetch_all("SELECT * FROM notifications")
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
    EventId: int = None
    Timestamp: int = None
    Message: str = None

    def __init__(self, data: list = None):
        """
        :param data: for parsing fields from the database.
        """
        if data is not None:
            self.id, self.EventId, self.Timestamp, self.Message = data

    def __repr__(self):
        return f"Message [{self.id}]: Event[{self.EventId}] {self.Timestamp} {self.Message}"

    def insert(self):
        Db().execute("INSERT INTO messages (EventId, Timestamp, Message) VALUES (?, ?, ?)",
                     (self.EventId, self.Timestamp, self.Message))

    def delete(self):
        Db().execute("DELETE FROM messages WHERE Id=?", (self.id,))


def fetch_messages_for_calendar(calendar_id: int) -> list[Message]:
    data = Db().fetch_all("SELECT * FROM messages JOIN events ON messages.EventId=events.Id WHERE CalendarId=?", (calendar_id,))
    return [Message(x) for x in data]