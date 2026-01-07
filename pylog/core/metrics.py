from typing import Dict
from threading import Lock

class MetricsRegistry:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._counters = {}
                cls._instance._gauges = {}
        return cls._instance

    def increment(self, name: str, value: int = 1):
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + value

    def gauge(self, name: str, value: int):
        with self._lock:
            self._gauges[name] = value

    def get_metrics(self) -> Dict[str, int]:
        with self._lock:
            return {**self._counters, **self._gauges}

    def reset(self):
        with self._lock:
            self._counters = {}
            self._gauges = {}
