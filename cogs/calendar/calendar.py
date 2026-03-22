from datetime import time, timedelta

from discord.ext import tasks, commands

from cogs.calendar.create import calendar_create
from cogs.calendar.delete import calendar_delete
from cogs.calendar.edit import calendar_edit
from cogs.calendar.update import calendar_update
from cogs.calendar.util import *

UPDATE_TIME = time()


class CalendarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_loop.start()

    def cog_unload(self):
        self.update_loop.cancel()

    @tasks.loop(time=UPDATE_TIME)
    async def update_loop(self):
        calendars = fetch_all_calendars()
        logger = get_logger(LogType.CALENDAR)

        logger.info("Removing old events")
        cutoff_timestamp = (
            int((datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(weeks=1)).timestamp()))
        outdated_events = fetch_outdated_events(cutoff_timestamp)
        logger.debug(f"Deleting {len(outdated_events)} old events")
        logger.debug(outdated_events)
        delete_events(outdated_events)

        logger.info("Start of updating all calendars")
        for calendar in calendars:
            logger.info(f"Updating calendar {repr(calendar)}")
            calendar_message: discord.Message = await (
                (await (await self.bot.fetch_guild(calendar.guildId)).fetch_channel(calendar.channelId))
                .fetch_message(calendar.messageId))

            await calendar_message.edit(content=str(calendar))
        logger.info("Updated all calendars")

    cal_group = discord.app_commands.Group(name="calendar", description="Polecenia kalendarza")

    @cal_group.command(name="create", description="Tworzy nowy kalendarz")
    @discord.app_commands.describe(title="Tytuł kalendarza", show_sections="Czy wydzielić sekcje w kalendarzu?")
    @discord.app_commands.choices(show_sections=[discord.app_commands.Choice(name="Tak", value=True),
                                                 discord.app_commands.Choice(name="Nie", value=False)])
    @discord.app_commands.check(check_user)
    async def create(self, interaction: discord.Interaction, title: str | None,
                     show_sections: discord.app_commands.Choice[int] | None):
        await calendar_create(self.bot, interaction, title, show_sections)

    @create.error
    async def create_error(self, interaction: discord.Interaction, error):
        await send_error_message(interaction, error)

    @cal_group.command(name="update", description="Aktualizuje kalendarz")
    @discord.app_commands.choices(quiet=[discord.app_commands.Choice(name="Tak", value=True),
                                                 discord.app_commands.Choice(name="Nie", value=False)])
    @discord.app_commands.check(check_user)
    async def update(self, interaction: discord.Interaction, quiet: discord.app_commands.Choice[int] | None = None):
        await calendar_update(interaction, self.bot, bool(quiet and quiet.value))

    @update.error
    async def update_error(self, interaction: discord.Interaction, error):
        await send_error_message(interaction, error)

    @cal_group.command(name="delete", description="Usuwa kalendarz")
    @discord.app_commands.check(check_user)
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
