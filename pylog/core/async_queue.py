import threading
import queue
import atexit
import sys
import time
import logging
from typing import List, Optional
from .log_event import LogEvent
from .metrics import MetricsRegistry

class AsyncQueueHandler:
    """
    Handles asynchronous logging using a background worker thread and a queue.
    Supports backpressure policies: Discard, Block, DiscardLowLevel.
    """
    def __init__(self, queue_size: int = 4096, full_policy: str = "Discard"):
        self.queue: queue.Queue = queue.Queue(maxsize=queue_size)
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.appenders = [] 
        self.full_policy = full_policy  # Discard, Block, DiscardLowLevel
        self.metrics = MetricsRegistry()

    def set_appenders(self, appenders: List):
        self.appenders = appenders

    def start(self):
        if self.running:
            return
        self.running = True
        self._stop_event.clear()
        self.worker_thread = threading.Thread(target=self._worker_loop, name="PyLog-AsyncWorker", daemon=True)
        self.worker_thread.start()
        atexit.register(self.stop)

    def stop(self):
        if not self.running:
            return
        self.running = False
        self._stop_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
        
        # Drain queue
        self._drain()

    def enqueue(self, event: LogEvent, appenders: List):
        """
        Enqueue an event to be processed by the given appenders.
        """
        if not self.running:
            # Synchronous fallback if not running
            for appender in appenders:
                appender.append(event)
            return

        # Metrics: Queue Size
        self.metrics.gauge("pylog_queue_size", self.queue.qsize())

        try:
            self.queue.put_nowait((event, appenders))
        except queue.Full:
            # Critical/Error Guarantee: Always try to block-put or fallback if critical
            if event.level >= logging.ERROR:
                try:
                    # Force put with timeout (effectively blocking but safe)
                    self.queue.put((event, appenders), timeout=1.0)
                    return
                except queue.Full:
                    # Still full? Fallback to sync write to stderr or specific appender?
                    # For now, sync write to appenders (bypass queue)
                    # This might slow down app, but guarantees delivery
                    sys.stderr.write("PyLog Queue Full (ERROR). Force syncing.\n")
                    for app in appenders:
                        try:
                            app.append(event)
                        except:
                            pass
                    return

            # Normal levels: Apply Policy
            self.metrics.increment("pylog_events_dropped_total")
            
            if self.full_policy == "Block":
                self.queue.put((event, appenders)) # Blocking put
            
            elif self.full_policy == "DiscardLowLevel":
                if event.level >= logging.WARN:
                     self.queue.put((event, appenders)) # Block for WARN+
                else:
                    pass # Discard INFO/DEBUG
            
            else: # Discard (Default)
                pass
                # Optionally print to stderr once per burst?
                # sys.stderr.write("PyLog Async Queue Full! Dropping event.\n")

    def _worker_loop(self):
        batch = []
        batch_size = 100
        while not self._stop_event.is_set():
            try:
                # Try to fill batch
                try:
                    # Blocking get for first item
                    item = self.queue.get(timeout=0.1)
                    batch.append(item)
                    
                    # Non-blocking get for rest of batch
                    for _ in range(batch_size - 1):
                        try:
                            item = self.queue.get_nowait()
                            batch.append(item)
                        except queue.Empty:
                            break
                except queue.Empty:
                    pass

                if batch:
                    for item in batch:
                        self._process_item(item)
                        self.queue.task_done()
                    batch.clear()

            except Exception as e:
                sys.stderr.write(f"PyLog Async Worker Error: {e}\n")
                # Prevent tight loop on error
                if batch:
                    # If error occurred during processing, we might lose some items in batch 
                    # or process them partially. 
                    # Ideally, we should handle per-item try-except in _process_item loop.
                    # Current implementation does handle per-item try-except in _process_item.
                    # This except block catches top-level errors.
                    batch.clear()
                time.sleep(0.1)

    def _process_item(self, item):
        event, appenders = item
        for appender in appenders:
            try:
                appender.append(event)
            except Exception as e:
                sys.stderr.write(f"PyLog Appender Error: {e}\n")

    def _drain(self):
        """Process remaining items in queue"""
        while not self.queue.empty():
            try:
                item = self.queue.get_nowait()
                self._process_item(item)
                self.queue.task_done()
            except queue.Empty:
                break
