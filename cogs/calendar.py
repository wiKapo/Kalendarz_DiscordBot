from datetime import time, timedelta

import discord
from discord.ext import tasks, commands

from util import *

DEFAULT_TITLE = "Kalendarz by wiKapo"

UPDATE_TIME = time()


class DeleteCalendarModal(discord.ui.Modal, title="Usuń kalendarz"):
    _ = discord.ui.TextDisplay(
        "# Czy na pewno chcesz usunąć ten kalendarz?\nUsuwając kalendarz usuniesz również wydarzenia!")

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


class EditCalendarModal(discord.ui.Modal):
    def __init__(self, interaction: discord.Interaction):
        calendar = Db().fetch_one("SELECT Title, ShowSections  FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                                  (interaction.guild.id, interaction.channel.id))
        calendar = list(calendar)
        super().__init__(title="Edytuj kalendarz")
        TITLE = 0
        SHOW_SECTIONS = 1

        self.add_item(discord.ui.Label(text="Tytuł",
                                       description="Podaj tytuł kalendarza lub zostaw puste, aby ustawić wartość domyślną",
                                       component=discord.ui.TextInput(required=False, default=calendar[TITLE],
                                                                      placeholder=DEFAULT_TITLE)))
        self.add_item(discord.ui.Label(text="Pokaż sekcje", component=discord.ui.Select(
            options=[discord.SelectOption(label="Nie", value="0", default=calendar[SHOW_SECTIONS] == 0),
                     discord.SelectOption(label="Tak", value="1", default=calendar[SHOW_SECTIONS] == 1)])))
        # TODO dynamic sections

    async def on_submit(self, interaction: discord.Interaction) -> None:
        data = []
        for child in self.walk_children():
            if type(child) is discord.ui.TextInput:
                data.append(str(child))
            if type(child) is discord.ui.Select:
                data.append(child.values[0])

        TITLE = 0
        SHOW_SECTIONS = 1

        print(data)
        try:
            calendar_id = Db().fetch_one("SELECT Id FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                                         (interaction.guild.id, interaction.channel.id))[0]
            Db().execute("UPDATE calendars SET Title = ?, ShowSections = ? WHERE Id = ?",
                         (data[TITLE] if data[TITLE] != "" else None, data[SHOW_SECTIONS], calendar_id))
            await update_calendar(interaction, calendar_id)
        except Exception as e:
            print(e)
        await interaction.response.send_message("Kalendarz został zmieniony", ephemeral=True)


def delete_old_messages():
    # dated 3 weeks ago
    cutoff_timestamp = int((datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) -
                            timedelta(weeks=3)).timestamp())
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
    show_sections, title = Db().fetch_one("SELECT ShowSections, Title FROM calendars WHERE Id = ?", (calendar_id,))

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

            if show_sections:  # TODO make sections dynamic and per calendar
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

    @cal_group.command(name="create", description="Tworzy nowy kalendarz")
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
                    await interaction.response.send_message('Błąd wewnętrzny Uh Oh', ephemeral=True)
                    print(f"[ERROR]\tInternal error: {e}")
                print("Done")
        else:
            print(f"[INFO]\tCreating calendar with {f'title \"{title}\"' if title is not None else 'default title'}")

            calendar_msg = await interaction.channel.send(f'Kaledarz pojawi się tutaj')

            Db().execute(
                "INSERT INTO calendars (GuildId, ChannelId, MessageId, Title, ShowSections) VALUES (?, ?, ?, ?, ?)",
                (interaction.guild.id, interaction.channel.id, calendar_msg.id, title,
                 show_sections if show_sections is not None else False))
            calendar_id = Db().fetch_one("SELECT Id FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                                         (interaction.guild.id, interaction.channel.id))[0]

            await update_calendar(interaction, calendar_id)

            await interaction.response.send_message(
                "Stworzono kalendarz. Kalendarz jest automatycznie aktualizowany codziennie o godzinie 0:00 UTC",
                ephemeral=True)

    @create.error
    async def cal_group_error(self, interaction: discord.Interaction, error):
        if await check_manager(interaction) and isinstance(error, discord.app_commands.CheckFailure):
            print(f"[INFO]\tUser {interaction.user.name} doesn't have permissions to create calendars.")
            await interaction.response.send_message("Brak uprawnień", ephemeral=True)

    @cal_group.command(name="update", description="Aktualizuje kalendarz")
    @discord.app_commands.check(check_user)
    async def update(self, interaction: discord.Interaction):
        calendar_id = await check_if_calendar_exists(interaction)
        if calendar_id is None: return

        await update_calendar(interaction, calendar_id)

        await interaction.response.send_message('Kalendarz został zaktualizowany', ephemeral=True)

    @cal_group.command(name="delete", description="Usuwa kalendarz")
    @discord.app_commands.check(check_user)
    async def delete(self, interaction: discord.Interaction):
        if not await check_if_calendar_exists(interaction): return

        print("[INFO]\tDeleting calendar")
        await interaction.response.send_modal(DeleteCalendarModal())

    @cal_group.command(name="edit", description="Edytuje kalendarz")
    @discord.app_commands.check(check_user)
    async def edit(self, interaction: discord.Interaction):
        if not await check_if_calendar_exists(interaction): return

        print("[INFO]\tEditing calendar")
        try:
            await interaction.response.send_modal(EditCalendarModal(interaction))
        except Exception as e:
            await interaction.response.send_message('Błąd wewnętrzny Uh Oh', ephemeral=True)
            print(e)


async def setup(bot):
    await bot.add_cog(CalendarCog(bot))
