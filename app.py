import asyncio

from discord.ext import commands
from dotenv import load_dotenv

from cogs.calendar.util import admin_update_calendar
from g.util import *

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents, help_command=None)


# TODO log to file
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    try:
        synced_commands = await bot.tree.sync()
        print(f"Synced {len(synced_commands)} commands")
    except Exception as e:
        print("Error with syncing bot commands: ", e)

    try:
        Db().execute('CREATE TABLE IF NOT EXISTS calendars ('
                     'Id INTEGER PRIMARY KEY AUTOINCREMENT,'
                     'Title TEXT,'
                     'ShowSections BOOLEAN NOT NULL DEFAULT FALSE,'
                     'GuildId BIGINT NOT NULL,'
                     'ChannelId BIGINT NOT NULL,'
                     'MessageId BIGINT NOT NULL,'
                     'UserRoleId BIGINT,'
                     'PingRoleId BIGINT,'
                     'PingMessageId BIGINT'
                     ');')
        Db().execute('CREATE TABLE IF NOT EXISTS events ('
                     'Id INTEGER PRIMARY KEY AUTOINCREMENT,'
                     'CalendarId INTEGER NOT NULL REFERENCES calendars(Id) ON DELETE CASCADE,'
                     'Timestamp INT NOT NULL,'
                     'WholeDay BOOLEAN NOT NULL,'
                     'Name TEXT NOT NULL,'
                     'Team TEXT,'
                     'Place TEXT'
                     ');')
        Db().execute('CREATE TABLE IF NOT EXISTS users ('
                     'Id INTEGER PRIMARY KEY AUTOINCREMENT,'
                     'UserId BIGINT NOT NULL,'
                     'GuildId BIGINT NOT NULL'
                     ');')
        Db().execute('CREATE TABLE IF NOT EXISTS notifications ('
                     'Id INTEGER PRIMARY KEY AUTOINCREMENT,'
                     'UserId BIGINT NOT NULL,'
                     'EventId INTEGER NOT NULL REFERENCES events(Id) ON DELETE CASCADE,'
                     'Timestamp INT NOT NULL,'
                     'TimeTag TEXT NOT NULL,'
                     'Description TEXT'
                     ');')
        Db().execute('CREATE TABLE IF NOT EXISTS messages ('
                     'Id INTEGER PRIMARY KEY AUTOINCREMENT,'
                     'CalendarId BIGINT NOT NULL REFERENCES calendars(Id) ON DELETE CASCADE,'
                     'Timestamp INT NOT NULL,'
                     'DeleteBy INT NOT NULL,'
                     'Message TEXT NOT NULL'
                     ');')

        print('Tables are ready')
    except Exception as e:
        print("Error with syncing database: ", e)


async def load():
    for filename in os.listdir("./cogs"):
        if not filename.endswith("__"):
            await bot.load_extension(f"cogs.{filename}.{filename}")


async def main():
    async with bot:
        await load()
        await bot.start(os.getenv("BOT_TOKEN"))

@bot.tree.command(name="update_all", description="[TYLKO DLA ADMINÓW KALENDARZA] Aktualizuje wszystkie wiadomości kalendarza do najnowszej werjsi")
async def update_all_calendars(interaction: discord.Interaction):
    admins = map(int, os.getenv("USERS").split(','))
    if interaction.user.id not in admins:
        await interaction.response.send_message("Brak uprawnień\n**Zarejestrowano próbę użycia komendy** :wink:", ephemeral=True)
        print(f"[{interaction.user.id} - {interaction.user.name}] tried to use update_all command")
        return

    await interaction.response.send_message("Aktualizowanie wszystkich kalendarzy. Poczekaj na potwierdzenie wykonania akcji.", ephemeral=True)

    calendars = fetch_all_calendars()
    for calendar in calendars:
        message = Message()
        message.calendarId = calendar.id
        message.set_time(5)
        message.message = "**Aktualizacja kalendarza** Dodano listę ostatnich zmian kalendarza"  # TODO ALWAYS UPDATE ME
        message.insert_with_check()
        try:
            await admin_update_calendar(bot, calendar)
        except Exception as e:
            print(e)
            return
        print(f"UPDATED: {calendar}")

    await interaction.followup.send(f"Zaktualizowano wszystkie kalendarze w ilości: `{len(calendars)}`", ephemeral=True)

