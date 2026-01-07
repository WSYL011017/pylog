import time
import logging
import datetime
import re
from typing import Optional, Dict
from .base import Formatter
from pylog.core.log_event import LogEvent

class PatternFormatter(Formatter):
    """
    Formats log events using a pattern string.
    Supports Log4j2 style patterns (subset).
    """
    
    def __init__(self, pattern: str = "%d [%t] %p %c - %m%n"):
        self.pattern = pattern
        
    def format(self, event: LogEvent) -> str:
        msg = event.get_message()
        if event.exc_info:
            import traceback
            exc_text = "".join(traceback.format_exception(*event.exc_info))
            msg = f"{msg}\n{exc_text}"
            
        dt = datetime.datetime.fromtimestamp(event.timestamp)
        
        # Helper for date formatting
        def replace_date(match):
            fmt = match.group(1)
            # Convert Java/Log4j format to Python strftime
            # Simplified mapping
            py_fmt = (fmt.replace("yyyy", "%Y")
                         .replace("MM", "%m")
                         .replace("dd", "%d")
                         .replace("HH", "%H")
                         .replace("mm", "%M")
                         .replace("ss", "%S")
                         .replace("SSS", "%f"))
            return dt.strftime(py_fmt)

        output = self.pattern
        
        # 1. Handle %d{...}
        output = re.sub(r"%d\{([^}]+)\}", replace_date, output)
        
        # 2. Handle Modifiers (specific first)
        # %-5level -> %p
        output = re.sub(r"%[-]?\d+level", "%p", output)
        output = re.sub(r"%[-]?\d+p", "%p", output)
        output = re.sub(r"%[-]?\d+logger", "%c", output)
        output = re.sub(r"%[-]?\d+c", "%c", output)
        
        # 3. Handle parameterized (strip args)
        # %c{36} -> %c
        output = re.sub(r"%c\{\d+\}", "%c", output)
        output = re.sub(r"%logger\{\d+\}", "%c", output)
        
        # 4. Handle aliases
        output = output.replace("%msg", "%m")
        output = output.replace("%level", "%p")
        output = output.replace("%logger", "%c")
        
        # 5. Standard replacements
        if "%d" in output:
             output = output.replace("%d", dt.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3])
             
        output = output.replace("%t", event.thread_name or "Unknown")
        output = output.replace("%p", logging.getLevelName(event.level))
        output = output.replace("%c", event.logger_name)
        output = output.replace("%m", msg)
        output = output.replace("%n", "\n")
        output = output.replace("%F", event.file_name or "?")
        output = output.replace("%L", str(event.line_number or "?"))
        output = output.replace("%M", event.func_name or "?")
        
        return output
