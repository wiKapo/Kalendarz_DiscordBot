import os
from datetime import datetime

from g.classes import Db


async def check_if_calendar_exists(interaction) -> None | int:
    calendar_id = Db().fetch_one("SELECT Id FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                                 (interaction.guild.id, interaction.channel.id))[0]
    if not calendar_id:
        await interaction.response.send_message('Kalendarz nie istnieje na tym kanale', ephemeral=True)
        return None
    return calendar_id


async def check_admin(interaction) -> bool:
    if (await interaction.guild.fetch_member(interaction.user.id)).guild_permissions.administrator:
        return True

    admins = map(int, os.getenv("USERS").split(','))
    if interaction.user.id in admins:
        return True
    return False


async def check_manager(interaction) -> bool:
    managers = Db().fetch_all('SELECT UserId FROM users WHERE GuildId = ?', (interaction.guild.id,))
    allowed_users = map(lambda a: a[0], managers)

    return interaction.user.id in allowed_users


async def check_user(interaction) -> bool:
    if await check_admin(interaction): return True
    if await check_manager(interaction): return True
    return False


async def check_if_event_id_exists(interaction, event_id) -> bool:
    amount_of_events = Db().fetch_one("SELECT COUNT(*) FROM events JOIN calendars ON events.CalendarId = calendars.Id "
                                      "WHERE GuildId = ? AND ChannelId = ?",
                                      (interaction.guild.id, interaction.channel.id))[0]
    if amount_of_events >= event_id:
        return True
    await interaction.response.send_message(f"Wydarzenie o id {event_id} nie istnieje", ephemeral=True)
    return False


def text_to_timestamp(time: str, date: str) -> tuple[int, bool]:
    if time == "":
        if len(date.split(".")) == 2:
            date += f".{datetime.now().year}"
        dt = datetime.strptime(date, "%d.%m.%Y")
        whole_day = True
    else:
        dt = datetime.strptime(f"{date} {time.replace(".", ":")}", "%d.%m.%Y %H:%M")
        whole_day = False
    timestamp = int(dt.timestamp())

    return timestamp, whole_day


def timestamp_to_text(timestamp: int, whole_day: bool) -> tuple[str, str]:
    dt = datetime.fromtimestamp(timestamp)

    if whole_day:
        time = ""
    else:
        time = dt.strftime("%H:%M")

    date = dt.strftime("%d.%m.%Y")

    return time, date
