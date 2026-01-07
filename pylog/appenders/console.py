import sys
from typing import Literal
from .base import Appender
from pylog.formatters.base import Formatter
from pylog.core.log_event import LogEvent

class ConsoleAppender(Appender):
    """
    Appender that writes to System.out or System.err
    """
    def __init__(self, name: str, formatter: Formatter, target: Literal["SYSTEM_OUT", "SYSTEM_ERR"] = "SYSTEM_OUT"):
        super().__init__(name, formatter)
        self.target = target
        self._stream = sys.stdout if target == "SYSTEM_OUT" else sys.stderr

    def append(self, event: LogEvent):
        # We don't strictly enforce started check for Console to allow early logging, 
        # but typically it should be checked.
        
        output = self.formatter.format(event)
        
        try:
            if isinstance(output, bytes):
                # Write bytes to buffer
                if hasattr(self._stream, 'buffer'):
                    self._stream.buffer.write(output)
                    self._stream.buffer.flush()
                else:
                    # Fallback if buffer not available (e.g. captured stream)
                    self._stream.write(output.decode('utf-8', errors='replace'))
                    self._stream.flush()
            else:
                self._stream.write(output)
                self._stream.flush()
        except Exception:
            # Emergency fallback
            pass
