import os
import time
import shutil
import gzip
import re
from datetime import datetime
from threading import RLock
from typing import Optional, Literal
from .base import Appender
from pylog.formatters.base import Formatter
from pylog.core.log_event import LogEvent

try:
    import portalocker
except ImportError:
    portalocker = None

def parse_size(size_str: str) -> int:
    """Parse size string like '10 MB' to bytes."""
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    size_str = size_str.upper().strip()
    match = re.match(r"^(\d+(?:\.\d+)?)\s*([KMGT]?B)$", size_str)
    if not match:
        try:
            return int(size_str)
        except ValueError:
            raise ValueError(f"Invalid size format: {size_str}")
    
    number, unit = match.groups()
    return int(float(number) * units[unit])

class TriggeringPolicy:
    def is_triggered(self, appender) -> bool:
        raise NotImplementedError

class SizeBasedTriggeringPolicy(TriggeringPolicy):
    def __init__(self, max_size: int):
        self.max_size = max_size

    def is_triggered(self, appender) -> bool:
        if not appender.file_path or not os.path.exists(appender.file_path):
            return False
        return os.path.getsize(appender.file_path) >= self.max_size

class TimeBasedTriggeringPolicy(TriggeringPolicy):
    def __init__(self, interval: int = 1, modulus: int = 1):
        self.interval = interval # In days, assuming daily rolling for now based on pattern
        self.modulus = modulus
        self._next_rollover_time = 0
        self._started = False

    def is_triggered(self, appender) -> bool:
        if not self._started:
            self._initialize(appender)
        
        return time.time() >= self._next_rollover_time

    def _initialize(self, appender):
        # Determine next rollover time based on file modification time or current time
        # Simplified: Roll at next midnight or interval
        # For this implementation, let's assume daily rolling if pattern contains date
        now = time.time()
        # Align to next interval boundary (e.g. next midnight)
        # This is a simplification. Real implementation parses the pattern.
        # Assuming Daily:
        current_day_start = now - (now % 86400)
        self._next_rollover_time = current_day_start + 86400 * self.interval
        self._started = True
        
    def update(self):
        # Called after rollover
        self._next_rollover_time += 86400 * self.interval

class RolloverStrategy:
    def rollover(self, appender):
        raise NotImplementedError

