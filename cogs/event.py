from datetime import datetime

import discord
from discord.ext import commands

from global_functions import *


class AddEventModal(discord.ui.Modal, title="Dodaj wydarzenie"):
    # TODO check for date format and time format optionally
    date = discord.ui.TextInput(label="Data", placeholder="Podaj datę (na przykład 1.12.2025)")
    time = discord.ui.TextInput(label="Godzina", placeholder="Podaj godzinę", required=False)
    name = discord.ui.TextInput(label="Nazwa", placeholder="Podaj nazwę wydarzenia")
    group = discord.ui.TextInput(label="Grupa", placeholder="Podaj grupę (np. 1, 3B)", required=False)
    place = discord.ui.TextInput(label="Miejsce", placeholder="Podaj miejsce wydarzenia", required=False)

    async def on_submit(self, interaction: discord.Interaction) -> None:

        if self.time.value:
            dt = datetime.strptime(f"{self.date.value} {self.time.value.replace(".", ":")}", "%d.%m.%Y %H:%M")
            whole_day = False
        else:
            dt = datetime.strptime(self.date.value, "%d.%m.%Y")
            whole_day = True
        timestamp = int(dt.timestamp())

        connection, cursor = db_connect()
        cursor.execute("SELECT Id FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                       (interaction.guild.id, interaction.channel.id))
        calendar_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO events (CalendarId, Timestamp, WholeDay, Name, Team, Place) VALUES (?, ?, ?, ?, ?, ?)",
            (calendar_id, timestamp, whole_day, self.name.value, self.group.value, self.place.value))
        connection.commit()
        db_disconnect(connection, cursor)

        await interaction.response.send_message(f'Dodano wydarzenie *{self.name}* do kalendarza', ephemeral=True)


class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    event_group = discord.app_commands.Group(name="event", description="Komendy do zarządzania wydarzeniami")

    @event_group.command(name="add", description="Dodaje nowe wydarzenie")
    async def add(self, interaction: discord.Interaction):
        if not await check_user(interaction): return

        connection, cursor = db_connect()
        if not await check_if_calendar_exists(interaction, connection, cursor): return
        db_disconnect(connection, cursor)

        print("[INFO]\tAdding event")
        await interaction.response.send_modal(AddEventModal())

    @event_group.command(name="edit", description="Zmienia istniejące wydarzenie")
    @discord.app_commands.describe(event_id="Numer wydarzenia do edycji (od najstarszego / od góry)", date="Data",
                                   time="Godzina (Wpisz '-' aby wydarzenie trwało cały dzień)", name="Nazwa wydarzenia",
                                   group="Grupa przypisana do wydarzenia", place="Miejsce ")
    async def edit(self, interaction: discord.Interaction, event_id: int, date: str | None, time: str | None,
                   name: str | None, group: str | None, place: str | None):
        if not await check_user(interaction): return

        connection, cursor = db_connect()
        if not await check_if_calendar_exists(interaction, connection, cursor): return

        if not await check_if_event_id_exists(interaction, connection, cursor, event_id): return

        print(f"[INFO]\tEditing event number {event_id}")
        cursor.execute("SELECT events.Id FROM events JOIN calendars ON events.CalendarId = calendars.Id "
                       "WHERE GuildId = ? AND ChannelId = ? ORDER BY events.Timestamp LIMIT 1 OFFSET ?",
                       (interaction.guild.id, interaction.channel.id, event_id - 1))
        db_event_id = cursor.fetchone()[0]

        if time or date:
            cursor.execute("SELECT timestamp, WholeDay FROM events WHERE Id = ?", (db_event_id,))
            old_timestamp, old_whole_day = cursor.fetchone()
            if not date:
                date = datetime.fromtimestamp(old_timestamp).date()
                date = f"{date:%d.%m.%Y}"
            if not time and not old_whole_day:
                time = datetime.fromtimestamp(old_timestamp).time()
                time = f"{time:%H:%M}"

            if time and time != "-":
                dt = datetime.strptime(f"{date} {time}", "%d.%m.%Y %H:%M")
                whole_day = False
            else:
                dt = datetime.strptime(date, "%d.%m.%Y")
                whole_day = True
            timestamp = int(dt.timestamp())

            cursor.execute("UPDATE events SET Timestamp = ?, WholeDay = ? WHERE Id = ?",
                           (timestamp, whole_day, db_event_id))

        if name:
            cursor.execute("UPDATE events SET Name = ? WHERE Id = ?", (name, db_event_id))
        if group:
            cursor.execute("UPDATE events SET Team = ? WHERE Id = ?", (group, db_event_id))
        if place:
            cursor.execute("UPDATE events SET Place = ? WHERE Id = ?", (place, db_event_id))
        connection.commit()
        db_disconnect(connection, cursor)

        await interaction.response.send_message(f'Wydarzenie numer {event_id} zostało zmienione', ephemeral=True)

    delete_group = discord.app_commands.Group(name="delete", description="Komendy do usuwania wydarzeń",
                                              parent=event_group)

    @delete_group.command(name="one", description="Usuwa wydarzenie")
    @discord.app_commands.describe(event_id="Numer wydarzenia do usunięcia (od najstarszego / od góry)")
    async def one(self, interaction: discord.Interaction, event_id: int):
        if not await check_user(interaction): return

        connection, cursor = db_connect()
        if not await check_if_calendar_exists(interaction, connection, cursor): return

        if not await check_if_event_id_exists(interaction, connection, cursor, event_id): return

        print(f"[INFO]\tDeleting event number {event_id}")
        cursor.execute(
            "DELETE FROM events WHERE Id = (SELECT events.Id FROM events JOIN calendars ON events.CalendarId = calendars.Id "
            "WHERE GuildId = ? AND ChannelId = ? ORDER BY events.Timestamp LIMIT 1 OFFSET ?)",
            (interaction.guild.id, interaction.channel.id, event_id - 1))
        connection.commit()
        db_disconnect(connection, cursor)
        await interaction.response.send_message(f'Wydarzenie numer {event_id} zostało usunięte', ephemeral=True)

    @delete_group.command(name="expired", description="Usuwa przedawnione wydarzenia")
    async def expired(self, interaction: discord.Interaction):
        if not await check_user(interaction): return

        connection, cursor = db_connect()
        if not await check_if_calendar_exists(interaction, connection, cursor): return

        print("[INFO]\tDeleting expired events")
        current_day = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())

        cursor.execute("DELETE FROM events WHERE timestamp < ? AND CalendarId = (SELECT CalendarId FROM events "
                       "JOIN calendars ON events.CalendarId = calendars.Id WHERE GuildId = ? AND ChannelId = ?)",
                       (current_day, interaction.guild.id, interaction.channel.id))
        connection.commit()
        db_disconnect(connection, cursor)
        await interaction.response.send_message('Usunięto przedawnione wydarzenia', ephemeral=True)


async def setup(bot):
    await bot.add_cog(EventCog(bot))
