import datetime as dt
from datetime import datetime

import discord
from discord.ext import tasks, commands

from global_functions import *

DEFAULT_TITLE = "Kalendarz by wiKapo"

UPDATE_TIME = dt.time(hour=0, minute=0)


class DeleteCalendarModal(discord.ui.Modal, title="Czy na pewno chcesz usunąć ten kalendarz?"):
    _ = discord.ui.TextInput(label="Wyślij aby potwierdzić",
                             placeholder="placeholder, bo discord jest głupi i musi być text input",
                             default="Usuwając kalendarz usuniesz również wydarzenia!", required=False)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        connection, cursor = db_connect()
        cursor.execute("SELECT Id, MessageId FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                       (interaction.guild.id, interaction.channel.id))
        calendar_id, calendar_message_id = cursor.fetchone()
        calendar_message = await (await interaction.guild.fetch_channel(interaction.channel.id)).fetch_message(
            calendar_message_id)
        await calendar_message.delete()

        cursor.execute("DELETE FROM events WHERE CalendarId = ?", (calendar_id,))
        cursor.execute("DELETE FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                       (interaction.guild.id, interaction.channel.id))
        connection.commit()
        db_disconnect(connection, cursor)
        await interaction.response.send_message("Kalendarz został usunięty RAZEM z wydarzeniami", ephemeral=True)


class CalendarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_loop.start()

    def cog_unload(self):
        self.update_loop.cancel()

    @tasks.loop(time=UPDATE_TIME)
    async def update_loop(self):
        connection, cursor = db_connect()
        cursor.execute("SELECT Id FROM calendars")
        calendar_ids = cursor.fetchall()
        db_disconnect(connection, cursor)

        print("[INFO]\tRemoving old messages")
        self.delete_old_messages()

        print("[INFO]\tStart of updating all calendars")
        for calendar_id in calendar_ids:
            await self.update_calendar(calendar_id[0])
        print("[INFO]\tEnd of updating all calendars")

    def delete_old_messages(self):
        # date 3 weeks ago
        cutoff_timestamp = int(
            (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - dt.timedelta(weeks=3)).timestamp())

        connection, cursor = db_connect()
        cursor.execute("DELETE FROM events WHERE Timestamp < ?", (cutoff_timestamp,))
        connection.commit()
        db_disconnect(connection, cursor)

    async def update_calendar(self, calendar_id: int):
        connection, cursor = db_connect()
        print("[INFO]\tUpdating calendar")
        cursor.execute("SELECT GuildId, ChannelId, MessageId, ShowSections, Title FROM calendars WHERE Id = ?",
                       (calendar_id,))
        guild_id, channel_id, calendar_message_id, show_sections, title = cursor.fetchone()

        cursor.execute(
            "SELECT Timestamp, WholeDay, Name, Team, Place FROM events JOIN calendars ON events.CalendarId = calendars.Id "
            "WHERE calendars.Id = ? ORDER BY timestamp", (calendar_id,))
        events = cursor.fetchall()
        db_disconnect(connection, cursor)

        calendar_message = await ((await (await self.bot.fetch_guild(guild_id)).fetch_channel(channel_id))
                                  .fetch_message(calendar_message_id))

        if len(events) == 0:
            message = "\nPUSTE"
        else:
            message = ""
            current_day_delta = 0
            for event in events:
                message += "\n"
                delta_days = (datetime.fromtimestamp(event[0]).date() - datetime.now().date()).days

                if show_sections:
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
        await calendar_message.edit(content=f':calendar:\t{title}\t:calendar:{message}')

    cal_group = discord.app_commands.Group(name="calendar", description="Polecenia kalendarza")

    @cal_group.command(name="create", description="Tworzy nowy kalendarz. Kalendarz jest automatycznie aktualizowany codziennie o godzinie 0:00 UTC")
    @discord.app_commands.describe(title="Tytuł kalendarza", show_sections="Czy wydzielić sekcje w kalendarzu?")
    @discord.app_commands.choices(show_sections=[discord.app_commands.Choice(name="Tak", value=True),
                                                 discord.app_commands.Choice(name="Nie", value=False)])
    async def create(self, interaction: discord.Interaction, title: str | None,
                     show_sections: discord.app_commands.Choice[int] | None):
        if not await check_user(interaction): return

        connection, cursor = db_connect()
        cursor.execute("SELECT * FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                       (interaction.guild.id, interaction.channel.id))
        if cursor.fetchone():
            await interaction.response.send_message('Kalendarz już istnieje na tym kanale', ephemeral=True)
        else:
            print("[INFO]\tCreating new calendar")

            show_title = title
            if show_title is None:
                show_title = DEFAULT_TITLE

            if show_sections is None:
                show_sections = False
            else:
                show_sections = show_sections.value

            calendar_msg = await interaction.response.send_message(f':calendar:\t{show_title}\t:calendar:\nPUSTE')

            cursor.execute(
                "INSERT INTO calendars (GuildId, ChannelId, MessageId, Title, ShowSections) VALUES (?, ?, ?, ?, ?)",
                (interaction.guild.id, interaction.channel.id, calendar_msg.message_id, title, show_sections))
            connection.commit()

        db_disconnect(connection, cursor)

    @cal_group.command(name="update", description="Zaktualizuj kalendarz")
    async def update(self, interaction: discord.Interaction):
        if not await check_user(interaction): return
        connection, cursor = db_connect()
        calendar_id = await check_if_calendar_exists(interaction, connection, cursor)
        if calendar_id is None: return
        db_disconnect(connection, cursor)

        await self.update_calendar(calendar_id)

        await interaction.response.send_message('Kalendarz został zaktualizowany', ephemeral=True)

    @cal_group.command(name="delete", description="Usuń kalendarz")
    async def delete(self, interaction: discord.Interaction):
        if not await check_user(interaction): return

        connection, cursor = db_connect()
        if not await check_if_calendar_exists(interaction, connection, cursor): return
        db_disconnect(connection, cursor)

        print("[INFO]\tDeleting calendar")
        await interaction.response.send_modal(DeleteCalendarModal())

    edit_group = discord.app_commands.Group(name="edit", description="Edycja kalendarza", parent=cal_group)

    @edit_group.command(name="title", description="Edytuj tytuł kalendarza")
    @discord.app_commands.describe(title="Tytuł kalendarza (pozostawione puste przywraca wartość domyślną)")
    async def title(self, interaction: discord.Interaction, title: str | None):
        if not await check_user(interaction): return

        connection, cursor = db_connect()
        calendar_id = await check_if_calendar_exists(interaction, connection, cursor)
        if calendar_id is None: return

        print("[INFO]\tEditing title of the calendar")
        cursor.execute("UPDATE calendars SET Title = ? WHERE Id = ?", (title, calendar_id))
        connection.commit()
        await interaction.response.send_message("Tytuł kalendarza został zmieniony", ephemeral=True)

        db_disconnect(connection, cursor)

    @edit_group.command(name="sections", description="Zdecyduj, czy pokazywać sekcje w kalendarzu")
    @discord.app_commands.describe(
        choice="Wybierz, czy chcesz pokazywać sekcje w kalendarzu (dzisiaj/jutro/w tym tygodni/itd.) [tak/NIE]")
    @discord.app_commands.choices(choice=[discord.app_commands.Choice(name="Tak", value=True),
                                          discord.app_commands.Choice(name="Nie", value=False)])
    async def sections(self, interaction: discord.Interaction, choice: discord.app_commands.Choice[int]):
        if not await check_user(interaction): return

        connection, cursor = db_connect()
        calendar_id = await check_if_calendar_exists(interaction, connection, cursor)
        if calendar_id is None: return

        print("[INFO]\tEditing if calendar shows sections")
        cursor.execute("UPDATE calendars SET ShowSections = ? WHERE Id = ?", (choice.value, calendar_id))

        connection.commit()
        await interaction.response.send_message("Kalendarz został zmieniony", ephemeral=True)

        db_disconnect(connection, cursor)


async def setup(bot):
    await bot.add_cog(CalendarCog(bot))
