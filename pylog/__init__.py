from .manager import LogManager
from .core.context import ThreadContext
from .core.marker import Marker
from .core.logger import Logger

def get_logger(name: str) -> Logger:
    return LogManager.get_logger(name)

__version__ = "2.2.1"
__all__ = ["LogManager", "ThreadContext", "Marker", "get_logger", "Logger"]
