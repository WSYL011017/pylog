"""
log_framework
~~~~~~~~~~~~~

A production-ready asynchronous logging framework for Python.

:copyright: (c) 2025
:license: MIT
"""

__version__ = "1.0.0"

from .logger_setup import (
    LogManager, 
    Slf4j, 
    MDC, 
    JSONFormatter, 
    ContextFilter, 
    HiddenTimedRotatingFileHandler
)
from .metrics import LogMetrics

__all__ = [
    "LogManager",
    "Slf4j",
    "MDC",
    "JSONFormatter",
    "ContextFilter",
    "HiddenTimedRotatingFileHandler",
    "LogMetrics",
    "__version__"
]

# 自动初始化日志框架
# 这样用户在使用时无需手动调用 LogManager.load_config()
LogManager.load_config()
