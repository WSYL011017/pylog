import unittest
import os
import tempfile
import time
import shutil
from pylog.manager import LogManager

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.test_dir, "app.log")
        self.config_file = os.path.join(self.test_dir, "logging.yaml")
        
        config_content = f"""
configuration:
  status: info
  appenders:
    file:
      type: RollingFile
      fileName: "{self.log_file.replace(os.sep, '/')}"
      filePattern: "{self.log_file.replace(os.sep, '/')}.%d{{yyyy-MM-dd}}"
      policies:
        size_based:
          size: "1 MB"
      strategy:
        max: 5
  loggers:
    root:
      level: info
      appender_refs:
        - ref: file
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)
            
        LogManager.load_config(self.config_file)

    def tearDown(self):
        LogManager.shutdown()
        shutil.rmtree(self.test_dir)

    def test_full_flow(self):
        logger = LogManager.get_logger("test.integration")
        logger.info("Integration Test Message")
        
        # Give async queue time to write
        time.sleep(0.5)
        
        self.assertTrue(os.path.exists(self.log_file))
        with open(self.log_file, 'r') as f:
            content = f.read()
            self.assertIn("Integration Test Message", content)
            self.assertIn('"message":"Integration Test Message"', content) # JSON check

