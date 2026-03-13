import logging
import os

import discord
from discord.ext.commands import Bot

from g.classes import *
from g.discord_classes import UpdateMessageView


# --------- CHECKS ---------

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

    if await check_calendar_admin(interaction): return True
    return False


async def check_calendar_admin(interaction) -> bool:
    admins = list(map(int, os.getenv("USERS").split(',')))
    logger = get_logger()
    logger.error([x for x in admins])
    logger.error(interaction.user.id)
    logger.error(interaction.user.id in admins)
    if interaction.user.id in admins:
        return True
    return False


async def check_manager(interaction) -> bool:  # TODO FIX MEEEEEEEEEEEEEEEE
    managers = Db().fetch_all('SELECT UserId FROM users WHERE GuildId = ?', (interaction.guild.id,))
    allowed_users = list(map(lambda a: a[0], managers))

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


# --------- Error handling ---------

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


# --------- update message handling ---------

async def update_calendar(interaction: discord.Interaction, calendar: Calendar, send_ping: bool = True):
    print(f"[INFO]\tUpdating calendar[{calendar.id}] {calendar.title}"
          f" in [{interaction.guild.name} - {interaction.guild.id}]"
          f" in [{interaction.channel.name} - {interaction.channel.id}]")

    delete_old_update_messages(calendar.id)

    delete_old_update_messages(calendar.id)

    await ((await interaction.channel.fetch_message(calendar.messageId)).edit(content=str(calendar)))

    if send_ping:
        if calendar.pingMessageId is not None:
            print(
                f"[INFO]\tRemoving old message in [{calendar.messageId}] {interaction.guild.name} - {interaction.guild.id},"
                f" {interaction.channel.name} - {interaction.channel.id}")
            await (await interaction.channel.fetch_message(calendar.pingMessageId)).delete()
            calendar.pingMessageId = None

        if calendar.pingRoleId is not None:
            print(
                f"[INFO]\tSending update message in [{calendar.messageId}] {interaction.guild.name} - {interaction.guild.id},"
                f" {interaction.channel.name} - {interaction.channel.id}")
            message = await interaction.channel.send(
                f"<@&{calendar.pingRoleId}>\n-# Ostatnia aktualizacja: <t:{int(datetime.now().timestamp())}>",
                view=UpdateMessageView(calendar.pingRoleId))
            calendar.pingMessageId = message.id

        calendar.update()


# --------- VVV only for /update_all command VVV ---------

async def admin_update_calendar(bot: Bot, calendar: Calendar):
    print(f"[INFO - ADMIN]\tAdmin is updating calendar {calendar.title}"
          f" in [{calendar.guildId}] in [{calendar.channelId}]")

    channel = await (await bot.fetch_guild(calendar.guildId)).fetch_channel(calendar.channelId)

    await (await channel.fetch_message(calendar.messageId)).edit(content=str(calendar))

    if calendar.pingMessageId is not None:
        print(
            f"[INFO - ADMIN]\tRemoving old message in [{calendar.messageId}] {calendar.guildId}, {calendar.channelId}")
        await (await channel.fetch_message(calendar.pingMessageId)).delete()
        calendar.pingMessageId = None

    if calendar.pingRoleId is not None:
        print(
            f"[INFO - ADMIN]\tSending update message in [{calendar.messageId}] {calendar.guildId}, {calendar.channelId}")
        message = await channel.send(
            f"Kalendarz został zaktualizowany do najnowszej wersji\n"
            f"Więcej o tej aktualizacji tutaj: https://discord.com/channels/1284116042473279509/1474908356538794056\n"
            f"-# Czas aktualizacji: <t:{int(datetime.now().timestamp())}>",
            view=UpdateMessageView(calendar.pingRoleId))
        calendar.pingMessageId = message.id

    calendar.update()


# --------- logging ---------

def init_logger():
    if not os.path.exists('logs/calendar'):
        os.makedirs('logs/calendar')
    if not os.path.exists('logs/dm'):
        os.makedirs('logs/dm')


def get_logger(log_type: LogType = LogType.ALL, id: int | None = None) -> logging.Logger:
    logger_name = f"{log_type.value}_{id}" if log_type != LogType.ALL else "default"
    folder = "" if log_type == LogType.ALL else f"{log_type.value}/"

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    stream_handler.setStream(logging.FileHandler(f"logs/{folder}{logger_name}.log").stream)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(stream_handler)

    return logger
