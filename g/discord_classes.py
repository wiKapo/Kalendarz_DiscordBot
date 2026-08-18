from collections.abc import Callable

import discord
from discord import SelectOption

from g.classes.calendar import Calendar, DEFAULT_TITLE
from g.classes.event import Event
from g.classes.logger import get_logger, LogType
from g.classes.message import fetch_messages_for_calendar
from g.classes.section import Section


def truncate_text(text: str, max_length: int) -> str:
    return text[:max_length - 3] + "..." if len(text) > max_length else text


class UniversalSelect(discord.ui.Select):
    action: Callable | None

    def __init__(self, options: list[SelectOption], placeholder: str, action: Callable | None = None,
                 max_values: int = 1):
        super().__init__(placeholder=placeholder, options=options, max_values=max_values)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        if self.action:
            try:
                await self.action(interaction, self.values)
            except Exception as e:
                await interaction.response.send_message(f"Błąd przy wykonywaniu akcji", ephemeral=True)
                logger = get_logger(LogType.USER, interaction.user.name)
                logger.error(f"In callback of {self.placeholder} in [{interaction.guild.name} - {interaction.guild_id}] "
                             f"in [{interaction.channel.name} - {interaction.channel_id}]: {e}", exc_info=True)


class UniversalSelectView(discord.ui.View):
    def __init__(self, options: list[SelectOption], placeholder: str, action: Callable,
                 max_values: int = 1):
        super().__init__()
        amount = len(options)
        for start in range(0, amount, 25):
            self.add_item(UniversalSelect(options[start:start + 25], placeholder, action, max_values))


class UniversalButton(discord.ui.Button):
    def __init__(self, label: str, style: discord.ButtonStyle, action: Callable):
        self.action = action
        super().__init__(label=label, style=style)

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.action(interaction)
        except Exception as e:
            await interaction.response.send_message(f"Błąd przy wykonywaniu akcji", ephemeral=True)
            logger = get_logger(LogType.USER, interaction.user.name)
            logger.error(
                f"in callback of {self.label} in [{interaction.guild.name} - {interaction.guild.id}] "
                f"in [{interaction.channel.name} - {interaction.channel.id}]: {e}", exc_info=True)


async def show_messages(interaction: discord.Interaction):
    calendar = Calendar()
    calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
    messages = fetch_messages_for_calendar(calendar.id)
    if not messages:
        await interaction.response.send_message("Brak zmian do pokazania", ephemeral=True)
    else:
        result = "## Ostatnie zmiany w kalendarzu:\n"
        for message in messages:
            result += "- " + str(message) + "\n"
        await interaction.response.send_message(result, ephemeral=True)


class UpdateMessageView(discord.ui.View):
    role: int

    def __init__(self, role: int | None):
        super().__init__(timeout=None)
        self.role: int | None = role

        self.add_item(UniversalButton(label="Pokaż ostatnie zmiany", style=discord.ButtonStyle.primary,
                                      action=show_messages))
        if self.role:
            self.add_item(UniversalButton(label="Otrzymuj powiadomienia o aktualizacji kalendarza",
                                          style=discord.ButtonStyle.secondary,
                                          action=self.get_ping_role))

    async def get_ping_role(self, interaction: discord.Interaction):
        role: discord.role.Role = interaction.guild.get_role(self.role)
        logger = get_logger(LogType.USER, interaction.user.name)
        try:
            if role in interaction.user.roles:
                logger.info(f"{interaction.user.name} unsubscribed from calendar updates")
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(
                    "Nie będziesz już otrzymywał powiadomień o aktualizacjach tego kalendarza", ephemeral=True)
            else:
                logger.info(f"{interaction.user.name} subscribed to calendar updates")
                await interaction.user.add_roles(role)
                await interaction.response.send_message(
                    "Teraz będziesz otrzymywał powiadomienia o dodaniu, edycji lub usunięciu wydarzeń z tego kalendarza\n"
                    "Aby zrezygnować kliknij ponownie.", ephemeral=True)
        except discord.Forbidden:
            logger.error(f"Bot can't add roles to user {interaction.user.name}")
            await interaction.response.send_message(
                "**Bot nie posiada uprawnień do zmieniania ról**\n"
                "Aby je dodać trzeba przejść do `Ustawienia serwera > Role`, "
                "wybrać rolę kalendarza i w uprawnieniach włączyć `Zarządzanie rolami`",
                ephemeral=True)


def format_section_options(sections: list[Section]) -> list[SelectOption]:
    options = []
    for section in sections:
        options.append(SelectOption(
            label=section.name,
            description=f"Zaczyna się {section.begin_date}"
                        f"{f', a kończy {section.end_date}' if section.end_date else ''}",
            value=f"{section.calendarId}.{section.beginTimestamp}"
        ))
    return options


def format_calendar_options(calendars: list[Calendar], selected_calendars: set[int] | None = None) \
        -> list[SelectOption]:
    options = []
    for calendar in calendars:
        event_amount = len(calendar.eventIds)
        if event_amount:
            amount_text = f"{event_amount} wydarze"
            if event_amount == 1:
                amount_text += "nie"
            elif event_amount < 5:
                amount_text += "nia"
            else:
                amount_text += "ń"
        else:
            amount_text = "Brak wydarzeń"
        label_text = f"[{calendar.id}] {calendar.title if calendar.title else DEFAULT_TITLE}"
        options.append(SelectOption(
            label=truncate_text(label_text, 100),
            description=f"{calendar.channelName} ({amount_text})",
            value=f"{calendar.id}",
            default=bool(selected_calendars and calendar.id in selected_calendars)
        ))
    return options


def format_event_options(events: list[Event], selected_event: int | None = None) -> list[SelectOption]:
    options = []
    for event in events:
        description = ""
        if event.team:
            description += f'[{event.team}] '
        if event.place:
            description += f"{event.place} "

        if len(description) < 40:
            description += f"w kalendarz{'u' if len(event.calendarIds) == 1 else 'ach'} "
        else:
            description += "w"
        description += f"#{", #".join(set(map(str, event.calendarIds)))}"

        label_text = f"{event.date}{f' {event.time}' if event.time else ''} {event.name}"
        options.append(
            SelectOption(
                label=truncate_text(label_text, 100),
                description=truncate_text(description, 100),
                value=f"{event.id}",
                default=event.id == selected_event
            )
        )

    return options
