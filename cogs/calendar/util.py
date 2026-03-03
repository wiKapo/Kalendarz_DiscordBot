from datetime import timedelta

from g.util import *


def delete_old_events():
    # dated 3 weeks ago
    cutoff_timestamp = int((datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) -
                            timedelta(weeks=3)).timestamp())
    old_events = Db().fetch_all("SELECT * FROM events WHERE Timestamp < ?", (cutoff_timestamp,))
    print("[INFO]\tDeleting old messages")
    for old_event in old_events:
        print(f"\n{old_event}")
    Db().execute("DELETE FROM events WHERE Timestamp < ?", (cutoff_timestamp,))


async def recreate_calendar(interaction: discord.Interaction, calendar: Calendar):
    new_msg = await interaction.channel.send("Nowa wiadomość kalendarza")
    calendar.messageId = new_msg.id
    calendar.update()

    await update_calendar(interaction, calendar)

    await interaction.response.send_message("Odtworzono kalendarz.", ephemeral=True)


async def update_notification_buttons(bot: Bot, interaction: discord.Interaction, calendar: Calendar):
    print(f"[INFO]\tUpdating notification buttons of calendar [no. {calendar.id}] "
          f"in [{interaction.guild.name} - {interaction.guild.id}]")

    actions = [send_notification_add, send_notification_list, send_notification_delete]

    from g.discord_classes import NotificationButtonsView
    await (await interaction.channel.fetch_message(calendar.messageId)).edit(view=NotificationButtonsView(bot, actions))


async def send_notification_add(bot: Bot, interaction: discord.Interaction):
    await bot.get_cog("NotificationCog").get_app_commands()[0].get_command("add").callback(bot, interaction)


async def send_notification_list(bot: Bot, interaction: discord.Interaction):
    await bot.get_cog("NotificationCog").get_app_commands()[0].get_command("list").callback(bot, interaction)


async def send_notification_delete(bot: Bot, interaction: discord.Interaction):
    await bot.get_cog("NotificationCog").get_app_commands()[0].get_command("delete").callback(bot, interaction)


async def bot_update_calendar(bot: Bot, calendar: Calendar):
    print(f"[INFO]\tBot is updating calendar {calendar.title}")
    calendar_message = await ((await (await bot.fetch_guild(calendar.guildId)).fetch_channel(calendar.channelId))
                              .fetch_message(calendar.messageId))

    await calendar_message.edit(content=str(calendar))
