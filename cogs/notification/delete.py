import discord

from cogs.event.classes import SelectEventView
from cogs.notification.classes import DeleteNotificationModal
from g.util import check_if_calendar_exists


async def notification_delete(interaction: discord.Interaction, event_id: int | None):
    if not await check_if_calendar_exists(interaction): return

    print(f"[INFO]\tDeleting notifications in [{interaction.guild.name} - {interaction.guild.id}]"
          f"in [{interaction.channel.name} - {interaction.channel.id}] from [{interaction.user.name} - {interaction.user.id}]")

    if event_id is None:
        await interaction.response.send_message(
            view=SelectEventView(interaction, "Wybierz wydarzenie", DeleteNotificationModal), ephemeral=True)
    else:
        await interaction.response.send_modal(DeleteNotificationModal(interaction, event_id))
