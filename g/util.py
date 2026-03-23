import logging
import os

import discord
from discord.ext.commands import Bot

from g.classes import *
from g.discord_classes import UpdateMessageView, NotificationButtonsView


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
    if interaction.user.id in admins:
        return True
    return False


async def check_manager(interaction: discord.Interaction) -> bool:
    manager_roles = fetch_manager_roles_for_guild(interaction.guild)
    return bool(set(interaction.user.roles).intersection(manager_roles))


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

    logger = get_logger()
    if isinstance(error, discord.app_commands.CheckFailure):
        if check_dm(interaction):
            logger.info(f"User {interaction.user.name} tried to use /{command_name} in DM channel")
            await interaction.response.send_message(f"`/{command_name}` nie jest wspierane w prywatnych wiadomościach",
                                                    ephemeral=True)
        else:
            logger.info(f"User {interaction.user.name} doesn't have permissions to use /{command_name}")
            await interaction.response.send_message("Brak uprawnień", ephemeral=True)
    else:
        logger.error(f"Received an error while executing {command_name}: {error}", exc_info=True)
        await interaction.response.send_message(
            f"Błąd: {error}\nZgłoś do @wiKapo lub na serwerze https://discord.gg/ayXkVwVkGA "
            f"na kanale: https://discord.com/channels/1479867817015771136/1479868335297527899", ephemeral=True)


# --------- update message handling ---------

async def update_calendar(interaction: discord.Interaction, calendar: Calendar, send_ping: bool = True):
    from datetime import datetime

    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info(f"Updating {repr(calendar)} in [{interaction.guild.name} - {interaction.guild.id}]"
                f" in [{interaction.channel.name} - {interaction.channel.id}]")

    outdated_update_messages = fetch_outdated_update_messages(calendar.id, int(datetime.now().timestamp()))
    delete_messages(outdated_update_messages)
    logger.info(f"Deleted {len(outdated_update_messages)} outdated update messages")

    await (await interaction.channel.fetch_message(calendar.messageId)).edit(content=str(calendar))
    logger.info("Updated calendar message")

    if calendar.pingMessageId:
        logger.info("Removing old update message")
        await (await interaction.channel.fetch_message(calendar.pingMessageId)).delete()
        calendar.pingMessageId = None
        logger.info("Done")

    logger.info(f"Sending new update message with{"" if send_ping else "out"} ping")
    ping = f"<@&{calendar.pingRoleId}>\n" if calendar.pingRoleId and send_ping else ""
    message = await interaction.channel.send(
        f"{ping}-# Ostatnia aktualizacja: <t:{int(datetime.now().timestamp())}>",
        view=UpdateMessageView(calendar.pingRoleId))
    calendar.pingMessageId = message.id
    logger.info("Done")

    calendar.update()
    logger.info("Calendar updated in the database. Finished updating calendar")


# --------- For notification button actions ---------

async def send_notification_add(bot: Bot, interaction: discord.Interaction):
    await bot.get_cog("NotificationCog").get_app_commands()[0].get_command("add").callback(bot, interaction)


async def send_notification_list(bot: Bot, interaction: discord.Interaction):
    await bot.get_cog("NotificationCog").get_app_commands()[0].get_command("list").callback(bot, interaction)


async def send_notification_delete(bot: Bot, interaction: discord.Interaction):
    await bot.get_cog("NotificationCog").get_app_commands()[0].get_command("delete").callback(bot, interaction)


# --------- VVV only for /update_all command VVV ---------

async def admin_update_calendar(bot: Bot, calendar: Calendar):
    logger = get_logger()

    channel = await (await bot.fetch_guild(calendar.guildId)).fetch_channel(calendar.channelId)

    logger.info(f"Admin is updating calendar {calendar.title} in [{channel.guild.name} - {calendar.guildId}] "
                f"in [{channel.name} - {channel.id}]")

    actions = [send_notification_add, send_notification_list, send_notification_delete]

    await (await channel.fetch_message(calendar.messageId)).edit(content=str(calendar),
                                                                 view=NotificationButtonsView(bot, actions))

    if calendar.pingMessageId is not None:
        logger.info("Removing old ping message")
        await (await channel.fetch_message(calendar.pingMessageId)).delete()
        calendar.pingMessageId = None

    if calendar.pingRoleId is not None:
        logger.info("Sending update message")
        from datetime import datetime
        message = await channel.send(
            f"Kalendarz został zaktualizowany do najnowszej wersji\n"
            f"Więcej o tej aktualizacji tutaj: https://discord.gg/ayXkVwVkGA lub pod przyciskiem `Pokaż ostatnie zmiany`\n"
            f"-# Czas aktualizacji: <t:{int(datetime.now().timestamp())}>",
            view=UpdateMessageView(calendar.pingRoleId))
        calendar.pingMessageId = message.id

    calendar.update()


# --------- logging ---------

def init_logger():
    if not os.path.exists('logs/calendar'):
        os.makedirs('logs/calendar')
    if not os.path.exists('logs/user'):
        os.makedirs('logs/user')


def get_logger(log_type: LogType = LogType.ALL, id: int | None = None) -> logging.Logger:
    match log_type:
        case LogType.CALENDAR | LogType.USER:
            logger_name = f"{log_type.value}_{id if id else "default"}"
        case LogType.NOTIFICATION:
            logger_name = log_type.value
        case LogType.ALL | _:
            logger_name = "default"

    folder = "" if log_type in (LogType.ALL, LogType.NOTIFICATION) else f"{log_type.value}/"

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setStream(logging.FileHandler(f"logs/{folder}{logger_name}.log").stream)
        stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(stream_handler)

    return logger
