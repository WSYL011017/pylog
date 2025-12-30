import sys
import os
import time
import random

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from log_framework import Slf4j, MDC, LogManager

# 🟢 1. 模拟一个 Web 服务 (比如 Flask 或 FastAPI)
@Slf4j
class FakeWebServer:
    def handle_request(self, path):
        # 模拟生成一个请求ID
        request_id = f"req-{random.randint(1000, 9999)}"
        
        # 🟢 2. 在请求开始时放入 MDC
        MDC.put("request_id", request_id)
        MDC.put("path", path)
        MDC.put("ip", "192.168.1.10")
        
        self.logger.info(f"收到请求: {path}")
        
        try:
            self.process_logic()
            self.logger.info("请求处理成功 200 OK")
        except Exception as e:
            # 🟢 3. 发生错误时，logger.error 会自动记录堆栈
            self.logger.error(f"请求处理失败 500: {e}", exc_info=True)
        finally:
            # 🟢 4. 请求结束，清理
            MDC.clear()

    def process_logic(self):
        # 模拟业务逻辑
        if random.random() < 0.3:
            raise ValueError("数据库连接断开！")
        self.logger.info("正在查询数据库...")
        self.logger.info("正在渲染模板...")

if __name__ == "__main__":
    server = FakeWebServer()
    
    print("--- 模拟服务器启动 ---")
    server.handle_request("/api/login")
    server.handle_request("/api/get_user")
    server.handle_request("/api/buy_item")
    
    time.sleep(0.5)
