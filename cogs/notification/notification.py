from datetime import time

from discord.ext import tasks, commands

from cogs.notification.add import notification_add
from cogs.notification.delete import notification_delete
from cogs.notification.list import notification_list
from g.util import *

UPDATE_TIMES = [time(hour=i) for i in range(0, 24)]

ID = 0
USER = 1
EVENT = 2
TIMESTAMP = 3
DESCRIPTION = 4


class NotificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_loop.start()

    def cog_unload(self):
        self.update_loop.cancel()

    @tasks.loop(time=UPDATE_TIMES)
    async def update_loop(self):
        logger = get_logger(LogType.NOTIFICATION)

        notifications = fetch_all_ready_notifications()
        if not notifications:
            logger.info("No due notifications found, skipping")
            return
        logger.info(f"Found {len(notifications)} notifications to send")

        for notification in notifications:
            user: discord.User = await self.bot.fetch_user(notification.userId)

            logger.info(f"Sending notification [{notification.id}] to [{user}]")
            user_logger = get_logger(LogType.USER, user.id)
            user_logger.info(f"Sending notification {repr(notification)}")

            await user.send(f"{notification}")
            user_logger.info("Sent notification")
            notification.delete()
            logger.info("Deleted notification from the database")
        logger.info("Finished sending notifications")

    notify_group = discord.app_commands.Group(name="notification", description="Polecenia powiadomień")

    @notify_group.command(name="add", description="Dodaje lub edytuje powiadomienia do wybranego wydarzenia")
    @discord.app_commands.describe(event_id="Numer wydarzenia (od najstarszego / od góry)")
    async def add(self, interaction: discord.Interaction, event_id: int | None = None):
        await notification_add(interaction, event_id)

    @add.error
    async def add_error(self, interaction: discord.Interaction, error):
        await send_error_message(interaction, error)

    # TODO może kiedyś
    # @notify_group.command(name="edit", description="Edytuje powiadomienia do wybranego wydarzenia")
    # @discord.app_commands.describe(event_id="Numer wydarzenia (od najstarszego / od góry)")
    # async def edit(self, interaction: discord.Interaction, event_id: int | None = None):
    #     await notification_edit(interaction, event_id)

    # @edit.error
    # async def edit_error(self, interaction: discord.Interaction, error):
    #     await send_error_message(interaction, error)

    @notify_group.command(name="list", description="Wyświetla powiadomienia użytkownika")
    async def list(self, interaction: discord.Interaction):
        if isinstance(self, Bot):
            await notification_list(interaction, self)
        else:
            await notification_list(interaction, self.bot)

    @list.error
    async def list_error(self, interaction: discord.Interaction, error):
        await send_error_message(interaction, error)

    @notify_group.command(name="delete", description="Usuwa wszystkie powiadomienia związane z wybranym wydarzeniem")
    @discord.app_commands.describe(event_id="Numer wydarzenia (od najstarszego / od góry)")
    async def delete(self, interaction: discord.Interaction, event_id: int | None = None):
        await notification_delete(interaction, event_id)

    @delete.error
    async def delete_error(self, interaction: discord.Interaction, error):
        await send_error_message(interaction, error)

    # @notify_group.command(name="test", description="DEBUG ONLY")
    # @discord.app_commands.check(check_admin)
    # async def test(self, interaction: discord.Interaction):
    #     logger = get_logger(LogType.NOTIFICATION)
    #     logger.info("Testing notification loop")
    #     await interaction.response.send_message("Testing notification loop", ephemeral=True)
    #     try:
    #         await self.update_loop()
    #     except Exception as e:
    #         logger.debug(e)
    #     await interaction.followup.send("Done", ephemeral=True)
    #
    # @test.error
    # async def test_error(self, interaction: discord.Interaction, error):
    #     await send_error_message(interaction, error)


async def setup(bot):
    await bot.add_cog(NotificationCog(bot))
