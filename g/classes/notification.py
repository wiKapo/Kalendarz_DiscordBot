from datetime import datetime

from g.classes.calendar import Calendar
from g.classes.db import Db
from g.classes.event import Event


class Notification:
    id: int
    userId: int
    eventId: int
    timestamp: int
    timeTag: str
    description: str | None = None

    def __init__(self, data: list | None = None):
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
        Db().execute("DELETE FROM notifications WHERE UserId=? AND EventId=? AND Timestamp=?",
                     (self.userId, self.eventId, self.timestamp))


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
