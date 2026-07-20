from collections.abc import Callable
from datetime import datetime

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


class Section:
    calendarId: int = None
    timestamp: int | None = None
    name: str = None

    def __init__(self, data: list = None):
        """
        :param data: for parsing fields from the database.
        """
        if data:
            self.calendarId, self.timestamp, self.name = data

    def __repr__(self):
        return f"Section[{self.calendarId}] Timestamp:{self.timestamp} Name:{self.name}"

    def __str__(self):
        return f"---==[  {self.name}  ]==---"

    def double_str(self, other):
        return f"---==[  {self.name}  ][  {other.name}  ]==---"

    def __eq__(self, other):
        return (isinstance(other, Section) and self.timestamp == other.timestamp
                and self.name == other.name and self.calendarId == other.calendarId)

    def timestamp_to_text(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%d.%m.%Y")

    def text_to_timestamp(self, date: str):
        if len(date.split(".")) == 2:
            date += f".{datetime.now().year}"

        self.timestamp = int(datetime.strptime(date, "%d.%m.%Y").timestamp())

    def create_modal_text(self):
        return f"{self.timestamp_to_text()}-{self.name}"

    def insert(self):
        Db().execute("INSERT INTO sections (CalendarId, Timestamp, Name) VALUES (?, ?, ?)",
                     (self.calendarId, self.timestamp, self.name))


DEFAULT_SECTIONS = [Section([0, 1, "Dzisiaj"]),
                    Section([0, 2, "Jutro"]),
                    Section([0, 3, "W tym tygodniu"]),
                    Section([0, 4, "Za tydzień"]),
                    Section([0, 5, "W tym miesiącu"]),
                    Section([0, 6, "Za miesiąc"]),
                    Section([0, 99, "W przyszłości"])]


def delete_all_sections(calendar_id: int):
    Db().execute("DELETE FROM sections WHERE CalendarId = ?", (calendar_id,))


def select_section(custom_sections: list[Section], timestamp: int) -> tuple[Section | None, Section | None]:
    now = datetime.now()
    check = datetime.fromtimestamp(timestamp)

    selected_custom_section = selected_section = None

    if check.date() >= now.date():
        if custom_sections:
            custom_sections.sort(key=lambda s: s.timestamp, reverse=True)
            for section in custom_sections:
                if timestamp >= section.timestamp:
                    selected_custom_section = section
                    break

        for section in DEFAULT_SECTIONS:
            rule = DEFAULT_SECTIONS_RULES.get(section.timestamp)
            if rule(now, check):
                selected_section = section
                break
    return selected_section, selected_custom_section
