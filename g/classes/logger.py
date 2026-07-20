import logging
import os
from enum import Enum


class LogType(Enum):  # when adding something that will need a new folder, add it to init_logger()
    ALL = ""
    CALENDAR = "calendar"
    USER = "user"
    NOTIFICATION = "notification"


def init_logger():
    if not os.path.exists('logs/calendar'):
        os.makedirs('logs/calendar')
    if not os.path.exists('logs/user'):
        os.makedirs('logs/user')


def get_logger(log_type: LogType = LogType.ALL, id: int | None = None) -> logging.Logger:
    match log_type:
        case LogType.CALENDAR | LogType.USER:
            logger_name = f"{log_type.value}_{id if id else "default"}"
        case LogType.NOTIFICATION:
            logger_name = log_type.value
        case LogType.ALL | _:
            logger_name = "default"

    folder = "" if log_type in (LogType.ALL, LogType.NOTIFICATION) else f"{log_type.value}/"

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setStream(logging.FileHandler(f"logs/{folder}{logger_name}.log").stream)
        stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(stream_handler)

    return logger
