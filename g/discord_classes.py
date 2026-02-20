from collections.abc import Callable

import discord

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
