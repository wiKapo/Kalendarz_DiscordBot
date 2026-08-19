import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from g.classes.db import Db
from g.classes.logger import init_logger, get_logger
from g.util import BOT_VERSION

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents, help_command=None)

init_logger()
logger = get_logger()


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")
    print(f'We have logged in as {bot.user}')
    try:
        synced_commands = await bot.tree.sync()
        logger.info(f"Synced {len(synced_commands)} commands")
        print(f"Synced {len(synced_commands)} commands")
    except Exception as e:
        logger.error(f"Error with syncing database: {e}", exc_info=True)
        print(f"Error with syncing bot commands: {e}")

    try:
        Db().execute('CREATE TABLE IF NOT EXISTS calendars ('
                     'Id INTEGER PRIMARY KEY AUTOINCREMENT,'
                     'Title TEXT,'
                     'GuildId BIGINT NOT NULL,'
                     'ChannelId BIGINT NOT NULL,'
                     'MessageId BIGINT NOT NULL,'
                     'PingRoleId BIGINT,'
                     'DescriptionMessageId BIGINT'
                     ');')
        Db().execute('CREATE TABLE IF NOT EXISTS events ('
                     'Id INTEGER PRIMARY KEY AUTOINCREMENT,'
                     'Timestamp INT NOT NULL,'
                     'WholeDay BOOLEAN NOT NULL,'
                     'Name TEXT NOT NULL,'
                     'Team TEXT,'
                     'Place TEXT'
                     ');')
        Db().execute('CREATE TABLE IF NOT EXISTS eventsInCalendars ('
                     'CalendarId INTEGER NOT NULL REFERENCES calendars(Id) ON DELETE CASCADE,'
                     'EventId INTEGER NOT NULL REFERENCES events(Id) ON DELETE CASCADE,'
                     'PRIMARY KEY (CalendarId, EventId)'
                     ');')
        Db().execute('CREATE TABLE IF NOT EXISTS managerRoles ('
                     'GuildId INTEGER,'
                     'RoleId BIGINT NOT NULL,'
                     'PRIMARY KEY (GuildId, RoleId)'
                     ');')
        Db().execute('CREATE TABLE IF NOT EXISTS notifications ('
                     'UserId BIGINT NOT NULL,'
                     'CalendarId INTEGER NOT NULL REFERENCES calendars(Id) ON DELETE CASCADE,'
                     'PRIMARY KEY (UserId, CalendarId)'
                     ');')
        Db().execute('CREATE TABLE IF NOT EXISTS messages ('
                     'Id INTEGER PRIMARY KEY AUTOINCREMENT,'
                     'CalendarId BIGINT NOT NULL REFERENCES calendars(Id) ON DELETE CASCADE,'
                     'Timestamp INT NOT NULL,'
                     'DeleteBy INT NOT NULL,'
                     'Message TEXT NOT NULL'
                     ');')
        Db().execute('CREATE TABLE IF NOT EXISTS sections ('
                     'CalendarId INTEGER NOT NULL REFERENCES calendars(Id) ON DELETE CASCADE, '
                     'BeginTimestamp INT NOT NULL,'
                     'EndTimestamp INT,'
                     'Name TEXT NOT NULL,'
                     'PRIMARY KEY (CalendarId, BeginTimestamp)'
                     ');')

        logger.info('Tables are ready')
        print('Tables are ready')
    except Exception as e:
        logger.error(f"Error with syncing database: {e}", exc_info=True)
        print("Error with syncing database: ", e)


async def load():
    for filename in os.listdir("./cogs"):
        if not filename.endswith("__"):
            logger.debug(f"Loading {filename} cog...")
            print(f"Loading {filename} cog...")
            await bot.load_extension(f"cogs.{filename}.{filename}")


async def main():
    async with bot:
        await load()
        await bot.start(os.getenv("BOT_TOKEN"))


@bot.tree.command(name="about")
async def about(interaction: discord.Interaction):
    await interaction.response.send_message(
        "## Bot stworzony przez wiKapo.\n"
        "Informacje o aktualizacjach i o znanych błędach są na tym serwerze: https://discord.gg/ayXkVwVkGA\n"
        "Ten serwer jest również przeznaczony do dzielenia się własnymi projektami\n\n"
        f"Wersja kalendarza: v{BOT_VERSION}",
        ephemeral=True)


@bot.tree.command(name="help")
async def help(interaction: discord.Interaction):
    message = f"""## Kalendarz by wiKapo (v{BOT_VERSION})
### ---==[ Polecenia kalendarza ]==---
`/calendar create <title>` - Tworzy nowy kalendarz.
Można opcjonalnie podać nazwę kalendarza.
Kalendarz jest aktualizowany automatycznie, **codziennie o godzinie 0:00 UTC**.
W przypadku usunięcia **wiadomości** z kalendarzem wykonaj ponownie `/calendar create`, która odtworzy wiadomość kalendarza.

`/calendar edit` - Otwiera okienko edycji kalendarza. Umożliwia zmianę tytułu oraz wybranie roli, która będzie wysyłać powiadomienia przy aktualizacji kalendarza.
`/calendar delete` - Usuwa kalendarz z tego kanału **RAZEM z wydarzeniami**. Tej operacji nie można cofnąć.
`/calendar update <calendar_id> <quiet>` - Aktualizuje kalendarz. Domyślnie wybierany jest kalendarz z kanału, na którym wykonano komendę.
Można podać id kalendarza, który ma być zaktualizowany. Można opcjonalnie ustawić `quiet` na `False`, aby powiadomić o aktualizacji.

### ---==[ Polecenia niestandardowych sekcji ]==---
`/section add <calendar_id>` - Dodaje sekcję do wybranego kalendarza. Można opcjonalnie podać id kalendarza do którego ma być dodana.
`/section edit <calendar_id>` - Edytuje wybraną sekcję. Można opcjonalnie podać id kalendarza, z którego będzie edytowana sekcja.
`/section delete <calendar_id>` - Usuwa wybrane sekcje. Można opcjonalnie podać id kalendarza, z którego będą usuwane sekcje.

### ---==[ Polecenia wydarzeń ]==---
`/event add` - Dodaje wydarzenie. Dodane wydarzenia będą usuwane po 3 tygodniach od dnia wydarzenia.
`/event edit <calendar_id>` - Wysyła wiadomość z polem wyboru wydarzenia do edycji. Po wyborze wydarzenia otwiera okienko edycji.
Można podać id kalendarza, z którego będzie wybierane wydarzenie do edycji.
`/event delete <calendar_id>` - Otwiera okienko z polem wyboru wydarzeń do usunięcia. Po wyborze wydarzeń usuwa je całkowicie. **Tej operacji nie można cofnąć**.
Można podać id kalendarza, z którego będą pobierane wydarzenia do usunięcia."""
    await interaction.response.send_message(message, ephemeral=True)

    message = """### ---==[ Polecenia menedżerów ]==---
Role menedżerów są dodawane przez administratorów na danym serwerze.
Menedżerowie otrzymują dostęp do wszystkich komend `/calendar`, `/event` i `/notification` na danym serwerze.
Menedżerowie nie mogą dodawać nowych menedżerów.

`/user set` - Otwiera okienko z polem wyboru ról dla menedżerów kalendarza.
    
### ---==[ Inne polecenia ]==---
`/about` - informacja o autorze
`/help` - pokazuje tą wiadomość"""
    await interaction.followup.send(message, ephemeral=True)


asyncio.run(main())
