import unittest
import time
import threading
from pylog.core.async_queue import AsyncQueueHandler
from pylog.core.log_event import LogEvent

class CounterAppender:
    def __init__(self):
        self.count = 0
        self.events = []
        self._lock = threading.Lock()

    def append(self, event):
        with self._lock:
            self.count += 1
            self.events.append(event)

class TestAsyncQueue(unittest.TestCase):
    def setUp(self):
        self.queue = AsyncQueueHandler(queue_size=1000)
        self.queue.start()
        self.appender = CounterAppender()

    def tearDown(self):
        self.queue.stop()

    def test_async_processing(self):
        event = LogEvent("test", 20, "msg", (), None, {}, {}, None)
        self.queue.enqueue(event, [self.appender])
        
        # Wait for processing
        start = time.time()
        while self.appender.count < 1:
            if time.time() - start > 1:
                self.fail("Timeout waiting for async processing")
            time.sleep(0.01)
            
        self.assertEqual(self.appender.count, 1)

    def test_throughput_benchmark(self):
        # This is a mini benchmark
        count = 1000
        event = LogEvent("test", 20, "msg", (), None, {}, {}, None)
        appenders = [self.appender]
        
        start_time = time.time()
        for _ in range(count):
            self.queue.enqueue(event, appenders)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"\nEnqueued {count} events in {duration:.6f}s ({(duration/count)*1000:.4f} ms/op)")
        
        # Verify all processed eventually
        wait_start = time.time()
        while self.appender.count < count:
            if time.time() - wait_start > 2:
                break
            time.sleep(0.01)
            
        self.assertEqual(self.appender.count, count)
        
        # NFR Check: Blocking time < 0.05ms per op?
        # Typically 1000 ops take ~0.01s total in pure python queue put, so 0.01ms per op.
        avg_time = duration / count
        self.assertLess(avg_time, 0.00005) # 0.05ms
