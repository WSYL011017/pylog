# PyLog API 设计规格说明书 (API Design Specification)

**版本**: 1.0
**日期**: 2026-01-06
**状态**: 待评审

本文档定义了 PyLog 库的公共接口（Public API），旨在为开发者提供类似于 Log4j2 的使用体验，同时保持 Pythonic 的代码风格。

## 1. 核心入口 (Core Entry Points)

### 1.1 获取 Logger
```python
import pylog

# 获取根 Logger
logger = pylog.get_logger()

# 获取指定名称的 Logger (通常使用 __name__)
logger = pylog.get_logger(__name__)

# 获取指定类的 Logger (Log4j2 风格)
logger = pylog.get_logger(MyClass)
```

### 1.2 初始化与配置
PyLog 推荐使用声明式配置，但也支持代码配置。

```python
from pylog import LogManager

# 1. 加载配置文件 (支持 .yaml, .json, .xml)
# monitor_interval: 自动重载检查间隔(秒)，0 表示不自动重载
LogManager.load_config("logging.yaml", monitor_interval=30)

# 2. 组合配置 (后覆盖前)
LogManager.load_config(["base-log.yaml", "prod-log.yaml"])

# 3. 编程式配置 (不推荐，仅用于简单脚本)
LogManager.basic_config(level="INFO", format="json")
```

## 2. 日志记录接口 (Logging Interface)

`Logger` 对象必须兼容标准库 `logging.Logger`，并扩展以下能力。

### 2.1 基础记录
```python
logger.info("Application started")
logger.error("Database connection failed", exc_info=True)
```

### 2.2 结构化数据 (Structured Data)
支持直接传递字典作为 `extra`，或使用关键字参数。

```python
# 方式 A: 标准 logging 风格
logger.info("Order processed", extra={"order_id": 123, "amount": 99.9})

# 方式 B: 关键字参数 (PyLog 增强)
logger.info("Order processed", order_id=123, amount=99.9)
```

### 2.3 延迟求值 (Lazy Evaluation)
为了性能，仅在日志级别满足时才执行计算。

```python
# 使用 lambda
logger.debug("Expensive calculation: {}", lambda: perform_heavy_calc())

# 使用 Callable 对象
logger.trace("System state: {}", SystemStateDumper())
```

### 2.4 标记 (Markers)
用于细粒度过滤。

```python
from pylog import Marker

SECURITY = Marker("SECURITY")
AUDIT = Marker("AUDIT", parents=[SECURITY]) # 标记继承

logger.info("User login successful", marker=SECURITY)
logger.warn("Unauthorized access attempt", marker=AUDIT)
```

## 3. 上下文管理 (Context / MDC)

基于 `contextvars` 实现，确保异步安全。

### 3.1 基础操作
```python
from pylog import ThreadContext

# 设置值
ThreadContext.put("req_id", "req-123456")
ThreadContext.put("user_id", "u-888")

# 获取值
uid = ThreadContext.get("user_id")

# 清除
ThreadContext.remove("req_id")
ThreadContext.clear()
```

### 3.2 自动管理 (Context Manager / Decorator)
```python
# 自动清理上下文
with ThreadContext.scope(transaction_id="tx-999"):
    logger.info("Inside transaction") 
    # log output: {"msg": "...", "ctx": {"transaction_id": "tx-999"}}

# 装饰器模式
@ThreadContext.inject(module="payment")
async def process_payment():
    logger.info("Processing") 
    # log output: {"msg": "...", "ctx": {"module": "payment"}}
```

## 4. 插件系统 (Plugin System)

使用装饰器注册自定义组件。

### 4.1 定义 Appender
```python
from pylog.plugins import Plugin, Appender
from pylog.core import LogEvent

@Plugin(name="Kafka", category="Appender")
class KafkaAppender(Appender):
    def __init__(self, topic: str, bootstrap_servers: str):
        self.topic = topic
        # ... init kafka producer ...

    def append(self, event: LogEvent):
        # 异步发送到 Kafka
        self.producer.send(self.topic, event.to_json())
```

### 4.2 定义 Filter
```python
from pylog.plugins import Plugin, Filter, Result

@Plugin(name="UserFilter", category="Filter")
class UserFilter(Filter):
    def filter(self, event: LogEvent) -> Result:
        if event.context.get("user_id") == "blocked_user":
            return Result.DENY
        return Result.NEUTRAL
```

## 5. 异常处理与故障转移 (Error Handling)

```python
try:
    1 / 0
except Exception:
    # 自动记录异常堆栈
    logger.error("Calculation error") 
    
    # 显式传递异常对象
    logger.error("Calculation error", exc_info=True)
```

## 6. 配置示例 (Configuration Schema)

`logging.yaml` 结构示例：

```yaml
configuration:
  status: warn
  monitorInterval: 30
  
  properties:
    logPath: "/var/log/app"
  
  appenders:
    console:
      name: Console
      target: SYSTEM_OUT
      json_layout:
        compact: true
        event_eol: true
        
    rolling_file:
      name: RollingFile
      fileName: "${logPath}/app.log"
      filePattern: "${logPath}/app-%d{yyyy-MM-dd}.log.gz"
      json_layout:
        complete: false
      policies:
        time_based:
          interval: 1
        size_based:
          size: "100 MB"
      strategy:
        max: 10
        
    # 故障转移配置
    failover:
      name: Failover
      primary: Kafka
      retryIntervalSeconds: 60
      failovers:
        - RollingFile

  loggers:
    root:
      level: info
      appender_refs:
        - ref: Console
        - ref: Failover
    
    logger:
      - name: "com.mycompany.payment"
        level: debug
        additivity: false
        appender_refs:
          - ref: RollingFile
```
