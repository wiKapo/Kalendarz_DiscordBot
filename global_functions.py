import os
import sqlite3


def db_connect():
    connection = sqlite3.connect('calendar_database.db')
    cursor = connection.cursor()
    print('[DB]\tConnected')
    return connection, cursor


def db_disconnect(connection, cursor):
    cursor.close()
    connection.close()
    print('[DB]\tDisconnected')


async def check_if_calendar_exists(interaction, connection, cursor) -> bool:
    cursor.execute("SELECT * FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                   (interaction.guild.id, interaction.channel.id))
    if not cursor.fetchone():
        await interaction.response.send_message('Kalendarz nie istnieje na tym kanale', ephemeral=True)
        db_disconnect(connection, cursor)
        return False
    return True


async def check_user(interaction) -> bool:
    admins = map(int, os.getenv("USERS").split(','))

    if interaction.user.id in admins:
        return True

    connection, cursor = db_connect()
    cursor.execute('SELECT UserId FROM users WHERE GuildId = ?', (interaction.guild.id,))
    allowed_users = map(lambda a: a[0], cursor.fetchall())
    db_disconnect(connection, cursor)

    if interaction.user.id in allowed_users:
        return True

    await interaction.response.send_message('Brak dostępu ;)', ephemeral=True)
    return False


async def check_if_event_id_exists(interaction, connection, cursor, event_id) -> bool:
    cursor.execute("SELECT COUNT(*) FROM events JOIN calendars ON events.CalendarId = calendars.Id "
                   "WHERE GuildId = ? AND ChannelId = ?", (interaction.guild.id, interaction.channel.id))
    if cursor.fetchone()[0] >= event_id:
        return True
    db_disconnect(connection, cursor)
    await interaction.response.send_message(f"Wydarzenie o id {event_id} nie istnieje", ephemeral=True)
    return False
