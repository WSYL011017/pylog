import sys
import os
import time

# 🟢 0. 魔法设置 (这一步是为了让你直接运行这个脚本，实际项目中不需要)
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# 🟢 1. 导入你需要的工具
from log_framework import Slf4j

# 🟢 2. 给你的类加上 @Slf4j 装饰器
@Slf4j
class HelloWorld:
    def run(self):
        # 🟢 3. 直接使用 self.logger 打印日志！
        # 就像 print() 一样简单，但更强大
        self.logger.info("你好，世界！这是我的第一条日志。")
        self.logger.warning("注意：这是一个警告消息。")
        self.logger.error("哎呀：出错了！(别担心，这是测试)")
        
        # 也可以打印变量
        user_name = "小白"
        self.logger.info(f"欢迎你，{user_name}！")

if __name__ == "__main__":
    app = HelloWorld()
    app.run()
    
    # 给日志一点时间写入文件 (因为是异步的)
    time.sleep(0.1)
