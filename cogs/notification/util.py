import re
from datetime import datetime, timedelta


def hour_rounder(t: datetime) -> datetime:
    # Rounds to the nearest hour by adding a timedelta hour if minute >= 30
    return t.replace(second=0, microsecond=0, minute=0, hour=t.hour) + timedelta(hours=t.minute // 30)


def get_time_from_tag(time_tag: str) -> int:
    times = re.findall(r"\d+\w?", time_tag)
    result = 0

    for t in times:
        if t[-1] == "d":
            result += int(t[:-1]) * 24
        elif t[-1] == "w":
            result += int(t[:-1]) * 168
        elif t[-1] == "h":
            result += int(t[:-1])
        else:
            result += int(t)

    return result
