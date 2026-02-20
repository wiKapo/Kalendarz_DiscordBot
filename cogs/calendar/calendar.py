from datetime import time

from discord.ext import tasks, commands

from cogs.calendar.create import calendar_create
from cogs.calendar.delete import calendar_delete
from cogs.calendar.edit import calendar_edit
from cogs.calendar.update import calendar_update
from cogs.calendar.util import *

UPDATE_TIME = time()


# TODO add error handling
class CalendarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_loop.start()

    def cog_unload(self):
        self.update_loop.cancel()

    @tasks.loop(time=UPDATE_TIME)
    async def update_loop(self):
        calendars = fetch_all_calendars()

        print("[INFO]\tRemoving old messages")
        delete_old_messages()

        print("[INFO]\tStart of updating all calendars")
        for calendar in calendars:
            await bot_update_calendar(self, calendar)
        print("[INFO]\tEnd of updating all calendars")

    cal_group = discord.app_commands.Group(name="calendar", description="Polecenia kalendarza")

    @cal_group.command(name="create", description="Tworzy nowy kalendarz")
    @discord.app_commands.describe(title="Tytuł kalendarza", show_sections="Czy wydzielić sekcje w kalendarzu?")
    @discord.app_commands.choices(show_sections=[discord.app_commands.Choice(name="Tak", value=True),
                                                 discord.app_commands.Choice(name="Nie", value=False)])
    @discord.app_commands.check(check_user)
    async def create(self, interaction: discord.Interaction, title: str | None,
                     show_sections: discord.app_commands.Choice[int] | None):
        await calendar_create(self, interaction, title, show_sections)

    @create.error
    async def cal_group_error(self, interaction: discord.Interaction, error):
        if await check_manager(interaction) and isinstance(error, discord.app_commands.CheckFailure):
            print(f"[INFO]\tUser {interaction.user.name} doesn't have permissions to create calendars.")
            await interaction.response.send_message("Brak uprawnień", ephemeral=True)

    @cal_group.command(name="update", description="Aktualizuje kalendarz")
    @discord.app_commands.check(check_user)
    async def update(self, interaction: discord.Interaction):
        await calendar_update(interaction)

    @cal_group.command(name="delete", description="Usuwa kalendarz")
    @discord.app_commands.check(check_user)
    async def delete(self, interaction: discord.Interaction):
        await calendar_delete(interaction)

    @cal_group.command(name="edit", description="Edytuje kalendarz")
    @discord.app_commands.check(check_user)
    async def edit(self, interaction: discord.Interaction):
        await calendar_edit(interaction)


async def setup(bot):
    await bot.add_cog(CalendarCog(bot))
