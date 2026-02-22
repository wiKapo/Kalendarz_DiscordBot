from datetime import timedelta

from discord.ext.commands import Bot

from g.util import *

DEFAULT_TITLE = "Kalendarz by wiKapo"


def delete_old_messages():
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


def create_calendar_message(calendar: Calendar):
    events: list[Event] = fetch_events_by_calendar(calendar.id)
    if len(events) == 0:
        message = "\nPUSTE"
    else:
        message = ""
        current_day_delta = 0
        for event in events:
            message += "\n"
            delta_days = (datetime.fromtimestamp(event.timestamp).date() - datetime.now().date()).days

            if calendar.showSections == 1:  # TODO make sections dynamic and per calendar
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

            message += format_event(event)

            # If expired
            if delta_days < 0:
                message += "~~"

    return (DEFAULT_TITLE if calendar.title is None else calendar.title), message


class AddRoleButtonView(discord.ui.View):
    role: int

    def __init__(self, role: int):
        super().__init__(timeout=None)
        self.role = role

    @discord.ui.button(label="Otrzymuj powiadomienia o aktualizacji kalendarza", style=discord.ButtonStyle.secondary,
                       custom_id="ping")
    async def ping(self, interaction: discord.Interaction, _):
        role: discord.role.Role = interaction.guild.get_role(self.role)
        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(
                    "Nie będziesz już otrzymywał powiadomień o aktualizacjach tego kalendarza", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(
                    "Teraz będziesz otrzymywał powiadomienia o aktualizacjach tego kalendarza\n"
                    "Aby zrezygnować kliknij ponownie.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("**Bot nie posiada uprawnień do zmieniania ról**\n"
                                                    "Aby je dodać trzeba przejść do `Ustawienia serwera > Role`, "
                                                    "wybrać rolę kalendarza i w uprawnieniach włączyć `Zarządzanie powiadomieniami`",
                                                    ephemeral=True)


async def update_calendar(interaction: discord.Interaction, calendar: Calendar):
    title, message = create_calendar_message(calendar)

    print(f"[INFO]\tUpdating calendar {title} in [{interaction.guild.name} - {interaction.guild.id}]"
          f" in [{interaction.channel.name} - {interaction.channel.id}]")

    await ((await interaction.channel.fetch_message(calendar.messageId))
           .edit(content=f':calendar:\t{title}\t:calendar:{message}\n\nZarządzaj powiadomieniami przyciskami poniżej'))

    await send_calendar_ping(interaction, calendar)


async def send_calendar_ping(interaction: discord.Interaction, calendar: Calendar):
    if calendar.pingMessageId is not None:
        await (await interaction.channel.fetch_message(calendar.pingMessageId)).delete()

    if calendar.pingRoleId is not None:
        message = await interaction.channel.send(
            f"<@&{calendar.pingRoleId}>\n-# Ostatnia aktualizacja: <t:{int(datetime.now().timestamp())}>",
            view=AddRoleButtonView(calendar.pingRoleId))
        calendar.pingMessageId = message.id
        calendar.update()


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
    title, message = create_calendar_message(calendar)

    print(f"[INFO]\tBot is updating calendar {title}")
    calendar_message = await ((await (await bot.fetch_guild(calendar.guildId)).fetch_channel(calendar.channelId))
                              .fetch_message(calendar.messageId))

    await calendar_message.edit(content=f':calendar:\t{title}\t:calendar:{message}')
