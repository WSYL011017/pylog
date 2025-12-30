from typing import Any, Dict
import logging
import queue

import threading
import time
import collections
import random
from typing import Any, Dict, Deque, Tuple

class PerformanceMonitor:
    """
    High-performance monitor to buffer metrics and reduce I/O overhead.
    """
    _metrics_buffer: Deque[Tuple[float, str, float]] = collections.deque(maxlen=1000)
    _last_flush: float = time.time()
    _lock: threading.Lock = threading.Lock()
    
    @classmethod
    def record_metric(cls, metric_type: str, value: float) -> None:
        # Batch collect
        with cls._lock:
            cls._metrics_buffer.append((time.time(), metric_type, value))
            
            # Flush every 1s
            if time.time() - cls._last_flush > 1.0:
                cls._flush_metrics()
    
    @classmethod
    def _flush_metrics(cls) -> None:
        # In a real system, send to Prometheus/StatsD
        # Here we just clear the buffer or maybe aggregate in memory
        # For demo purposes, we keep them in memory to be queryable if needed,
        # but in production this would push out.
        
        # Simulating flush by clearing buffer to prevent memory leak
        # In real world: send_to_monitoring(list(cls._metrics_buffer))
        cls._metrics_buffer.clear()
        cls._last_flush = time.time()

class AdaptiveSampler:
    """
    Adaptive sampling rate based on queue pressure.
    """
    def __init__(self, base_rate: float = 0.01) -> None:
        self.base_rate = base_rate
        self.current_rate = base_rate
        self.queue_pressure = 0.0
        
    def update_pressure(self, qsize: int, maxsize: int) -> None:
        if maxsize > 0:
            self.queue_pressure = qsize / maxsize
        else:
            self.queue_pressure = 0.0
            
    def should_sample(self) -> bool:
        # Adjust rate based on pressure
        if self.queue_pressure > 0.8:  # High pressure
            # Increase sampling to monitor closely
            self.current_rate = min(self.base_rate * 5, 0.1) # Max 10%
        elif self.queue_pressure < 0.2: # Low pressure
            # Decrease sampling to save CPU
            self.current_rate = max(self.base_rate / 2, 0.001) # Min 0.1%
            
        return random.random() < self.current_rate

class LogMetrics:
    """
    Simple metrics collector.
    In a real app, replace with prometheus_client or similar.
    """
    _queue_size: int = 0
    _dropped_count: int = 0
    _sample_rate: float = 0.01 # Changed to float for adaptive
    _error_count: int = 0
    
    @staticmethod
    def set_queue_size(size: int) -> None:
        LogMetrics._queue_size = size
        PerformanceMonitor.record_metric("queue_size", float(size))

    @staticmethod
    def set_sample_rate(rate: float) -> None:
        LogMetrics._sample_rate = rate
        
    @staticmethod
    def increment_dropped() -> None:
        LogMetrics._dropped_count += 1
        PerformanceMonitor.record_metric("dropped", 1.0)

    @staticmethod
    def increment_error() -> None:
        LogMetrics._error_count += 1
        PerformanceMonitor.record_metric("error", 1.0)
        
    @staticmethod
    def get_metrics() -> Dict[str, Any]:
        return {
            "queue_size": LogMetrics._queue_size,
            "dropped_total": LogMetrics._dropped_count,
            "error_count": LogMetrics._error_count,
            "sample_rate": LogMetrics._sample_rate
        }

class LossyQueueHandler(logging.handlers.QueueHandler):
    """
    QueueHandler that monitors queue size and drops records if full.
    Includes sampling for metrics and thread-safe dropping.
    """
    def __init__(self, queue: queue.Queue, max_size: int = 10000) -> None:
        super().__init__(queue)
        self.max_size = max_size
        # Use AdaptiveSampler
        self.sampler = AdaptiveSampler(base_rate=0.01) # 1% base
        self._drop_lock: threading.Lock = threading.Lock()

    def enqueue(self, record: logging.LogRecord) -> None:
        # Check sampling
        if self.sampler.should_sample():
            if hasattr(self.queue, 'qsize'):
                 qsize = self.queue.qsize()
                 # Update metrics
                 LogMetrics.set_queue_size(qsize)
                 LogMetrics.set_sample_rate(self.sampler.current_rate)
                 # Update pressure for next time
                 self.sampler.update_pressure(qsize, self.max_size)
             
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            LogMetrics.increment_dropped()
            
            # High pressure! Update sampler immediately
            self.sampler.queue_pressure = 1.0
            
            # Drop the oldest record to make space
            # Use lock to prevent race conditions during drop-then-put
            with self._drop_lock:
                try:
                    self.queue.get_nowait()
                except queue.Empty:
                    pass # Queue became empty, just proceed
                
                try:
                    self.queue.put_nowait(record)
                except queue.Full:
                    # Still full? Drop this record then (last resort)
                    pass
                except queue.Empty:
                     # Race condition: queue became empty during put? Unlikely for put_nowait but possible implementation detail
                     pass
