from datetime import datetime


def is_today(check: datetime) -> bool:
    now = datetime.now()
    return check.day == now.day and check.month == now.month and check.year == now.year


def is_tomorrow(check: datetime) -> bool:
    now = datetime.now()
    return check.day == now.day + 1 and check.month == now.month and check.year == now.year


def is_this_week(check: datetime) -> bool:
    now = datetime.now()
    return check.isocalendar()[1] == now.isocalendar()[1] and check.year == now.year


def is_next_week(check: datetime) -> bool:
    now = datetime.now()
    return check.isocalendar()[1] + 1 == now.isocalendar()[1] and check.year == now.year


def is_this_month(check: datetime) -> bool:
    now = datetime.now()
    return check.month == now.month and check.year == now.year


def is_next_month(check: datetime) -> bool:
    now = datetime.now()
    return check.month + 1 == now.month and check.year == now.year
