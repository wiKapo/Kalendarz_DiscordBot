from datetime import datetime

from g.classes.calendar import fetch_calendars_from_ids
from g.classes.db import Db
from g.classes.event import Event


class Notification:
    id: int = None
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
        calendars = sorted(fetch_calendars_from_ids(event.calendarIds), key=lambda x: x.id)
        ids = [str(x.id) for x in calendars]

        return (f"Powiadomienie o wydarzeniu [{event}]\n"
                f"Odbędzie się <t:{event.timestamp}:R>\n"
                f"-# Z kalendarz{'a' if len(calendars) == 1 else 'y'} {', '.join(ids)}\n"
                f"{self.description if self.description else ""}\n"
                f"Linki do kalendarzy: {', '.join(
                    map(lambda x: f'[{x.id}] https://discord.com/channels/{x.guildId}/{x.channelId}/{x.messageId}', calendars))}")

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
    data = Db().fetch_all("SELECT notifications.* FROM notifications "
                          "INNER JOIN events ON notifications.EventId = events.Id "
                          "INNER JOIN eventsInCalendars ON events.Id = eventsInCalendars.EventId "
                          "WHERE UserId=? AND CalendarId=?", (user_id, calendar_id))
    return [Notification(x) for x in data]


def fetch_events_with_notifications(user_id: int) -> list[Event]:
    return [Event(x) for x in Db().fetch_all(
        "SELECT DISTINCT events.* FROM events JOIN notifications ON events.Id = notifications.EventId WHERE UserId=?",
        (user_id,))]


def fetch_events_with_notifications_by_calendar(user_id: int, calendar_id: int) -> list[Event]:
    return [Event(x) for x in Db().fetch_all("SELECT DISTINCT events.* FROM events "
                                             "INNER JOIN notifications ON events.Id = notifications.EventId "
                                             "INNER JOIN eventsInCalendars ON events.Id = eventsInCalendars.EventId"
                                             " WHERE UserId=? AND CalendarId=?", (user_id, calendar_id))]
