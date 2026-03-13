from g.util import *


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
