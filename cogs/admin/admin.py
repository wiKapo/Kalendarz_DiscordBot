import discord
from discord.ext import commands

from g.classes import fetch_all_calendars, Message
from g.util import check_calendar_admin, get_logger, admin_update_calendar


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    admin_group = discord.app_commands.Group(name="admin", description="[TYLKO DLA ADMINÓW KALENDARZA]")

    @admin_group.command(name="update_all_calendars", description="[TYLKO DLA ADMINÓW KALENDARZA] "
                                                                  "Aktualizuje wszystkie wiadomości kalendarza do najnowszej wersji")
    @discord.app_commands.check(check_calendar_admin)
    async def update_all_calendars(self, interaction: discord.Interaction):
        logger = get_logger()

        logger.info("Updating all calendars")
        await interaction.response.send_message(
            "Aktualizowanie wszystkich kalendarzy. Poczekaj na potwierdzenie wykonania akcji.", ephemeral=True)

        calendars = fetch_all_calendars()
        for calendar in calendars:
            logger.info(f"Updating calendar id={calendar.id}")
            message = Message()
            message.calendarId = calendar.id
            message.set_time(5)
            message.message = "**Aktualizacja kalendarza** Naprawiono działanie przycisków powiadomień"  # TODO ALWAYS UPDATE ME
            message.insert_with_check()
            logger.info("Sent update message")

            try:
                await admin_update_calendar(self.bot, calendar)
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                await interaction.followup.send(f"Aktualizowanie nie powiodło się. Błąd w kalendarzu:{repr(calendar)}\n"
                                                f"ERROR: {e}", ephemeral=True)
                return
            logger.info(f"Updated calendar id={calendar.id}")

        logger.info(f"Finished updating {len(calendars)} calendar{"" if len(calendars) == 1 else "s"}")
        await interaction.followup.send(f"Zaktualizowano wszystkie kalendarze w ilości: `{len(calendars)}`",
                                        ephemeral=True)

    @update_all_calendars.error
    async def update_all_calendars_error(self, interaction: discord.Interaction, error):
        logger = get_logger()
        logger.warning(f"{error}\nUser {interaction.user.name} {interaction.user.id} "
                       f"doesn't have permissions to use admin commands")
        await interaction.response.send_message("Brak uprawnień", ephemeral=True)

    @admin_group.command(name="remove_admin_cog", description="[TYLKO DLA ADMINÓW KALENDARZA] "
                                                              "Chowa komendy administratorów")
    @discord.app_commands.check(check_calendar_admin)
    async def remove_admin_cog(self, interaction: discord.Interaction):
        logger = get_logger()
        logger.info("Hiding admin cog")
        # for command in self.admin_group.walk_commands(): # Saved maybe for later
        #     logger.debug(f"TEST {type(command)}: {command.name} - desc {command.description}\n")
        #     command.description = "[NIEDOSTĘPNE]"
        #
        # self.admin_group.description = "[NIEDOSTĘPNE]"
        #
        # for command in self.admin_group.walk_commands(): # Saved maybe for later
        #     logger.debug(f"TEST {type(command)}: {command.name} - desc {command.description}\n")
        #
        # logger.debug(f"A_G: {self.admin_group.description}")

        check = await self.bot.remove_cog(self.qualified_name)
        logger.info(f"Removed cog: {check}")
        await self.bot.tree.sync()

        await interaction.response.send_message("Usunięto komendy administratora", ephemeral=True)
        logger.info(f"Finished hiding admin cog")

    @remove_admin_cog.error
    async def remove_admin_cog_error(self, interaction: discord.Interaction, error):
        logger = get_logger()
        logger.warning(f"{error}\nUser {interaction.user.name} {interaction.user.id} "
                       f"doesn't have permissions to use admin commands")
        await interaction.response.send_message("Brak uprawnień", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
