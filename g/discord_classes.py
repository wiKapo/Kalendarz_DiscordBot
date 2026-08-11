import logging
from collections.abc import Callable

import discord
from discord import SelectOption
from discord.ext.commands import Bot

from g.classes.calendar import Calendar, DEFAULT_TITLE
from g.classes.event import Event
from g.classes.message import fetch_messages_for_calendar
from g.classes.section import Section


def truncate_text(text: str, max_length: int) -> str:
    return text[:max_length - 3] + "..." if len(text) > max_length else text


# TODO merge all SelectViews into one function

class SelectEvent(discord.ui.Select):
    action: Callable
    events: list[Event]

    def __init__(self, events: list[Event], placeholder: str, action: Callable, max_values: int = 1):
        options = format_event_options(events)
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


class SelectCalendar(discord.ui.Select):
    action: Callable

    def __init__(self, placeholder: str, action: Callable, calendars: list[Calendar]):
        options = format_calendar_options(calendars)
        super().__init__(placeholder=placeholder, options=options)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.action(interaction, self.values)
        except Exception as e:
            logger = logging.getLogger("default")
            logger.error(f"in callback of SelectCalendar {e}", exc_info=True)


class SelectCalendarView(discord.ui.View):
    def __init__(self, calendars: list[Calendar], action: Callable):
        super().__init__()
        self.add_item(SelectCalendar(placeholder="Wybierz kalendarz", action=action, calendars=calendars))


class SelectSection(discord.ui.Select):
    action: Callable

    def __init__(self, placeholder: str, action: Callable | None, sections: list[Section], max_values: int = 1):
        options = format_section_options(sections)
        super().__init__(placeholder=placeholder, options=options, max_values=max_values)
        self.action: Callable | None = action

    async def callback(self, interaction: discord.Interaction):
        if self.action:
            try:
                await self.action(interaction, self.values)
            except Exception as e:
                logger = logging.getLogger("default")
                logger.error(f"in callback of SelectSection {e}", exc_info=True)


class SelectSectionView(discord.ui.View):
    def __init__(self, sections: list[Section], action: Callable):
        super().__init__()
        self.add_item(SelectSection(placeholder="Wybierz sekcję", action=action, sections=sections))


class CalendarDescriptionButton(discord.ui.Button):
    def __init__(self, label: str, style: discord.ButtonStyle, action: Callable):
        self.action = action
        super().__init__(label=label, style=style)

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.action(interaction)
        except Exception as e:
            await interaction.response.send_message(f"Błąd przy wykonywaniu akcji", ephemeral=True)
            logger = logging.getLogger("default")
            logger.error(
                f"in callback of CalendarDescriptionButton in [{interaction.guild.name} - {interaction.guild.id}] "
                f"in [{interaction.channel.name} - {interaction.channel.id}]: {e}", exc_info=True)


class UpdateMessageView(discord.ui.View):
    role: int

    def __init__(self, role: int | None):
        super().__init__(timeout=None)
        self.role: int | None = role

        self.add_item(CalendarDescriptionButton(label="Pokaż ostatnie zmiany", style=discord.ButtonStyle.primary,
                                                action=self.show_messages))

        if self.role:
            self.add_item(CalendarDescriptionButton(label="Otrzymuj powiadomienia o aktualizacji kalendarza",
                                                    style=discord.ButtonStyle.secondary,
                                                    action=self.get_ping_role))

    async def show_messages(self, interaction: discord.Interaction):
        calendar = Calendar()
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
        messages = fetch_messages_for_calendar(calendar.id)
        if not messages:
            await interaction.response.send_message("Brak zmian do pokazania", ephemeral=True)
        else:
            result = "## Ostatnie zmiany w kalendarzu:\n"
            for message in messages:
                result += str(message) + "\n"
            await interaction.response.send_message(result, ephemeral=True)

    async def get_ping_role(self, interaction: discord.Interaction):
        role: discord.role.Role = interaction.guild.get_role(self.role)
        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(
                    "Nie będziesz już otrzymywał powiadomień o aktualizacjach tego kalendarza", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(
                    "Teraz będziesz otrzymywał powiadomienia o dodaniu, edycji lub usunięciu wydarzeń z tego kalendarza\n"
                    "Aby zrezygnować kliknij ponownie.", ephemeral=True)
        except discord.Forbidden:
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
        options.append(SelectOption(
            label=f"[{calendar.id}] {calendar.title if calendar.title else DEFAULT_TITLE}",
            description=f"{calendar.channelName}",
            value=f"{calendar.id}",
            default=True if len(calendars) == 1 or (
                    selected_calendars and calendar.id in selected_calendars) else False
        ))
    return options


def format_event_options(events: list[Event], selected_event: int | None = None) -> list[SelectOption]:
    options = []
    for i, event in enumerate(events):
        description = ""
        if event.team:
            description += f'[{event.team}] '
        if event.place:
            description += event.place

        label_text = f"{event.date}{f' {event.time}' if event.time else ''} {event.name}"
        options.append(
            SelectOption(
                label=truncate_text(label_text, 100),
                description=description,
                value=f"{i}",
                default=i == selected_event
            )
        )

    return options
