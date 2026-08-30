from discord import Guild

from g.classes.db import Db
from g.classes.event import Event
from g.classes.logger import LogType, get_logger
from g.classes.section import Section, select_section, delete_all_sections

DEFAULT_TITLE = ":calendar:\tKalendarz by wiKapo\t:calendar:"
DEFAULT_TITLE_RAW = "Kalendarz by wiKapo"


class Calendar:
    id: int = None
    title: str | None = None
    customSections: list[Section] = []
    eventIds: set[int] = None
    guildId: int
    channelId: int
    messageId: int
    pingRoleId: int | None = None
    descriptionMessageId: int | None = None
    guildName: str
    channelName: str

    def __init__(self, data: list | None = None):
        """
        :param data: for parsing fields from the database.
        """
        if data:
            self.id, self.title, self.guildId, self.channelId, self.messageId, \
                self.pingRoleId, self.descriptionMessageId = data
            event_ids = Db().fetch_all("SELECT DISTINCT EventId FROM eventsInCalendars WHERE CalendarId=?", (self.id,))
            self.eventIds = set()
            for event_id in event_ids:
                self.eventIds.add(event_id[0])
            custom_sections = Db().fetch_all("SELECT * FROM sections WHERE calendarId=?", (self.id,))
            self.customSections = [Section(x) for x in custom_sections]

    def __repr__(self):
        event_amount = Db().fetch_one("SELECT COUNT(*) FROM eventsInCalendars WHERE CalendarId=?", (self.id,))[0]
        event_amount_text = f"{event_amount if event_amount else "No"} event{"s" if event_amount != 1 else ""}"
        return (f"Calendar[{self.id}] Title:{self.title} ({event_amount_text}) "
                f"(GuildId:{self.guildId}, ChannelId:{self.channelId}, MessageId:{self.messageId}) "
                f"(PingRoleId:{self.pingRoleId} DescriptionMessageId:{self.descriptionMessageId})")

    def __str__(self):
        message = f"## \t{self.title if self.title else DEFAULT_TITLE}\t"
        events = self.fetch_events()
        if not events:
            message += "\nPUSTE"
        else:
            current_section = None
            current_custom_section = None
            for event in events:
                message += "\n"
                new_section, new_custom_section = select_section(self.customSections, event.timestamp)

                # The new section and custom section changed. Custom section is not null
                if new_section != current_section and new_custom_section and new_custom_section != current_custom_section:
                    message += f"\n\t{new_section.double_str(new_custom_section)}\n"

                # Only custom section changed and is not null
                elif new_custom_section and new_custom_section != current_custom_section:
                    message += f"\n\t{new_custom_section}\n"

                # Only section changed
                elif new_section != current_section:
                    message += f"\n\t{new_section}\n"

                current_section = new_section
                current_custom_section = new_custom_section

                if not current_section:
                    message += "-# ~~"

                message += str(event)

                if not current_section:
                    message += "~~"

        return message

    def __bool__(self):
        return bool(self.id)

    def fetch(self, calendar_id: int):
        data = Db().fetch_one("SELECT * FROM calendars WHERE id=?", (calendar_id,))
        if data:
            self.__init__(data)

    def fetch_in_guild(self, calendar_id: int, guild_id: int):
        """
        Check if this calendar is in the selected guild.
        :param calendar_id: Calendar id to fetch.
        :param guild_id: Check if this calendar is in the selected guild.
        :return:
        """
        data = Db().fetch_one("SELECT * FROM calendars WHERE id=? AND GuildId=?", (calendar_id, guild_id))
        if data:
            self.__init__(data)

    def fetch_by_channel(self, guild_id: int, channel_id: int):
        data = Db().fetch_one("SELECT * FROM calendars WHERE GuildId=? AND ChannelId=?", (guild_id, channel_id))
        if data:
            self.__init__(data)

    def insert(self):
        db_id = Db().execute(  # returns list of tuples [(xx,)]
            "INSERT INTO calendars (Title, GuildId, ChannelId, MessageId) VALUES (?, ?, ?, ?) RETURNING Id",
            (self.title, self.guildId, self.channelId, self.messageId))
        self.id = db_id[0][0]

    def update(self):
        Db().execute(
            "UPDATE calendars SET Title=?, MessageId=?, PingRoleId=?, DescriptionMessageId=? WHERE id=?",
            (self.title, self.messageId, self.pingRoleId, self.descriptionMessageId, self.id))

    def delete(self):
        logger = get_logger(LogType.CALENDAR, self.id)
        logger.warning("Deleting self")
        for event in self.fetch_events():
            event.remove_calendar(self.id)

        Db().execute("DELETE FROM calendars WHERE GuildId = ? AND ChannelId = ?", (self.guildId, self.channelId))
        logger.info("Done. Goodbye")

    def fetch_events(self) -> list[Event]:
        data = Db().fetch_all("SELECT events.* FROM events INNER JOIN eventsInCalendars eic on events.Id = eic.EventId "
                              "WHERE CalendarId=? ORDER BY Timestamp", (self.id,))
        return [Event(e) for e in data]

    def update_sections(self):
        delete_all_sections(self.id)
        for section in self.customSections:
            section.insert()

    async def get_additional_data(self, guild: Guild):
        self.guildName = guild.name
        self.channelName = (await guild.fetch_channel(self.channelId)).name

    def get_notification(self, user_id: int) -> bool:
        data = Db().fetch_one("SELECT * FROM notifications WHERE UserId=? AND CalendarId=?", (user_id, self.id))
        return bool(data)

    def delete_notification(self, user_id: int):
        Db().execute("DELETE FROM notifications WHERE UserId=? AND CalendarId=?", (user_id, self.id))

    def add_notification(self, user_id: int):
        Db().execute("INSERT INTO notifications (UserId, CalendarId) VALUES (?, ?)", (user_id, self.id))

    def get_exclusive_events(self) -> set[int]:
        """ Checks how many events are exclusive to the given calendar """
        exclusive_events = Db().fetch_all(
            "SELECT EventId FROM eventsInCalendars GROUP BY EventId HAVING COUNT(EventId) = 1")

        return set(map(lambda x: x[0], exclusive_events)).intersection(self.eventIds)


