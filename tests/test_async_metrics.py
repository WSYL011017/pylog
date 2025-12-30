import pytest
import logging
import queue
import time
import threading
from unittest.mock import MagicMock, patch
from log_framework.logger_setup import LogManager, SafeQueueListener
from log_framework.metrics import LogMetrics

@pytest.fixture
def async_manager():
    LogManager._initialized = False
    LogManager.shutdown()
    LogManager.load_config(user_config_path=None, async_mode=True)
    yield
    LogManager.shutdown()

def test_add_async_handler(async_manager):
    """Test adding a handler dynamically in async mode."""
    assert LogManager._queue_listener is not None
    
    mock_handler = MagicMock(spec=logging.Handler)
    mock_handler.level = logging.INFO
    
    logger = logging.getLogger("test_async_add")
    LogManager.add_async_handler(logger, mock_handler)
    
    assert mock_handler in LogManager._queue_listener.handlers

def test_add_async_handler_concurrency(async_manager):
    """Test thread-safety of adding handlers concurrently."""
    def add_handlers():
        for i in range(10):
            h = MagicMock(spec=logging.Handler)
            LogManager.add_async_handler(logging.getLogger("test"), h)
            time.sleep(0.001)

    threads = [threading.Thread(target=add_handlers) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    assert isinstance(LogManager._queue_listener.handlers, tuple)
    # 5 threads * 10 handlers = 50 new handlers + existing ones
    # We expect at least 50 handlers
    assert len(LogManager._queue_listener.handlers) >= 50
    assert all(isinstance(h, logging.Handler) for h in LogManager._queue_listener.handlers)

def test_safe_queue_listener_exception():
    """Test that listener survives handler exceptions."""
    q = queue.Queue()
    handler = MagicMock()
    handler.handle.side_effect = Exception("Boom")
    
    listener = SafeQueueListener(q, handler)
    listener.start()
    
    record = logging.LogRecord("name", logging.INFO, "path", 1, "msg", (), None)
    q.put(record)
    
    time.sleep(0.1)
    
    assert listener._thread.is_alive()
    listener.stop()

def test_lossy_queue_handler():
    """Test that queue drops items when full."""
    # Create a small queue for testing
    q = queue.Queue(maxsize=5)
    
    # We need to manually use LossyQueueHandler logic or use the class
    from log_framework.metrics import LossyQueueHandler
    handler = LossyQueueHandler(q)
    
    # Fill queue
    for i in range(5):
        record = logging.LogRecord("name", logging.INFO, "path", 1, f"msg {i}", (), None)
        handler.enqueue(record)
        
    assert q.full()
    
    # Add one more (should drop oldest)
    new_record = logging.LogRecord("name", logging.INFO, "path", 1, "new msg", (), None)
    handler.enqueue(new_record)
    
    # Check metrics
    metrics = LogMetrics.get_metrics()
    assert metrics["dropped_total"] > 0
    
    # Verify content: oldest (msg 0) should be gone, new_record should be present
    # Queue is FIFO. 
    # Current queue state should be: msg 1, msg 2, msg 3, msg 4, new msg
    items = []
    while not q.empty():
        items.append(q.get().msg)
        
    assert "msg 0" not in items
    assert "new msg" in items

def test_metrics_sampling():
    """Test that metrics are sampled correctly."""
    q = queue.Queue()
    from log_framework.metrics import LossyQueueHandler, LogMetrics
    handler = LossyQueueHandler(q)
    
    # Reset metrics
    LogMetrics.set_queue_size(0)
    
    # Initial state
    assert LogMetrics.get_metrics()["queue_size"] == 0
    
    # Enqueue 99 items
    record = logging.LogRecord("name", logging.INFO, "path", 1, "msg", (), None)
    for _ in range(99):
        handler.enqueue(record)
        
    # Should still be 0 because sampling happens every 100th call
    # Wait, the counter starts at 0, first call increments to 1.
    # 1 % 100 != 0.
    # 100th call increments to 100. 100 % 100 == 0.
    # So the 100th call triggers update.
    
    # Let's verify qsize is actually > 0
    assert q.qsize() == 99
    # Metric should still be old value (0) or whatever it was before if we rely on sampling
    # But here we assume set_queue_size wasn't called.
    
    # NOTE: In our implementation, we check `if hasattr(self.queue, 'qsize')`. 
    # Standard queue has it.
    
    # To strictly test sampling, we can mock LogMetrics.set_queue_size
    with patch("log_framework.metrics.LogMetrics.set_queue_size") as mock_set:
         # Reset counter
         handler._sample_counter = 0
         
         # 99 calls
         for _ in range(99):
             handler.enqueue(record)
         
         assert mock_set.call_count == 0
         
         # 100th call
         handler.enqueue(record)
         assert mock_set.call_count == 1

