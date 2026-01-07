import unittest
import logging
import asyncio
from pylog.core.logger import Logger, LoggerConfig
from pylog.core.context import ThreadContext
from pylog.core.log_event import LogEvent
from pylog.core.marker import Marker

class MockAppender:
    def __init__(self):
        self.events = []

    def append(self, event):
        self.events.append(event)

class TestCore(unittest.TestCase):
    def setUp(self):
        self.config = LoggerConfig("test_logger", level=logging.INFO)
        self.appender = MockAppender()
        self.config.add_appender(self.appender)
        self.logger = Logger("test_logger", self.config)
        ThreadContext.clear()

    def test_basic_logging(self):
        self.logger.info("Hello World")
        self.assertEqual(len(self.appender.events), 1)
        self.assertEqual(self.appender.events[0].message, "Hello World")
        self.assertEqual(self.appender.events[0].level, logging.INFO)

    def test_level_filtering(self):
        self.logger.debug("Should not pass")
        self.logger.info("Should pass")
        self.assertEqual(len(self.appender.events), 1)
        self.assertEqual(self.appender.events[0].message, "Should pass")

    def test_lazy_evaluation(self):
        # Test lambda
        self.logger.info("Value: {}", lambda: 42)
        self.assertEqual(self.appender.events[0].args[0](), 42)
        
        # Test not evaluated if level low
        flag = {"evaluated": False}
        def side_effect():
            flag["evaluated"] = True
            return 100
            
        self.logger.debug("Value: {}", side_effect)
        self.assertFalse(flag["evaluated"])

    def test_marker(self):
        security_marker = Marker("SECURITY")
        self.logger.info("Login", marker=security_marker)
        self.assertEqual(self.appender.events[0].marker.name, "SECURITY")

    def test_context_mdc(self):
        ThreadContext.put("user", "alice")
        self.logger.info("Action")
        self.assertEqual(self.appender.events[0].context["user"], "alice")
        
        ThreadContext.remove("user")
        self.logger.info("Action2")
        self.assertNotIn("user", self.appender.events[1].context)

    def test_context_manager(self):
        with ThreadContext.scope(req_id="123"):
            self.logger.info("In scope")
            self.assertEqual(self.appender.events[0].context["req_id"], "123")
        
        self.logger.info("Out scope")
        self.assertNotIn("req_id", self.appender.events[1].context)

class TestAsyncContext(unittest.IsolatedAsyncioTestCase):
    async def test_async_context(self):
        config = LoggerConfig("async_logger", level=logging.INFO)
        appender = MockAppender()
        config.add_appender(appender)
        logger = Logger("async_logger", config)
        
        ThreadContext.clear()
        
        @ThreadContext.inject(trace_id="async-1")
        async def worker():
            logger.info("Work")
            await asyncio.sleep(0.01)
            
        await worker()
        self.assertEqual(appender.events[0].context["trace_id"], "async-1")
        
        # Ensure context didn't leak
        self.assertIsNone(ThreadContext.get("trace_id"))
