import os
import sqlite3
from datetime import datetime

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix='/', intents=intents)

DEFAULT_TITLE = "Kalendarz by wiKapo"


def db_connect():
    connection = sqlite3.connect('calendar_database.db')
    cursor = connection.cursor()
    print('Connected to SQLite')
    return connection, cursor


def db_disconnect(connection, cursor):
    cursor.close()
    connection.close()
    print('Disconnected from SQLite')


async def check_if_calendar_exists(interaction, connection, cursor) -> bool:
    cursor.execute("SELECT * FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                   (interaction.guild.id, interaction.channel.id))
    if not cursor.fetchone():
        await interaction.response.send_message('Kalendarz nie istnieje na tym kanale', ephemeral=True)
        db_disconnect(connection, cursor)
        return False
    return True


async def check_user(interaction) -> bool:
    admins = map(int, os.getenv("USERS").split(','))

    if interaction.user.id in admins:
        return True

    connection, cursor = db_connect()
    cursor.execute('SELECT UserId FROM users WHERE GuildId = ?', (interaction.guild.id,))
    allowed_users = map(lambda a: a[0], cursor.fetchall())
    db_disconnect(connection, cursor)

    if interaction.user.id in allowed_users:
        return True

    await interaction.response.send_message('Brak dostępu ;)', ephemeral=True)
    return False


async def check_if_event_id_exists(interaction, connection, cursor, event_id) -> bool:
    cursor.execute("SELECT COUNT(*) FROM events JOIN calendars ON events.CalendarId = calendars.Id "
                   "WHERE GuildId = ? AND ChannelId = ?", (interaction.guild.id, interaction.channel.id))
    if cursor.fetchone()[0] >= event_id:
        return True
    db_disconnect(connection, cursor)
    await interaction.response.send_message(f"Wydarzenie o id {event_id} nie istnieje", ephemeral=True)
    return False


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    try:
        await bot.add_cog(CalendarCog(bot))
        await bot.add_cog(EventsCog(bot))
        await bot.add_cog(UsersCog(bot))
        synced_commands = await bot.tree.sync()
        print(f"Synced {len(synced_commands)} commands")
    except Exception as e:
        print("Error with syncing bot commands: ", e)

    connection, cursor = db_connect()
    cursor.execute('CREATE TABLE IF NOT EXISTS events ('
                   'Id INTEGER PRIMARY KEY AUTOINCREMENT,'
                   'CalendarId BIGINT NOT NULL,'
                   'Timestamp INT NOT NULL,'
                   'WholeDay BOOLEAN NOT NULL,'
                   'Name TEXT NOT NULL,'
                   'Team TEXT,'
                   'Place TEXT'
                   ');')
    cursor.execute('CREATE TABLE IF NOT EXISTS users ('
                   'Id INTEGER PRIMARY KEY AUTOINCREMENT,'
                   'UserId BIGINT NOT NULL,'
                   'Name TEXT NOT NULL,'
                   'GuildId BIGINT NOT NULL'
                   ')')
    cursor.execute('CREATE TABLE IF NOT EXISTS calendars ('
                   'Id INTEGER PRIMARY KEY AUTOINCREMENT,'
                   'Title TEXT,'
                   'GuildId BIGINT NOT NULL,'
                   'ChannelId BIGINT NOT NULL,'
                   'MessageId BIGINT NOT NULL'
                   ');')

    print('Tables are ready')
    db_disconnect(connection, cursor)


class DeleteCalendarModal(discord.ui.Modal, title="Czy na pewno chcesz usunąć ten kalendarz?"):
    _ = discord.ui.TextInput(label="Wyślij aby potwierdzić",
                             placeholder="placeholder, bo discord jest głupi i musi być text input",
                             default="Usuwając kalendarz usuniesz również wydarzenia!", required=False)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        connection, cursor = db_connect()
        cursor.execute("SELECT Id, MessageId FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                       (interaction.guild.id, interaction.channel.id))
        calendar_id, calendar_message_id = cursor.fetchone()
        calendar_message = await (await interaction.guild.fetch_channel(interaction.channel.id)).fetch_message(
            calendar_message_id)
        await calendar_message.delete()

        cursor.execute("DELETE FROM events WHERE CalendarId = ?", (calendar_id,))
        cursor.execute("DELETE FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                       (interaction.guild.id, interaction.channel.id))
        connection.commit()
        db_disconnect(connection, cursor)
        await interaction.response.send_message("Kalendarz został usunięty RAZEM z wydarzeniami", ephemeral=True)


class CalendarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    cal_group = discord.app_commands.Group(name="calendar", description="Polecenia kalendarza")

    @cal_group.command(name="create", description="Tworzy nowy kalendarz")
    @discord.app_commands.describe(title="Tytuł kalendarza")
    async def create(self, interaction: discord.Interaction, title: str | None):
        if not await check_user(interaction): return

        connection, cursor = db_connect()
        cursor.execute("SELECT * FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                       (interaction.guild.id, interaction.channel.id))
        if cursor.fetchone():
            await interaction.response.send_message('Kalendarz już istnieje na tym kanale', ephemeral=True)
        else:
            print("[INFO]\tCreating new calendar")

            show_title = title
            if show_title is None:
                show_title = DEFAULT_TITLE
            calendar_msg = await interaction.response.send_message(f':calendar:\t{show_title}\t:calendar:\nPUSTE')

            cursor.execute("INSERT INTO calendars (GuildId, ChannelId, MessageId, Title) VALUES (?, ?, ?, ?)",
                           (interaction.guild.id, interaction.channel.id, calendar_msg.message_id, title))
            connection.commit()

        db_disconnect(connection, cursor)

    @cal_group.command(name="update", description="Zaktualizuj kalendarz")
    async def update(self, interaction: discord.Interaction):
        if not await check_user(interaction): return
        connection, cursor = db_connect()
        if not await check_if_calendar_exists(interaction, connection, cursor): return

        print("[INFO]\tUpdating calendar")
        cursor.execute("SELECT MessageId FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                       (interaction.guild.id, interaction.channel.id))
        calendar_message_id = cursor.fetchone()[0]

        cursor.execute(
            "SELECT Timestamp, WholeDay, Name, Team, Place FROM events JOIN calendars ON events.CalendarId = calendars.Id "
            "WHERE calendars.GuildId = ? AND calendars.ChannelId = ? ORDER BY timestamp",
            (interaction.guild.id, interaction.channel.id))
        events = cursor.fetchall()
        cursor.execute("SELECT Title FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                       (interaction.guild.id, interaction.channel.id))
        title = cursor.fetchone()[0]
        db_disconnect(connection, cursor)

        calendar_message = await (await interaction.guild.fetch_channel(interaction.channel.id)).fetch_message(
            calendar_message_id)

        if len(events) == 0:
            message = "\nPUSTE"
        else:
            message = ""
            for event in events:
                message += "\n"

                # If expired
                if event[0] < int(datetime.now().timestamp()):
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
                if event[0] < int(datetime.now().timestamp()):
                    message += "~~"

        if title is None:
            title = DEFAULT_TITLE
        await calendar_message.edit(content=f':calendar:\t{title}\t:calendar:{message}')

        await interaction.response.send_message('Kalendarz został zaktualizowany', ephemeral=True)

    @cal_group.command(name="edit", description="Edytuj kalendarz")
    @discord.app_commands.describe(title="Tytuł kalendarza (pozostawione puste przywraca wartość domyślną)")
    async def edit(self, interaction: discord.Interaction, title: str | None):
        if not await check_user(interaction): return

        connection, cursor = db_connect()
        if not await check_if_calendar_exists(interaction, connection, cursor): return

        print("[INFO]\tEditing calendar")
        cursor.execute("UPDATE calendars SET Title = ? WHERE GuildId = ? AND ChannelId = ?",
                       (title, interaction.guild.id, interaction.channel.id))
        connection.commit()
        await interaction.response.send_message("Kalendarz został zmieniony", ephemeral=True)

        db_disconnect(connection, cursor)

    @cal_group.command(name="delete", description="Usuń kalendarz")
    async def delete(self, interaction: discord.Interaction):
        if not await check_user(interaction): return

        connection, cursor = db_connect()
        if not await check_if_calendar_exists(interaction, connection, cursor): return
        db_disconnect(connection, cursor)

        print("[INFO]\tDeleting calendar")
        await interaction.response.send_modal(DeleteCalendarModal())


class AddEventModal(discord.ui.Modal, title="Dodaj wydarzenie"):
    # TODO check for date format and time format optionally
    date = discord.ui.TextInput(label="Data", placeholder="Podaj datę (na przykład 1.12.2025)")
    time = discord.ui.TextInput(label="Godzina", placeholder="Podaj godzinę", required=False)
    name = discord.ui.TextInput(label="Nazwa", placeholder="Podaj nazwę wydarzenia")
    group = discord.ui.TextInput(label="Grupa", placeholder="Podaj grupę (np. 1, 3B)", required=False)
    place = discord.ui.TextInput(label="Miejsce", placeholder="Podaj miejsce wydarzenia", required=False)

    async def on_submit(self, interaction: discord.Interaction) -> None:

        if self.time.value:
            dt = datetime.strptime(f"{self.date.value} {self.time.value}", "%d.%m.%Y %H:%M")
        else:
            dt = datetime.strptime(self.date.value, "%d.%m.%Y")
        timestamp = int(dt.timestamp())

        if self.time.value:
            whole_day = False
        else:
            whole_day = True

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


class EventsCog(commands.Cog):
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

    @event_group.command(name="delete", description="Usuwa wydarzenie")
    @discord.app_commands.describe(event_id="Numer wydarzenia do usunięcia (od najstarszego / od góry)")
    async def delete(self, interaction: discord.Interaction, event_id: int):
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

    @event_group.command(name="delete_expired", description="Usuwa przedawnione wydarzenia")
    async def delete_expired(self, interaction: discord.Interaction):
        if not await check_user(interaction): return

        connection, cursor = db_connect()
        if not await check_if_calendar_exists(interaction, connection, cursor): return

        print("[INFO]\tDeleting expired events")
        cursor.execute(
            "DELETE FROM events WHERE Id = (SELECT events.Id FROM events JOIN calendars ON events.CalendarId = calendars.Id "
            "WHERE GuildId = ? AND ChannelId = ? AND timestamp < ?)",
            (interaction.guild.id, interaction.channel.id, int(datetime.now().timestamp())))
        connection.commit()
        db_disconnect(connection, cursor)
        await interaction.response.send_message('Usunięto przedawnione wydarzenia', ephemeral=True)

    @event_group.command(name="edit", description="Zmienia istniejące wydarzenie")
    @discord.app_commands.describe(event_id="Numer wydarzenia do edycji (od najstarszego / od góry)", date="Data",
                                   time="Godzina",
                                   name="Nazwa wydarzenia", group="Grupa przypisana do wydarzenia", place="Miejsce ")
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
            cursor.execute("SELECT timestamp FROM events WHERE Id = ?", (db_event_id,))
            old_timestamp = cursor.fetchone()[0]
            if not date:
                date = datetime.fromtimestamp(old_timestamp).date()
                date = f"{date:%d.%m.%Y}"
            if not time:
                time = datetime.fromtimestamp(old_timestamp).time()
                time = f"{time:%H:%M}"

            if time:
                dt = datetime.strptime(f"{date} {time}", "%d.%m.%Y %H:%M")
            else:
                dt = datetime.strptime(date, "%d.%m.%Y")
            timestamp = int(dt.timestamp())

            if time:
                whole_day = False
            else:
                whole_day = True

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


class UsersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    user_group = discord.app_commands.Group(name='user', description='Komendy do zarządzania menedżerami')

    @user_group.command(name="add", description="Dodaj menedżera do bota na tym serwerze")
    @discord.app_commands.describe(user="Użytkownik do dodania jako menedżer")
    async def add(self, interaction: discord.Interaction, user: discord.User):
        if not await check_user(interaction): return

        print(f"[INFO]\tAdding user {user.name}")
        connection, cursor = db_connect()
        cursor.execute("INSERT INTO users (UserId, Name, GuildId) VALUES (?, ?, ?)",
                       (user.id, user.name, interaction.guild.id))
        connection.commit()
        db_disconnect(connection, cursor)
        await interaction.response.send_message(
            f'Dodano użytkownika *{user.name}* jako menedżera kalendarza na tym serwerze', ephemeral=True)

    @user_group.command(name="remove", description="Usuń menedżera z tego serwera")
    @discord.app_commands.describe(user="Użytkownik do usunięcia")
    async def remove(self, interaction: discord.Interaction, user: discord.User):
        if not await check_user(interaction): return

        connection, cursor = db_connect()
        cursor.execute("SELECT * FROM users WHERE UserId = ? AND GuildId = ?", (user.id, interaction.guild.id))
        if cursor.fetchone():
            print(f"[INFO]\tRemoving user {user.name}")
            cursor.execute("DELETE FROM users WHERE UserId = ? AND GuildId = ?", (user.id, interaction.guild.id))
            connection.commit()
            await interaction.response.send_message(f'Usunięto użytkownika *{user.name}*', ephemeral=True)
        else:
            await interaction.response.send_message(f'Nie znaleziono użytkownika *{user.name}*', ephemeral=True)
        db_disconnect(connection, cursor)
        return


@bot.tree.command(name="about")
async def about(interaction: discord.Interaction):
    await interaction.response.send_message("Bot stworzony przez wiKapo", ephemeral=True)


bot.run(os.getenv("BOT_TOKEN"))
