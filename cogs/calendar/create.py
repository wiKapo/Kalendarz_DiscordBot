from cogs.calendar.util import *


async def calendar_create(bot: Bot, interaction, title: str = None, show_sections: bool = None):
    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)

    if calendar.id:
        logger = get_logger(LogType.CALENDAR, calendar.id)
        logger.info(f"Checking calendar in [{interaction.guild.name} - {interaction.guild.id}]"
                    f" in [{interaction.channel.name} - {interaction.channel.id}]")

        try:
            await (await (await bot.fetch_guild(interaction.guild.id))
                   .fetch_channel(interaction.channel.id)).fetch_message(calendar.messageId)

        except discord.NotFound:
            await recreate_calendar(interaction, calendar)
        except discord.HTTPException as e:
            logger.error(f"HTTP exception: {e}")
            await interaction.response.send_message('Błąd HTTP Uh Oh', ephemeral=True)
        except Exception as e:
            logger.error(f"Internal error: {e}")
            await interaction.response.send_message('Błąd wewnętrzny Uh Oh', ephemeral=True)
        else:
            logger.info("Calendar already exists on this channel.")
            await interaction.response.send_message('Kalendarz już istnieje na tym kanale', ephemeral=True)
    else:
        logger = get_logger(LogType.CALENDAR)
        logger.info(f"Creating calendar with {f'title \"{title}\"' if title is not None else 'default title'}"
                    f" in [{interaction.guild.name} - {interaction.guild.id}]"
                    f" in [{interaction.channel.name} - {interaction.channel.id}]")

        calendar_msg = await interaction.channel.send(f'Kalendarz pojawi się tutaj')
        logger.info(f"Calendar message created: {calendar_msg.id}")

        calendar.title = title
        calendar.showSections = show_sections if show_sections is not None else False
        calendar.guildId = interaction.guild_id
        calendar.channelId = interaction.channel_id
        calendar.messageId = calendar_msg.id
        calendar.insert()
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
        logger.info(f"Calendar inserted. ID: {calendar.id}")

        await update_calendar(interaction, calendar)
        await update_notification_buttons(bot, interaction, calendar)

        await interaction.response.send_message(
            "Stworzono kalendarz. Kalendarz jest automatycznie aktualizowany codziennie o godzinie 0:00 UTC\n"
            "Dodaj rolę do powiadomień przez wykonanie `/calendar edit`\n"
            "Dodaj role dla menedżerów przez wykonanie `/user set`\n"
            "Wszystkie komendy są opisane w `/help`",
            ephemeral=True)
        logger.info("Calendar created")
