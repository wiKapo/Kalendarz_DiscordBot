from cogs.calendar.util import update_calendar
from cogs.event.util import *


class DeleteEventsModal(discord.ui.Modal):
    def __init__(self, events: list[Event]):
        options = format_event_entries(events)
        super().__init__(title="Usuń wydarzenia")

        self.add_item(discord.ui.Label(
            text="Wybierz wydarzenia do usunięcia",
            component=discord.ui.Select(options=options, max_values=len(options), required=True)))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        event_ids = []
        for child in self.walk_children():
            if type(child) is discord.ui.Select:
                event_ids = sorted(list(map(int, child.values)))

        print(f"[INFO]\t{event_ids}")

        calendar = Calendar()
        calendar.fetch_by_channel(interaction.guild_id, interaction.channel_id)
        events = fetch_events_by_calendar(calendar.id)

        events_to_delete = [events[i] for i in event_ids]
        for event in events_to_delete:
            event.delete()

        await update_calendar(interaction, calendar)
        print(f"[INFO]\tDeleted events {events_to_delete}")

        if len(event_ids) > 1:
            await interaction.response.send_message(f'Wydrzenia zostały usunięte', ephemeral=True)
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

        print(f"Event [DB ID]: {event}")

        self.add_item(EventEditLabel("Nazwa", True, event.name, "Podaj nazwę wydarzenia"))
        if event.id is None:
            time = date = ""
        else:
            time, date = timestamp_to_text(int(event.timestamp), bool(int(event.wholeDay)))
        self.add_item(EventEditLabel("Data", True, date, "Podaj datę (np. 1.12.2025 lub 6.02 [doda obecny rok])"))
        self.add_item(EventEditLabel("Godzina", False, time, "Podaj godzinę (np. 12:35)"))
        self.add_item(EventEditLabel("Grupa", False, event.team, "Podaj grupę (np. 1, 3B)"))
        self.add_item(EventEditLabel("Miejsce", False, event.place, "Podaj miejsce wydarzenia"))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            data = []
            for child in self.walk_children():
                if type(child) is discord.ui.TextInput:
                    data.append(str(child))

            if self.event.id is None:  # Adding new event
                print(f"[INFO]\tAdding new event [Name = {data[0]}, Date = {data[1]}, Time = {data[2]}, "
                      f"Group = {data[3]}, Place = {data[4]}]")

                self.event.set_and_insert(data)
                create_event_update_message(self.event)
                print("[INFO]\tAdded this event")
                await interaction.response.send_message(
                    f'Dodano wydarzenie *{self.event.name}* do kalendarza.\n'
                    f'Wydarzenia będą automatycznie usuwane po upłynięciu 3 tygodni od dnia wydarzenia',
                    ephemeral=True)
            else:  # Event exists already
                print(
                    f"[INFO]\tEditing event [DB ID {self.event.id}] with values [Name = {data[0]}, Date = {data[1]}, "
                    f"Time = {data[2]}, Group = {data[3]}, Place = {data[4]}]")
                old_event = self.event
                self.event.set_and_update(data)
                create_event_update_message(self.event, old_event)
                print("[INFO]\tEdited this event")
                await interaction.response.send_message(f'Wydarzenie *{self.event.name}* zostało zmienione',
                                                        ephemeral=True)

            calendar = Calendar()
            calendar.fetch(self.event.calendarId)
            await update_calendar(interaction, calendar)

        except Exception as e:
            print(e)
            return


async def send_event_edit_modal(interaction: discord.Interaction, events: list[Event], values: list[str]):
    await interaction.response.send_modal(EventEditModal(events[int(values[0])]))
