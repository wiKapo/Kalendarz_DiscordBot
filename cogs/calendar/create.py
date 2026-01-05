from cogs.calendar.util import *


async def calendar_create(self, interaction, title: str = None, show_sections: bool = None):
    print(f"[INFO]\tCreating calendar in [{interaction.guild.name} - {interaction.guild.id}]"
          f" in [{interaction.channel.name} - {interaction.channel.id}]")

    result = Db().fetch_one("SELECT Id, MessageId FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                            (interaction.guild.id, interaction.channel.id))
    if result:
        try:
            await (await (await self.bot.fetch_guild(interaction.guild.id))
                   .fetch_channel(interaction.channel.id)).fetch_message(result[1])
        except discord.NotFound:
            print("[INFO]\tRecreating calendar on this channel")
            await recreate_calendar(result[0], interaction)
        except discord.HTTPException as e:
            print(f"[ERROR]\tHTTP exception: {e}")
            await interaction.response.send_message('Błąd HTTP Uh Oh', ephemeral=True)
        except Exception as e:
            print(f"[ERROR]\tInternal error: {e}")
            await interaction.response.send_message('Błąd wewnętrzny Uh Oh', ephemeral=True)
        else:
            print(f"[INFO]\tCalendar already exists on this channel. Result of the query: {result}")
            try:
                await interaction.response.send_message('Kalendarz już istnieje na tym kanale', ephemeral=True)
            except Exception as e:
                await interaction.response.send_message('Błąd wewnętrzny Uh Oh', ephemeral=True)
                print(f"[ERROR]\tInternal error: {e}")
            print("Done")
    else:
        print(f"[INFO]\tCreating calendar with {f'title \"{title}\"' if title is not None else 'default title'}")

        calendar_msg = await interaction.channel.send(f'Kaledarz pojawi się tutaj')

        Db().execute(
            "INSERT INTO calendars (GuildId, ChannelId, MessageId, Title, ShowSections) VALUES (?, ?, ?, ?, ?)",
            (interaction.guild.id, interaction.channel.id, calendar_msg.id, title,
             show_sections if show_sections is not None else False))
        calendar_id = Db().fetch_one("SELECT Id FROM calendars WHERE GuildId = ? AND ChannelId = ?",
                                     (interaction.guild.id, interaction.channel.id))[0]

        await update_calendar(interaction, calendar_id)

        await interaction.response.send_message(
            "Stworzono kalendarz. Kalendarz jest automatycznie aktualizowany codziennie o godzinie 0:00 UTC",
            ephemeral=True)
