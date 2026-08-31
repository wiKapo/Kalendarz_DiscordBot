from datetime import time, datetime, timedelta

import discord
from discord.ext import tasks, commands

from cogs.calendar.create import calendar_create
from cogs.calendar.delete import calendar_delete
from cogs.calendar.edit import calendar_edit
from cogs.calendar.update import calendar_update
from cogs.calendar.util import DMNotificationButtonsView
from g.classes.calendar import fetch_all_calendars, fetch_all_notifications, Calendar
from g.classes.event import fetch_outdated_events, fetch_events_from_ids
from g.classes.logger import get_logger, LogType
from g.classes.section import fetch_outdated_sections
from g.datetime_util import is_today, is_tomorrow, is_this_week, is_next_week
from g.util import check_dm, check_admin, check_user, send_error_message

UPDATE_TIME = time()
NOTIFICATION_TIME = time(hour=7, minute=0, second=0)


class CalendarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_loop.start()
        self.notification_loop.start()

    def cog_unload(self):
        self.update_loop.cancel()
        self.notification_loop.cancel()

    @tasks.loop(time=UPDATE_TIME)
    async def update_loop(self):
        calendars = fetch_all_calendars()
        logger = get_logger(LogType.CALENDAR)

        logger.info("Start of update loop")
        cutoff_timestamp = (
            int((datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(weeks=1)).timestamp()))
        outdated_events = fetch_outdated_events(cutoff_timestamp)
        if len(outdated_events) > 0:
            logger.info(f"Deleting {len(outdated_events)} old events")
            logger.debug(outdated_events)
            for event in outdated_events:
                event.delete()
            logger.info("Deleted outdated events")
        else:
            logger.info("No outdated events found")

        outdated_sections = fetch_outdated_sections()
        if len(outdated_sections) > 0:
            logger.info(f"Deleting {len(outdated_sections)} old custom sections")
            logger.debug(outdated_sections)
            for section in outdated_sections:
                section.delete()
            logger.info("Deleted outdated custom sections")
        else:
            logger.info("No outdated sections found")

        logger.info("Start of updating all calendars")
        for calendar in calendars:
            logger.info(f"Updating calendar {repr(calendar)}")
            calendar_message: discord.Message = await (
                (await (await self.bot.fetch_guild(calendar.guildId)).fetch_channel(calendar.channelId))
                .fetch_message(calendar.messageId))

            await calendar_message.edit(content=str(calendar))
        logger.info("Updated all calendars")

    @tasks.loop(time=NOTIFICATION_TIME)
    async def notification_loop(self):
        notifications: dict[int, set[Calendar]] = fetch_all_notifications()
        notification_logger = get_logger(LogType.NOTIFICATION)
        notification_logger.info("Start of notification loop")

        for user_id in notifications:
            user_name = (await self.bot.fetch_user(user_id)).name
            user_logger = get_logger(LogType.USER, user_name)

            notification_logger.info(f"Checking notifications for user {user_name} ({user_id})")
            user_logger.info(f"Checking notifications")
            calendars = notifications[user_id]
            event_ids = set().union(*(calendar.eventIds for calendar in calendars))
            # Getting all event ids from all calendars user has notifications for

            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            events = list(filter(lambda e: today.timestamp() <= e.timestamp < (today + timedelta(weeks=2)).timestamp(),
                                 fetch_events_from_ids(event_ids)))  # Filtering events that are in the next 2 weeks
            if not events:
                user_logger.info("No events to be notified about in the next 2 weeks")
                continue

            events.sort(key=lambda e: e.timestamp)
            user_logger.info(f"Found {len(events)} events in the next 2 weeks")
            user_logger.debug(events)

            calendar_ids = set().union(*(event.calendarIds for event in events))
            calendars = list(filter(lambda c: c.id in calendar_ids, calendars))
            # Filtering calendars that have events in the next 2 weeks

            notification_message = ""
            section_number = 0
            for event in events:
                event_date = datetime.fromtimestamp(event.timestamp)
                if section_number <= 1 and is_today(event_date):
                    if section_number == 0:
                        notification_message += f"# Wydarzenia dzisiaj\n"
                    section_number = 1

                elif section_number <= 2 and is_tomorrow(event_date):
                    if section_number < 2:
                        notification_message += f"## Wydarzenia jutro\n"
                    section_number = 2

                elif datetime.now().weekday() == 6:  # 6 == Sunday
                    if section_number <= 7 and is_this_week(event_date):
                        if section_number < 7:
                            notification_message += f"### Wydarzenia w tym tygodniu\n"
                        section_number = 7

                    elif section_number <= 14 and is_next_week(event_date):
                        if section_number < 14:
                            notification_message += f"### Wydarzenia w następnym tygodniu\n"
                        section_number = 14

                else:
                    break

                notification_message += f"{event}\n"
                user_logger.info("Prepared main part of notification message")

            calendar_links = ", ".join(
                map(lambda c: f"[#{c.id}](https://discord.com/channels/{c.guildId}/{c.channelId}/{c.messageId})",
                    calendars))
            notification_message += f"\nZ kalendarz{"a" if len(calendars) == 1 else "y"} {calendar_links}\n"
            user_logger.info("Prepared final part of notification message")

            await self.bot.get_user(user_id).send(notification_message, view=DMNotificationButtonsView())
            user_logger.info("Sent notification")
        notification_logger.info("Finished notification loop")

    cal_group = discord.app_commands.Group(name="calendar", description="Polecenia kalendarza")

    @cal_group.command(name="create", description="Tworzy nowy kalendarz")
    @discord.app_commands.describe(title="Tytuł kalendarza")
    @discord.app_commands.check(check_dm)
    @discord.app_commands.check(check_admin)
    async def create(self, interaction: discord.Interaction, title: str | None):
        await calendar_create(interaction, title)

    @create.error
    async def create_error(self, interaction: discord.Interaction, error):
        await send_error_message(interaction, error)

    @cal_group.command(name="update", description="Aktualizuje kalendarz")
    @discord.app_commands.choices(quiet=[discord.app_commands.Choice(name="Yes (default)", value=True),
                                         discord.app_commands.Choice(name="No", value=False)])
    @discord.app_commands.describe(
        calendar_id="Numer kalendarza do aktualizacji (domyślnie kalendarz, który znajduje się na kanale)")
    @discord.app_commands.check(check_user)
    async def update(self, interaction: discord.Interaction, calendar_id: int | None,
                     quiet: discord.app_commands.Choice[int] | None):
        await calendar_update(interaction, calendar_id, bool(not quiet or quiet.value))

    @update.error
    async def update_error(self, interaction: discord.Interaction, error):
        await send_error_message(interaction, error)

    @cal_group.command(name="delete", description="Usuwa kalendarz")
    @discord.app_commands.check(check_dm)
    @discord.app_commands.check(check_admin)
    async def delete(self, interaction: discord.Interaction):
        await calendar_delete(interaction)

    @delete.error
    async def delete_error(self, interaction: discord.Interaction, error):
        await send_error_message(interaction, error)

    @cal_group.command(name="edit", description="Edytuje kalendarz")
    @discord.app_commands.check(check_user)
    async def edit(self, interaction: discord.Interaction):
        await calendar_edit(interaction)

    @edit.error
    async def edit_error(self, interaction: discord.Interaction, error):
        await send_error_message(interaction, error)


async def setup(bot):
    await bot.add_cog(CalendarCog(bot))
