import discord

from g.util import *

NAME = 0
TIMESTAMP = 1
WHOLE_DAY = 2
TEAM = 3
PLACE = 4


def format_event(event: tuple) -> str:
    """
    Pass event in this pattern:\n
    Name, Timestamp, WholeDay, Team, Place
    """
    message = ""

    # Timestamp
    message += f"<t:{str(event[TIMESTAMP])}"
    if event[WHOLE_DAY]:
        message += ":D"
    message += "> "

    # Team
    if event[TEAM]:
        message += f"[{event[TEAM]}] "
    # Name
    message += f"**{event[NAME]}"
    # Place
    if event[PLACE]:
        message += f" @ {event[PLACE]}"
    message += " **"

    return message


def format_event_entries(interaction: discord.Interaction, selected_event: int | None = None) \
        -> list[discord.SelectOption]:
    events = Db().fetch_all(
        "SELECT Name, Timestamp, WholeDay, Team, Place FROM events JOIN calendars ON events.CalendarId = calendars.Id "
        "WHERE GuildId = ? AND ChannelId = ? ORDER BY timestamp", (interaction.guild.id, interaction.channel.id))

    options = []
    for i, event in enumerate(events):
        time, date = timestamp_to_text(event[TIMESTAMP], event[WHOLE_DAY])
        if time != "": date = f"{date} {time}"

        description = ""
        if event[TEAM] != "":
            description += f'[{event[TEAM]}] '
        if event[PLACE] != "":
            description += event[PLACE]

        options.append(
            discord.SelectOption(
                label=f"{date} {event[NAME]}",
                description=description,
                value=f'{i}',
                default=i == selected_event
            )
        )

    return options