class DefaultRolloverStrategy(RolloverStrategy):
    def __init__(self, max_files: int, file_pattern: str):
        self.max_files = max_files
        self.file_pattern = file_pattern # e.g. logs/app-%d{yyyy-MM-dd}.log.gz

    def rollover(self, appender):
        """
        Rollover the file.
        1. Close current file.
        2. Rename/Compress current file to pattern.
        3. Delete old files if max_files exceeded.
        4. Re-open current file.
        """
        appender.close_file()
        
        # Generate target filename
        # Replace %d{...} with timestamp
        # Simple regex for %d{...}
        pattern = self.file_pattern
        date_match = re.search(r"%d\{([^}]+)\}", pattern)
        if date_match:
            date_fmt = date_match.group(1)
            # Convert Java/Log4j format to Python strftime
            # yyyy->%Y, MM->%m, dd->%d
            py_fmt = (date_fmt
                      .replace("yyyy", "%Y")
                      .replace("MM", "%m")
                      .replace("dd", "%d")
                      .replace("HH", "%H")
                      .replace("mm", "%M")
                      .replace("ss", "%S")
                      .replace("SSS", "%f"))
            # Use current time or file modification time?
            # Usually the time of the content.
            timestamp_str = datetime.now().strftime(py_fmt)
            target_path = pattern.replace(date_match.group(0), timestamp_str)
        else:
            # Fallback if no date pattern, maybe use index?
            target_path = f"{appender.file_path}.{int(time.time())}"

        # Check if compression needed
        compress = target_path.endswith(".gz")
        if compress:
            # Remove .gz for intermediate rename
            rename_target = target_path[:-3]
        else:
            rename_target = target_path
            
        # Rename current file
        if os.path.exists(appender.file_path):
            if os.path.exists(rename_target):
                # Conflict resolution: append counter?
                # For now, overwrite or simple counter
                i = 1
                while os.path.exists(f"{rename_target}.{i}"):
                    i += 1
                rename_target = f"{rename_target}.{i}"
                if compress:
                    target_path = f"{rename_target}.gz"

            shutil.move(appender.file_path, rename_target)
            
            # Compress if needed
            if compress:
                with open(rename_target, 'rb') as f_in:
                    with gzip.open(target_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(rename_target)
                
        # Cleanup old files (GC)
        # This requires listing files matching the pattern and sorting by time
        if self.max_files > 0:
            self._delete_old_files(os.path.dirname(appender.file_path) or ".", appender.file_name)

    def _delete_old_files(self, dir_path, base_name):
        """
        Deletes old log files exceeding max_files.
        Uses file_pattern to identify candidates more accurately.
        """
        try:
            # 1. Build Regex from file_pattern
            pattern_base = os.path.basename(self.file_pattern)
            
            # Placeholders for variable parts
            DATE_PH = "___DATE___"
            INDEX_PH = "___INDEX___"
            
            # Replace %d{...} -> placeholder
            temp_pattern = re.sub(r"%d\{[^}]+\}", DATE_PH, pattern_base)
            # Replace %i -> placeholder
            temp_pattern = temp_pattern.replace("%i", INDEX_PH)
            
            # Escape the fixed parts
            regex_str = re.escape(temp_pattern)
            
            # Replace placeholders with regex groups
            # Date can be anything non-separator ideally, but .*? is safe enough for filenames
            regex_str = regex_str.replace(DATE_PH, r".*?") 
            regex_str = regex_str.replace(INDEX_PH, r"\d+")
            
            # Anchor strictly
            regex_pattern = re.compile(f"^{regex_str}$")
            
            candidates = []
            
            if os.path.exists(dir_path):
                for f in os.listdir(dir_path):
                    full_path = os.path.join(dir_path, f)
                    if os.path.isfile(full_path):
                        # Don't delete the active file (even if it matches pattern by chance)
                        if os.path.abspath(full_path) == os.path.abspath(os.path.join(dir_path, base_name)):
                            continue
                            
                        if regex_pattern.match(f):
                            candidates.append(full_path)
            
            # Sort by modification time (oldest first)
            candidates.sort(key=os.path.getmtime)
            
            # Delete if more than max
            while len(candidates) > self.max_files:
                to_delete = candidates.pop(0)
                try:
                    os.remove(to_delete)
                    # print(f"Deleted old log file: {to_delete}")
                except OSError as e:
                    print(f"Error deleting old file {to_delete}: {e}")
                    
        except Exception as e:
            print(f"Error during file retention cleanup: {e}")

class RollingFileAppender(Appender):
    def __init__(self, 
                 name: str, 
                 formatter: Formatter, 
                 file_name: str, 
                 file_pattern: str,
                 policies: list, 
                 strategy: RolloverStrategy,
                 use_multiprocess_lock: bool = False,
                 immediate_flush: bool = True):
        super().__init__(name, formatter)
        self.file_name = file_name
        self.file_path = os.path.abspath(file_name)
        self.policies = policies
        self.strategy = strategy
        self._file = None
        self._lock = RLock()
        self.use_multiprocess_lock = use_multiprocess_lock and (portalocker is not None)
        self.immediate_flush = immediate_flush
        
        # Ensure dir exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def start(self):
        super().start()
        self._open_file()

    def stop(self):
        with self._lock:
            self.close_file()
        super().stop()

    def _open_file(self):
        if self._file is None:
            self._file = open(self.file_path, 'a', encoding='utf-8')

    def close_file(self):
        if self._file:
            self._file.flush()
            self._file.close()
            self._file = None

    def append(self, event: LogEvent):
        if self.use_multiprocess_lock:
            lock_path = self.file_path + ".lock"
            try:
                # Use a separate lock file for coordination
                with portalocker.Lock(lock_path, timeout=10):
                    with self._lock:
                        self._inner_append(event)
            except Exception as e:
                # Fallback or error logging
                # If lock fails (timeout), we might lose log or just print to stderr
                print(f"PyLog: Failed to acquire lock for {self.file_path}: {e}")
        else:
            with self._lock:
                self._inner_append(event)

    def flush(self):
        if self._file:
            self._file.flush()

    def _inner_append(self, event: LogEvent):
        output = self.formatter.format(event)
        if isinstance(output, bytes):
            output = output.decode('utf-8')
        self.write_raw(output)

    def write_raw(self, content: str):
        # Check policies
        triggered = False
        for policy in self.policies:
            if policy.is_triggered(self):
                triggered = True
                # Some policies might need state update
                if isinstance(policy, TimeBasedTriggeringPolicy):
                    policy.update()
        
        if triggered:
            try:
                self.strategy.rollover(self)
            except Exception as e:
                print(f"PyLog: Rollover failed: {e}")
            self._open_file()
        
        if self._file is None:
            self._open_file()
            
        self._file.write(content)
        if self.immediate_flush:
            self._file.flush()

