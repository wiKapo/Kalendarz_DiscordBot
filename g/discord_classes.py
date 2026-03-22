import logging
from collections.abc import Callable

import discord
from discord.ext.commands import Bot

from g.classes import Event, Calendar, fetch_messages_for_calendar, format_event_entries


class SelectEvent(discord.ui.Select):
    action: Callable
    events: list[Event]

    def __init__(self, events: list[Event], placeholder: str, action: Callable, max_values: int = 1):
        options = format_event_entries(events)
        super().__init__(placeholder=placeholder, options=options, max_values=max_values)
        self.action = action
        self.events = events

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.action(interaction, self.events, self.values)
        except Exception as e:
            await interaction.response.send_message(f"Błąd przy wykonywaniu akcji", ephemeral=True)
            logger = logging.getLogger("default")
            logger.error(f"in callback of SelectEvent in [{interaction.guild.name} - {interaction.guild.id}] "
                         f"in [{interaction.channel.name} - {interaction.channel.id}]: {e}", exc_info=True)


class SelectEventView(discord.ui.View):
    def __init__(self, events: list[Event], placeholder: str, action: Callable, max_values: int = 1):
        super().__init__()
        self.add_item(SelectEvent(events, placeholder, action, max_values))


class NotificationButton(discord.ui.Button):
    action: Callable
    bot: Bot

    def __init__(self, label: str, style: discord.ButtonStyle, bot: Bot, action: Callable):
        super().__init__(label=label, style=style)
        self.action = action
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.action(self.bot, interaction)
        except Exception as e:
            await interaction.response.send_message(f"Błąd przy wykonywaniu akcji", ephemeral=True)
            logger = logging.getLogger("default")
            logger.error(f"in callback of NotificationButton in [{interaction.guild.name} - {interaction.guild.id}] "
                         f"in [{interaction.channel.name} - {interaction.channel.id}]: {e}", exc_info=True)


class NotificationButtonsView(discord.ui.View):
    def __init__(self, bot: Bot, actions: list[Callable]):
        super().__init__(timeout=None)
        self.add_item(
            NotificationButton(label="Dodaj/Edytuj", style=discord.ButtonStyle.primary, bot=bot, action=actions[0]))
        self.add_item(NotificationButton(label="Pokaż wszystkie", style=discord.ButtonStyle.secondary, bot=bot,
                                         action=actions[1]))
        self.add_item(NotificationButton(label="Usuń", style=discord.ButtonStyle.danger, bot=bot, action=actions[2]))


class UpdateMessageView(discord.ui.View):
    role: int

    def __init__(self, role: int):
        super().__init__(timeout=None)
        self.role = role

    @discord.ui.button(label="Pokaż ostatnie zmiany", style=discord.ButtonStyle.primary, custom_id="show_messages")
    async def show_messages(self, interaction: discord.Interaction, _):
        calendar = Calendar()
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
        messages = fetch_messages_for_calendar(calendar.id)
        if not messages:
            await interaction.response.send_message("Brak zmian do pokazania", ephemeral=True)
        else:
            result = "### Ostatnie zmiany w kalendarzu:\n"
            for message in messages:
                result += f"- {message.message}\n"
            await interaction.response.send_message(result, ephemeral=True)

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
                    "Teraz będziesz otrzymywał powiadomienia o aktualizacjach tego kalendarza.\n"
                    "Aby zrezygnować kliknij ponownie.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(
                "**Bot nie posiada uprawnień do zmieniania ról**\n"
                "Aby je dodać trzeba przejść do `Ustawienia serwera > Role`, "
                "wybrać rolę kalendarza i w uprawnieniach włączyć `Zarządzanie powiadomieniami`",
                ephemeral=True)
