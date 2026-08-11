import logging
import os
from enum import Enum


class LogType(Enum):  # when adding something that will need a new folder, add it to init_logger()
    DEFAULT = "default"
    CALENDAR = "calendar"
    USER = "user"
    EVENT = "event"


def init_logger():
    if not os.path.exists('logs/calendar'):
        os.makedirs('logs/calendar')
    if not os.path.exists('logs/user'):
        os.makedirs('logs/user')
    if not os.path.exists('logs/event'):
        os.makedirs('logs/event')


def get_logger(log_type: LogType = LogType.DEFAULT, data: str | None = None) -> logging.Logger:
    match log_type:
        case LogType.CALENDAR | LogType.USER | LogType.EVENT:
            logger_name = f"{log_type.value}_{data if data else "default"}"
        case LogType.DEFAULT | _:
            logger_name = "default"

    folder = "" if log_type is LogType.DEFAULT else f"{log_type.value}/"

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setStream(logging.FileHandler(f"logs/{folder}{logger_name}.log").stream)
        stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(stream_handler)

        error_handler = logging.StreamHandler()
        error_handler.setStream(logging.FileHandler(f"logs/error.log").stream)
        error_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        error_handler.addFilter(lambda record: record.levelno == logging.ERROR)
        logger.addHandler(error_handler)

    return logger
