import discord
from discord.ext import commands
import json
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix='/', intents=intents)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    try:
        synced_commands = await bot.tree.sync()
        print(f"Synced {len(synced_commands)} commands")
    except Exception as e:
        print("Error with syncing bot commands: ", e)


class CreateCalendarModal(discord.ui.Modal, title="Dodaj wydarzenie"):
    # TODO check for date format and time format optionally
    date = discord.ui.TextInput(label="Data", style=discord.TextStyle.short,
                                placeholder="Podaj datę (na przykład 01.12.2025)")
    time = discord.ui.TextInput(label="Godzina", style=discord.TextStyle.short, placeholder="Podaj godzinę",
                                required=False)
    name = discord.ui.TextInput(label="Nazwa", style=discord.TextStyle.long, placeholder="Podaj nazwę wydarzenia")
    group = discord.ui.TextInput(label="Grupa", style=discord.TextStyle.short, placeholder="Podaj grupę (np. 1, 3B)",
                                 required=False)
    place = discord.ui.TextInput(label="Miejsce", style=discord.TextStyle.short, placeholder="Podaj miejsce wydarzenia",
                                 required=False)

    async def on_submit(self, interaction: discord.Interaction) -> None:

        if self.time.value:
            dt = datetime.strptime(f"{self.date.value} {self.time.value}", "%d.%m.%Y %H:%M")
        else:
            dt = datetime.strptime(self.date.value, "%d.%m.%Y")
        timestamp = int(dt.timestamp())

        new_event = {"timestamp": str(timestamp)}
        if self.time.value:
            new_event.update({"whole_day": "False"})
        else:
            new_event.update({"whole_day": "True"})
        new_event.update({"name": self.name.value})
        if self.group.value:
            new_event.update({"group": self.group.value})
        if self.place.value:
            new_event.update({"place": self.place.value})

        try:
            with open("events.json", "x") as f:
                f.write(json.dumps([]))
        except FileExistsError:
            pass

        # Error if events.json file exists and there is nothing inside. To resolve the problem delete the file.
        with open("events.json", "r+") as f:
            events = json.load(f)
            events.append(new_event)
            f.seek(0)
            json.dump(events, f, indent=4)

        await interaction.response.send_message(f'Dodano wydarzenie *{self.name}* do kalendarza', ephemeral=True)


@bot.tree.command(name="create", description="Tworzy nowy kalendarz")
async def create(interaction: discord.Interaction):
    calendar_msg = await interaction.response.send_message(':calendar:\tKalendarz PG 2025\t:calendar:\n\t\t\t\t\tPUSTE')
    with open('calendar.txt', 'w') as f:
        f.write(f'{str(calendar_msg.message_id)} {str(interaction.channel.id)}')


@bot.tree.command(name="add", description="Dodaje nowe wydarzenie")
async def add(interaction: discord.Interaction):
    modal = CreateCalendarModal()
    await interaction.response.send_modal(modal)


@bot.tree.command(name="update", description="Zaktualizuj kalendarz")
async def update(interaction: discord.Interaction):
    # DATA (godzina) ([grupa]) - NAZWA (miejsce)
    try:
        with open("calendar.txt", "r") as f:
            data = f.read()
            calendar_message_id = data.split(' ')[0]
            calendar_channel_id = data.split(' ')[1]
    except FileNotFoundError:
        print("HI")
        # await interaction.response.send_message('Kalendarz nie istnieje', ephemeral=True)
        return

    print(calendar_message_id)
    calendar_message = await (await interaction.guild.fetch_channel(calendar_channel_id)).fetch_message(
        calendar_message_id)

    try:
        with open("events.json", "r") as f:
            events = json.load(f)
            message = "\n"
            for event in events:
                message += "<t:" + str(event.get('timestamp')) + ">** "
                if event.get('group'):
                    message += "**[" + event.get('group') + "]** "
                message += event.get('name')
                if event.get('place'):
                    message += " -> " + event.get('place')
                message += " **\n"
    except FileNotFoundError:
        message = "\n\t\t\t\t\tPUSTE"

    await calendar_message.edit(content=f'{calendar_message.content.split('\n')[0]}{message}')

    await interaction.response.send_message('Kalendarz został zaktualizowany', ephemeral=True)


@bot.tree.command(name="delete", description="Usuwa wydarzenie")
async def delete(interaction: discord.Interaction):
    pass


@bot.tree.command(name="edit", description="Zmienia istniejące wydarzenie")
async def edit(interaction: discord.Interaction):
    pass

    # await calendar_msg.edit(content=f'{calendar_msg.content}\nHELLO there :)')


bot.run()
