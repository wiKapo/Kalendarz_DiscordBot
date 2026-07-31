import os

import discord
from discord import Guild
from discord.ext.commands import Bot

from g.classes.logger import LogType, get_logger
from g.classes.calendar import Calendar
from g.classes.db import Db
from g.classes.message import fetch_manager_roles_for_guild, fetch_outdated_update_messages
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


# --------- For notification button actions ---------

async def send_notification_add(bot: Bot, interaction: discord.Interaction):
    await bot.get_cog("NotificationCog").get_app_commands()[0].get_command("add").callback(bot, interaction)


async def send_notification_list(bot: Bot, interaction: discord.Interaction):
    await bot.get_cog("NotificationCog").get_app_commands()[0].get_command("list").callback(bot, interaction)


async def send_notification_delete(bot: Bot, interaction: discord.Interaction):
    await bot.get_cog("NotificationCog").get_app_commands()[0].get_command("delete").callback(bot, interaction)


# --------- update message handling ---------

async def update_calendar(guild: Guild, calendar: Calendar, caller: str):
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

    # TODO move to separate function
    # if send_ping:
    #     if calendar.pingMessageId is not None:
    #         logger.info("Removing old ping message")
    #         await (await interaction.channel.fetch_message(calendar.pingMessageId)).delete()
    #         calendar.pingMessageId = None
    #         logger.info("Done")
    #
    #     if calendar.pingRoleId is not None:
    #         logger.info("Sending new ping message")
    #         message = await interaction.channel.send(
    #             f"<@&{calendar.pingRoleId}>\n-# Ostatnia aktualizacja: <t:{int(datetime.now().timestamp())}>",
    #             view=UpdateMessageView(calendar.pingRoleId))
    #         calendar.pingMessageId = message.id
    #         logger.info("Done")
    #
    #    calendar.update()
    #    logger.info("Calendar updated in the database. Finished updating calendar")


# --------- For notification button actions ---------

async def send_notification_add(bot: Bot, interaction: discord.Interaction):
    await bot.get_cog("NotificationCog").get_app_commands()[0].get_command("add").callback(bot, interaction)


async def send_notification_list(bot: Bot, interaction: discord.Interaction):
    await bot.get_cog("NotificationCog").get_app_commands()[0].get_command("list").callback(bot, interaction)


async def send_notification_delete(bot: Bot, interaction: discord.Interaction):
    await bot.get_cog("NotificationCog").get_app_commands()[0].get_command("delete").callback(bot, interaction)


# --------- VVV only for /update_all command VVV ---------

async def admin_update_calendar(bot: Bot, calendar: Calendar):
    logger = get_logger(LogType.CALENDAR, calendar.id)

    channel = await (await bot.fetch_guild(calendar.guildId)).fetch_channel(calendar.channelId)

    logger.info(
        f"Admin is updating calendar{" " + calendar.title if calendar.title else ""} "
        f"in [{channel.guild.name} - {calendar.guildId}] in [{channel.name} - {channel.id}]")

    actions = [send_notification_add, send_notification_list, send_notification_delete]

    await (await channel.fetch_message(calendar.messageId)).edit(content=str(calendar),
                                                                 view=NotificationButtonsView(bot, actions))

    if calendar.pingMessageId is not None:  # TODO need to rethink this
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
