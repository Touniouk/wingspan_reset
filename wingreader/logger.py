from enum import Enum
from PIL import Image
from colorama import Fore

class Level(Enum):
    INFIME = 0
    TRACE = 1
    DEBUG = 2
    INFO = 3
    WARN = 4
    ERROR = 5
    OFF = 6

LOGGING_LEVEL = Level.TRACE
SHOW_IMAGES = False

def infime(message): log(message, Level.INFIME, Fore.LIGHTRED_EX)
def trace(message): log(message, Level.TRACE, Fore.MAGENTA)
def debug(message): log(message, Level.TRACE, Fore.LIGHTMAGENTA_EX)
def info(message): log(message, Level.TRACE, Fore.CYAN)
def warn(message): log(message, Level.TRACE, Fore.YELLOW)
def error(message): log(message, Level.ERROR, Fore.RED)

def log(message, level: Level, color: Fore):
    if (LOGGING_LEVEL.value > level.value): return
    if isinstance(message, str):
        print(color + message)
    # if isinstance(message, Image):
    elif SHOW_IMAGES:
        message.show()