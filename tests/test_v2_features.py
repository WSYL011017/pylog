import unittest
import os
import time
import shutil
import tempfile
import logging
import queue
from pylog.manager import LogManager
from pylog.core.log_event import LogEvent
from pylog.formatters.json_formatter import JSONFormatter
from pylog.appenders.rolling_file import RollingFileAppender, DefaultRolloverStrategy, SizeBasedTriggeringPolicy
from pylog.infra.config_loader import ConfigLoader

class TestV2Features(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        LogManager.shutdown()
        shutil.rmtree(self.test_dir)

    def test_rolling_retention(self):
        """Verify that old files are deleted based on max_files strategy."""
        log_file = os.path.join(self.test_dir, "app.log")
        file_pattern = os.path.join(self.test_dir, "app-%i.log")
        
        # Strategy with max=2
        strategy = DefaultRolloverStrategy(max_files=2, file_pattern=file_pattern)
        policy = SizeBasedTriggeringPolicy(max_size=10) # Small size to trigger often
        
        appender = RollingFileAppender(
            "rolling", 
            JSONFormatter(), 
            log_file, 
            file_pattern, 
            [policy], 
            strategy
        )
        appender.start()
        
        # Create 5 rollovers
        for i in range(5):
            # Write enough data to trigger rollover
            # "Test Message" is > 10 bytes
            appender.append(LogEvent("test", logging.INFO, f"Message {i} " + "x"*10))
            # Force triggering check (append triggers it)
            time.sleep(0.1) # Ensure different mtimes
        
        appender.stop()
        
        # Check files in dir
        files = os.listdir(self.test_dir)
        # Should have app.log (active) + 2 archived files
        # archives: app-1.log, app-2.log ...
        
        archives = [f for f in files if f.startswith("app-") and f.endswith(".log")]
        self.assertLessEqual(len(archives), 2, f"Expected max 2 archives, found: {archives}")
        
    def test_json_masking(self):
        """Verify sensitive data masking."""
        formatter = JSONFormatter(masked_keys=["password", "secret"])
        # Use extra for structured fields
        event = LogEvent(
            "test", 
            logging.INFO, 
            "Login", 
            extra={"user": "admin", "password": "super_secret", "data": {"secret": "12345"}}
        )
        
        json_bytes = formatter.format(event)
        json_str = json_bytes.decode('utf-8')
        
        self.assertIn('"password":"***"', json_str)
        self.assertIn('"secret":"***"', json_str)
        self.assertIn('"user":"admin"', json_str)
        self.assertNotIn("super_secret", json_str)
        self.assertNotIn("12345", json_str)

    def test_async_backpressure_discard(self):
        """Verify Discard policy."""
        # Setup LogManager with small queue
        LogManager.configure_async_queue(queue_size=2, full_policy="Discard")
        q = LogManager._get_async_queue()
        
        # Stop worker to manually control queue
        q.stop()
        # Re-init queue directly to avoid worker draining it
        q.queue = queue.Queue(maxsize=2)
        q.running = True 
        
        # Fill queue
        evt = LogEvent("test", logging.INFO, "msg")
        q.enqueue(evt, [])
        q.enqueue(evt, [])
        self.assertTrue(q.queue.full())
        
        # Try 3rd (INFO) - Should be discarded
        q.enqueue(evt, [])
        self.assertTrue(q.queue.full())
        # Verify metric if possible, or just that it didn't block/crash
        
        # Try 3rd (ERROR) - Should be forced (might block or fallback)
        # In current impl, it tries to put with timeout 1.0s. 
        # Since queue is full and no consumer, it will eventually timeout and print/fallback.
        # We can't easily test the fallback without mocking time or waiting 1s.
        # But we can verify it doesn't discard immediately.
        
    def test_config_loader_global(self):
        """Verify config loader parses global async settings."""
        config_path = os.path.join(self.test_dir, "logging.yaml")
        with open(config_path, 'w') as f:
            f.write("""
configuration:
  status: info
  async_queue:
    size: 5000
    full_policy: Block
  appenders:
    console:
      type: Console
      json_layout:
        masked_keys: ["token"]
  loggers:
    root:
      level: info
      appender_refs: [{ref: console}]
""")
        
        LogManager.load_config(config_path)
        
        # Check Queue Config
        q = LogManager._get_async_queue()
        self.assertEqual(q.queue.maxsize, 5000)
        self.assertEqual(q.full_policy, "Block")
        
        # Check Formatter Config
        root = LogManager.get_logger("root")
        appender = root.config.appenders[0]
        self.assertIn("token", appender.formatter.masked_keys)

if __name__ == "__main__":
    unittest.main()
