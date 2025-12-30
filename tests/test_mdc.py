import pytest
import threading
import contextvars
from log_framework import MDC
import time

def test_mdc_basic_operations():
    """Test basic MDC put, get, remove, clear operations."""
    MDC.clear()
    MDC.put("user", "alice")
    assert MDC.get("user") == "alice"
    assert MDC.getAll() == {"user": "alice"}
    
    MDC.remove("user")
    assert MDC.get("user") is None
    assert MDC.getAll() == {}

def test_mdc_thread_isolation():
    """Test that MDC context is isolated between threads."""
    MDC.clear()
    MDC.put("main", "thread")
    
    def worker():
        MDC.put("worker", "thread")
        assert MDC.get("worker") == "thread"
        # Context is NOT propagated to threads by default
        assert MDC.get("main") is None 
        
    t = threading.Thread(target=worker)
    t.start()
    t.join()
    
    # Main thread context should be unchanged
    assert MDC.get("main") == "thread"
    assert MDC.get("worker") is None

def test_mdc_async_support():
    """Test MDC context isolation in asyncio tasks."""
    import asyncio
    
    async def task(name, value):
        MDC.put(name, value)
        await asyncio.sleep(0.01)
        return MDC.get(name)
        
    async def main():
        MDC.clear()
        # Run two tasks concurrently
        t1 = asyncio.create_task(task("t1", "v1"))
        t2 = asyncio.create_task(task("t2", "v2"))
        
        r1 = await t1
        r2 = await t2
        
        assert r1 == "v1"
        assert r2 == "v2"
        # Main context should be empty
        assert MDC.getAll() == {}

    asyncio.run(main())
