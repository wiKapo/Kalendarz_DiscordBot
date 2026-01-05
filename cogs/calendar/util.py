from datetime import timedelta

import discord

from g.util import *

DEFAULT_TITLE = "Kalendarz by wiKapo"


def delete_old_messages():
    # dated 3 weeks ago
    cutoff_timestamp = int((datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) -
                            timedelta(weeks=3)).timestamp())
    old_events = Db().fetch_all("SELECT * FROM events WHERE Timestamp < ?", (cutoff_timestamp,))
    print("[INFO]\tDeleting old messages")
    for old_event in old_events:
        print(f"\n{old_event}")
    Db().execute("DELETE FROM events WHERE Timestamp < ?", (cutoff_timestamp,))


async def recreate_calendar(calendar_id: int, interaction: discord.Interaction):
    new_msg = await interaction.channel.send("Nowa wiadomość kalendarza")
    Db().execute("UPDATE calendars SET MessageId = ? WHERE Id = ?", (new_msg.id, calendar_id))

    await update_calendar(interaction, calendar_id)

    await interaction.response.send_message("Odtworzono kalendarz.")


def create_calendar_message(calendar_id: int):
    show_sections, title = Db().fetch_one("SELECT ShowSections, Title FROM calendars WHERE Id = ?", (calendar_id,))

    events = Db().fetch_all(
        "SELECT Timestamp, WholeDay, Name, Team, Place FROM events JOIN calendars "
        "ON events.CalendarId = calendars.Id WHERE calendars.Id = ? ORDER BY timestamp", (calendar_id,))

    if len(events) == 0:
        message = "\nPUSTE"
    else:
        message = ""
        current_day_delta = 0
        for event in events:
            message += "\n"
            delta_days = (datetime.fromtimestamp(event[0]).date() - datetime.now().date()).days

            if show_sections:  # TODO make sections dynamic and per calendar
                if delta_days >= 0 and delta_days >= current_day_delta != 99:
                    if delta_days < 1:
                        message += "\n\t---==[  Dzisiaj  ]==---\n"
                        current_day_delta = 1
                    elif delta_days < 2:
                        message += "\n\t---==[  Jutro  ]==---\n"
                        current_day_delta = 2
                    elif delta_days < 7:
                        message += "\n\t---==[  W tym tygodniu  ]==---\n"
                        current_day_delta = 7
                    elif delta_days < 14:
                        message += "\n\t---==[  Za tydzień  ]==---\n"
                        current_day_delta = 14
                    elif delta_days < 30:
                        message += "\n\t---==[  W tym miesiącu  ]==---\n"
                        current_day_delta = 30
                    elif delta_days < 60:
                        message += "\n\t---==[  Za miesiąc  ]==---\n"
                        current_day_delta = 60
                    else:
                        message += "\n\t---==[  W przyszłości  ]==---\n"
                        current_day_delta = 99

            # If expired
            if delta_days < 0:
                message += "~~"

            # Timestamp
            message += f"<t:{str(event[0])}"
            if event[1]:
                message += ":D"
            message += "> "

            # Group
            if event[3]:
                message += f"[{event[3]}] "
            # Name
            message += f"**{event[2]}"
            # Place
            if event[4]:
                message += f" @ {event[4]}"
            message += " **"

            # If expired
            if delta_days < 0:
                message += "~~"

    if title is None:
        title = DEFAULT_TITLE

    return title, message


async def update_calendar(interaction: discord.Interaction, calendar_id: int):
    title, message = create_calendar_message(calendar_id)

    print(f"[INFO]\tUpdating calendar {title} in [{interaction.guild.name} - {interaction.guild.id}]"
          f" in [{interaction.channel.name} - {interaction.channel.id}]")

    calendar_message_id = Db().fetch_one("SELECT MessageId FROM calendars WHERE Id = ?", (calendar_id,))[0]
    calendar_message = await interaction.channel.fetch_message(calendar_message_id)

    await calendar_message.edit(content=f':calendar:\t{title}\t:calendar:{message}')


async def bot_update_calendar(self, calendar_id: int):
    title, message = create_calendar_message(calendar_id)

    print(f"[INFO]\tBot is updating calendar {title}")
    guild_id, channel_id, calendar_message_id = Db().fetch_one(
        "SELECT GuildId, ChannelId, MessageId FROM calendars WHERE Id = ?", (calendar_id,))

    calendar_message = await ((await (await self.bot.fetch_guild(guild_id)).fetch_channel(channel_id))
                              .fetch_message(calendar_message_id))

    await calendar_message.edit(content=f':calendar:\t{title}\t:calendar:{message}')
