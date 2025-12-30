import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from log_framework.logger_setup import LogManager
from log_framework import Slf4j

# 🟢 1. 告诉框架使用我们的配置文件
# 注意：这行代码通常放在程序的最开始
config_path = os.path.join(os.path.dirname(__file__), 'logging.yaml')
LogManager.load_config(config_path)

@Slf4j
class ConfigDemo:
    def run(self):

        self.logger.info("这条日志使用了 logging.yaml 的配置！")
        self.logger.info("你看控制台是简单格式，但文件里是 JSON 格式哦。")
        self.logger.debug("这条 DEBUG 日志能不能看到，取决于 yaml 里的 level 设置。")

if __name__ == "__main__":
    app = ConfigDemo()
    app.run()
    time.sleep(0.1)
