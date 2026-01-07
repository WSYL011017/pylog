import urllib.request
import urllib.error
import logging
from typing import Optional, Dict
from .base import Appender
from pylog.formatters.base import Formatter
from pylog.core.log_event import LogEvent

class HTTPAppender(Appender):
    """
    Appends logs to a HTTP/HTTPS endpoint via POST.
    """
    def __init__(self, name: str, url: str, method: str = 'POST', headers: Optional[Dict[str, str]] = None, formatter: Optional[Formatter] = None):
        super().__init__(name, formatter)
        self.url = url
        self.method = method.upper()
        self.headers = headers or {"Content-Type": "application/json"}
        
    def append(self, event: LogEvent):
        try:
            if self.formatter:
                data = self.formatter.format(event)
            else:
                data = str(event.get_message()).encode('utf-8')

            # Ensure data is bytes
            if isinstance(data, str):
                data = data.encode('utf-8')
                
            req = urllib.request.Request(self.url, data=data, method=self.method)
            
            for k, v in self.headers.items():
                req.add_header(k, v)
                
            with urllib.request.urlopen(req, timeout=5) as response:
                # We expect 2xx
                pass
                
        except Exception as e:
            # Prevent recursive logging if this logger logs its own errors
            # sys.stderr.write(f"HTTPAppender Error: {e}\n")
            pass
