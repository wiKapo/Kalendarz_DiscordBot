import asyncio

import discord
from discord.ext import commands
from dotenv import load_dotenv

from global_functions import *

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix='/', intents=intents)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    try:
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
                   'GuildId BIGINT NOT NULL'
                   ')')
    cursor.execute('CREATE TABLE IF NOT EXISTS calendars ('
                   'Id INTEGER PRIMARY KEY AUTOINCREMENT,'
                   'Title TEXT,'
                   'ShowSections BOOLEAN NOT NULL DEFAULT FALSE,'
                   'GuildId BIGINT NOT NULL,'
                   'ChannelId BIGINT NOT NULL,'
                   'MessageId BIGINT NOT NULL'
                   ');')

    print('Tables are ready')
    db_disconnect(connection, cursor)


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


asyncio.run(main())
