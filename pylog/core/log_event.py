import time
import logging
from typing import Any, Callable, Dict, Optional, Tuple, Union
from .marker import Marker

class LogEvent:
    """
    Represents a single log event.
    """
    __slots__ = (
        'timestamp',
        'level',
        'logger_name',
        'message',
        'args',
        'marker',
        'context',
        'extra',
        'exc_info',
        '_resolved_message'
    )

    def __init__(
        self,
        logger_name: str,
        level: int,
        message: Union[str, Callable[[], Any]],
        args: Tuple = (),
        marker: Optional[Marker] = None,
        context: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Tuple] = None,
        timestamp: Optional[float] = None
    ):
        self.timestamp = timestamp or time.time()
        self.level = level
        self.logger_name = logger_name
        self.message = message
        self.args = args
        self.marker = marker
        self.context = context or {}
        self.extra = extra or {}
        self.exc_info = exc_info
        self._resolved_message: Optional[str] = None

    def get_message(self) -> str:
        """
        Return the resolved message string. 
        Executes the callable if message is a function.
        Formats the message with args if provided.
        """
        if self._resolved_message is not None:
            return self._resolved_message

        msg = self.message
        if callable(msg):
            msg = msg()
        
        msg = str(msg)
        
        if self.args:
            # Evaluate callable args (Lazy evaluation support)
            evaluated_args = []
            for arg in self.args:
                if callable(arg):
                    try:
                        evaluated_args.append(arg())
                    except Exception as e:
                        evaluated_args.append(f"<Error evaluating arg: {e}>")
                else:
                    evaluated_args.append(arg)
            
            args = tuple(evaluated_args)

            # Check if it looks like brace formatting
            if "{}" in msg:
                try:
                     self._resolved_message = msg.format(*args)
                except Exception:
                     # Fallback to string concatenation or raw
                     self._resolved_message = f"{msg} args={args}"
            else:
                # Fallback to standard % formatting if args exist but no {}
                try:
                    self._resolved_message = msg % args
                except TypeError:
                     self._resolved_message = f"{msg} {args}"
        else:
            self._resolved_message = msg

        return self._resolved_message

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        """
        data = {
            "timestamp": self.timestamp,
            "level": logging.getLevelName(self.level),
            "logger": self.logger_name,
            "message": self.get_message(),
            "context": self.context,
        }
        
        if self.marker:
            data["marker"] = self.marker.name
            
        if self.extra:
            data.update(self.extra)
            
        if self.exc_info:
            # Exception serialization is usually handled by the formatter
            # But we can provide a hint here or leave it to formatter
            pass
            
        return data
