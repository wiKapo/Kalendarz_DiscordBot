from datetime import datetime

from discord import SelectOption

from g.classes.db import Db


class Event:
    id: int
    timestamp: int
    wholeDay: bool
    name: str
    team: str | None = None
    place: str | None = None
    calendarIds: set[int] = set()

    def __init__(self, data: list | None = None):
        """
        :param data: for parsing fields from the database.
        """
        if data is not None:
            self.id, self.timestamp, self.wholeDay, self.name, self.team, self.place = data
            calendar_ids = Db().fetch_all("SELECT CalendarId FROM eventsInCalendars WHERE EventId=?", (self.id,))
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

    def date(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%d.%m.%Y")

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

    def fetch_id_using_raw(self):  # I don't like this, but I have no idea how to do it differently
        db_id = Db().fetch_one("SELECT Id FROM events WHERE Timestamp=? AND WholeDay=? "
                               "AND Name=? AND Team=? AND Place=? ORDER BY Id DESC LIMIT 1",
                               (self.timestamp, self.wholeDay, self.name, self.team, self.place))[0]
        self.id = db_id

    def insert(self):
        Db().execute(
            "INSERT INTO events (Timestamp, WholeDay, Name, Team, Place) VALUES (?, ?, ?, ?, ?)",
            (self.timestamp, self.wholeDay, self.name, self.team, self.place))

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
        Db().execute("DELETE FROM events WHERE Id=?", (self.id,))
        Db().execute("DELETE FROM eventsInCalendars WHERE EventId=?", (self.id,))
        Db().execute("DELETE FROM notifications WHERE EventId=?", (self.id,))

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
    data = Db().fetch_all("SELECT events.* FROM events INNER JOIN eventsInCalendars AS eic "
                          "ON events.Id = eic.EventId INNER JOIN calendars ON eic.CalendarId = calendars.Id "
                          "WHERE guildId=? ORDER BY Timestamp", (guild_id,))
    return [Event(x) for x in data]


def fetch_outdated_events(cutoff_timestamp: int) -> list[Event]:
    data = Db().fetch_all("SELECT * FROM events WHERE Timestamp<? ORDER BY Timestamp", (cutoff_timestamp,))
    return [Event(x) for x in data]


def format_event_options(events: list[Event], selected_event: int | None = None) -> list[SelectOption]:
    options = []
    for i, event in enumerate(events):
        description = ""
        if event.team:
            description += f'[{event.team}] '
        if event.place:
            description += event.place

        options.append(
            SelectOption(
                label=f"{event.date}{" " + event.time if event.time else ""} {event.name}",
                description=description,
                value=f"{i}",
                default=i == selected_event
            )
        )

    return options
