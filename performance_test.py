#!/usr/bin/env python3
"""
Log Framework V7 High Performance Mode Benchmark Test
"""

import time
import threading
import logging
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from log_framework import LogManager, MDC
from log_framework.metrics import LogMetrics, PerformanceMonitor, AdaptiveSampler

class PerformanceBenchmark:
    def __init__(self, duration_seconds=10, thread_counts=None):
        self.duration = duration_seconds
        self.thread_counts = thread_counts or [1, 5, 10, 20, 50]
        self.results = {}
        
    def setup_logging(self, async_mode=True):
        """Initialize logging framework"""
        LogManager.load_config(async_mode=async_mode)
        return logging.getLogger("benchmark")
    
    def single_threaded_test(self, logger, num_messages=100000):
        """Single threaded performance test"""
        start_time = time.time()
        
        for i in range(num_messages):
            MDC.put("request_id", f"req-{i}")
            MDC.put("user_id", f"user-{i % 1000}")
            logger.info(f"Benchmark message {i}")
            
        end_time = time.time()
        
        MDC.clear()
        
        duration = end_time - start_time
        throughput = num_messages / duration
        
        return {
            "messages": num_messages,
            "duration": duration,
            "throughput": throughput,
            "latency_ms": (duration / num_messages) * 1000
        }
    
    def multi_threaded_test(self, logger, num_threads, messages_per_thread=10000):
        """Multi-threaded performance test"""
        
        def worker(thread_id):
            local_results = []
            start_time = time.time()
            
            for i in range(messages_per_thread):
                MDC.put("thread_id", str(thread_id))
                MDC.put("request_id", f"req-{thread_id}-{i}")
                logger.info(f"Thread {thread_id} message {i}")
                
            end_time = time.time()
            MDC.clear()
            
            return {
                "thread_id": thread_id,
                "duration": end_time - start_time,
                "messages": messages_per_thread
            }
        
        # Run workers
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            
            thread_results = []
            for future in as_completed(futures):
                thread_results.append(future.result())
        
        end_time = time.time()
        
        total_messages = num_threads * messages_per_thread
        total_duration = end_time - start_time
        throughput = total_messages / total_duration
        
        # Calculate per-thread statistics
        thread_durations = [r["duration"] for r in thread_results]
        avg_thread_duration = statistics.mean(thread_durations)
        max_thread_duration = max(thread_durations)
        
        return {
            "threads": num_threads,
            "total_messages": total_messages,
            "total_duration": total_duration,
            "throughput": throughput,
            "avg_thread_duration": avg_thread_duration,
            "max_thread_duration": max_thread_duration,
            "latency_ms": (total_duration / total_messages) * 1000,
            "thread_results": thread_results
        }
    
    def adaptive_sampling_test(self, logger, burst_size=50000):
        """Test adaptive sampling under load"""
        print("\n=== Adaptive Sampling Test ===")
        
        # Normal load
        print("Phase 1: Normal load (10K messages)")
        normal_start = time.time()
        for i in range(10000):
            logger.info(f"Normal load message {i}")
        normal_duration = time.time() - normal_start
        
        metrics_before = LogMetrics.get_metrics()
        print(f"Metrics before burst: {metrics_before}")
        
        # High load burst
        print(f"Phase 2: High load burst ({burst_size} messages)")
        burst_start = time.time()
        
        # Create multiple threads to simulate burst
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for thread_id in range(10):
                future = executor.submit(
                    self._burst_worker, logger, thread_id, burst_size // 10
                )
                futures.append(future)
            
            for future in as_completed(futures):
                future.result()
        
        burst_duration = time.time() - burst_start
        
        metrics_after = LogMetrics.get_metrics()
        print(f"Metrics after burst: {metrics_after}")
        
        # Calculate adaptive behavior
        dropped_during_burst = metrics_after["dropped_total"] - metrics_before["dropped_total"]
        sampling_rate_change = metrics_after["sample_rate"] - metrics_before["sample_rate"]
        
        return {
            "normal_duration": normal_duration,
            "burst_duration": burst_duration,
            "dropped_during_burst": dropped_during_burst,
            "sampling_rate_change": sampling_rate_change,
            "metrics_before": metrics_before,
            "metrics_after": metrics_after
        }
    
    def _burst_worker(self, logger, thread_id, message_count):
        """Worker for burst testing"""
        for i in range(message_count):
            MDC.put("thread_id", str(thread_id))
            MDC.put("burst_seq", str(i))
            logger.info(f"Burst message from thread {thread_id} seq {i}")
        MDC.clear()
    
    def memory_monitoring_test(self, logger, duration_seconds=30):
        """Monitor memory usage over time"""
        print(f"\n=== Memory Monitoring Test ({duration_seconds}s) ===")
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_samples = []
        
        start_time = time.time()
        message_count = 0
        
        while time.time() - start_time < duration_seconds:
            # Log messages
            for i in range(1000):
                logger.info(f"Memory test message {message_count + i}")
            
            message_count += 1000
            
            # Sample memory
            memory_info = process.memory_info()
            memory_samples.append({
                "time": time.time() - start_time,
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024
            })
            
            # Small delay
            time.sleep(0.1)
        
        # Calculate memory statistics
        rss_values = [sample["rss_mb"] for sample in memory_samples]
        vms_values = [sample["vms_mb"] for sample in memory_samples]
        
        return {
            "duration": duration_seconds,
            "total_messages": message_count,
            "memory_samples": memory_samples,
            "avg_rss_mb": statistics.mean(rss_values),
            "max_rss_mb": max(rss_values),
            "avg_vms_mb": statistics.mean(vms_values),
            "max_vms_mb": max(vms_values)
        }
    
    def run_all_tests(self):
        """Run complete benchmark suite"""
        print("🚀 Log Framework V7 Performance Benchmark")
        print("=" * 50)
        
        # Setup
        logger = self.setup_logging(async_mode=True)
        
        # 1. Single threaded test
        print("\n📊 Single Threaded Performance Test")
        single_result = self.single_threaded_test(logger)
        self.print_single_results(single_result)
        
        # 2. Multi-threaded tests
        print("\n📊 Multi-threaded Performance Test")
        multi_results = []
        for num_threads in self.thread_counts:
            print(f"\nTesting with {num_threads} threads...")
            result = self.multi_threaded_test(logger, num_threads)
            multi_results.append(result)
            self.print_multi_results(result)
        
        # 3. Adaptive sampling test
        print("\n🎯 Adaptive Sampling Test")
        adaptive_result = self.adaptive_sampling_test(logger)
        self.print_adaptive_results(adaptive_result)
        
        # 4. Memory monitoring (optional)
        try:
            print("\n💾 Memory Monitoring Test")
            memory_result = self.memory_monitoring_test(logger, duration_seconds=10)
            self.print_memory_results(memory_result)
        except ImportError:
            print("psutil not available, skipping memory test")
            memory_result = None
        
        # Final metrics
        final_metrics = LogMetrics.get_metrics()
        print(f"\n📈 Final Metrics: {final_metrics}")
        
        # Summary
        self.print_summary(single_result, multi_results, adaptive_result, memory_result)
        
        return {
            "single_threaded": single_result,
            "multi_threaded": multi_results,
            "adaptive_sampling": adaptive_result,
            "memory_monitoring": memory_result,
            "final_metrics": final_metrics
        }
    
    def print_single_results(self, result):
        print(f"  Messages: {result['messages']:,}")
        print(f"  Duration: {result['duration']:.3f}s")
        print(f"  Throughput: {result['throughput']:,.0f} msgs/sec")
        print(f"  Latency: {result['latency_ms']:.3f}ms per message")
    
    def print_multi_results(self, result):
        print(f"  Threads: {result['threads']}")
        print(f"  Total Messages: {result['total_messages']:,}")
        print(f"  Total Duration: {result['total_duration']:.3f}s")
        print(f"  Throughput: {result['throughput']:,.0f} msgs/sec")
        print(f"  Avg Thread Duration: {result['avg_thread_duration']:.3f}s")
        print(f"  Max Thread Duration: {result['max_thread_duration']:.3f}s")
        print(f"  Latency: {result['latency_ms']:.3f}ms per message")
    
    def print_adaptive_results(self, result):
        print(f"  Normal Load Duration: {result['normal_duration']:.3f}s")
        print(f"  Burst Duration: {result['burst_duration']:.3f}s")
        print(f"  Dropped During Burst: {result['dropped_during_burst']}")
        print(f"  Sampling Rate Change: {result['sampling_rate_change']:.4f}")
        print(f"  Queue Size Before: {result['metrics_before']['queue_size']}")
        print(f"  Queue Size After: {result['metrics_after']['queue_size']}")
        print(f"  Final Sampling Rate: {result['metrics_after']['sample_rate']:.4f}")
    
    def print_memory_results(self, result):
        print(f"  Duration: {result['duration']}s")
        print(f"  Total Messages: {result['total_messages']:,}")
        print(f"  Avg RSS: {result['avg_rss_mb']:.1f}MB")
        print(f"  Max RSS: {result['max_rss_mb']:.1f}MB")
        print(f"  Avg VMS: {result['avg_vms_mb']:.1f}MB")
        print(f"  Max VMS: {result['max_vms_mb']:.1f}MB")
        print(f"  Memory per 1K messages: {(result['max_rss_mb'] / result['total_messages'] * 1000):.3f}MB")
    
    def print_summary(self, single, multi, adaptive, memory):
        print("\n" + "=" * 50)
        print("📋 PERFORMANCE SUMMARY")
        print("=" * 50)
        
        if single:
            print(f"🚀 Single-threaded: {single['throughput']:,.0f} msgs/sec")
        
        if multi:
            best_multi = max(multi, key=lambda x: x['throughput'])
            print(f"🚀 Multi-threaded (best): {best_multi['throughput']:,.0f} msgs/sec")
            print(f"🔧 Optimal thread count: {best_multi['threads']}")
        
        if adaptive:
            print(f"🎯 Adaptive Sampling: {adaptive['dropped_during_burst']} dropped during burst")
            print(f"📊 Final sampling rate: {adaptive['metrics_after']['sample_rate']:.2%}")
        
        if memory:
            print(f"💾 Memory efficiency: {memory['max_rss_mb']:.1f}MB max RSS")
        
        print("\n✅ All tests completed successfully!")


def main():
    """Main entry point"""
    benchmark = PerformanceBenchmark(
        duration_seconds=10,
        thread_counts=[1, 5, 10, 20]
    )
    
    results = benchmark.run_all_tests()
    
    # Optional: Save results to file
    import json
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to benchmark_results.json")


if __name__ == "__main__":
    main()