from discord import SelectOption

from g.classes.db import Db
from g.classes.event import Event
from g.classes.section import Section, select_section, delete_all_sections

DEFAULT_TITLE = "Kalendarz by wiKapo"


class Calendar:
    id: int = None
    title: str | None = None
    customSections: list[Section] = []
    eventIds: set[int] = set()
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
            self.id, self.title, self.guildId, self.channelId, self.messageId, \
                self.pingRoleId, self.pingMessageId = data
            self.get_events()
            self.fetch_sections()

    def __repr__(self):
        event_amount = Db().fetch_one("SELECT COUNT(*) FROM eventsInCalendars WHERE CalendarId=?", (self.id,))[0]
        event_amount_text = f"{event_amount if event_amount else "No"} event{"s" if event_amount != 1 else ""}"
        return (f"Calendar[{self.id}] Title:{self.title} ({event_amount_text}) "
                f"(GuildId:{self.guildId}, ChannelId:{self.channelId}, MessageId:{self.messageId}) "
                f"(PingRoleId:{self.pingRoleId} PingMessageId:{self.pingMessageId})")

    def __str__(self):
        message = f":calendar:\t{self.title if self.title else DEFAULT_TITLE}\t:calendar:"
        events = self.fetch_events()
        if not events:
            message += "\nPUSTE"
        else:
            current_section = None
            current_custom_section = None
            for event in events:
                message += "\n"
                new_section, new_custom_section = select_section(self.customSections, event.timestamp)
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
        if data:
            self.__init__(data)

    def fetch_by_channel(self, guild_id: int, channel_id: int):
        data = Db().fetch_one("SELECT * FROM calendars WHERE GuildId=? AND ChannelId=?", (guild_id, channel_id))
        if data:
            self.__init__(data)

    def insert(self):
        Db().execute(
            "INSERT INTO calendars (Title, GuildId, ChannelId, MessageId) VALUES (?, ?, ?, ?)",
            (self.title, self.guildId, self.channelId, self.messageId))

    def update(self):
        Db().execute(
            "UPDATE calendars SET Title=?, MessageId=?, PingRoleId=?, PingMessageId=? WHERE id=?",
            (self.title, self.messageId, self.pingRoleId, self.pingMessageId, self.id))

    def delete(self):
        for event in self.fetch_events():
            event.remove_calendar(self.id)

        Db().execute("DELETE FROM calendars WHERE GuildId = ? AND ChannelId = ?", (self.guildId, self.channelId))

    def get_events(self):
        event_ids = Db().fetch_all("SELECT EventId FROM eventsInCalendars WHERE CalendarId=?", (self.id,))
        for event_id in event_ids:
            self.eventIds.add(event_id)

    def fetch_events(self) -> list[Event]:
        data = Db().fetch_all("SELECT events.* FROM events INNER JOIN eventsInCalendars eic on events.Id = eic.EventId "
                              "WHERE CalendarId=? ORDER BY Timestamp", (self.id,))
        return [Event(e) for e in data]

    def fetch_sections(self):
        data = Db().fetch_all("SELECT * FROM sections WHERE calendarId=?", (self.id,))
        self.customSections = [Section(x) for x in data]

    def update_sections(self):
        delete_all_sections(self.id)
        for section in self.customSections:
            section.insert()


def format_calendar_options(calendars: list[Calendar], selected_calendars: set[int] | None = None) \
        -> list[SelectOption]:
    options = []
    for calendar in calendars:
        options.append(
            SelectOption(
                label=f"{calendar.title if calendar.title else DEFAULT_TITLE}",
                description=f"{calendar.channelName}",
                value=f"{calendar.id}",
                default=True if len(calendars) == 1 or (
                        selected_calendars and calendar.id in selected_calendars) else False
            )
        )
    return options


def fetch_calendars_in_guild(guild_id: int) -> list[Calendar]:
    data = Db().fetch_all("SELECT * FROM calendars WHERE GuildId=?", (guild_id,))
    if data:
        return [Calendar(x) for x in data]
    return []


def fetch_all_calendars() -> list[Calendar]:
    data = Db().fetch_all("SELECT * FROM calendars")
    if data:
        return [Calendar(x) for x in data]
    return []
