import logging
import time
import os
import shutil
import sys

# Add project root to path
sys.path.append(os.getcwd())

from pylog.core.logger import Logger, LoggerConfig
from pylog.appenders.rolling_file import RollingFileAppender, DefaultRolloverStrategy, SizeBasedTriggeringPolicy
from pylog.appenders.buffering import BufferingAppender
from pylog.formatters.json_formatter import JSONFormatter

def benchmark(name, logger, count):
    print(f"Starting {name} benchmark with {count} messages...")
    start = time.time()
    for i in range(count):
        logger.info(f"Benchmark log message {i} with some data payload to simulate real logs. Payload size is about 100 bytes.")
    end = time.time()
    duration = end - start
    eps = count / duration
    print(f"Result: {duration:.4f}s => {eps:.2f} EPS")
    return eps

def setup_logger_sync(file_path):
    formatter = JSONFormatter()
    appender = RollingFileAppender(
        "file_sync", formatter, file_path, file_path + ".%i", 
        [SizeBasedTriggeringPolicy(10*1024*1024)], 
        DefaultRolloverStrategy(5, file_path + ".%i"),
        immediate_flush=True # V2.0 baseline behavior
    )
    appender.start()
    config = LoggerConfig("sync_logger", logging.INFO, False)
    config.add_appender(appender)
    return Logger("sync_logger", config)

def setup_logger_buffered(file_path):
    formatter = JSONFormatter()
    target = RollingFileAppender(
        "file_target", formatter, file_path, file_path + ".%i", 
        [SizeBasedTriggeringPolicy(10*1024*1024)], 
        DefaultRolloverStrategy(5, file_path + ".%i"),
        immediate_flush=False # Target should not flush
    )
    # Wrap with BufferingAppender
    appender = BufferingAppender(target, batch_size=1000, flush_interval=1.0)
    appender.start()
    
    config = LoggerConfig("buffered_logger", logging.INFO, False)
    config.add_appender(appender)
    return Logger("buffered_logger", config)

def main():
    bench_dir = "bench_logs"
    if os.path.exists(bench_dir):
        try:
            shutil.rmtree(bench_dir)
        except:
            pass
    os.makedirs(bench_dir, exist_ok=True)

    count = 20000
    
    print("=== PyLog V2.1 Benchmark ===")
    
    # 1. Sync File (Baseline)
    print("\n[Scenario 1: Sync File Write (Baseline)]")
    l1 = setup_logger_sync(os.path.join(bench_dir, "sync.log"))
    eps1 = benchmark("Sync", l1, count)
    for app in l1.config.appenders:
        app.stop()
    
    # 2. Buffered File (Target)
    print("\n[Scenario 2: Buffered File Write (Batch=1000)]")
    l2 = setup_logger_buffered(os.path.join(bench_dir, "buffered.log"))
    eps2 = benchmark("Buffered", l2, count)
    for app in l2.config.appenders:
        app.stop()

    print("\n=== Summary ===")
    print(f"Baseline: {eps1:.0f} EPS")
    print(f"Buffered: {eps2:.0f} EPS")
    print(f"Speedup:  {eps2/eps1:.2f}x")

if __name__ == "__main__":
    main()
