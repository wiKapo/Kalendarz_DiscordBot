import sqlite3
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from cogs.calendar.create import calendar_create
from cogs.calendar.util import update_calendar_buttons
from g.classes.calendar import fetch_all_calendars, Calendar
from g.classes.db import Db
from g.classes.event import fetch_all_events, Event
from g.classes.logger import get_logger, LogType
from g.classes.message import Message
from g.util import check_calendar_admin, update_calendar, check_if_calendar_exists, BOT_VERSION


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
            message.message = "**Aktualizacja kalendarza** WERSJA 1.0!!!"
            message.insert_with_check()
            message.message = "**Aktualizacja kalendarza** Możliwe jest dodawanie jednego wydarzenia do wielu kalendarzy"
            message.insert_with_check()
            message.message = "**Aktualizacja kalendarza** Zaktualizowano opis kalendarza, który teraz pojawia się zawsze. Jest niezależny od roli aktualizacji kalendarza"
            message.insert_with_check()
            message.message = "**Aktualizacja kalendarza** Wydzielono tworzenie niestandardowych sekcji do komendy `/section`"
            message.insert_with_check()
            message.message = (
                "**Aktualizacja kalendarza** Zmieniono działanie powiadomień. Teraz można zaznaczyć chęć otrzymywania powiadomień przez przycisk pod kalendarzem. "
                "Powiadomienia zostają wysyłane w dniu lub dzień przed wydarzeniem. W niedzielę zostaje wysłane większe powiadomienie, które zawiera wydarzenia z najbliższego i następnego tygodnia. "
                "Powiadomienia są wysyłane o godzinie 7:00.")
            message.insert_with_check()
            message.message = "**Aktualizacja kalendarza** ***UWAGA*** Usunięto wszystkie utworzone niestandardowe sekcje i powiadomienia"  # TODO ALWAYS UPDATE ME
            message.insert_with_check()
            logger.info("Sent update message")

            try:
                guild = await self.bot.fetch_guild(calendar.guildId)
                await update_calendar(guild, calendar, interaction.user.name, True,
                                      f"**Kalendarz został zaktualizowany do wersji {BOT_VERSION}**\n"
                                      f"Więcej o tej aktualizacji tutaj: https://discord.gg/ayXkVwVkGA "
                                      f"i pod przyciskiem `Pokaż ostatnie zmiany`\n")
                await update_calendar_buttons(guild, calendar)

                await interaction.followup.send(f"Zaktualizowano kalendarz #{calendar.id}", ephemeral=True)
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
        await no_permissions_message(interaction, error)

    @admin_group.command(name="remove_admin_cog", description="[TYLKO DLA ADMINÓW KALENDARZA] "
                                                              "Ukrywa komendy administratorów")
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
        await no_permissions_message(interaction, error)

    @admin_group.command(name="update_db", description="[TYLKO DLA ADMINÓW KALENDARZA] "
                                                       "Aktualizuje strukturę bazy danych")
    @discord.app_commands.check(check_calendar_admin)
    async def update_db(self, interaction: discord.Interaction):
        logger = get_logger()
        logger.info(f"Updating database for guild: {interaction.guild.name}")

        await interaction.response.send_message("Aktualizowanie bazy danych", ephemeral=True)

        try:
            logger.info("Updating calendars table. Removing ShowSections column")
            Db().execute("ALTER TABLE calendars DROP COLUMN ShowSections")
            await interaction.followup.send("Zaktualizowano tabelę `calendars`. Usunięto kolumnę `ShowSections",
                                            ephemeral=True)
            logger.info("Success")
        except sqlite3.OperationalError as e:
            logger.error(f"Failed on purpose. Error: {e}")
            await interaction.followup.send("Tabela `calendars` jest już zaktualizowana", ephemeral=True)
        except Exception as e:
            logger.error(f"Failed. Error: {e} Type: {type(e)}")
            await interaction.followup.send(f"Wykryto błąd zatrzymuję. ERROR: {e}", ephemeral=True)
            return

        try:
            logger.info("Updating events")
            calendar_ids = Db().fetch_all("SELECT Id FROM calendars")
            for c_id in calendar_ids:
                c_id = c_id[0]
                event_ids = Db().fetch_all("SELECT Id FROM events WHERE CalendarId=?", (c_id,))
                logger.info(
                    f"Found {len(event_ids)} events in calendar {c_id}."
                    f"{"" if len(event_ids) == 0 else "Populating eventsInCalendars table..."}")

                if event_ids:
                    for e_id in event_ids:
                        e_id = e_id[0]
                        try:
                            Db().execute("INSERT INTO eventsInCalendars (CalendarId, EventId) VALUES (?, ?)",
                                         (c_id, e_id))
                        except Exception as e:
                            logger.error(f"(C{c_id}, E{e_id}) Pair already exists in database. Error: {e}")

            logger.info("Finished")
            await interaction.followup.send("Uzupełniono tabelę `eventsInCalendars`", ephemeral=True)

        except sqlite3.OperationalError as e:
            logger.error(f"Failed on purpose. Error: {e}")
            await interaction.followup.send(f"Tabela `eventsInCalendars` została już uzupełniona", ephemeral=True)
        except Exception as e:
            logger.error(f"Failed. Error: {e} Type: {type(e)}")
            await interaction.followup.send(f"Wykryto błąd zatrzymuję. ERROR: {e}", ephemeral=True)
            return

        try:
            logger.info("Updating events table")
            Db().execute("ALTER TABLE events DROP COLUMN CalendarId")
            logger.info("Finished")
            await interaction.followup.send(
                "Zaktualizowano tabelę `events` i stworzono tabelę `eventsInCalendars` aktualizację bazy danych",
                ephemeral=True)
        except sqlite3.OperationalError as e:
            logger.error(f"Failed on purpose. Error: {e}")
            await interaction.followup.send(f"Tabela `events` została już zaktualizowana", ephemeral=True)
        except Exception as e:
            logger.error(f"Failed. Error: {e} Type: {type(e)}")
            await interaction.followup.send(f"Wykryto błąd zatrzymuję. ERROR: {e}", ephemeral=True)
            return

        try:
            logger.info("Updating sections table")
            Db().execute("SELECT TimeTag FROM sections")

            Db().execute("DROP TABLE IF EXISTS sections ")
            Db().execute("CREATE TABLE IF NOT EXISTS sections ("
                         "CalendarId INT NOT NULL REFERENCES calendars(Id) ON DELETE CASCADE, "
                         "BeginTimestamp INT NOT NULL,"
                         "EndTimestamp INT,"
                         "Name TEXT NOT NULL,"
                         "PRIMARY KEY (CalendarId, BeginTimestamp)"
                         ");")
            logger.info("Finished")
            await interaction.followup.send("Zmieniono tabelę `sections`", ephemeral=True)

        except sqlite3.OperationalError as e:
            logger.error(f"Failed on purpose. Error: {e}")
            await interaction.followup.send(f"Tabela `sections` została już zaktualizowana", ephemeral=True)
        except Exception as e:
            logger.error(f"Failed. Error: {e} Type: {type(e)}")
            await interaction.followup.send(f"Wykryto błąd zatrzymuję. ERROR: {e}", ephemeral=True)
            return

        try:
            logger.info("Changing the name of field PingMessageId in calendars table")
            Db().execute("ALTER TABLE calendars RENAME PingMessageId TO DescriptionMessageId")
            logger.info("Finished")
            await interaction.followup.send(
                f"Zaktualizowano tabelę `calendars`. Zmieniono pole `PingMessageId` na `DescriptionMessageId`",
                ephemeral=True)

        except sqlite3.OperationalError as e:
            logger.error(f"Failed on purpose. Error: {e}")
            await interaction.followup.send(f"Tabela `calendars` została już zaktualizowana", ephemeral=True)
        except Exception as e:
            logger.error(f"Failed. Error: {e} Type: {type(e)}")
            await interaction.followup.send(f"Wykryto błąd zatrzymuję. ERROR: {e}", ephemeral=True)
            return

        try:
            logger.info("Removing notifications table")
            data = Db().fetch_all("PRAGMA table_info(notifications)")
            if 0 < len(data) <= 2:
                raise sqlite3.OperationalError("Notification table is smaller than 3 columns")

            Db().execute("DROP TABLE IF EXISTS notifications")
            Db().execute("CREATE TABLE IF NOT EXISTS notifications ("
                         "UserId BIGINT NOT NULL,"
                         "CalendarId INTEGER NOT NULL REFERENCES calendars(Id) ON DELETE CASCADE,"
                         "PRIMARY KEY (UserId, CalendarId)"
                         ");")
            logger.info("Done")
            await interaction.followup.send("Zmieniono tabelę `notifications`", ephemeral=True)

        except sqlite3.OperationalError as e:
            logger.error(f"Failed on purpose. Error: {e}")
            await interaction.followup.send(f"Tabela `notifications` została już zmodyfikowana", ephemeral=True)
        except Exception as e:
            logger.error(f"Failed. Error: {e} Type: {type(e)}")
            await interaction.followup.send(f"Wykryto błąd zatrzymuję. ERROR: {e}", ephemeral=True)
            return

        await interaction.followup.send("Skończono aktualizować bazę danych", ephemeral=True)

    @update_db.error
    async def update_db_error(self, interaction: discord.Interaction, error):
        await no_permissions_message(interaction, error)

    # @admin_group.command(name="test", description="Testowanie")
    # @discord.app_commands.check(check_calendar_admin)
    # async def test(self, interaction: discord.Interaction):
    #     test = fetch_all_notifications()
    #     print(test)
    #     await interaction.response.send_message("Test", ephemeral=True)
    #
    # @test.error
    # async def test_error(self, interaction: discord.Interaction, error):
    #     await no_permissions_message(interaction, error)

    @admin_group.command(name="update_event_loggers", description="[TYLKO DLA ADMINÓW KALENDARZA] "
                                                                  "Aktualizuje loggery wydarzeń")
    @discord.app_commands.check(check_calendar_admin)
    async def update_event_loggers(self, interaction: discord.Interaction):
        await interaction.response.send_message("Tworzenie wpisów do loggerów wydarzeń", ephemeral=True)

        events = fetch_all_events()
        for event in events:
            guild_id = event.get_guild_id()
            logger = get_logger(LogType.EVENT, event.id)
            logger.info(f"In guild {(await self.bot.fetch_guild(guild_id)).name} "
                        f"({guild_id}) in calendars {event.calendarIds}")
            logger.debug(repr(event))
        await interaction.followup.send("Dopisano lokację każdego wydarzenia", ephemeral=True)

    @update_event_loggers.error
    async def update_event_loggers_error(self, interaction: discord.Interaction, error):
        await no_permissions_message(interaction, error)

    @admin_group.command(name="create_test_calendar", description="[TYLKO DLA ADMINÓW KALENDARZA] "
                                                                  "Tworzy testowy kalendarz")
    @discord.app_commands.check(check_calendar_admin)
    async def create_test_calendar(self, interaction: discord.Interaction):
        default_calendar_logger = get_logger(LogType.CALENDAR)
        default_calendar_logger.info("Checking if calendar exists on the channel")
        calendar_id = await check_if_calendar_exists(interaction)
        if calendar_id:
            default_calendar_logger.warning("Calendar already exists")
            calendar = Calendar()
            calendar.fetch(calendar_id)
            await interaction.response.send_message("Dodawanie do tego kalendarza wydarzeń testowych", ephemeral=True)
        else:
            default_calendar_logger.warning("Creating test calendar")
            calendar = await calendar_create(interaction, "Kalendarz testowy")
            await interaction.followup.send("Utworzono testowy kalendarz", ephemeral=True)
        logger = get_logger(LogType.CALENDAR, calendar.id)
        logger.info("Creating test events")

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        create_event("Uno", today, calendar.id)
        create_event("Dwa", today + timedelta(hours=1), calendar.id, whole_day=False)
        create_event("Set", today + timedelta(days=1), calendar.id)
        create_event("Vier", today + timedelta(days=2), calendar.id)
        create_event("Week", today + timedelta(weeks=1), calendar.id, team="LOL")
        create_event("Weak", today + timedelta(weeks=1, days=2, hours=14, minutes=22), calendar.id, whole_day=False)
        create_event("Week2", today + timedelta(weeks=2), calendar.id, team="xD", place="Chrząszczyżewoszyce")
        create_event("Tygodzianka", today + timedelta(weeks=3), calendar.id, place=":calendar: :calendar: :calendar:")
        create_event("Monat", today + timedelta(days=31, hours=21, minutes=37), calendar.id, whole_day=False)
        create_event("Moneta", today + timedelta(days=35, hours=8, minutes=13, weeks=2), calendar.id, whole_day=False)
        create_event("Money", today + timedelta(days=42, hours=15, minutes=45, weeks=3), calendar.id, whole_day=False)
        create_event("Przyszłość", today + timedelta(days=62, hours=11, minutes=55, weeks=3), calendar.id,
                     team="Przyszłość", place="Przyszłość", whole_day=False)
        logger.info("Done")
        await update_calendar(interaction.guild, calendar, interaction.user.name)
        await interaction.followup.send("Utworzono testowe wydarzenia", ephemeral=True)

    @create_test_calendar.error
    async def create_test_calendar_error(self, interaction: discord.Interaction, error):
        await no_permissions_message(interaction, error)


def create_event(name: str, dt: datetime, calendar_id: int, whole_day: bool = True, place: str | None = None,
                 team: str | None = None) -> Event:
    event = Event()
    event.name = name
    if whole_day:
        event.set_datetime(dt.strftime("%d.%m.%Y"))
    else:
        event.set_datetime(dt.strftime("%d.%m.%Y %H:%M"))
    event.place = place
    event.team = team
    event.insert()
    event.connect_to_calendar(calendar_id)
    return event


async def setup(bot):
    await bot.add_cog(AdminCog(bot))


async def no_permissions_message(interaction: discord.Interaction, error):
    logger = get_logger()
    logger.warning(f"{error}\nUser {interaction.user.name} {interaction.user.id} "
                   f"doesn't have permissions to use admin commands", exc_info=True)
    await interaction.response.send_message("Brak uprawnień", ephemeral=True)
