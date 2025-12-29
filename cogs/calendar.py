import datetime as base_datetime

import discord
from discord.ext import tasks, commands

from util import *

DEFAULT_TITLE = "Kalendarz by wiKapo"

UPDATE_TIME = base_datetime.time(hour=0, minute=0)


class DeleteCalendarModal(discord.ui.Modal, title="Czy na pewno chcesz usunąć ten kalendarz?"):
    _ = discord.ui.TextInput(label="Wyślij aby potwierdzić",
                             placeholder="placeholder, bo discord jest głupi i musi być text input",
                             default="Usuwając kalendarz usuniesz również wydarzenia!", required=False)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        calendar_id, calendar_message_id = Db().fetch_one(
            "SELECT Id, MessageId FROM calendars WHERE GuildId = ? AND ChannelId = ?",
            (interaction.guild.id, interaction.channel.id))
        print(
            f"[INFO]\tDeleting calendar from server [{interaction.guild.name}] from channel [{interaction.channel.name}]")
        calendar_message = await (await interaction.guild.fetch_channel(interaction.channel.id)).fetch_message(
            calendar_message_id)
        await calendar_message.delete()
        print("[INFO] Removed the calendar message.")
        Db().execute("DELETE FROM events WHERE CalendarId = ?", (calendar_id,))
        Db().execute("DELETE FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                     (interaction.guild.id, interaction.channel.id))
        print("[INFO] The calendar and its events have been removed from the database.")

        await interaction.response.send_message("Kalendarz został usunięty RAZEM z wydarzeniami", ephemeral=True)


def delete_old_messages():
    # date 3 weeks ago
    cutoff_timestamp = int((datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) -
                            base_datetime.timedelta(weeks=3)).timestamp())
    old_events = Db().fetch_all("SELECT * FROM events WHERE Timestamp < ?", (cutoff_timestamp,))
    print("[INFO]\tDeleting old messages")
    for old_event in old_events:
        print(f"\n{old_event}")
    Db().execute("DELETE FROM events WHERE Timestamp < ?", (cutoff_timestamp,))


async def recreate_calendar(calendar_id: int, interaction: discord.Interaction):
    new_msg = await interaction.channel.send("Nowa wiadomość kalendarza")
    Db().execute("UPDATE calendars SET MessageId = ? WHERE Id = ?", (new_msg.id, calendar_id))

    await update_calendar(interaction, calendar_id)

    await interaction.response.send_message("Odtworzono kalendarz.")


def create_calendar_message(calendar_id: int):
    show_sections, title = Db().fetch_one("SELECT ShowSections, Title FROM calendars WHERE Id = ?",
                                          (calendar_id,))

    events = Db().fetch_all(
        "SELECT Timestamp, WholeDay, Name, Team, Place FROM events JOIN calendars "
        "ON events.CalendarId = calendars.Id WHERE calendars.Id = ? ORDER BY timestamp", (calendar_id,))

    if len(events) == 0:
        message = "\nPUSTE"
    else:
        message = ""
        current_day_delta = 0
        for event in events:
            message += "\n"
            delta_days = (datetime.fromtimestamp(event[0]).date() - datetime.now().date()).days

            if show_sections: #TODO make sections dynamic and per calendar
                if delta_days >= 0 and delta_days >= current_day_delta != 99:
                    if delta_days < 1:
                        message += "\n\t---==[  Dzisiaj  ]==---\n"
                        current_day_delta = 1
                    elif delta_days < 2:
                        message += "\n\t---==[  Jutro  ]==---\n"
                        current_day_delta = 2
                    elif delta_days < 7:
                        message += "\n\t---==[  W tym tygodniu  ]==---\n"
                        current_day_delta = 7
                    elif delta_days < 14:
                        message += "\n\t---==[  Za tydzień  ]==---\n"
                        current_day_delta = 14
                    elif delta_days < 30:
                        message += "\n\t---==[  W tym miesiącu  ]==---\n"
                        current_day_delta = 30
                    elif delta_days < 60:
                        message += "\n\t---==[  Za miesiąc  ]==---\n"
                        current_day_delta = 60
                    else:
                        message += "\n\t---==[  W przyszłości  ]==---\n"
                        current_day_delta = 99

            # If expired
            if delta_days < 0:
                message += "~~"

            # Timestamp
            message += f"<t:{str(event[0])}"
            if event[1]:
                message += ":D"
            message += "> "

            # Group
            if event[3]:
                message += f"[{event[3]}] "
            # Name
            message += f"**{event[2]}"
            # Place
            if event[4]:
                message += f" @ {event[4]}"
            message += " **"

            # If expired
            if delta_days < 0:
                message += "~~"

    if title is None:
        title = DEFAULT_TITLE

    return title, message


