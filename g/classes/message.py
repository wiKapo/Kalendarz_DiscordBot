from datetime import datetime, timedelta

from discord import Guild, Role

from g.classes.db import Db


class Message:
    id: int = None
    calendarId: int = None
    timestamp: int = None
    deleteBy: int = None
    message: str = None

    def __init__(self, data: list = None):
        """
        :param data: for parsing fields from the database.
        """
        if data is not None:
            self.id, self.calendarId, self.timestamp, self.deleteBy, self.message = data

    def __repr__(self):
        return f"Message [{self.id}]: Event[{self.calendarId}] {self.timestamp} {self.deleteBy} {self.message}"

    def set_time(self, delay_in_days: int = 1):
        current_time = datetime.now()
        self.timestamp = int(current_time.timestamp())
        self.deleteBy = int((current_time + timedelta(days=delay_in_days)).timestamp())

    def insert_with_check(self):
        if not self.check_if_duplicate():
            self.insert()

    def insert(self):
        Db().execute("INSERT INTO messages (CalendarId, Timestamp, DeleteBy, Message) VALUES (?, ?, ?, ?)",
                     (self.calendarId, self.timestamp, self.deleteBy, self.message))

    def delete(self):
        Db().execute("DELETE FROM messages WHERE Id=?", (self.id,))

    def check_if_duplicate(self) -> bool:
        data = Db().fetch_one("SELECT * FROM messages WHERE CalendarId=? AND Message=?",
                              (self.calendarId, self.message))
        return data is not None


def fetch_outdated_update_messages(calendar_id: int, cutoff_timestamp: int) -> list[Message]:
    data = Db().fetch_all("SELECT * FROM messages WHERE CalendarId=? AND DeleteBy<?",
                          (calendar_id, cutoff_timestamp))
    return [Message(x) for x in data]


def delete_messages(messages: list[Message]):
    for message in messages: message.delete()


def fetch_messages_for_calendar(calendar_id: int) -> list[Message]:
    data = Db().fetch_all("SELECT * FROM messages WHERE CalendarId=?", (calendar_id,))
    return [Message(x) for x in data]


def fetch_manager_roles_for_guild(guild: Guild) -> list[Role]:
    role_ids = Db().fetch_all("SELECT RoleId FROM managerRoles WHERE GuildId=?", (guild.id,))
    return [guild.get_role(r[0]) for r in role_ids] if role_ids else []


def update_manager_roles_for_guild(guild_id: int, roles: list[Role]):
    Db().execute("DELETE FROM managerRoles WHERE GuildId=?", (guild_id,))  # remove all old roles

    if roles:  # if there are any roles, add them
        for role in roles:
            Db().execute("INSERT INTO managerRoles (GuildId, RoleId) VALUES (?, ?)", (guild_id, role.id))
