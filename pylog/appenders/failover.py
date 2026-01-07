import time
import sys
from typing import List, Callable, Optional
from .base import Appender
from pylog.core.log_event import LogEvent
from pylog.core.metrics import MetricsRegistry

class FailoverAppender(Appender):
    """
    Appender that wraps a primary appender and a list of failover appenders.
    If the primary fails, it tries the failovers in order.
    It automatically retries the primary after a configured interval.
    """
    def __init__(self, name: str, primary: Appender, failovers: List[Appender], retry_interval: int = 60, on_switch: Optional[Callable[[str], None]] = None):
        # Failover appender doesn't need a formatter itself, as it delegates
        super().__init__(name, primary.formatter) 
        self.primary = primary
        self.failovers = failovers
        self.retry_interval = retry_interval
        self._last_failure_time = 0
        self._primary_active = True
        self.on_switch = on_switch
        self.metrics = MetricsRegistry()

    def start(self):
        self.primary.start()
        for f in self.failovers:
            f.start()
        super().start()

    def stop(self):
        self.primary.stop()
        for f in self.failovers:
            f.stop()
        super().stop()

    def append(self, event: LogEvent):
        current_time = time.time()
        
        # Try primary if active or retry interval passed
        if self._primary_active or (current_time - self._last_failure_time >= self.retry_interval):
            try:
                self.primary.append(event)
                if not self._primary_active:
                    # Recovered
                    self._primary_active = True
                    # Optional: Log recovery to stderr or internal logger
                    sys.stderr.write(f"FailoverAppender: Primary {self.primary.name} recovered.\n")
                return
            except Exception as e:
                # Primary failed
                if self._primary_active:
                    self._primary_active = False
                    self.metrics.increment("pylog_failover_switch_total")
                    sys.stderr.write(f"FailoverAppender: Primary {self.primary.name} failed: {e}. Switching to failover.\n")
                    if self.on_switch:
                        try:
                            self.on_switch(f"Primary failed: {e}")
                        except:
                            pass
                
                self._last_failure_time = current_time
        
        # Try failovers
        for failover in self.failovers:
            try:
                failover.append(event)
                return
            except Exception:
                continue
                
        # All failed
        self.metrics.increment("pylog_failover_all_failed_total")
        sys.stderr.write(f"FailoverAppender: All appenders failed for event {event.timestamp}\n")
