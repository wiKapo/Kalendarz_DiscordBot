from g.util import *

def create_event_update_message(new_event: Event, old_event: Event | None = None):
    message = Message()
    message.set_time()
    message.calendarId = new_event.calendarId
    if old_event:
        message.message = compare_event_changes(new_event, old_event)
    else:
        message.message = f"Utworzono nowe wydarzenie: {new_event}"
    message.insert()


def compare_event_changes(new_event: Event, old_event: Event) -> str | None:
    if new_event == old_event:
        return None
    message = f"Zmiany w wydarzeniu **{old_event.name}**: "

    if new_event.name != old_event.name:
        message += f"| *Nazwa*: `{old_event.name}` -> `{new_event.name}` "

    if new_event.timestamp != old_event.timestamp:
        new_time, new_date = new_event.timestamp_to_text()
        old_time, old_date = old_event.timestamp_to_text()
        if new_time != old_time:
            message += f"| *Godzina*: `{old_time if old_time else "-"}` -> `{new_time if new_time else "-"}` "
        if new_date != old_date:
            message += f"| *Data*: `{old_date}` -> `{new_date}` "

    if new_event.team != old_event.team:
        message += f"| *Grupa*: `{old_event.team if old_event.team else "-"}` -> `{new_event.team if new_event.team else "-"}` "

    if new_event.place != old_event.place:
        message += f"| *Miejsce*: `{old_event.place if old_event.place else "-"}` -> `{new_event.place if new_event.place else "-"}` "

    message += "|"

    return message


def create_event_delete_message(event: Event):
    message = Message()
    message.set_time()
    message.calendarId = event.calendarId
    message.message = f"Usunięto wydarzenie: {event}"
    message.insert()
