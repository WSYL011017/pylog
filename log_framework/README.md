# Python Log4j2-Style Logging Framework 使用手册

这是一个基于 Python 标准库 `logging` 的高级封装框架，旨在复刻 Java 生态中 **Log4j2 / Logback** 的核心特性。

## 🚀 核心特性

1.  **异步日志 (Async Logger)**: 采用 `QueueHandler` + `QueueListener` 架构，将日志写入移至后台线程，主线程零 I/O 阻塞。
2.  **Lombok 风格注解**: 提供 `@Slf4j` 装饰器，自动注入 Logger 实例，减少样板代码，统一命名规范。
3.  **MDC (Mapped Diagnostic Context)**: 支持请求级上下文追踪（如 `request_id`, `user_id`），并能自动穿越异步队列。
4.  **JSON Layout**: 输出结构化 JSON 日志，包含时间戳、线程、异常栈及 MDC 上下文，完美适配 ELK/Splunk。
5.  **Context Filter**: 支持基于 MDC 值的日志路由（例如：将 VIP 用户日志分离到独立文件）。
6.  **自动目录创建**: 如果配置的日志文件目录不存在，框架会自动创建，无需手动 `mkdir`。

---

## 📦 快速开始

### 1. 初始化

将 `log_framework` 目录放入您的项目中。

在程序中直接导入即可（框架会自动查找并加载配置）：

```python
import sys
# 确保能导入 log_framework
sys.path.append("path/to/project_root")

# 只要导入了包，日志系统就会自动初始化！
# 默认加载顺序：log_framework/log_config.yaml -> ./logging.yaml -> 环境变量
from log_framework import LogManager, Slf4j
```

### 2. 获取 Logger

#### 方式 A: 标准方式 (类似 LoggerFactory)
```python
# 使用标准 logging 模块或 LogManager 获取
import logging
logger = logging.getLogger("my_module")
# 或者
logger = LogManager.get_logger("my_module")
```

#### 方式 B: 注解方式 (推荐，类似 Lombok @Slf4j)
我们提供了 `@Slf4j` 装饰器，自动为类注入 `logger` 属性，命名规则默认为 `模块名.类名`。

```python
from log_framework import Slf4j

@Slf4j
class UserService:
    def process(self):
        # 自动注入 self.logger
        self.logger.info("Processing user request")

@Slf4j
class ConfigUtils:
    @classmethod
    def load(cls):
        # 类方法中自动注入 cls.logger
        cls.logger.debug("Loading config")
```

### 3. 使用 MDC (上下文追踪)

在业务逻辑中添加上下文信息（通常在 Web 框架的拦截器/中间件中做）：

```python
from log_framework import MDC

def process_request(user_id):
    # 1. 设置上下文
    MDC.put("user_id", user_id)
    MDC.put("request_id", "req-123456")
    
    # 2. 记录日志 (自动携带上下文)
    logger.info("Processing start")  # 输出 JSON 中将包含 user_id 和 request_id
    
    try:
        # 业务逻辑...
        pass
    finally:
        # 3. 清理上下文 (必须做，防止污染线程池中其他请求)
        MDC.clear()
```

---

## ⚙️ 配置文件说明 (`log_config.yaml`)

配置文件采用标准 YAML 格式，扩展了自定义组件。

### 1. 定义 Filter (基于上下文过滤)

```yaml
filters:
  vip_filter:
    (): logger_setup.ContextFilter  # 引用自定义类
    key: user_type                  # 检查 MDC 中的 key
    value: vip                      # 检查 value 是否匹配 (可选，不填则只检查 key 是否存在)
```

### 2. 定义 Handler (输出目的地)

```yaml
handlers:
  # JSON 文件输出
  file:
    class: logging.handlers.TimedRotatingFileHandler
    formatter: json
    filename: ./app.log
    when: "midnight"
    
  # VIP 专属日志 (应用了上面的 filter)
  vip_file:
    class: logging.FileHandler
    formatter: json
    filename: ./vip.log
    filters: [vip_filter]  # 仅当 MDC[user_type] == 'vip' 时写入

### 3. 隐藏日志文件 (Hidden Handler)
我们提供了一个特殊的 `HiddenTimedRotatingFileHandler`，它会在创建日志文件后自动将其属性设为**隐藏** (Windows)。这非常适合存储机器可读的 JSON 日志，避免干扰视线。

```yaml
  file_json:
    (): logger_setup.HiddenTimedRotatingFileHandler
    formatter: json
    filename: ./app_json.log
```

### 4. 定义 Loggers

建议让所有 Logger 最终都 Propagate 到 Root Logger，以便统一由异步队列处理。

```yaml
root:
  level: INFO
  handlers: [console, file, vip_file] # 所有日志最终汇聚到这里

loggers:
  my_module:
    level: DEBUG
    # 不要在这里配置 handlers，除非你想绕过异步队列直接写
```

---

## 🧩 高级原理

### 异步日志是如何工作的？
当您调用 `LogManager.load_config(async_mode=True)` 时，框架会执行“偷梁换柱”：
1.  创建一个后台线程 (`QueueListener`)。
2.  将 Root Logger 的原有 Handlers（如 FileHandler）移动到 Listener 中。
3.  将 Root Logger 的 Handler 替换为 `QueueHandler`。
4.  **结果**：`logger.info()` 仅仅是将一个对象放入内存队列（极快），真正的文件写入由后台线程完成。

### 上下文是如何传递的？
Python 的 `contextvars` 是线程隔离的。为了解决异步线程无法读取主线程 Context 的问题，我们注入了一个自定义的 `LogRecordFactory`。它会在日志记录生成的瞬间（主线程）将当前的 MDC 数据**拷贝**一份到日志记录对象中，从而确保后台线程能读取到正确的上下文。

---

## 🛠️ 最佳实践集成

### 集成到 Flask/FastAPI

建议在中间件（Middleware）中管理 MDC：

```python
# FastAPI 示例
@app.middleware("http")
async def log_middleware(request: Request, call_next):
    # 生成 Request ID
    req_id = str(uuid.uuid4())
    
    # 设置 MDC
    MDC.put("request_id", req_id)
    MDC.put("path", request.url.path)
    
    try:
        response = await call_next(request)
        return response
    finally:
        # 清理 MDC
        MDC.clear()
```
