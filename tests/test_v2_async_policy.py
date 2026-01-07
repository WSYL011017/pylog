import unittest
import logging
import time
import threading

from pylog.core.async_queue import AsyncQueueHandler
from pylog.core.log_event import LogEvent
from pylog.core.metrics import MetricsRegistry


class SlowAppender:
    def __init__(self, delay=0.2):
        self.delay = delay
        self.events = []
        self.lock = threading.Lock()

    def append(self, event):
        time.sleep(self.delay)
        with self.lock:
            self.events.append(event)


class TestAsyncBackpressurePolicies(unittest.TestCase):
    def setUp(self):
        self.metrics = MetricsRegistry()
        self.metrics.reset()

    def test_discard_policy_drops_on_full(self):
        queue = AsyncQueueHandler(queue_size=1, full_policy="Discard")
        appender = SlowAppender(delay=0.3)
        queue.start()
        
        try:
            e1 = LogEvent("t", logging.INFO, "info-1", (), None, {}, {}, None)
            e2 = LogEvent("t", logging.INFO, "info-2", (), None, {}, {}, None)
            queue.enqueue(e1, [appender])
            queue.enqueue(e2, [appender])  # Should hit Full and drop

            # Wait until processed
            start = time.time()
            while len(appender.events) < 1 and time.time() - start < 2:
                time.sleep(0.01)

            self.assertEqual(len(appender.events), 1)
            m = self.metrics.get_metrics()
            self.assertGreaterEqual(m.get("pylog_events_dropped_total", 0), 1)
        finally:
            queue.stop()

    def test_block_policy_blocks_instead_of_drop(self):
        queue = AsyncQueueHandler(queue_size=1, full_policy="Block")
        appender = SlowAppender(delay=0.2)
        queue.start()

        try:
            e1 = LogEvent("t", logging.INFO, "info-1", (), None, {}, {}, None)
            e2 = LogEvent("t", logging.INFO, "info-2", (), None, {}, {}, None)
            queue.enqueue(e1, [appender])
            queue.enqueue(e2, [appender])  # Should block until space then enqueue

            # Wait for both to be processed
            start = time.time()
            while len(appender.events) < 2 and time.time() - start < 3:
                time.sleep(0.01)

            self.assertEqual(len(appender.events), 2)
            # Metrics may still count a drop on Full, implementation increments before applying policy.
            # Core behavior we assert: both events are eventually processed.
        finally:
            queue.stop()

    def test_discard_low_level_policy(self):
        queue = AsyncQueueHandler(queue_size=1, full_policy="DiscardLowLevel")
        appender = SlowAppender(delay=0.3)
        queue.start()

        try:
            # 1) Fill queue with INFO
            info_event = LogEvent("t", logging.INFO, "info", (), None, {}, {}, None)
            queue.enqueue(info_event, [appender])

            # 2) Attempt to enqueue DEBUG while full -> should be dropped
            debug_event = LogEvent("t", logging.DEBUG, "debug", (), None, {}, {}, None)
            queue.enqueue(debug_event, [appender])

            # 3) Attempt to enqueue WARN while full -> should block and enqueue
            warn_event = LogEvent("t", logging.WARN, "warn", (), None, {}, {}, None)
            queue.enqueue(warn_event, [appender])

            # Wait until at least 2 events processed (INFO and WARN)
            start = time.time()
            while len(appender.events) < 2 and time.time() - start < 3:
                time.sleep(0.01)

            self.assertEqual(len(appender.events), 2)
            messages = [e.message for e in appender.events]
            self.assertIn("info", messages)
            self.assertIn("warn", messages)
            self.assertNotIn("debug", messages)
            m = self.metrics.get_metrics()
            self.assertGreaterEqual(m.get("pylog_events_dropped_total", 0), 1)
        finally:
            queue.stop()

    def test_error_level_guarantee(self):
        queue = AsyncQueueHandler(queue_size=1, full_policy="Discard")
        appender = SlowAppender(delay=0.3)
        queue.start()

        try:
            info_event = LogEvent("t", logging.INFO, "info", (), None, {}, {}, None)
            error_event = LogEvent("t", logging.ERROR, "error", (), None, {}, {}, None)

            queue.enqueue(info_event, [appender])
            queue.enqueue(error_event, [appender])  # Should be guaranteed (block or sync)

            # Wait for both
            start = time.time()
            while len(appender.events) < 2 and time.time() - start < 3:
                time.sleep(0.01)

            messages = [e.message for e in appender.events]
            self.assertIn("info", messages)
            self.assertIn("error", messages)
        finally:
            queue.stop()
