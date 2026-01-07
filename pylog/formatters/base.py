from abc import ABC, abstractmethod
from typing import Union
from pylog.core.log_event import LogEvent

class Formatter(ABC):
    @abstractmethod
    def format(self, event: LogEvent) -> Union[str, bytes]:
        pass
