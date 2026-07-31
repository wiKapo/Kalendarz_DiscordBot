from collections.abc import Callable
from datetime import datetime

from discord import SelectOption

from g.classes.db import Db

DEFAULT_SECTIONS_RULES: dict[int, Callable[[datetime, datetime], bool]] = {
    1: lambda now, check: now.day == check.day and now.month == check.month and now.year == check.year,
    2: lambda now, check: now.day + 1 == check.day and now.month == check.month and now.year == check.year,
    3: lambda now, check: now.isocalendar()[1] == check.isocalendar()[1] and now.year == check.year,
    4: lambda now, check: now.isocalendar()[1] + 1 == check.isocalendar()[1] and now.year == check.year,
    5: lambda now, check: now.month == check.month and now.year == check.year,
    6: lambda now, check: now.month + 1 == check.month and now.year == check.year,
    99: lambda now, check: True
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

    def __repr__(self):
        return f"Section[{self.calendarId}] BeginTimestamp:{self.beginTimestamp} EndTimestamp:{self.endTimestamp} Name:{self.name}"

    def __str__(self):
        return f"---==[  {self.name}  ]==---"

    def double_str(self, other):
        return f"---==[  {self.name}  ]=[  {other.name}  ]==---"

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
        self.__init__(Db().fetch_all("SELECT * FROM sections WHERE CalendarId = ? AND BeginTimestamp = ?",
                                     (calendar_id, begin_timestamp)))

    def delete(self):
        Db().execute("DELETE FROM sections WHERE CalendarId = ? AND BeginTimestamp = ?",
                     (self.calendarId, self.beginTimestamp))


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
            custom_sections.sort(key=lambda s: s.timestamp, reverse=True)
            for custom_section in custom_sections:
                if custom_section.beginTimestamp <= timestamp <= custom_section.endTimestamp:
                    selected_custom_section = custom_section
                    break

        for section in DEFAULT_SECTIONS:
            rule = DEFAULT_SECTIONS_RULES.get(section.beginTimestamp)
            if rule(now, check):
                selected_section = section
                break
    return selected_section, selected_custom_section


def format_section_options(sections: list[Section]) -> list[SelectOption]:
    options = []
    for section in sections:
        options.append(SelectOption(
            label=section.name,
            description=f"Zaczyna się {section.begin_date}"
                        f"{f', a kończy {section.end_date}' if section.end_date else ''}",
            value=f"{section.calendarId}.{section.beginTimestamp}"
        ))
    return options
