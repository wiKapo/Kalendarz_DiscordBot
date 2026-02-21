from collections.abc import Callable

import discord
from discord.ext.commands import Bot

from g.classes import Event
from g.util import format_event_entries


class SelectEvent(discord.ui.Select):
    action: Callable
    events: list[Event]

    def __init__(self, events: list[Event], placeholder: str, action: Callable, max_values: int = 1):
        options = format_event_entries(events)
        super().__init__(placeholder=placeholder, options=options, max_values=max_values)
        self.action = action
        self.events = events

    async def callback(self, interaction: discord.Interaction):
        print(f"Recieved values from select: {self.values}")
        try:
            await self.action(interaction, self.events, self.values)
        except Exception as e:
            await interaction.response.send_message(f"Błąd przy wykonywaniu akcji", ephemeral=True)
            print(e)


class SelectEventView(discord.ui.View):
    def __init__(self, events: list[Event], placeholder: str, action: Callable, max_values: int = 1):
        super().__init__()
        self.add_item(SelectEvent(events, placeholder, action, max_values))
        print("[INFO]\tSent event selection form")


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
            print(e)


class NotificationButtonsView(discord.ui.View):
    def __init__(self, bot: Bot, actions: list[Callable]):
        super().__init__(timeout=None)
        self.add_item(NotificationButton(label="Dodaj/Edytuj", style=discord.ButtonStyle.primary, bot=bot, action=actions[0]))
        self.add_item(NotificationButton(label="Pokaż wszystkie", style=discord.ButtonStyle.secondary, bot=bot, action=actions[1]))
        self.add_item(NotificationButton(label="Usuń", style=discord.ButtonStyle.danger, bot=bot, action=actions[2]))
