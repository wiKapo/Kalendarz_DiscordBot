from datetime import datetime, timedelta


def is_today(check: datetime) -> bool:
    return check.date() == datetime.now()


def is_tomorrow(check: datetime) -> bool:
    return check.date() == datetime.now().date() + timedelta(days=1)


def is_this_week(check: datetime) -> bool:
    now = datetime.now().isocalendar()
    check = check.isocalendar()
    return check.week == now.week and check.year == now.year


def is_next_week(check: datetime) -> bool:
    now = datetime.now().isocalendar()
    check = check.isocalendar()
    return check.week == now.week + 1 and check.year == now.year


def is_this_month(check: datetime) -> bool:
    now = datetime.now()
    return check.month == now.month and check.year == now.year


def is_next_month(check: datetime) -> bool:
    now = datetime.now()
    return check.month == now.month + 1 and check.year == now.year
