import unittest
import time
from pylog.appenders.failover import FailoverAppender
from pylog.core.log_event import LogEvent
from pylog.core.metrics import MetricsRegistry


class FailingAppender:
    def __init__(self, name="Primary"):
        self.name = name
        self.formatter = type("F", (), {"format": lambda self, e: str(e.message) + "\n"})()
        self.fail = True
        self.events = []

    def start(self):
        pass

    def stop(self):
        pass

    def append(self, event):
        if self.fail:
            raise RuntimeError("fail")
        self.events.append(event)


class SuccessAppender:
    def __init__(self, name="Backup"):
        self.name = name
        self.formatter = type("F", (), {"format": lambda self, e: str(e.message) + "\n"})()
        self.events = []

    def start(self):
        pass

    def stop(self):
        pass

    def append(self, event):
        self.events.append(event)


class TestFailoverMetrics(unittest.TestCase):
    def setUp(self):
        self.metrics = MetricsRegistry()
        self.metrics.reset()

    def test_switch_and_all_failed_metrics_and_callback(self):
        primary = FailingAppender("Primary")
        backup = SuccessAppender("Backup")
        callbacks = {"called": False, "msg": None}

        def on_switch(msg):
            callbacks["called"] = True
            callbacks["msg"] = msg

        app = FailoverAppender("Failover", primary, [backup], retry_interval=1, on_switch=on_switch)
        app.start()

        try:
            e = LogEvent("t", 20, "m1", (), None, {}, {}, None)
            app.append(e)

            m = self.metrics.get_metrics()
            self.assertEqual(m.get("pylog_failover_switch_total", 0), 1)
            self.assertTrue(callbacks["called"])

            # Make backup fail too, then append
            def failing_append(event):
                raise RuntimeError("backup fail")
            backup.append = failing_append

            app.append(LogEvent("t", 20, "m2", (), None, {}, {}, None))
            m = self.metrics.get_metrics()
            self.assertEqual(m.get("pylog_failover_all_failed_total", 0), 1)

            # Wait retry interval, recover primary
            time.sleep(1.1)
            primary.fail = False
            app.append(LogEvent("t", 20, "m3", (), None, {}, {}, None))
            self.assertEqual(len(primary.events), 1)
        finally:
            app.stop()

