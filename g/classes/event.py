from datetime import datetime

from g.classes.db import Db
from g.classes.logger import get_logger, LogType


class Event:
    id: int = None
    timestamp: int
    wholeDay: bool
    name: str
    team: str | None = None
    place: str | None = None
    calendarIds: set[int] = None

    def __init__(self, data: list | None = None):
        """
        :param data: for parsing fields from the database.
        """
        if data:
            self.id, self.timestamp, self.wholeDay, self.name, self.team, self.place = data
            calendar_ids = Db().fetch_all("SELECT DISTINCT CalendarId FROM eventsInCalendars WHERE EventId=?",
                                          (self.id,))
            self.calendarIds = set()
            for calendar_id in calendar_ids:
                self.calendarIds.add(calendar_id[0])

    def __repr__(self):
        return (f"Event[{self.id}]: {self.name} team[{self.team}] place[{self.place}] {self.timestamp} {self.wholeDay} "
                f"in calendars {self.calendarIds}")

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
        message += f"**{self.name}**"
        # Place
        if self.place:
            message += f" @ {self.place}"

        return message

    @property
    def datetime(self) -> str:
        if self.wholeDay:
            return datetime.fromtimestamp(self.timestamp).strftime("%d.%m.%Y")
        return datetime.fromtimestamp(self.timestamp).strftime("%d.%m.%Y %H:%M")

    @property
    def date(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%d.%m.%Y")

    @property
    def time(self) -> str:
        if self.wholeDay:
            return ""
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M")

    def set_datetime(self, datetime_string: str):
        datetime_list = datetime_string.split(" ")

        date = datetime_list[0]
        if len(date.split(".")) == 2:
            date += f".{datetime.now().year}"

        if len(datetime_list) == 1:  # if time was not given
            dt = datetime.strptime(date, "%d.%m.%Y")
            self.wholeDay = True
        else:
            time = datetime_list[1]
            dt = datetime.strptime(f"{date} {time.replace(".", ":")}", "%d.%m.%Y %H:%M")
            self.wholeDay = False
        self.timestamp = int(dt.timestamp())

    def fetch(self, event_id: int):
        data = Db().fetch_one("SELECT * FROM events WHERE Id=?", (event_id,))
        self.__init__(data)

    def insert(self):
        db_id = Db().execute(  # returns list of tuples [(xx,)]
            "INSERT INTO events (Timestamp, WholeDay, Name, Team, Place) VALUES (?, ?, ?, ?, ?) RETURNING Id",
            (self.timestamp, self.wholeDay, self.name, self.team, self.place))
        self.id = db_id[0][0]

    def connect_to_calendar(self, calendar_id: int):
        Db().execute("INSERT INTO eventsInCalendars (CalendarId, EventId) VALUES (?, ?)", (calendar_id, self.id))

    def update(self):
        Db().execute("UPDATE events SET Timestamp=?, WholeDay=?, Name=?, Team=?, Place=? WHERE Id=?",
                     (self.timestamp, self.wholeDay, self.name, self.team, self.place, self.id))

    def update_calendar_connections(self):
        Db().execute("DELETE FROM eventsInCalendars WHERE EventId=?", (self.id,))
        for calendar_id in self.calendarIds:
            self.connect_to_calendar(calendar_id)

    def delete(self):
        logger = get_logger(LogType.EVENT, self.id)
        logger.warning("Deleting self")
        Db().execute("DELETE FROM events WHERE Id=?", (self.id,))
        Db().execute("DELETE FROM eventsInCalendars WHERE EventId=?", (self.id,))
        logger.info("Żegnam")

    def remove_calendar(self, calendar_id: int):
        if calendar_id in self.calendarIds:
            self.calendarIds.remove(calendar_id)
            Db().execute("DELETE FROM eventsInCalendars WHERE CalendarId=? AND EventId=?", (calendar_id, self.id))
            if not len(self.calendarIds):
                self.delete()

    def get_guild_id(self) -> int:
        guild_id = Db().fetch_one("SELECT GuildId FROM calendars INNER JOIN eventsInCalendars eic "
                                  "ON calendars.Id = eic.CalendarId INNER JOIN events ON events.Id = eic.EventId "
                                  "WHERE events.Id = ?", (self.id,))[0]
        return guild_id


def fetch_events_from_guild(guild_id: int) -> list[Event]:
    data = Db().fetch_all("SELECT DISTINCT events.* FROM events INNER JOIN eventsInCalendars AS eic "
                          "ON events.Id = eic.EventId INNER JOIN calendars ON eic.CalendarId = calendars.Id "
                          "WHERE guildId=? ORDER BY Timestamp", (guild_id,))
    return [Event(x) for x in data]


def fetch_events_from_ids(event_ids: set[int]) -> list[Event]:
    events: list[Event] = []
    for event_id in event_ids:
        event = Event()
        event.fetch(event_id)
        events.append(event)
    return events


def fetch_outdated_events(cutoff_timestamp: int) -> list[Event]:
    data = Db().fetch_all("SELECT * FROM events WHERE Timestamp<? ORDER BY Timestamp", (cutoff_timestamp,))
    return [Event(x) for x in data]


def fetch_all_events() -> list[Event]:
    data = Db().fetch_all("SELECT * FROM events ORDER BY Timestamp")
    if data:
        return [Event(x) for x in data]
    return []
