from datetime import time

import discord
from discord.ext import tasks, commands

from cogs.notification.add import notification_add
from cogs.notification.delete import notification_delete
from cogs.notification.edit import notification_edit
from cogs.notification.util import hour_rounder
from g.util import *

UPDATE_TIMES = [time(hour=i) for i in range(0, 24)]

ID = 0
USER = 1
EVENT = 2
TIMESTAMP = 3
DESCRIPTION = 4

# TODO add error handling
class NotificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_loop.start()

    def cog_unload(self):
        self.update_loop.cancel()

    @tasks.loop(time=UPDATE_TIMES)
    async def update_loop(self):

        current_time = hour_rounder(datetime.now()).timestamp()
        print(f"[INFO]\tChecking for notifications to send at {current_time}")

        notifications = Db().fetch_all("SELECT Id, UserId, EventId, Timestamp, Description FROM notifications")
        if len(notifications) == 0:
            return
        print(len(notifications))
        for notification in notifications:
            print(f"Checking notification: {notification} |{notification[TIMESTAMP] <= current_time}|")
            if notification[TIMESTAMP] <= current_time:
                user = await self.bot.fetch_user(notification[USER])
                print(f"Sending notification to [{user} {notification[USER]}]")
                event_name, calendar_id = Db().fetch_one("SELECT Name, CalendarId FROM events WHERE Id = ?",
                                                         (notification[EVENT],))
                guild_id, channel_id, message_id = Db().fetch_one(
                    "SELECT GuildId, ChannelId, MessageId FROM calendars WHERE Id = ?", (calendar_id,))
                await user.send(f"Powiadomienie o wydarzeniu \"{event_name}\"\n"
                                f"Link do wiadomości: https://discord.com/channels/{guild_id}/{channel_id}/{message_id}\n"
                                f"{notification[DESCRIPTION] if notification[DESCRIPTION] else None}")
                # TODO make better notification message
                Db().execute("DELETE FROM notifications WHERE Id = ?", (notification[ID],))
        print("DONE checking notifications")

    notify_group = discord.app_commands.Group(name="notification", description="Polecenia powiadomień")

    @notify_group.command(name="add", description="Dodaje lub edytuje powiadomienia do wybranego wydarzenia")
    @discord.app_commands.describe(event_id="Numer wydarzenia (od najstarszego / od góry)")
    async def add(self, interaction: discord.Interaction, event_id: int | None):
        await notification_add(interaction, event_id)

    @notify_group.command(name="edit", description="Edytuje powiadomienia do wybranego wydarzenia")
    @discord.app_commands.describe(event_id="Numer wydarzenia (od najstarszego / od góry)")
    async def edit(self, interaction: discord.Interaction, event_id: int | None):
        await notification_edit(interaction, event_id)

    @notify_group.command(name="delete", description="Usuwa wszystkie powiadomienia związane z wybranym wydarzeniem")
    @discord.app_commands.describe(event_id="Numer wydarzenia (od najstarszego / od góry)")
    async def delete(self, interaction: discord.Interaction, event_id: int | None):
        await notification_delete(interaction, event_id)

    @notify_group.command(name="test", description="DEBUG ONLY")
    @discord.app_commands.check(check_admin)
    async def test(self, interaction: discord.Interaction):
        print("Testing notification loop")
        try:
            await self.update_loop()
        except Exception as e:
            print(e)
        await interaction.response.send_message("Done", ephemeral=True)


async def setup(bot):
    await bot.add_cog(NotificationCog(bot))
