import contextvars
from contextlib import contextmanager
from typing import Dict, Any, Optional, Iterator
import functools

class ThreadContext:
    """
    Thread Context (similar to MDC in Log4j2) based on contextvars.
    Provides a way to store contextual data that is accessible to loggers.
    """
    _context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar("pylog_context", default={})

    @classmethod
    def put(cls, key: str, value: Any) -> None:
        """Add a value to the current context"""
        ctx = cls._context.get().copy()
        ctx[key] = value
        cls._context.set(ctx)

    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """Get a value from the current context"""
        return cls._context.get().get(key)

    @classmethod
    def remove(cls, key: str) -> None:
        """Remove a value from the current context"""
        ctx = cls._context.get().copy()
        if key in ctx:
            del ctx[key]
            cls._context.set(ctx)

    @classmethod
    def clear(cls) -> None:
        """Clear the current context"""
        cls._context.set({})

    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get a copy of the full context"""
        return cls._context.get().copy()

    @classmethod
    @contextmanager
    def scope(cls, **kwargs) -> Iterator[None]:
        """
        Context manager to set context values for a scope and restore them afterwards.
        
        Usage:
            with ThreadContext.scope(request_id="123"):
                logger.info("processing")
        """
        token = cls._context.set(cls._context.get().copy())
        try:
            current = cls._context.get()
            current.update(kwargs)
            yield
        finally:
            cls._context.reset(token)

    @classmethod
    def inject(cls, **kwargs):
        """
        Decorator to inject context values into a function call.
        Supports both sync and async functions.
        """
        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **func_kwargs):
                    with cls.scope(**kwargs):
                        return await func(*args, **func_kwargs)
                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **func_kwargs):
                    with cls.scope(**kwargs):
                        return func(*args, **func_kwargs)
                return sync_wrapper
        return decorator

import asyncio
