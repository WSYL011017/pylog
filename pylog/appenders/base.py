from abc import ABC, abstractmethod
from typing import Optional
from pylog.core.log_event import LogEvent
from pylog.formatters.base import Formatter

class Appender(ABC):
    """
    Base class for Appenders.
    """
    def __init__(self, name: str, formatter: Formatter):
        self.name = name
        self.formatter = formatter
        self.started = False

    def start(self):
        self.started = True

    def stop(self):
        self.started = False

    @abstractmethod
    def append(self, event: LogEvent):
        pass

    def flush(self):
        """
        Flushes any buffered content to the destination.
        """
        pass
