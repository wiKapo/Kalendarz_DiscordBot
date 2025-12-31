import asyncio

import discord
from discord.ext import commands
from dotenv import load_dotenv

from util import *

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix='/', intents=intents, help_command=None)


# TODO log to file
# TODO add notification system
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
                     'MessageId BIGINT NOT NULL'
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

        print('Tables are ready')
    except Exception as e:
        print("Error with syncing database: ", e)


async def load():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")


async def main():
    async with bot:
        await load()
        await bot.start(os.getenv("BOT_TOKEN"))


@bot.tree.command(name="about")
async def about(interaction: discord.Interaction):
    await interaction.response.send_message("Bot stworzony przez wiKapo", ephemeral=True)


@bot.tree.command(name="help")
async def help(interaction: discord.Interaction):  # TODO Update help
    message = """## Kalendarz by wiKapo
### ---==[ Polecenia kalendarza ]==---
NIE JEST ZAKTUALIZOWANE DO NAJNOWSZEJ WERSJI
`/calendar create <title|show_sections>` - Tworzy nowy kalendarz. 
Można opcjonalnie podać nazwę kalendarza oraz zdecydować, czy kalendarz ma dzielić wydarzenia na sekcje. 
Kalendarz jest aktualizowany automatycznie, **codziennie o godzinie 0:00 UTC**.
W przypaku usunięcia **wiadomości** z kalendarzem wykonaj ponownie `/calendar create`, która odtworzy wiadomość kalendarza.

`/calendar update` - Aktualizuje kalendarz z tego kanału.
`/calendar delete` - **Permamentnie** usuwa kalendarz z tego kanału **RAZEM z wydarzeniami**. Tej operacji nie można cofnąć.
`/calendar edit title [title]` - Zmienia nazwę kalendarza.
`/calendar edit sections [choice]` - Zmienia decyzję o wyświetlaniu sekcji.

### ---==[ Polecenia wydarzeń ]==---
`/event add` - Dodaje wydarzenie. Dodane wydarzenia będą usuwane po 3 tygodniach od dnia wydarzenia.
`/event edit [id] <date|time|name|group|place>` - Modyfikuje wydarzenie o numerze `id` w kalendarzu.
`/event delete one [id]` - Usuwa wydarzenie o numerze `id` z kalendarza. Tej operacji nie można cofnąć.
`/event delete expired` - Usuwa przedawnione wydarzenia z kalendarza. Tej operacji nie można cofnąć.

### ---==[ Polecenia menedżerów]==---
Menedżerowie są dodawani przez administratorów serwera do danego serwera.
Dodani menedżerowie otrzymują dostęp do tworzenia, edycji, usuwania kalendarza i wydarzeń na danym serwerze.
Mendżerowie nie mogą dodawać nowych mendżerów.

`/user add [user]` - Dodaje nowego menedżera do tego serwera.
`/user list` - Wyświetla menedżerów dodanych do tego serwera.
`/user remove [user]` - Usuwa menedżera z tego serwera. Tej operacji nie można cofnąć.

### ---==[ Inne polecenia ]==---
`/about` - informacja o autorze (WIP)
`/help` - pokazuje tą wiadomość"""
    await interaction.response.send_message(message, ephemeral=True)


asyncio.run(main())
