from datetime import datetime

from discord import SelectOption

from g.classes.db import Db


class Event:
    id: int = None
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
            self.id, self.timestamp, self.wholeDay, self.name, self.team, self.place = data

    def __repr__(self):
        return f"Event[{self.id}]: {self.name} team[{self.team}] place[{self.place}] {self.timestamp} {self.wholeDay}"

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
        self.__init__(data)

    def insert(self):
        Db().execute(
            "INSERT INTO events (Timestamp, WholeDay, Name, Team, Place) VALUES (?, ?, ?, ?, ?)",
            (self.timestamp, self.wholeDay, self.name, self.team, self.place))

    def update(self):
        Db().execute("UPDATE events SET Timestamp=?, WholeDay=?, Name=?, Team=?, Place=? WHERE Id=?",
                     (self.timestamp, self.wholeDay, self.name, self.team, self.place, self.id))

    def delete(self):
        Db().execute("DELETE FROM events WHERE Id=?", (self.id,))


def fetch_events_from_guild(guild_id: int) -> list[Event]:  # TODO move this to list of events in calendar class
    data = Db().fetch_all("SELECT events.* FROM events INNER JOIN eventsInCalendars AS eic "
                          "ON events.Id = eic.EventId INNER JOIN calendars ON eic.CalendarId = calendars.Id "
                          "WHERE guildId=? ORDER BY Timestamp", (guild_id,))
    return [Event(x) for x in data]


def fetch_events_by_channel(guild_id: int, channel_id: int) -> list[Event]:  # TODO remove
    data = Db().fetch_all("SELECT events.* FROM events INNER JOIN calendars ON events.CalendarId = calendars.Id "
                          "WHERE guildId=? AND channelId=? ORDER BY Timestamp", (guild_id, channel_id))
    return [Event(x) for x in data]


def fetch_events_from_calendar(calendar_id: int) -> list[Event]:
    data = Db().fetch_all("SELECT events.* FROM events INNER JOIN eventsInCalendars AS eic "
                          "ON events.Id = eic.EventId WHERE eic.CalendarId=? ORDER BY Timestamp", (calendar_id,))
    return [Event(x) for x in data]


def fetch_outdated_events(cutoff_timestamp: int) -> list[Event]:
    data = Db().fetch_all("SELECT * FROM events WHERE Timestamp<? ORDER BY Timestamp", (cutoff_timestamp,))
    return [Event(x) for x in data]


def remove_old_events(events: list[Event], cutoff_timestamp: int) -> list[Event]:
    good_events = []
    for event in events:
        if event.timestamp > cutoff_timestamp:
            good_events.append(event)
    return good_events


def format_event_options(events: list[Event], selected_event: int | None = None) -> list[SelectOption]:
    options = []
    for i, event in enumerate(events):
        time, date = event.timestamp_to_text()
        if time:
            date = f"{date} {time}"

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
