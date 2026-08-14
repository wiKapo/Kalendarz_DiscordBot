from datetime import datetime


def is_today(check: datetime) -> bool:
    now = datetime.now()
    return check.day == now.day and check.month == now.month and check.year == now.year


def is_tomorrow(check: datetime) -> bool:
    now = datetime.now()
    return check.day == now.day + 1 and check.month == now.month and check.year == now.year


def is_this_week(check: datetime) -> bool:
    now = datetime.now()
    return check.isocalendar().week == now.isocalendar().week and check.year == now.year


def is_next_week(check: datetime) -> bool:
    now = datetime.now()
    return check.isocalendar().week == now.isocalendar().week + 1 and check.year == now.year


def is_this_month(check: datetime) -> bool:
    now = datetime.now()
    return check.month == now.month and check.year == now.year


def is_next_month(check: datetime) -> bool:
    now = datetime.now()
    return check.month == now.month + 1 and check.year == now.year
