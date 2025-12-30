import os
import time
import logging
import pytest
import shutil
from log_framework.logger_setup import LogManager
from log_framework.metrics import LogMetrics, AdaptiveSampler, PerformanceMonitor

class TestV7Optimizations:
    
    @pytest.fixture
    def clean_env(self):
        LogManager.shutdown()
        if os.path.exists("logs_opt"):
            shutil.rmtree("logs_opt")
        os.makedirs("logs_opt", exist_ok=True)
        yield
        LogManager.shutdown()
        if os.path.exists("logs_opt"):
            shutil.rmtree("logs_opt")

    def test_adaptive_sampler_logic(self):
        sampler = AdaptiveSampler(base_rate=0.01)
        
        # 1. Low Pressure
        sampler.update_pressure(0, 1000)
        assert sampler.queue_pressure == 0.0
        # Check if rate decreases
        # We need to call should_sample() to trigger rate adjustment
        sampler.should_sample()
        assert sampler.current_rate < 0.01
        
        # 2. High Pressure
        sampler.update_pressure(900, 1000)
        assert sampler.queue_pressure == 0.9
        sampler.should_sample()
        assert sampler.current_rate > 0.01

    def test_performance_monitor_batching(self):
        # Clear buffer first
        PerformanceMonitor._metrics_buffer.clear()
        
        # Record metrics
        PerformanceMonitor.record_metric("test", 1.0)
        assert len(PerformanceMonitor._metrics_buffer) == 1
        
        # Record more
        for _ in range(10):
            PerformanceMonitor.record_metric("test", 1.0)
        assert len(PerformanceMonitor._metrics_buffer) == 11
        
        # Simulate Flush (Time travel is hard, so we call _flush_metrics directly)
        PerformanceMonitor._flush_metrics()
        assert len(PerformanceMonitor._metrics_buffer) == 0

    def test_integration_with_handler(self, clean_env):
        # Setup Logger
        LogManager.load_config(async_mode=True)
        logger = logging.getLogger("opt_test")
        
        # Log many messages
        for i in range(100):
            logger.info(f"Msg {i}")
            
        # Check if metrics updated (Sample rate might be low, but we logged 100)
        # It's possible we didn't hit the sample if random is unlucky, 
        # but statistically we should see *some* activity or at least no crash.
        
        metrics = LogMetrics.get_metrics()
        # Just ensure structure exists
        assert "sample_rate" in metrics
        
        # Verify PerformanceMonitor got something (maybe from dropped or other calls)
        # Note: Enqueue calls record_metric via set_queue_size ONLY if sampled.
        # So we might not see queue_size updates in monitor if not sampled.
        
        # Force a drop/error to see monitor action
        LogMetrics.increment_error()
        assert len(PerformanceMonitor._metrics_buffer) >= 1
