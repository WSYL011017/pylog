import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from log_framework import Slf4j, MDC

@Slf4j
class UserService:
    def process_user(self, user_id):
        # 🟢 1. 设置上下文 (Context)
        # 比如：这是一个请求，请求ID是 123，用户是 user_id
        # 之后所有的日志都会自动带上这些信息！不用每行都写！
        MDC.put("req_id", "REQ-8888")
        MDC.put("user_id", user_id)
        
        try:
            self.logger.info("开始处理用户数据...")
            self.do_something_complex()
            self.logger.info("用户数据处理完成！")
            
        finally:
            # 🟢 2. 清理上下文
            # 处理完了，打扫干净，不影响下一个请求
            MDC.clear()

    def do_something_complex(self):
        # 注意：这里我没有传 user_id，但日志里依然会有！
        self.logger.debug("正在计算复杂的积分...")
        time.sleep(0.1)
        self.logger.warning("积分计算耗时有点长")

if __name__ == "__main__":
    service = UserService()
    service.process_user("user_9527")
    
    time.sleep(0.1)
