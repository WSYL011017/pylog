import orjson
import traceback
from typing import Union, List, Set
from pylog.core.log_event import LogEvent
from .base import Formatter

class JSONFormatter(Formatter):
    """
    Formats LogEvents as JSON using orjson.
    Supports sensitive data masking.
    """
    def __init__(self, compact: bool = True, event_eol: bool = True, masked_keys: List[str] = None):
        self.compact = compact
        self.event_eol = event_eol
        self.masked_keys: Set[str] = set(masked_keys) if masked_keys else set()
        
    def format(self, event: LogEvent) -> bytes:
        # Get base dict
        data = event.to_dict()
        
        # Mask sensitive data
        if self.masked_keys:
            self._mask_data(data)
        
        # Handle exceptions
        if event.exc_info:
            exc_type, exc_value, exc_tb = event.exc_info
            if exc_value:
                 data['exception'] = {
                     'type': exc_type.__name__ if exc_type else "Unknown",
                     'message': str(exc_value),
                     'stacktrace': "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
                 }

        option = 0
        if not self.compact:
            option |= orjson.OPT_INDENT_2
            
        # Serialize
        try:
            json_bytes = orjson.dumps(data, option=option)
        except TypeError:
            # Fallback for non-serializable objects in extra/args
            # We could do a default=str but let's try to be safe
            json_bytes = orjson.dumps(data, default=str, option=option)
        
        if self.event_eol:
            json_bytes += b'\n'
            
        return json_bytes

    def _mask_data(self, data: dict):
        """Recursively mask sensitive keys."""
        for key, value in data.items():
            if key in self.masked_keys:
                data[key] = "***"
            elif isinstance(value, dict):
                self._mask_data(value)
            # Note: We assume lists of dicts might exist, but deep recursion on list is expensive.
            # Only recurse on dicts for now.
