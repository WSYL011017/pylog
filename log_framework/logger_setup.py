import logging
import logging.config
import logging.handlers
import json
import time
import os
import yaml
import threading
import contextvars
import queue
import atexit
import ctypes
import sys
import gzip
import shutil
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from .metrics import LossyQueueHandler, LogMetrics

# ==========================================
# 1. MDC (Mapped Diagnostic Context) Definition
#    Must be defined before LogRecordFactory
# ==========================================
_context: contextvars.ContextVar = contextvars.ContextVar("log_context", default={})

class MDC:
    @staticmethod
    def put(key: str, value: Any) -> None:
        # Optimized: Only copy if we need to modify. 
        # But dictionary is mutable, so we need a copy to set a new contextvar value.
        ctx = _context.get().copy()
        ctx[key] = value
        _context.set(ctx)

    @staticmethod
    def get(key: str) -> Any:
        return _context.get().get(key)

    @staticmethod
    def getAll() -> Dict[str, Any]:
        return _context.get()

    @staticmethod
    def remove(key: str) -> None:
        ctx = _context.get().copy()
        if key in ctx:
            del ctx[key]
            _context.set(ctx)

    @staticmethod
    def clear() -> None:
        _context.set({})

# ==========================================
# 2. LogRecordFactory Setup
#    Delayed initialization to avoid circular dependency
# ==========================================
_record_factory_setup = False

def _setup_record_factory():
    global _record_factory_setup
    if _record_factory_setup:
        return

    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        # Snapshot context at creation time
        record.mdc_context = MDC.getAll().copy()
        return record

    logging.setLogRecordFactory(record_factory)

# ==========================================
# 3. Custom Formatters & Filters
# ==========================================
class JSONFormatter(logging.Formatter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Pre-calculate static fields
        self.static_fields: Dict[str, str] = {
            "hostname": os.getenv("HOSTNAME", "localhost")
        }

    def format(self, record: logging.LogRecord) -> str:
        # Basic fields
        log_record: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "thread": record.threadName,
            "file": record.filename,
            "line": record.lineno
        }
        
        # Add static fields
        log_record.update(self.static_fields)
        
        # Merge MDC
        mdc_context = getattr(record, "mdc_context", None)
        if not mdc_context:
            mdc_context = MDC.getAll()
            
        if mdc_context:
            log_record["context"] = mdc_context

        # Exception info
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record, ensure_ascii=False)

class ContextFilter(logging.Filter):
    def __init__(self, key: str, value: Optional[str] = None, name: str = "") -> None:
        super().__init__(name)
        self.key = key
        self.value = value

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = getattr(record, "mdc_context", None)
        if not ctx:
             ctx = MDC.getAll()
             
        if self.key not in ctx:
            return False
        
        if self.value is not None:
            return str(ctx[self.key]) == str(self.value)
        
        return True
        
class SensitiveDataFilter(logging.Filter):
    """
    Filter that masks sensitive data (like passwords, tokens) in log messages.
    """
    def __init__(self, name: str = "") -> None:
        super().__init__(name)
        self.patterns = [
            (re.compile(r'(password|secret|token|key|pwd)=[^&\s]+', re.IGNORECASE), r'\1=***'),
            (re.compile(r'(Authorization:\s*Bearer\s+)[^\s]+', re.IGNORECASE), r'\1***'),
        ]

    def filter(self, record: logging.LogRecord) -> bool:
        # Check and mask msg string
        if isinstance(record.msg, str):
            for pattern, repl in self.patterns:
                record.msg = pattern.sub(repl, record.msg)
        return True

# ==========================================
# 4. Handlers
# ==========================================
class HiddenTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    def _open(self) -> Any:
        stream = super()._open()
        try:
            FILE_ATTRIBUTE_HIDDEN = 0x02
            if os.name == 'nt':
                # Use absolute path to be safe
                path = os.path.abspath(self.baseFilename)
                ret = ctypes.windll.kernel32.SetFileAttributesW(path, FILE_ATTRIBUTE_HIDDEN)
                if not ret:
                    # Non-fatal warning
                    sys.stderr.write(f"Warning: Failed to set hidden attribute for {path}\n")
        except Exception as e:
            # Safe catch-all to prevent logging crash
             sys.stderr.write(f"Warning: Error setting hidden attribute: {e}\n")
        return stream

class CompressedTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """
    TimedRotatingFileHandler that compresses rotated logs using gzip.
    """
    def rotate(self, source: str, dest: str) -> None:
        super().rotate(source, dest)
        # Compress
        try:
            with open(dest, 'rb') as f_in:
                with gzip.open(f"{dest}.gz", 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            # Remove original uncompressed file
            os.remove(dest)
        except Exception as e:
            # Fallback or log error
            sys.stderr.write(f"Error compressing log file {dest}: {e}\n")

# ==========================================
# 5. Log Manager
# ==========================================
def _deep_merge(base: Dict[str, Any], override: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(base, dict):
        return override if isinstance(override, dict) else base
    if not isinstance(override, dict):
        return base
    
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged

class SafeQueueListener(logging.handlers.QueueListener):
    def handle(self, record: logging.LogRecord) -> None:
        try:
            super().handle(record)
        except Exception as e:
            sys.stderr.write(f"Error in QueueListener handle: {e}\n")

class LogManager:
    _initialized: bool = False
    _queue_listener: Optional[logging.handlers.QueueListener] = None
    _default_config_path: str = os.path.join(os.path.dirname(__file__), "log_config.yaml")
    _lock: threading.Lock = threading.Lock()
    # Shared queue for all async loggers
    _log_queue: Optional[queue.Queue] = None 

    @staticmethod
    def load_config(user_config_path: str = "logging.yaml", async_mode: bool = True) -> None:
        # Thread-safe initialization
        with LogManager._lock:
            if LogManager._initialized:
                return

            # Setup Record Factory first
            _setup_record_factory()

            # 1. Load Defaults
            config: Dict[str, Any] = {}
            if os.path.exists(LogManager._default_config_path):
                with open(LogManager._default_config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
            else:
                print("Warning: Default log config not found.")

            # 2. Load User Config
            if user_config_path and os.path.exists(user_config_path):
                print(f"Loading user config from {user_config_path}")
                with open(user_config_path, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f)
                    config = _deep_merge(config, user_config)

            # 3. Env Vars
            env_level = os.getenv("PYLOG_LEVEL")
            if env_level:
                print(f"Overriding Log Level from Env: {env_level}")
                if "root" not in config: config["root"] = {}
                config["root"]["level"] = env_level.upper()

            # 3.5 Create Dirs
            LogManager._ensure_log_dirs(config)

            # 4. Apply Config
            try:
                logging.config.dictConfig(config)
            except Exception as e:
                print(f"Error applying log config: {e}")
                logging.basicConfig(level=logging.INFO)
            
            # 5. Setup Async
            if async_mode:
                LogManager._setup_async_mode()
                
            LogManager._initialized = True
            print(f"Log Framework Initialized (Async: {async_mode}).")

    @staticmethod
    def reload_config(config_path: str = None) -> bool:
        """
        Hot reload the logging configuration.
        Stops the async listener, resets the queue, and re-applies configuration.
        """
        try:
            print("Reloading configuration...")
            with LogManager._lock:
                # Stop existing listener
                if LogManager._queue_listener:
                    LogManager._queue_listener.stop()
                    LogManager._queue_listener = None
                
                # Reset state
                LogManager._log_queue = None
                LogManager._initialized = False
                
            # Re-initialize
            target_path = config_path if config_path else "logging.yaml"
            LogManager.load_config(target_path)
            return True
        except Exception as e:
            sys.stderr.write(f"Failed to reload config: {e}\n")
            return False

    @staticmethod
    def _ensure_log_dirs(config: Dict[str, Any]) -> None:
        handlers = config.get("handlers", {})
        for name, handler_config in handlers.items():
            filename = handler_config.get("filename")
            if filename:
                log_dir = os.path.dirname(os.path.abspath(filename))
                if log_dir and not os.path.exists(log_dir):
                    try:
                        os.makedirs(log_dir, exist_ok=True)
                        print(f"Created log directory: {log_dir}")
                    except Exception as e:
                        print(f"Warning: Failed to create log dir {log_dir}: {e}")

    @staticmethod
    def _setup_async_mode() -> None:
        """
        Recursively wrap all loggers with QueueHandler for true async I/O.
        """
        # Bounded queue to prevent OOM
        MAX_QUEUE_SIZE = 10000
        LogManager._log_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        handlers_to_listen: List[logging.Handler] = []
        
        def asyncify_logger(logger: logging.Logger) -> None:
            # If logger has handlers, replace them
            if not logger.handlers:
                return
                
            has_queue_handler = any(isinstance(h, logging.handlers.QueueHandler) for h in logger.handlers)
            if has_queue_handler:
                return

            current_handlers = logger.handlers[:]
            logger.handlers = [] # Remove all
            
            # Add QueueHandler
            # Use LossyQueueHandler for metrics and overflow protection
            q_handler = LossyQueueHandler(LogManager._log_queue, max_size=MAX_QUEUE_SIZE)
            logger.addHandler(q_handler)
            
            # Add original handlers to listener list
            for h in current_handlers:
                if h not in handlers_to_listen:
                    handlers_to_listen.append(h)

        # 1. Asyncify Root
        root_logger = logging.getLogger()
        asyncify_logger(root_logger)
        
        # 2. Asyncify any other existing loggers
        # Use .items() to get name and logger instance, and filter for actual Logger objects
        for name, logger in logging.Logger.manager.loggerDict.items():
            if isinstance(logger, logging.Logger) and logger.handlers:
                asyncify_logger(logger)
            
        if not handlers_to_listen:
            return

        # 3. Start Listener (Safe version)
        LogManager._queue_listener = SafeQueueListener(
            LogManager._log_queue, *handlers_to_listen, respect_handler_level=True
        )
        LogManager._queue_listener.start()
        atexit.register(LogManager.shutdown)

    @staticmethod
    def add_async_handler(logger: logging.Logger, handler: logging.Handler) -> None:
        """
        Safely add a handler to a logger in async mode.
        If async mode is active, the handler is added to the listener instead of the logger.
        Thread-safe implementation updating handlers tuple atomically without stopping the listener.
        """
        if LogManager._queue_listener:
             # Thread-safe update: Read -> Append -> Write
             # In CPython, tuple assignment is atomic. 
             # QueueListener iterates over self.handlers in its loop, so updating the reference is safe.
             with LogManager._lock:
                 current_handlers = list(LogManager._queue_listener.handlers)
                 current_handlers.append(handler)
                 LogManager._queue_listener.handlers = tuple(current_handlers)
        else:
            logger.addHandler(handler)

    @staticmethod
    def get_logger(name: Optional[str] = None) -> logging.Logger:
        return logging.getLogger(name)

    @staticmethod
    def shutdown() -> None:
        with LogManager._lock:
            if LogManager._queue_listener:
                LogManager._queue_listener.stop()
                LogManager._queue_listener = None
            
            LogManager._initialized = False
            LogManager._log_queue = None
            
        logging.shutdown()

# ==========================================
# 6. Decorator
# ==========================================
def Slf4j(cls: Any) -> Any:
    logger_name = f"{cls.__module__}.{cls.__name__}"
    logger = logging.getLogger(logger_name)
    setattr(cls, "logger", logger)
    return cls
