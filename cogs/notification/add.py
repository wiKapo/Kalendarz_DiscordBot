from cogs.notification.classes import AddNotificationModal, send_add_notification_modal
from g.discord_classes import SelectEventView
from g.util import *


async def notification_add(interaction: discord.Interaction, event_id: int | None):
    if not await check_if_calendar_exists(interaction): return

    print(f"[INFO]\tModifying notifications in [{interaction.guild.name} - {interaction.guild.id}]"
          f" in [{interaction.channel.name} - {interaction.channel.id}] for [{interaction.user.name} - {interaction.user.id}]")

    if event_id is None:
        events = fetch_events_by_channel(interaction.guild_id, interaction.channel_id)
        await interaction.response.send_message(
            view=SelectEventView(events, "Wybierz wydarzenie", send_add_notification_modal), ephemeral=True)
    else:
        await interaction.response.send_modal(AddNotificationModal(interaction, event_id))
