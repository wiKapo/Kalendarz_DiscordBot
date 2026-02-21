import os
from datetime import datetime

import discord

from g.classes import *


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
    """
    Checks if the user is admin or manager AND if it is called in a guild
    """
    if not check_dm(interaction):
        if await check_admin(interaction): return True
        if await check_manager(interaction): return True
    return False


def check_dm(interaction) -> bool:
    return isinstance(interaction.channel, discord.channel.DMChannel)


async def check_if_event_id_exists(interaction, event_id) -> bool:
    amount_of_events = Db().fetch_one("SELECT COUNT(*) FROM events JOIN calendars ON events.CalendarId = calendars.Id "
                                      "WHERE GuildId = ? AND ChannelId = ?",
                                      (interaction.guild.id, interaction.channel.id))[0]
    if amount_of_events >= event_id:
        return True
    await interaction.response.send_message(f"Wydarzenie o id {event_id} nie istnieje", ephemeral=True)
    return False


def text_to_timestamp(time: str, date: str) -> tuple[int, bool]:
    if len(date.split(".")) == 2:
        date += f".{datetime.now().year}"

    if time == "":
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


def format_event(event: Event) -> str:
    message = ""

    # Timestamp
    message += f"<t:{str(event.timestamp)}"
    if event.wholeDay:
        message += ":D"
    message += "> "

    # Team
    if event.team:
        message += f"[{event.team}] "
    # Name
    message += f"**{event.name}"
    # Place
    if event.place:
        message += f" @ {event.place}"
    message += " **"

    return message


def format_event_entries(events: list[Event], selected_event: int | None = None) -> list[discord.SelectOption]:
    options = []
    for i, event in enumerate(events):
        time, date = timestamp_to_text(event.timestamp, event.wholeDay)
        if time != "": date = f"{date} {time}"

        description = ""
        if event.team != "":
            description += f'[{event.team}] '
        if event.place != "":
            description += event.place

        options.append(
            discord.SelectOption(
                label=f"{date} {event.name}",
                description=description,
                value=f"{i}",
                default=i == selected_event
            )
        )

    return options


async def send_error_message(interaction: discord.Interaction, error):
    command_name = interaction.command.qualified_name
    if isinstance(error, discord.app_commands.CheckFailure):
        if check_dm(interaction):
            print(f"[INFO]\tUser {interaction.user.name} tried to use /{command_name} in DM channel. LOL")
            await interaction.response.send_message(f"`/{command_name}` nie jest wspierane w prywatnych wiadomościach",
                                                    ephemeral=True)
        else:
            print(f"[INFO]\tUser {interaction.user.name} doesn't have permissions to use /{command_name}")
            await interaction.response.send_message("Brak uprawnień", ephemeral=True)
    else:
        print(f"[ERROR]\t{error}")
        await interaction.response.send_message(
            f"Błąd: {error}\nZgłoś do @wiKapo lub "
            f"w wątku: https://discord.com/channels/1284116042473279509/1474884364520259737", ephemeral=True)


def remove_old_events(events: list[Event]) -> list[Event]:
    for event in events:
        if event.timestamp < datetime.now().timestamp():
            events.remove(event)
    return events
