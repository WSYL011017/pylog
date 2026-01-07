import logging
import sys
import os
import threading
import multiprocessing
from typing import Any, Callable, Dict, List, Optional, Union
from .log_event import LogEvent
from .context import ThreadContext
from .marker import Marker

class LoggerConfig:
    """
    Configuration for a Logger.
    Determines the log level, appenders, and additivity.
    """
    def __init__(self, name: str, level: int = logging.INFO, additivity: bool = True):
        self.name = name
        self.level = level
        self.additivity = additivity
        self.appenders: List[Any] = [] # List of Appenders
        self.parent: Optional['LoggerConfig'] = None

    def is_enabled(self, level: int) -> bool:
        return level >= self.level

    def add_appender(self, appender):
        self.appenders.append(appender)

    def log(self, event: LogEvent):
        """
        Dispatch event to appenders. 
        Handles additivity (bubbling up to parent).
        """
        for appender in self.appenders:
            try:
                appender.append(event)
            except Exception:
                # Fallback error handling to stderr to avoid infinite loops
                sys.stderr.write(f"Error in appender {appender}: {sys.exc_info()[1]}\n")

        if self.additivity and self.parent:
            self.parent.log(event)

    def get_effective_appenders(self) -> List[Any]:
        """
        Get all appenders applicable for this config, including parents if additivity is True.
        """
        appenders = list(self.appenders)
        if self.additivity and self.parent:
            appenders.extend(self.parent.get_effective_appenders())
        return appenders

class Logger:
    """
    The main Logger class used by the application.
    """
    def __init__(self, name: str, config: LoggerConfig, async_queue: Optional[Any] = None):
        self.name = name
        self.config = config
        self.async_queue = async_queue

    def debug(self, msg: Union[str, Callable], *args, **kwargs):
        self._log(logging.DEBUG, msg, args, kwargs)

    def info(self, msg: Union[str, Callable], *args, **kwargs):
        self._log(logging.INFO, msg, args, kwargs)

    def warning(self, msg: Union[str, Callable], *args, **kwargs):
        self._log(logging.WARNING, msg, args, kwargs)

    def warn(self, msg: Union[str, Callable], *args, **kwargs):
        self.warning(msg, *args, **kwargs)

    def error(self, msg: Union[str, Callable], *args, **kwargs):
        self._log(logging.ERROR, msg, args, kwargs)

    def critical(self, msg: Union[str, Callable], *args, **kwargs):
        self._log(logging.CRITICAL, msg, args, kwargs)

    def log(self, level: int, msg: Union[str, Callable], *args, **kwargs):
        self._log(level, msg, args, kwargs)

    def _log(self, level: int, msg: Union[str, Callable], args, kwargs):
        if not self.config.is_enabled(level):
            return

        marker = kwargs.pop('marker', None)
        exc_info = kwargs.pop('exc_info', None)
        
        # If exc_info is not provided but we are in an exception handler, 
        # and level is error/critical, maybe we should auto-capture?
        # Standard logging does this if exc_info=True. 
        # For now, let's stick to explicit exc_info passed.
        # But if the user calls logger.exception(), it implies exc_info=True.
        
        context = ThreadContext.get_all()
        
        # Capture thread and process info
        thread_name = threading.current_thread().name
        try:
            process_name = multiprocessing.current_process().name
        except Exception:
            process_name = "MainProcess"

        # Capture caller info
        file_name, line_number, func_name = "(unknown file)", 0, "(unknown function)"
        try:
            f = sys._getframe(1) # Start from caller of _log
            while f:
                co = f.f_code
                if co.co_filename == __file__:
                    f = f.f_back
                    continue
                
                file_name = os.path.basename(co.co_filename)
                line_number = f.f_lineno
                func_name = co.co_name
                break
        except ValueError:
            pass

        event = LogEvent(
            logger_name=self.name,
            level=level,
            message=msg,
            args=args,
            marker=marker,
            context=context,
            extra=kwargs,
            exc_info=exc_info,
            thread_name=thread_name,
            process_name=process_name,
            file_name=file_name,
            line_number=line_number,
            func_name=func_name
        )
        
        if self.async_queue and getattr(self.async_queue, 'running', False):
            appenders = self.config.get_effective_appenders()
            if appenders:
                self.async_queue.enqueue(event, appenders)
        else:
            self.config.log(event)

    def exception(self, msg: Union[str, Callable], *args, **kwargs):
        """
        Log an exception with ERROR level.
        """
        kwargs['exc_info'] = True # Or sys.exc_info()
        # In standard logging, exc_info=True causes the handler to fetch sys.exc_info()
        # In our LogEvent, we expect exc_info tuple.
        if kwargs.get('exc_info') is True:
            kwargs['exc_info'] = sys.exc_info()
            
        self.error(msg, *args, **kwargs)