async def update_calendar(interaction: discord.Interaction, calendar_id: int):
    title, message = create_calendar_message(calendar_id)

    print(f"[INFO]\tUpdating calendar {title} in [{interaction.guild.name} - {interaction.guild.id}]"
          f" in [{interaction.channel.name} - {interaction.channel.id}]")

    calendar_message_id = Db().fetch_one("SELECT MessageId FROM calendars WHERE Id = ?", (calendar_id,))[0]
    calendar_message = await interaction.channel.fetch_message(calendar_message_id)

    await calendar_message.edit(content=f':calendar:\t{title}\t:calendar:{message}')


class CalendarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_loop.start()

    def cog_unload(self):
        self.update_loop.cancel()

    @tasks.loop(time=UPDATE_TIME)
    async def update_loop(self):
        calendar_ids = Db().fetch_all("SELECT Id FROM calendars")

        print("[INFO]\tRemoving old messages")
        delete_old_messages()

        print("[INFO]\tStart of updating all calendars")
        for calendar_id in calendar_ids:
            await self.bot_update_calendar(calendar_id[0])
        print("[INFO]\tEnd of updating all calendars")

    async def bot_update_calendar(self, calendar_id: int):
        title, message = create_calendar_message(calendar_id)

        print(f"[INFO]\tBot is updating calendar {title}")
        guild_id, channel_id, calendar_message_id = Db().fetch_one(
            "SELECT GuildId, ChannelId, MessageId FROM calendars WHERE Id = ?", (calendar_id,))

        calendar_message = await ((await (await self.bot.fetch_guild(guild_id)).fetch_channel(channel_id))
                                  .fetch_message(calendar_message_id))

        await calendar_message.edit(content=f':calendar:\t{title}\t:calendar:{message}')

    cal_group = discord.app_commands.Group(name="calendar", description="Polecenia kalendarza")

    @cal_group.command(name="create",
                       description="Tworzy nowy kalendarz. Kalendarz jest automatycznie aktualizowany codziennie o godzinie 0:00 UTC")
    @discord.app_commands.describe(title="Tytuł kalendarza", show_sections="Czy wydzielić sekcje w kalendarzu?")
    @discord.app_commands.choices(show_sections=[discord.app_commands.Choice(name="Tak", value=True),
                                                 discord.app_commands.Choice(name="Nie", value=False)])
    @discord.app_commands.check(check_user)
    async def create(self, interaction: discord.Interaction, title: str | None,
                     show_sections: discord.app_commands.Choice[int] | None):
        print(f"[INFO]\tCreating calendar in [{interaction.guild.name} - {interaction.guild.id}]"
              f" in [{interaction.channel.name} - {interaction.channel.id}]")

        result = Db().fetch_one("SELECT Id, MessageId FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                                (interaction.guild.id, interaction.channel.id))
        if result:
            try:
                await (await (await self.bot.fetch_guild(interaction.guild.id))
                       .fetch_channel(interaction.channel.id)).fetch_message(result[1])
            except discord.NotFound:
                print("[INFO]\tRecreating calendar on this channel")
                await recreate_calendar(result[0], interaction)
            except discord.HTTPException as e:
                print(f"[ERROR]\tHTTP exception: {e}")
                await interaction.response.send_message('Błąd HTTP Uh Oh', ephemeral=True)
            except Exception as e:
                print(f"[ERROR]\tInternal error: {e}")
                await interaction.response.send_message('Błąd wewnętrzny Uh Oh', ephemeral=True)
            else:
                print(f"[INFO]\tCalendar already exists on this channel. Result of the query: {result}")
                try:
                    await interaction.response.send_message('Kalendarz już istnieje na tym kanale', ephemeral=True)
                except Exception as e:
                    print(f"[ERROR]\tInternal error: {e}")
                print("Done")
        else:
            print(
                f"[INFO]\tCreating calendar with title \"{title}\"")

            show_title = title
            if show_title is None:
                show_title = DEFAULT_TITLE

            if show_sections is None:
                show_sections = False
            else:
                show_sections = show_sections.value

            calendar_msg = await interaction.channel.send(f':calendar:\t{show_title}\t:calendar:\nPUSTE')

            Db().execute(
                "INSERT INTO calendars (GuildId, ChannelId, MessageId, Title, ShowSections) VALUES (?, ?, ?, ?, ?)",
                (interaction.guild.id, interaction.channel.id, calendar_msg.id, title, show_sections))

            await interaction.response.send_message("Stworzono kalendarz", ephemeral=True)

    @create.error
    async def cal_group_error(self, interaction: discord.Interaction, error):
        if await check_manager(interaction) and isinstance(error, discord.app_commands.CheckFailure):
            print(f"[INFO]\tUser {interaction.user.name} doesn't have permissions to create calendars.")
            await interaction.response.send_message("Brak uprawnień", ephemeral=True)

    @cal_group.command(name="update", description="Zaktualizuj kalendarz")
    @discord.app_commands.check(check_user)
    async def update(self, interaction: discord.Interaction):
        calendar_id = await check_if_calendar_exists(interaction)
        if calendar_id is None: return

        await update_calendar(interaction, calendar_id)

        await interaction.response.send_message('Kalendarz został zaktualizowany', ephemeral=True)

    @cal_group.command(name="delete", description="Usuń kalendarz")
    @discord.app_commands.check(check_user)
    async def delete(self, interaction: discord.Interaction):
        if not await check_if_calendar_exists(interaction): return

        print("[INFO]\tDeleting calendar")
        await interaction.response.send_modal(DeleteCalendarModal())

    edit_group = discord.app_commands.Group(name="edit", description="Edycja kalendarza", parent=cal_group)
    # TODO Change to one big modal

    @edit_group.command(name="title", description="Edytuj tytuł kalendarza")
    @discord.app_commands.describe(title="Tytuł kalendarza (pozostawione puste przywraca wartość domyślną)")
    @discord.app_commands.check(check_user)
    async def title(self, interaction: discord.Interaction, title: str | None):
        calendar_id = await check_if_calendar_exists(interaction)
        if calendar_id is None: return

        print("[INFO]\tEditing title of the calendar")
        Db().execute("UPDATE calendars SET Title = ? WHERE Id = ?", (title, calendar_id))
        await interaction.response.send_message("Tytuł kalendarza został zmieniony", ephemeral=True)

    @edit_group.command(name="sections", description="Zdecyduj, czy pokazywać sekcje w kalendarzu")
    @discord.app_commands.describe(
        choice="Wybierz, czy chcesz pokazywać sekcje w kalendarzu (dzisiaj/jutro/w tym tygodni/itd.) [tak/NIE]")
    @discord.app_commands.choices(choice=[discord.app_commands.Choice(name="Tak", value=True),
                                          discord.app_commands.Choice(name="Nie", value=False)])
    @discord.app_commands.check(check_user)
    async def sections(self, interaction: discord.Interaction, choice: discord.app_commands.Choice[int]):
        calendar_id = await check_if_calendar_exists(interaction)
        if calendar_id is None: return

        print("[INFO]\tEditing if calendar shows sections")
        Db().execute("UPDATE calendars SET ShowSections = ? WHERE Id = ?", (choice.value, calendar_id))
        await interaction.response.send_message("Kalendarz został zmieniony", ephemeral=True)


async def setup(bot):
    await bot.add_cog(CalendarCog(bot))