@bot.tree.command(name="about")
async def about(interaction: discord.Interaction):
    await interaction.response.send_message("Bot stworzony przez wiKapo", ephemeral=True)


@bot.tree.command(name="help")
async def help(interaction: discord.Interaction):
    print("HI")
    message = """## Kalendarz by wiKapo
### ---==[ Polecenia kalendarza ]==---
`/calendar create <title|show_sections>` - Tworzy nowy kalendarz.
Można opcjonalnie podać nazwę kalendarza oraz zdecydować, czy kalendarz ma dzielić wydarzenia na sekcje.
Kalendarz jest aktualizowany automatycznie, **codziennie o godzinie 0:00 UTC**.
W przypaku usunięcia **wiadomości** z kalendarzem wykonaj ponownie `/calendar create`, która odtworzy wiadomość kalendarza.

`/calendar edit` - Otwiera okienko edycji kalendarza. Umożliwia zmianę tytułu i sekcji kalendarza.
`/calendar delete` - **Permamentnie** usuwa kalendarz z tego kanału **RAZEM z wydarzeniami**. Tej operacji nie można cofnąć.
`/calendar update` - Aktualizuje kalendarz z tego kanału. (Komenda nie powinna być już potrzebna)

### ---==[ Polecenia wydarzeń ]==---
`/event add` - Dodaje wydarzenie. Dodane wydarzenia będą usuwane po 3 tygodniach od dnia wydarzenia.
`/event edit <event_id>` - Wysyła wiadomość z polem wyboru wydarzenia do edycji. Po wyborze wydarzenia otwiera okienko edycji.
Podając `event_id` wydarzenia wysyła od razu okienko edycji.
`/event delete <event_id>` - Otwiera okienko z polem wyboru wydarzeń do usunięcia. Po wyborze wydarzeń usuwa je.
Podając `event_id` wydarzenia wysyła od razu je usuwa. **Tej operacji nie można cofnąć**.
"""
    await interaction.response.send_message(message, ephemeral=True)

    message = """~~### ---==[ Polecenia menedżerów ]==---~~ *(w następnej aktualizacji zostanie zastąpione rolami)*
~~Menedżerowie są dodawani przez administratorów serwera do danego serwera.
Dodani menedżerowie otrzymują dostęp do tworzenia, edycji, usuwania kalendarza i wydarzeń na danym serwerze.
Mendżerowie nie mogą dodawać nowych mendżerów.

`/user add [user]` - Dodaje nowego menedżera do tego serwera.
`/user list` - Wyświetla menedżerów dodanych do tego serwera.
`/user remove [user]` - Usuwa menedżera z tego serwera. **Tej operacji nie można cofnąć**.~~

### ---==[ Polecenia powiadomień ]==---
`/notification add <event_id>` - Wysyła wiadomość z polem wyboru wydarzenia do którego ma dodać powiadomienia.
Po wyborze wydarzenia otwiera okienko tworzenia powiadomień. Podając `event_id` od razu pokazuje okienko tworzenia.
(WIP) ~~`/notification edit <event_id>` - Wysyła wiadomość z listą wydarzeń. Po wyborze wydarzenia wysyła wiadomość z listą powiadomień przypisanych do tego wydarzenia.
Podając `event_id` pokazuje od razu listę powiadomień. Po wyborze powiadomienia otwiera okienko edycji wybranego powiadomienia.~~
`/notification delete <event_id>` - Wysyła wiadomość z listą wydarzeń. Po wyborze wydarzenia otwiera okienko z listą powiadomień przypisanych do tego wydarzenia.
Podając `event_id` pokazuje od razu to okienko. Po wyborze powiadomień usuwa je. **Tej operacji nie można cofnąć**.
`/notification list` - Wysyła wiadomość z listą powiadomień użytkownika
    
    ### ---==[ Inne polecenia ]==---
    `/about` - informacja o autorze
    `/help` - pokazuje tą wiadomość"""

    await interaction.followup.send(message, ephemeral=True)


asyncio.run(main())
