import discord

from cogs.calendar.util import update_calendar_buttons
from g.classes.calendar import Calendar
from g.classes.logger import get_logger, LogType
from g.util import update_calendar


async def calendar_create(interaction: discord.Interaction, title: str = None) -> Calendar:
    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)

    if calendar.id:
        logger = get_logger(LogType.CALENDAR, calendar.id)
        logger.info(f"{interaction.user.name} is checking calendar "
                    f"in [{interaction.guild.name} - {interaction.guild.id}] "
                    f"in [{interaction.channel.name} - {interaction.channel.id}]")

        try:
            await (await interaction.guild.fetch_channel(interaction.channel_id)).fetch_message(calendar.messageId)

        except discord.NotFound:
            await recreate_calendar(interaction, calendar)
        except discord.HTTPException as e:
            logger.error(f"HTTP exception: {e}", exc_info=True)
            await interaction.response.send_message('Błąd HTTP Uh Oh', ephemeral=True)
        except Exception as e:
            logger.error(f"Internal error: {e}", exc_info=True)
            await interaction.response.send_message('Błąd wewnętrzny Uh Oh', ephemeral=True)
        else:
            logger.info("Calendar already exists on this channel.")
            await interaction.response.send_message('Kalendarz już istnieje na tym kanale', ephemeral=True)
    else:
        logger = get_logger(LogType.CALENDAR)
        logger.info(f"{interaction.user.name} is creating calendar with "
                    f"{f'title \"{title}\"' if title is not None else 'default title'} "
                    f"in [{interaction.guild.name} - {interaction.guild.id}] "
                    f"in [{interaction.channel.name} - {interaction.channel.id}]")

        calendar_msg = await interaction.channel.send(f'Kalendarz pojawi się tutaj')
        logger.info(f"Calendar message created: {calendar_msg.id}")

        calendar.title = title
        calendar.guildId = interaction.guild_id
        calendar.channelId = interaction.channel_id
        calendar.messageId = calendar_msg.id
        calendar.insert()
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
        logger.info(f"Calendar inserted. ID: {calendar.id}")

        calendar_logger = get_logger(LogType.CALENDAR, calendar.id)
        calendar_logger.info(f"Calendar created in {interaction.guild.name} ({interaction.guild.id}) "
                             f"in {interaction.channel.name} ({interaction.channel.id})")

        await update_calendar(interaction.guild, calendar, interaction.user.name)
        await update_calendar_buttons(interaction.guild, calendar)

        await interaction.response.send_message(
            "## Stworzono kalendarz\n"
            "Kalendarz jest automatycznie aktualizowany codziennie o godzinie 0:00 UTC\n"
            "- Dodaj wydarzenia przez wykonanie `/event add`\n"
            "- Dodaj rolę do powiadomień przez wykonanie `/calendar edit`\n"
            "- Dodaj niestandardowe sekcje przez wykonanie `/section add`\n"
            "- Dodaj role dla menedżerów przez wykonanie `/user set` Domyślnie dostęp do kalendarza mają tylko administratorzy serwera\n"
            "- Wszystkie komendy są opisane w `/help`",
            ephemeral=True)
        logger.info("Calendar created")
    return calendar


async def recreate_calendar(interaction: discord.Interaction, calendar: Calendar):
    logger = get_logger(LogType.CALENDAR, calendar.id)
    logger.info(f"{interaction.user.name} is recreating calendar on this channel")
    new_msg = await interaction.channel.send("Nowa wiadomość kalendarza")
    logger.info(f"New calendar message created: {new_msg.id}")
    calendar.messageId = new_msg.id
    calendar.update()
    logger.info("Calendar updated in the database")

    await update_calendar(interaction.guild, calendar, interaction.user.name)

    await interaction.response.send_message("Odtworzono kalendarz.", ephemeral=True)
    logger.info("Calendar is recreated")
