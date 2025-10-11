from datetime import datetime

import discord
from discord.ext import commands

from global_functions import *

DEFAULT_TITLE = "Kalendarz by wiKapo"


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

    cal_group = discord.app_commands.Group(name="calendar", description="Polecenia kalendarza")

    @cal_group.command(name="create", description="Tworzy nowy kalendarz")
    @discord.app_commands.describe(title="Tytuł kalendarza")
    async def create(self, interaction: discord.Interaction, title: str | None, show_sections: bool = False):
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
        if not await check_if_calendar_exists(interaction, connection, cursor): return

        print("[INFO]\tUpdating calendar")
        cursor.execute("SELECT MessageId FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                       (interaction.guild.id, interaction.channel.id))
        calendar_message_id = cursor.fetchone()[0]

        cursor.execute(
            "SELECT Timestamp, WholeDay, Name, Team, Place FROM events JOIN calendars ON events.CalendarId = calendars.Id "
            "WHERE calendars.GuildId = ? AND calendars.ChannelId = ? ORDER BY timestamp",
            (interaction.guild.id, interaction.channel.id))
        events = cursor.fetchall()
        cursor.execute("SELECT Title FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                       (interaction.guild.id, interaction.channel.id))
        title = cursor.fetchone()[0]
        db_disconnect(connection, cursor)

        calendar_message = await (await interaction.guild.fetch_channel(interaction.channel.id)).fetch_message(
            calendar_message_id)

        if len(events) == 0:
            message = "\nPUSTE"
        else:
            message = ""
            for event in events:
                message += "\n"

                # If expired
                if event[0] < int(datetime.now().timestamp()):
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
                if event[0] < int(datetime.now().timestamp()):
                    message += "~~"

        if title is None:
            title = DEFAULT_TITLE
        await calendar_message.edit(content=f':calendar:\t{title}\t:calendar:{message}')

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
        if not await check_if_calendar_exists(interaction, connection, cursor): return

        print("[INFO]\tEditing title of the calendar")
        cursor.execute("UPDATE calendars SET Title = ? WHERE GuildId = ? AND ChannelId = ?",
                       (title, interaction.guild.id, interaction.channel.id))
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
        if not await check_if_calendar_exists(interaction, connection, cursor): return

        print("[INFO]\tEditing if calendar shows sections")
        cursor.execute("UPDATE calendars SET ShowSections = ? WHERE GuildId = ? AND ChannelId = ?",
                       (choice.value, interaction.guild.id, interaction.channel.id))

        connection.commit()
        await interaction.response.send_message("Kalendarz został zmieniony", ephemeral=True)

        db_disconnect(connection, cursor)


async def setup(bot):
    await bot.add_cog(CalendarCog(bot))
