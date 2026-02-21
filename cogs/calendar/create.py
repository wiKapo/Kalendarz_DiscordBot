from cogs.calendar.util import *


async def calendar_create(bot: Bot, interaction, title: str = None, show_sections: bool = None):
    print(f"[INFO]\tCreating calendar in [{interaction.guild.name} - {interaction.guild.id}]"
          f" in [{interaction.channel.name} - {interaction.channel.id}]")

    calendar = Calendar()
    try:
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
    except Exception as e:
        print(e)
        return

    if calendar.id:
        try:
            await (await (await bot.fetch_guild(interaction.guild.id))
                   .fetch_channel(interaction.channel.id)).fetch_message(calendar.messageId)

        except discord.NotFound:
            print("[INFO]\tRecreating calendar on this channel")
            await recreate_calendar(interaction, calendar)
        except discord.HTTPException as e:
            print(f"[ERROR]\tHTTP exception: {e}")
            await interaction.response.send_message('Błąd HTTP Uh Oh', ephemeral=True)
        except Exception as e:
            print(f"[ERROR]\tInternal error: {e}")
            await interaction.response.send_message('Błąd wewnętrzny Uh Oh', ephemeral=True)
        else:
            print(f"[INFO]\tCalendar already exists on this channel.")
            await interaction.response.send_message('Kalendarz już istnieje na tym kanale', ephemeral=True)
    else:
        print(f"[INFO]\tCreating calendar with {f'title \"{title}\"' if title is not None else 'default title'}")

        calendar_msg = await interaction.channel.send(f'Kaledarz pojawi się tutaj')

        calendar.set_insert_and_fetch(
            [title, show_sections if show_sections is not None else False, interaction.guild_id, interaction.channel_id,
             calendar_msg.id])
        await update_calendar(interaction, calendar)
        print("Heyo")
        await update_notification_buttons(bot, interaction, calendar)

        await interaction.response.send_message(
            "Stworzono kalendarz. Kalendarz jest automatycznie aktualizowany codziennie o godzinie 0:00 UTC",
            ephemeral=True)
