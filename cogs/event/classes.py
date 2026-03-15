import copy

from cogs.event.util import *
from g.classes import format_event_entries


class DeleteEventsModal(discord.ui.Modal):
    def __init__(self, events: list[Event]):
        super().__init__(title="Usuń wydarzenia")

        options = format_event_entries(events)
        self.event_select = discord.ui.Select(options=options, max_values=len(options), required=True)
        self.add_item(discord.ui.Label(text="Wybierz wydarzenia do usunięcia", component=self.event_select))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        calendar = Calendar()
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
        events = fetch_events_by_calendar(calendar.id)

        events_to_delete = [events[int(i)] for i in self.event_select.values]
        for event in events_to_delete:
            create_event_delete_message(event)
            event.delete()

        await update_calendar(interaction, calendar)
        print(f"[INFO]\tDeleted events {events_to_delete}")

        if len(self.event_select.values) > 1:
            await interaction.response.send_message(f'Wydarzenia zostały usunięte', ephemeral=True)
        else:
            await interaction.response.send_message(f'Wydarzenie zostało usunięte', ephemeral=True)


class EventEditLabel(discord.ui.Label):
    def __init__(self, text: str, required: bool, default: str, placeholder: str):
        super().__init__(text=text,
                         component=discord.ui.TextInput(required=required, default=default, placeholder=placeholder))


class EventEditModal(discord.ui.Modal):
    event: Event

    def __init__(self, event: Event):
        """
        Event has to have a calendarId set.
        """
        self.event = event
        if event.id is None:
            title = "Dodaj wydarzenie"
        else:
            title = "Edytuj wydarzenie"
        super().__init__(title=title)

        print(event)
        self.name_input = discord.ui.TextInput(default=event.name, placeholder="Podaj nazwę wydarzenia")
        self.add_item(discord.ui.Label(text="Nazwa", component=self.name_input))

        if event.id is None:
            time = date = ""
        else:
            time, date = event.timestamp_to_text()
        self.date_input = discord.ui.TextInput(default=date,
                                               placeholder="Podaj datę (np. 1.12.2025 lub 6.02 [doda obecny rok])")
        self.add_item(discord.ui.Label(text="Data", component=self.date_input))

        self.time_input = discord.ui.TextInput(default=time, placeholder="Podaj godzinę (np. 12:35)", required=False)
        self.add_item(discord.ui.Label(text="Godzina", component=self.time_input))

        self.team_input = discord.ui.TextInput(default=event.team, placeholder="Podaj grupę (np. 1, 3B)",
                                               required=False)
        self.add_item(discord.ui.Label(text="Grupa", component=self.team_input))

        self.place_input = discord.ui.TextInput(default=event.place, placeholder="Podaj miejsce wydarzenia",
                                                required=False)
        self.add_item(discord.ui.Label(text="Miejsce", component=self.place_input))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        old_event = copy.deepcopy(self.event)
        print(old_event)
        self.event.name = self.name_input.value
        self.event.text_to_timestamp(self.time_input.value, self.date_input.value)
        self.event.team = self.team_input.value
        self.event.place = self.place_input.value
        print(self.event)

        if self.event.id is None:
            # Adding new event
            print(f"[INFO]\tAdding new event [Name = {self.name_input.value}, Date = {self.date_input.value}, "
                  f"Time = {self.time_input.value}, Group = {self.team_input.value}, Place = {self.place_input.value}]")

            self.event.insert()
            create_event_update_message(self.event)
            print("[INFO]\tAdded this event")
            await interaction.response.send_message(
                f'Dodano wydarzenie *{self.event.name}* do kalendarza.\n'
                f'Wydarzenia będą automatycznie usuwane po upłynięciu 3 tygodni od dnia wydarzenia',
                ephemeral=True)
        else:
            # Event exists already
            print(
                f"[INFO]\tEditing event [DB ID {self.event.id}] with values [Name = {self.name_input.value}, Date = {self.date_input.value}, "
                f"Time = {self.time_input.value}, Group = {self.team_input.value}, Place = {self.place_input.value}]")
            self.event.update()
            create_event_update_message(self.event, old_event)
            print("[INFO]\tEdited this event")
            await interaction.response.send_message(f'Wydarzenie *{self.event.name}* zostało zmienione',
                                                    ephemeral=True)

        calendar = Calendar()
        calendar.fetch(self.event.calendarId)
        await update_calendar(interaction, calendar)


async def send_event_edit_modal(interaction: discord.Interaction, events: list[Event], values: list[str]):
    await interaction.response.send_modal(EventEditModal(events[int(values[0])]))
