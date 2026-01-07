import time
from threading import RLock
from typing import List
from .base import Appender
from pylog.core.log_event import LogEvent

class BufferingAppender(Appender):
    """
    Wraps another Appender to provide buffering capabilities.
    Accumulates log events and writes them in batches to reduce I/O operations.
    """
    def __init__(self, target: Appender, batch_size: int = 100, flush_interval: float = 1.0):
        super().__init__(target.name, target.formatter)
        self.target = target
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer: List[str] = []
        self.last_flush_time = time.time()
        self.lock = RLock()
        
        # Optimize target for buffering
        if hasattr(self.target, 'immediate_flush'):
             self.target.immediate_flush = False

    def start(self):
        self.target.start()
        super().start()

    def stop(self):
        self.flush()
        self.target.stop()
        super().stop()

    def append(self, event: LogEvent):
        if not self.started:
            return

        # Format immediately to capture state and prepare for writing
        try:
            formatted = self.target.formatter.format(event)
            if isinstance(formatted, bytes):
                formatted = formatted.decode('utf-8')
        except Exception:
            # If formatting fails, we can't buffer it properly for raw write
            return

        with self.lock:
            self.buffer.append(formatted)
            should_flush = (len(self.buffer) >= self.batch_size) or \
                           (time.time() - self.last_flush_time >= self.flush_interval)
        
        if should_flush:
            self.flush()

    def flush(self):
        """
        Flushes the buffer to the target appender.
        """
        content = ""
        with self.lock:
            if not self.buffer:
                return
            content = "".join(self.buffer)
            self.buffer.clear()
            self.last_flush_time = time.time()
            
        if hasattr(self.target, 'write_raw'):
            try:
                self.target.write_raw(content)
                self.target.flush()
            except Exception as e:
                # Handle write error
                print(f"BufferingAppender: Error writing to target: {e}")
        else:
            # Fallback? If target doesn't support write_raw, we can't easily write a bulk string
            # unless we fake events, but we already formatted.
            # So we assume target supports write_raw or we print error.
            # RollingFileAppender and SocketAppender (we should update it) support it.
            print(f"BufferingAppender: Target {type(self.target)} does not support write_raw")
