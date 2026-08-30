from collections.abc import Callable
from datetime import datetime

from g.classes.db import Db
from g.classes.logger import get_logger, LogType
from g.datetime_util import is_today, is_tomorrow, is_this_week, is_next_week, is_this_month, is_next_month

DEFAULT_SECTIONS_RULES: dict[int, Callable[[datetime], bool]] = {
    1: lambda check: is_today(check),
    2: lambda check: is_tomorrow(check),
    3: lambda check: is_this_week(check),
    4: lambda check: is_next_week(check),
    5: lambda check: is_this_month(check),
    6: lambda check: is_next_month(check),
    99: lambda check: True
}

DATE_FORMAT = "%d.%m.%Y"


class Section:
    calendarId: int
    beginTimestamp: int
    endTimestamp: int | None = None
    name: str

    def __init__(self, data: list | None = None):
        """
        :param data: for parsing fields from the database.
        """
        if data:
            self.calendarId, self.beginTimestamp, self.endTimestamp, self.name = data

    def __repr__(self) -> str:
        return f"Section[{self.calendarId}] BeginTimestamp:{self.beginTimestamp} EndTimestamp:{self.endTimestamp} Name:{self.name}"

    def __str__(self) -> str:
        return f"---==[  {self.name}  ]==---"

    def double_str(self, other: object) -> str:
        if isinstance(other, Section):
            return f"---==[  {self.name}  ]=[  {other.name}  ]==---"
        return f"{self} | {other}\n-# Did not receive correct custom section"

    def __eq__(self, other: object):
        return (isinstance(other, Section) and self.beginTimestamp == other.beginTimestamp
                and self.endTimestamp == other.endTimestamp and self.name == other.name
                and self.calendarId == other.calendarId)

    @staticmethod
    def _parse_date(date: str) -> int:
        if len(date.split(".")) == 2:
            date += f".{datetime.now().year}"

        return int(datetime.strptime(date, DATE_FORMAT).timestamp())

    @property
    def begin_date(self) -> str:
        return datetime.fromtimestamp(self.beginTimestamp).strftime(DATE_FORMAT)

    @begin_date.setter
    def begin_date(self, date: str):
        self.beginTimestamp = self._parse_date(date)

    @property
    def end_date(self) -> str | None:
        if self.endTimestamp:
            return datetime.fromtimestamp(self.endTimestamp).strftime(DATE_FORMAT)
        return None

    @end_date.setter
    def end_date(self, date: str | None):
        if date and date != "":
            self.endTimestamp = self._parse_date(date)
        else:
            self.endTimestamp = None

    def insert(self):
        Db().execute("INSERT INTO sections (CalendarId, BeginTimestamp, EndTimestamp, Name) VALUES (?, ?, ?, ?)",
                     (self.calendarId, self.beginTimestamp, self.endTimestamp, self.name))

    def fetch(self, calendar_id: int, begin_timestamp: int):
        self.__init__(Db().fetch_one("SELECT * FROM sections WHERE CalendarId = ? AND BeginTimestamp = ?",
                                     (calendar_id, begin_timestamp)))

    def delete(self):
        logger = get_logger(LogType.CALENDAR, self.calendarId)
        logger.warning(f"Deleting section {repr(self)}")
        Db().execute("DELETE FROM sections WHERE CalendarId = ? AND BeginTimestamp = ?",
                     (self.calendarId, self.beginTimestamp))
        logger.info("Bye. Bye.")


DEFAULT_SECTIONS = [Section([0, 1, None, "Dzisiaj"]),
                    Section([0, 2, None, "Jutro"]),
                    Section([0, 3, None, "W tym tygodniu"]),
                    Section([0, 4, None, "Za tydzień"]),
                    Section([0, 5, None, "W tym miesiącu"]),
                    Section([0, 6, None, "Za miesiąc"]),
                    Section([0, 99, None, "W przyszłości"])]


def delete_all_sections(calendar_id: int):
    Db().execute("DELETE FROM sections WHERE CalendarId = ?", (calendar_id,))


def select_section(custom_sections: list[Section], timestamp: int) -> tuple[Section | None, Section | None]:
    now = datetime.now()
    check = datetime.fromtimestamp(timestamp)

    selected_custom_section = selected_section = None

    if check.date() >= now.date():
        if custom_sections:
            custom_sections.sort(key=lambda section: section.beginTimestamp, reverse=True)
            for custom_section in custom_sections:
                if custom_section.beginTimestamp <= timestamp <= custom_section.endTimestamp:
                    selected_custom_section = custom_section
                    break

        for section in DEFAULT_SECTIONS:
            rule = DEFAULT_SECTIONS_RULES.get(section.beginTimestamp)
            if rule(check):
                selected_section = section
                break
    return selected_section, selected_custom_section


def fetch_outdated_sections() -> list[Section]:
    return Db().fetch_all("SELECT * FROM sections WHERE EndTimestamp < ?", (datetime.now().timestamp()))
