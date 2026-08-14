import os

import discord
from discord import Guild

from g.classes.calendar import Calendar
from g.classes.db import Db
from g.classes.logger import LogType, get_logger
from g.classes.message import fetch_manager_roles_for_guild, fetch_outdated_update_messages
from g.discord_classes import UpdateMessageView

BOT_VERSION = "PREv1.0"  # TODO ALWAYS UPDATE ME


# --------- CHECKS ---------

async def check_if_calendar_exists(interaction) -> None | int:
    calendar_id = Db().fetch_one("SELECT Id FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                                 (interaction.guild.id, interaction.channel.id))
    if not calendar_id:
        await interaction.response.send_message('Kalendarz nie istnieje na tym kanale', ephemeral=True)
        return None
    return calendar_id[0]


async def check_admin(interaction) -> bool:
    if (await interaction.guild.fetch_member(interaction.user.id)).guild_permissions.administrator:
        return True

    if await check_calendar_admin(interaction):
        return True
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
        if await check_admin(interaction):
            return True
        if await check_manager(interaction):
            return True
    return False


def check_dm(interaction) -> bool:
    return isinstance(interaction.channel, discord.channel.DMChannel)


# --------- Error handling ---------

async def send_error_message(interaction: discord.Interaction, error):
    command_name = interaction.command.qualified_name

    logger = get_logger()
    if isinstance(error, discord.app_commands.CheckFailure):
        if check_dm(interaction):
            logger.warning(f"User {interaction.user.name} tried to use /{command_name} in DM channel")
            await interaction.response.send_message(f"`/{command_name}` nie jest wspierane w prywatnych wiadomościach",
                                                    ephemeral=True)
        else:
            logger.warning(f"User {interaction.user.name} doesn't have permissions to use /{command_name}")
            await interaction.response.send_message("Brak uprawnień", ephemeral=True)
    else:
        logger.error(f"Received an error while executing {command_name}: {error}", exc_info=True)
        await interaction.response.send_message(
            f"Błąd: {error}\nZgłoś do @wiKapo lub na serwerze https://discord.gg/ayXkVwVkGA "
            f"na kanale: https://discord.com/channels/1479867817015771136/1479868335297527899", ephemeral=True)


# --------- update message handling ---------

async def update_calendar(guild: Guild, calendar: Calendar, caller: str, quiet: bool = False,
                          update_text: str | None = None):
    from datetime import datetime

    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info(f"{caller} is updating this calendar")

    outdated_update_messages = fetch_outdated_update_messages(calendar.id, int(datetime.now().timestamp()))
    if len(outdated_update_messages) > 0:
        for message in outdated_update_messages:
            message.delete()
        logger.info(f"Deleted {len(outdated_update_messages)} outdated update messages")

    channel = await guild.fetch_channel(calendar.channelId)
    await (await channel.fetch_message(calendar.messageId)).edit(content=str(calendar))
    logger.info("Updated calendar message")

    await create_calendar_description(channel, calendar, quiet=quiet, update_text=update_text)


# --------- Create calendar description ---------

async def create_calendar_description(channel, calendar: Calendar, update_text: str | None = None, quiet: bool = False):
    logger = get_logger(LogType.CALENDAR, calendar.id)

    if calendar.descriptionMessageId is not None:
        logger.info("Removing old calendar description")
        await (await channel.fetch_message(calendar.descriptionMessageId)).delete()
        calendar.descriptionMessageId = None
        logger.info("Done")

    ping_text: str = ""
    if calendar.pingRoleId and not quiet:
        ping_text += f"<@&{calendar.pingRoleId}>\n\n"

    logger.info("Sending new calendar description")
    message = await channel.send(ping_text + (update_text if update_text else "") +
                                 f"-# Wersja kalendarza: {BOT_VERSION} | Numer kalendarza: **{calendar.id}**",
                                 view=UpdateMessageView(calendar.pingRoleId))
    calendar.descriptionMessageId = message.id
    calendar.update()
    logger.info("Done")
