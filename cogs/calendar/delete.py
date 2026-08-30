import discord

from g.classes.calendar import Calendar, DEFAULT_TITLE
from g.classes.logger import get_logger, LogType
from g.util import check_if_calendar_exists


async def calendar_delete(interaction: discord.Interaction):
    if not await check_if_calendar_exists(interaction):
        await interaction.response.send_message("Kalendarz nie istnieje na tym kanale", ephemeral=True)
        return

    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info(f"Showing delete calendar modal for {interaction.user.name} "
                f"in [{interaction.guild.name} - {interaction.guild.id}] "
                f"in [{interaction.channel.name} - {interaction.channel.id}]")
    await interaction.response.send_modal(DeleteCalendarModal(calendar))


class DeleteCalendarModal(discord.ui.Modal):
    calendar: Calendar

    def __init__(self, calendar: Calendar):
        super().__init__(title="Usuń kalendarz")
        self.calendar = calendar
        event_count = len(calendar.eventIds)
        if event_count:
            event_amount_text = "zawiera "
            if event_count == 1:
                event_amount_text += "1 wydarzenie"
            elif event_count < 5:
                event_amount_text += f"{event_count} wydarzenia"
            else:
                event_amount_text += f"{event_count} wydarzeń"

            exclusive_events_count = len(calendar.get_exclusive_events())
            if exclusive_events_count > 0:
                event_amount_text += f"** (w tym {exclusive_events_count} przypisan{"e" if exclusive_events_count < 5 else "ych"} tylko do tego kalendarza)** "

        else:
            event_amount_text = "nie zawiera wydarzeń"

        self.add_item(discord.ui.TextDisplay(
            f"# Czy na pewno chcesz usunąć ten kalendarz?\n"
            f"**Kalendarz, który próbujesz usunąć to: "
            f"`{calendar.title if calendar.title else DEFAULT_TITLE}`, który {event_amount_text}**\n"
            f"Usuwając kalendarz usuniesz również wydarzenia, które są przypisane tylko do niego."))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        logger = get_logger(LogType.CALENDAR, self.calendar.id)
        logger.info(f"{interaction.user.name} is deleting this calendar")

        channel = await interaction.guild.fetch_channel(self.calendar.channelId)
        try:
            calendar_message = await channel.fetch_message(self.calendar.messageId)
            await calendar_message.delete()
            logger.info("Removed the calendar message.")
        except discord.NotFound:
            logger.info("The calendar message was already deleted.")
        except Exception as e:
            await interaction.response.send_message(f"Wystąpił błąd przy usuwaniu wiadomości kalendarza\n{e}",
                                                    ephemeral=True)
            logger.error(f"Error while deleting the calendar message: {e}", exc_info=True)
            return

        if self.calendar.descriptionMessageId:
            try:
                await (await channel.fetch_message(self.calendar.descriptionMessageId)).delete()
                logger.info("Removed the calendar description message.")
            except discord.NotFound:
                logger.info("The calendar description message was already deleted.")
            except Exception as e:
                await interaction.response.send_message(
                    f"Wystąpił błąd przy usuwaniu wiadomości z opisem kalendarza\n{e}",
                    ephemeral=True)

        self.calendar.delete()
        logger.info("The calendar and its events have been removed from the database.")

        await interaction.response.send_message("Kalendarz został usunięty", ephemeral=True)
