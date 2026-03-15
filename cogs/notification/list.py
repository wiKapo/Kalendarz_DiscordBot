from collections.abc import Callable
from typing import Any

from g.util import *


async def notification_list(interaction: discord.Interaction, bot: Bot):
    logger = get_logger(LogType.USER, interaction.user.id)

    if check_dm(interaction):
        logger.info(f"Showing notifications in DMs")
        await interaction.response.send_message("Wybierz które powiadomienia wyświetlić", view=NotificationDMView(bot),
                                                ephemeral=True)
    else:
        calendar = Calendar()
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
        logger.info(f"Showing notifications in [{interaction.guild.name} - {interaction.guild.id}] "
                    f"in [{interaction.channel.name} - {interaction.channel.id}] for calendar no.{calendar.id}")
        await interaction.response.send_message("Wybierz które powiadomienia wyświetlić",
                                                view=NotificationGuildView(calendar.id), ephemeral=True)


async def send_all_notifications(interaction: discord.Interaction, _):
    await send_notification_list(interaction, fetch_events_with_notifications(interaction.user.id))


async def send_all_calendar_notifications(interaction: discord.Interaction, calendar_id: int):
    await send_notification_list(interaction,
                                 fetch_events_with_notifications_by_calendar(interaction.user.id, calendar_id))


async def send_notification_list(interaction: discord.Interaction, events: list[Event]):
    message = format_notifications(interaction, events)
    logger = get_logger(LogType.USER, interaction.user.id)
    logger.info(f"Sending notification list")
    await interaction.response.send_message(f"### Twoje powiadomienia:\n{message}", ephemeral=True)


def format_notifications(interaction: discord.Interaction, events: list[Event]) -> str:
    if not events:
        return "Brak powiadomień"

    message = ""
    for event in events:
        notifications = fetch_notifications_by_event(interaction.user.id, event.id)
        calendar = Calendar()
        calendar.fetch(event.calendarId)

        message += f"W kalendarzu: https://discord.com/channels/{calendar.guildId}/{calendar.channelId}/{calendar.messageId}"
        message += f" do wydarzenia: ({event})"

        selected_time_tags = [n.timeTag for n in notifications]
        message += f" masz powiadomienia: {selected_time_tags}"

        descriptions = [n.description for n in notifications]
        message += f"z opisami: {descriptions}"
        message += "\n"
    return message


class ListNotificationButton(discord.ui.Button):
    action: Callable
    data: Any

    def __init__(self, label: str, style: discord.ButtonStyle, action: Callable, data: Any = None,
                 disabled: bool = False):
        super().__init__(label=label, style=style, disabled=disabled)
        self.action = action
        self.data = data

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.action(interaction, self.data)
        except Exception as e:
            logger = get_logger(LogType.USER, interaction.user.id)
            logger.error(f"in callback of NotificationButton {e}")


class NotificationDMView(discord.ui.View):
    def __init__(self, bot: Bot):
        super().__init__()
        self.add_item(ListNotificationButton(label="Wszystkie powiadomienia", style=discord.ButtonStyle.primary,
                                             action=send_all_notifications))
        self.add_item(ListNotificationButton(label="Wybierz kalendarz", style=discord.ButtonStyle.primary,
                                             action=send_calendar_select_view, data=bot))


async def send_calendar_select_view(interaction: discord.Interaction, bot: Bot):
    logger = get_logger(LogType.USER, interaction.user.id)

    logger.info(f"Showing calendar select view for [{interaction.user.name} - {interaction.user.id}]")
    calendars = []
    for calendar in fetch_all_calendars():  # Showing only those calendars from those guilds where the user has access
        guild: discord.Guild
        try:
            guild = await bot.fetch_guild(calendar.guildId)
            await guild.fetch_member(interaction.user.id)
        except (discord.NotFound, discord.Forbidden):
            continue

        calendar.guildName = guild.name
        calendar.channelName = (await guild.fetch_channel(calendar.channelId)).name
        calendars.append(calendar)

    logger.debug(f"Available calendars: {[repr(c) for c in calendars]}")
    await interaction.response.send_message("Wybierz kalendarz", view=SelectCalendarView(calendars),
                                            ephemeral=True)


def format_calendars(calendars: list[Calendar]) -> list[discord.SelectOption]:
    options = []
    for calendar in calendars:
        options.append(
            discord.SelectOption(
                label=f"{calendar.title if calendar.title else DEFAULT_TITLE}",
                description=f"{calendar.guildName} - {calendar.channelName}",
                value=f"{calendar.id}"
            )
        )
    return options


class SelectCalendar(discord.ui.Select):
    action: Callable

    def __init__(self, placeholder: str, action: Callable, calendars: list[Calendar]):
        options = format_calendars(calendars)
        super().__init__(placeholder=placeholder, options=options)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.action(interaction, int(self.values[0]))
        except Exception as e:
            logger = get_logger(LogType.USER, interaction.user.id)
            logger.error(f"in callback of SelectCalendar {e}")


class SelectCalendarView(discord.ui.View):
    def __init__(self, calendars: list[Calendar]):
        super().__init__()
        self.add_item(
            SelectCalendar(placeholder="Wybierz kalendarz", action=send_all_calendar_notifications,
                           calendars=calendars))


class NotificationGuildView(discord.ui.View):
    def __init__(self, calendar_id: int):
        super().__init__()
        self.add_item(
            ListNotificationButton(label="Wszystkie powiadomienia z tego kalendarza", style=discord.ButtonStyle.primary,
                                   action=send_all_calendar_notifications, data=calendar_id))
        self.add_item(ListNotificationButton(label="Wybierz wydarzenie", style=discord.ButtonStyle.primary,
                                             action=(), data=calendar_id,
                                             disabled=True))  # TODO add action send_event_select_view
