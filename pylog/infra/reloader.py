import time
import os
from typing import List, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigChangeHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str], None], files: List[str]):
        self.callback = callback
        self.files = {os.path.abspath(f) for f in files}
        self._last_trigger = 0

    def on_modified(self, event):
        if event.is_directory:
            return
        
        abs_path = os.path.abspath(event.src_path)
        if abs_path in self.files:
            # Debounce
            current_time = time.time()
            if current_time - self._last_trigger < 1.0:
                return
            self._last_trigger = current_time
            
            print(f"Config file changed: {abs_path}. Reloading...")
            self.callback(abs_path)

class HotReloader:
    def __init__(self, callback: Callable[[], None], files: List[str]):
        self.callback = callback
        self.files = files
        self.observer = None

    def start(self):
        if not self.files:
            return

        self.observer = Observer()
        handler = ConfigChangeHandler(lambda x: self.callback(), self.files)
        
        # Watch directories of config files
        watched_dirs = set()
        for f in self.files:
            d = os.path.dirname(os.path.abspath(f))
            if d not in watched_dirs:
                self.observer.schedule(handler, d, recursive=False)
                watched_dirs.add(d)
        
        self.observer.start()

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
