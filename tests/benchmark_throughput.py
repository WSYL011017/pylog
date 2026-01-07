import time
import threading
import logging
import os
import shutil
import tempfile
from pylog.core.logger import Logger, LoggerConfig
from pylog.core.async_queue import AsyncQueueHandler
from pylog.appenders.rolling_file import RollingFileAppender, DefaultRolloverStrategy, SizeBasedTriggeringPolicy
from pylog.formatters.json_formatter import JSONFormatter

def run_benchmark():
    print("=== PyLog Throughput Benchmark (Baseline) ===")
    
    # Setup
    tmp_dir = tempfile.mkdtemp()
    log_file = os.path.join(tmp_dir, "bench.log")
    
    # Components
    formatter = JSONFormatter(compact=True)
    strategy = DefaultRolloverStrategy(max_files=5, file_pattern=os.path.join(tmp_dir, "bench-%i.log"))
    policy = SizeBasedTriggeringPolicy(max_size=10*1024*1024) # 10MB
    
    appender = RollingFileAppender("BenchAppender", formatter, log_file, "bench-%i.log", [policy], strategy)
    appender.start()
    
    # Async Queue
    queue = AsyncQueueHandler(queue_size=10000, full_policy="Block")
    queue.start()
    
    # Logger
    config = LoggerConfig("bench", logging.INFO)
    config.add_appender(appender)
    logger = Logger("bench", config, async_queue=queue)
    
    # Parameters
    NUM_THREADS = 4
    LOGS_PER_THREAD = 25000
    TOTAL_LOGS = NUM_THREADS * LOGS_PER_THREAD
    msg = "Benchmark log message payload " + ("x" * 50) # ~100 bytes payload
    
    print(f"Configuration: {NUM_THREADS} threads, {TOTAL_LOGS} total logs, AsyncQueue=Block")
    
    def worker():
        for _ in range(LOGS_PER_THREAD):
            logger.info(msg)
            
    threads = []
    start_time = time.time()
    
    for _ in range(NUM_THREADS):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    # Wait for queue to drain
    queue.stop() # This triggers drain
    
    end_time = time.time()
    duration = end_time - start_time
    ops = TOTAL_LOGS / duration
    
    print(f"\nResults:")
    print(f"Total Time: {duration:.4f} seconds")
    print(f"Throughput: {ops:.2f} logs/sec")
    
    # Cleanup
    appender.stop()
    try:
        shutil.rmtree(tmp_dir)
    except:
        pass
    
    return ops

if __name__ == "__main__":
    run_benchmark()
