import unittest
import os
import shutil
import time
import tempfile
import gzip
from pylog.appenders.rolling_file import RollingFileAppender, SizeBasedTriggeringPolicy, DefaultRolloverStrategy
from pylog.appenders.failover import FailoverAppender
from pylog.core.log_event import LogEvent
from pylog.formatters.json_formatter import JSONFormatter

class MockFormatter:
    def format(self, event):
        return str(event.message) + "\n"

class TestRollingFileAppender(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.test_dir, "test.log")
        self.file_pattern = os.path.join(self.test_dir, "test-%d{yyyy-MM-dd-HH-mm-ss}.log.gz")
        
        # 1KB size limit
        self.policy = SizeBasedTriggeringPolicy(max_size=100) 
        self.strategy = DefaultRolloverStrategy(max_files=5, file_pattern=self.file_pattern)
        self.formatter = MockFormatter()
        
        self.appender = RollingFileAppender(
            name="RollingFile",
            formatter=self.formatter,
            file_name=self.log_file,
            file_pattern=self.file_pattern,
            policies=[self.policy],
            strategy=self.strategy
        )
        self.appender.start()

    def tearDown(self):
        self.appender.stop()
        shutil.rmtree(self.test_dir)

    def test_rolling(self):
        # Write enough data to trigger rollover
        # Max size is 100 bytes. 
        msg = "x" * 50
        event = LogEvent("logger", 20, msg, (), None, {}, {}, None)
        
        # 1st write: 51 bytes (50 chars + newline)
        self.appender.append(event)
        self.assertTrue(os.path.exists(self.log_file))
        
        # 2nd write: 102 bytes -> Trigger? 
        # Trigger checks BEFORE write usually? Or AFTER?
        # Looking at code: policy.is_triggered(self) is checked.
        # SizeBased checks os.path.getsize(appender.file_path) >= max_size.
        # So after 1st write, size is 51. 51 < 100. No trigger.
        self.appender.append(event)
        
        # Now size is 102.
        # 3rd write -> Check trigger -> 102 >= 100 -> True -> Rollover
        self.appender.append(event)
        
        # After rollover:
        # 1. test.log should be empty (re-opened) or contain the 3rd message
        # 2. There should be a .gz file
        
        files = os.listdir(self.test_dir)
        gz_files = [f for f in files if f.endswith(".gz")]
        self.assertEqual(len(gz_files), 1)
        
        # Check current log file size (should be 3rd message size approx 51 bytes)
        self.assertLess(os.path.getsize(self.log_file), 100)

class FailingAppender:
    def __init__(self, name="Failing"):
        self.name = name
        self.formatter = MockFormatter()
        self.fail = True
        self.events = []

    def start(self): pass
    def stop(self): pass
    
    def append(self, event):
        if self.fail:
            raise RuntimeError("Failed")
        self.events.append(event)

class SuccessAppender:
    def __init__(self, name="Success"):
        self.name = name
        self.formatter = MockFormatter()
        self.events = []

    def start(self): pass
    def stop(self): pass
    
    def append(self, event):
        self.events.append(event)

class TestFailoverAppender(unittest.TestCase):
    def test_failover(self):
        primary = FailingAppender("Primary")
        backup = SuccessAppender("Backup")
        
        failover = FailoverAppender("Failover", primary, [backup], retry_interval=1)
        failover.start()
        
        event = LogEvent("logger", 20, "test", (), None, {}, {}, None)
        
        # 1. Primary fails, should go to backup
        failover.append(event)
        self.assertEqual(len(backup.events), 1)
        self.assertEqual(len(primary.events), 0)
        
        # 2. Immediate retry, Primary still inactive (interval not passed)
        # Should go directly to backup without calling primary.append
        failover.append(event)
        self.assertEqual(len(backup.events), 2)
        
        # 3. Wait for interval
        time.sleep(1.1)
        
        # 4. Primary recovers
        primary.fail = False
        failover.append(event)
        self.assertEqual(len(primary.events), 1)
        # Backup count should remain 2
        self.assertEqual(len(backup.events), 2)

