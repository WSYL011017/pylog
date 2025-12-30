import pytest
import logging
from log_framework.logger_setup import LogManager

def test_shutdown_cleanup():
    """Test that shutdown cleans up resources and resets state."""
    LogManager.load_config(user_config_path=None, async_mode=True)
    assert LogManager._initialized
    assert LogManager._queue_listener is not None
    assert LogManager._log_queue is not None
    
    LogManager.shutdown()
    
    assert not LogManager._initialized
    assert LogManager._queue_listener is None
    assert LogManager._log_queue is None
    
    # Verify double shutdown is safe
    try:
        LogManager.shutdown()
    except Exception as e:
        pytest.fail(f"Double shutdown raised exception: {e}")

def test_shutdown_concurrency():
    """Test concurrent shutdown calls."""
    import threading
    LogManager.load_config(user_config_path=None, async_mode=True)
    
    threads = [threading.Thread(target=LogManager.shutdown) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    assert not LogManager._initialized
