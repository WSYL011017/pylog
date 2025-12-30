import pytest
import logging
import json
import os
import shutil
from unittest.mock import MagicMock, patch
from log_framework.logger_setup import LogManager, _deep_merge, JSONFormatter, MDC

@pytest.fixture
def clean_env():
    # Reset singleton
    LogManager._initialized = False
    LogManager.shutdown()
    yield
    LogManager.shutdown()

def test_deep_merge():
    """Test deep dictionary merging logic."""
    base = {"a": 1, "b": {"c": 2}}
    override = {"b": {"d": 3}, "e": 4}
    merged = _deep_merge(base, override)
    
    assert merged["a"] == 1
    assert merged["b"]["c"] == 2
    assert merged["b"]["d"] == 3
    assert merged["e"] == 4

def test_deep_merge_none():
    """Test deep merge with None values."""
    base = {"a": 1}
    assert _deep_merge(base, None) == base
    assert _deep_merge(None, base) == base

def test_json_formatter():
    """Test JSON formatter output structure."""
    formatter = JSONFormatter()
    record = logging.LogRecord("test_logger", logging.INFO, "test.py", 10, "Hello World", (), None)
    
    # Test with MDC
    MDC.clear()
    MDC.put("req_id", "123")
    
    # Simulate record_factory logic if needed, or rely on formatter reading MDC directly
    # The formatter reads getattr(record, "mdc_context") OR MDC.getAll()
    
    json_str = formatter.format(record)
    data = json.loads(json_str)
    
    assert data["message"] == "Hello World"
    assert data["level"] == "INFO"
    assert data["context"]["req_id"] == "123"
    assert "hostname" in data
    
    MDC.clear()

@patch("log_framework.logger_setup.logging.config.dictConfig")
def test_log_manager_init(mock_dict_config, clean_env):
    """Test LogManager initialization."""
    LogManager.load_config(user_config_path=None, async_mode=False)
    
    assert mock_dict_config.called
    assert LogManager._initialized

def test_ensure_log_dirs(tmpdir):
    """Test automatic log directory creation."""
    config = {
        "handlers": {
            "file": {
                "filename": str(tmpdir.join("subdir/test.log"))
            }
        }
    }
    LogManager._ensure_log_dirs(config)
    assert os.path.exists(str(tmpdir.join("subdir")))
