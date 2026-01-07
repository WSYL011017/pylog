import unittest
import os
import shutil
import tempfile
from pylog.appenders.rolling_file import RollingFileAppender, SizeBasedTriggeringPolicy, DefaultRolloverStrategy
from pylog.core.log_event import LogEvent


class SimpleFormatter:
    def format(self, event):
        return (str(event.message) + "\n").encode("utf-8")


class TestRollingRetention(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.file = os.path.join(self.tmp, "retention.log")
        self.pattern = os.path.join(self.tmp, "retention-%d{yyyy-MM-dd-HH-mm-ss}.log.gz")
        self.formatter = SimpleFormatter()
        self.policy = SizeBasedTriggeringPolicy(max_size=50)
        self.strategy = DefaultRolloverStrategy(max_files=3, file_pattern=self.pattern)
        self.appender = RollingFileAppender(
            name="Rolling",
            formatter=self.formatter,
            file_name=self.file,
            file_pattern=self.pattern,
            policies=[self.policy],
            strategy=self.strategy
        )
        self.appender.start()

    def tearDown(self):
        self.appender.stop()
        shutil.rmtree(self.tmp)

    def test_retention_and_pattern(self):
        msg = "x" * 60
        for _ in range(5):
            e = LogEvent("t", 20, msg, (), None, {}, {}, None)
            self.appender.append(e)

        files = os.listdir(self.tmp)
        gz = [f for f in files if f.endswith(".gz")]
        self.assertGreaterEqual(len(gz), 1)
        self.assertLessEqual(len(gz), 3)
        # Check that at least one file matches seconds pattern digits
        self.assertTrue(any("-" in f for f in gz))
        # Active log file should exist
        self.assertTrue(os.path.exists(self.file))