def fetch_all_notifications() -> dict[int, set[Calendar]]:
    calendars = fetch_all_calendars()
    user_ids = Db().fetch_all("SELECT DISTINCT UserId FROM notifications")
    user_ids = [u[0] for u in user_ids]
    notify_calendars: list[set[Calendar]] = []
    for user_id in user_ids:
        calendar_ids = Db().fetch_all("SELECT DISTINCT CalendarId FROM notifications WHERE UserId=?", (user_id,))
        calendar_ids = [c[0] for c in calendar_ids]
        notify_calendars.append(set(filter(lambda x: x.id in calendar_ids, calendars)))

    return dict(zip(user_ids, notify_calendars))


def remove_all_notifications_from_user(user_id: int):
    Db().execute("DELETE FROM notifications WHERE UserId=?", (user_id,))


def fetch_calendars_in_guild(guild_id: int) -> list[Calendar]:
    data = Db().fetch_all("SELECT * FROM calendars WHERE GuildId=?", (guild_id,))
    if data:
        return [Calendar(x) for x in data]
    return []


def fetch_calendars_in_guild_with_sections(guild_id: int) -> list[Calendar]:
    data = Db().fetch_all(
        "SELECT calendars.* FROM calendars INNER JOIN sections ON calendars.Id = sections.CalendarId "
        "WHERE GuildId=?", (guild_id,))
    if data:
        return [Calendar(x) for x in data]
    return []


def fetch_calendars_from_ids(calendar_ids: set[int]) -> list[Calendar]:
    calendars: list[Calendar] = []
    for calendar_id in calendar_ids:
        calendar = Calendar()
        calendar.fetch(calendar_id)
        calendars.append(calendar)
    return calendars


def fetch_all_calendars() -> list[Calendar]:
    data = Db().fetch_all("SELECT * FROM calendars")
    if data:
        return [Calendar(x) for x in data]
    return []
