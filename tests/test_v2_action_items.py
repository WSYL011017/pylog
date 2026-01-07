import unittest
import logging
import json
import tempfile
import os
import shutil
from pylog.formatters.json_formatter import JSONFormatter
from pylog.core.log_event import LogEvent
from pylog.infra.config_loader import ConfigLoader
from pylog.core.logger import LoggerConfig

class TestV2ActionItems(unittest.TestCase):
    
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    # --- Must Have #3: Sensitive Field Protection ---
    def test_json_formatter_masking(self):
        """
        验证 JSONFormatter 字段掩码功能。
        验收标准: 示例包含密码/Token掩码生效。
        """
        # Configure formatter with masked keys
        masked_keys = ["password", "token", "secret"]
        formatter = JSONFormatter(compact=True, masked_keys=masked_keys)
        
        # Create an event with sensitive data in 'extra'
        extra = {
            "user": "alice",
            "password": "super_secret_password",
            "token": "abcdef123456",
            "nested": {
                "secret": "hide_me",
                "public": "show_me"
            }
        }
        event = LogEvent("test_logger", logging.INFO, "Login attempt", (), None, {}, extra, None)
        
        # Format
        output_bytes = formatter.format(event)
        output_str = output_bytes.decode('utf-8')
        output_json = json.loads(output_str)
        
        # Verify
        self.assertEqual(output_json.get("password"), "***")
        self.assertEqual(output_json.get("token"), "***")
        self.assertEqual(output_json.get("user"), "alice")
        
        # Verify nested masking (current implementation supports recursive dict masking)
        self.assertEqual(output_json.get("nested", {}).get("secret"), "***")
        self.assertEqual(output_json.get("nested", {}).get("public"), "show_me")
        
        print("\n[Pass] Sensitive Field Protection: Verified password/token masking.")

    # --- Must Have #4: Log Level Robustness ---
    def test_config_loader_level_robustness(self):
        """
        验证日志级别解析显式映射与容错。
        验收标准: 配置注入异常值时系统稳定，回退到 INFO。
        """
        loader = ConfigLoader()
        
        # Test Case 1: Valid Levels (Standard)
        self.assertEqual(loader._parse_level("DEBUG"), logging.DEBUG)
        self.assertEqual(loader._parse_level("ERROR"), logging.ERROR)
        
        # Test Case 2: Lowercase (should work if robust, implementation uses .upper())
        self.assertEqual(loader._parse_level("warn"), logging.WARN)
        
        # Test Case 3: Invalid Level -> Fallback to INFO
        # We expect a print warning, but return value should be INFO (20)
        level = loader._parse_level("UNKNOWN_SUPER_LEVEL")
        self.assertEqual(level, logging.INFO)
        
        # Test Case 4: Empty -> INFO
        self.assertEqual(loader._parse_level(""), logging.INFO)
        
        # Test Case 5: None -> INFO
        self.assertEqual(loader._parse_level(None), logging.INFO)
        
        print("\n[Pass] Log Level Robustness: Verified fallback to INFO for invalid levels.")

    # --- Verification of Previous Must Haves (Summary) ---
    def test_verify_retention_completeness(self):
        """
        验证滚动保留策略 (Must Have #1) - 简单确认类存在且可实例化
        详细测试在 test_v2_rolling_retention.py
        """
        from pylog.appenders.rolling_file import DefaultRolloverStrategy
        strategy = DefaultRolloverStrategy(max_files=5, file_pattern="test-%d.log")
        self.assertEqual(strategy.max_files, 5)
        # Assuming previous tests passed, this confirms the component is available.

    def test_verify_backpressure_completeness(self):
        """
        验证异步背压 (Must Have #2) - 简单确认参数
        详细测试在 test_v2_async_policy.py
        """
        from pylog.core.async_queue import AsyncQueueHandler
        queue = AsyncQueueHandler(full_policy="DiscardLowLevel")
        self.assertEqual(queue.full_policy, "DiscardLowLevel")

if __name__ == '__main__':
    unittest.main()
