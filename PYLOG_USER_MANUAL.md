# PyLog V2.0 使用手册 (User Manual)

**PyLog** 是一个高性能、生产就绪的 Python 异步日志框架。本手册将指导您如何配置和使用 V2.0 的新特性（包括文件清理、背压保护、数据脱敏等）。

---

## 1. 快速开始 (Quick Start)

### 安装
```bash
pip install pylog
```

### 最小化代码示例
```python
from pylog import LogManager, get_logger

# 1. 加载配置 (默认自动加载 pylog_config.yaml, pylog.yaml, pylog.json)
# LogManager.load_config("pylog_config.yaml")  # 手动加载（可选）

# 2. 获取 Logger
logger = get_logger("my.service")

# 3. 打印日志
logger.info("Service started", extra={"port": 8080})

# 4. 结构化上下文 (MDC)
with LogManager.context(user_id="1001"):
    logger.info("Processing request")  # 自动携带 user_id

# 5. 进程退出前关闭
LogManager.shutdown()
```

---

## 2. 核心配置详解 (Configuration)

PyLog 推荐使用 `YAML` 格式进行配置。V2.0 引入了多项关键配置以提升生产环境的可靠性。

### 2.1 全局设置与异步背压 (Global & Backpressure)

在 `configuration` 根节点下配置：

```yaml
configuration:
  status: INFO          # PyLog 内部自身的日志级别
  monitorInterval: 30   # 配置文件热重载扫描间隔 (秒)
  
  # [V2 新增] 异步队列配置
  async_queue:
    size: 4096                  # 环形队列大小 (建议 2^N)
    full_policy: Discard        # 队列满时的策略:
                                # - Discard: 丢弃新日志 (默认)
                                # - Block: 阻塞业务线程 (防丢失)
                                # - DiscardLowLevel: 仅丢弃 INFO 及以下
```

> **⚠️ 注意**: 无论选择何种策略，`ERROR` 和 `CRITICAL` 级别的日志 **永远不会被丢弃**（将强制阻塞或降级同步写入）。

### 2.2 Appenders (输出源)

#### RollingFileAppender (滚动文件)
V2.0 修复了文件保留问题，支持精准清理。

```yaml
    rolling:
      type: RollingFileAppender
      file_name: "logs/app.log"
      file_pattern: "logs/archive/app-%d{yyyy-MM-dd}-%i.log.gz" # 归档命名模式
      
      # 触发策略 (何时滚动)
      policies:
        - type: SizeBasedTriggeringPolicy
          size: "100 MB"      # 满 100MB 滚动
        - type: TimeBasedTriggeringPolicy
          interval: 1         # 每天滚动
          
      # 滚动策略 (保留多少)
      strategy:
        type: DefaultRolloverStrategy
        max: 30               # [V2 新增] 最多保留 30 个归档文件，旧的自动删除
```

#### FailoverAppender (故障转移)
当主 Appender 失败时（如磁盘满、网络断），自动切换到备用 Appender。

```yaml
    failover:
      type: FailoverAppender
      primary: socket_appender    # 主输出 (如发往 Logstash)
      failovers:
        - file_appender           # 备用输出 (本地磁盘)
      retry_interval: 60          # 60秒后尝试切回主输出
```

### 2.3 Layouts 与数据脱敏 (Masking)

#### JSONLayout (结构化输出)
支持自动将敏感字段值替换为 `***`。

```yaml
      json_layout:
        compact: true
        event_eol: true
        # [V2 新增] 脱敏字段黑名单
        masked_keys:
          - "password"
          - "secret"
          - "token"
          - "mobile"
```

---

## 3. 完整配置示例 (Full Example)

将以下内容保存为 `pylog_config.yaml`:

```yaml
configuration:
  status: WARN
  # 1. 异步队列背压设置
  async_queue:
    size: 8192
    full_policy: DiscardLowLevel  # 队列满时保 WARN/ERROR，丢 INFO/DEBUG

  appenders:
    # 控制台输出
    console:
      name: Console
      target: SYSTEM_OUT
      pattern_layout:
        pattern: "%d{HH:mm:ss.SSS} [%t] %-5level %logger{36} - %msg%n"

    # 滚动文件 (带自动清理)
    app_log:
      name: AppLog
      type: RollingFileAppender
      file_name: "logs/app.log"
      file_pattern: "logs/archive/app-%d{yyyy-MM-dd}-%i.log.gz"
      policies:
        - type: TimeBasedTriggeringPolicy
          interval: 1
        - type: SizeBasedTriggeringPolicy
          size: "500 MB"
      strategy:
        type: DefaultRolloverStrategy
        max: 7  # 只保留最近 7 个文件
      json_layout:
        masked_keys: ["password", "api_key"]

  loggers:
    # 根日志记录器
    root:
      level: INFO
      appender_refs:
        - ref: Console
        - ref: AppLog

    # 独立模块配置
    my.module:
      level: DEBUG
      additivity: false
      appender_refs:
        - ref: Console
```

---

## 4. 高级用法 (Advanced Usage)

### 4.1 结构化上下文 (MDC)
在多线程或异步 (`asyncio`) 环境中追踪请求 ID。

```python
from pylog import ThreadContext

# 进入作用域，自动绑定上下文
with ThreadContext.scope(request_id="req-123", user="Alice"):
    logger.info("Handling payment") 
    # JSON 输出: {"message": "Handling payment", "context": {"request_id": "req-123", "user": "Alice"}}
```

### 4.2 懒加载日志 (Lazy Logging)
避免在日志级别未开启时进行昂贵的字符串拼接或计算。

```python
def expensive_debug_info():
    # 复杂计算...
    return detailed_dump

# 只有当 DEBUG 级别开启时，才会调用 expensive_debug_info
logger.debug("Debug data: {}", expensive_debug_info)
```

### 4.3 多进程安全 (Multiprocessing)
在 Gunicorn / uWSGI 等多进程场景下，**请勿使用 RollingFileAppender 直接写文件**。

**推荐方案**: 使用 `SocketAppender` 将日志发往中心 Agent。

```yaml
    socket:
      type: SocketAppender
      host: "127.0.0.1"
      port: 9000
```

---

## 5. 故障排查 (Troubleshooting)

- **日志文件未生成**: 检查 `file_name` 路径权限，确保文件夹存在。
- **旧文件未删除**: 检查 `file_pattern` 是否包含 `%i` (索引) 或 `%d` (日期)，并确认 `strategy.max` 已设置。
- **关键日志丢失**: 检查 `async_queue.full_policy` 是否为 `Discard`，建议改为 `Block` 或 `DiscardLowLevel`。

---

## 6. 附录：完整配置参数参考 (Configuration Reference)

### 6.1 全局配置 (Global Settings)
位于 `configuration` 根节点。

| 参数名 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| **status** | String | `INFO` | PyLog 内部调试级别 (DEBUG/INFO/ERROR)。 |
| **monitorInterval** | Int | `0` | 热重载检测间隔(秒)。0=禁用。 |
| **async_queue** | Object | `{}` | [V2] 异步队列配置。 |

#### 异步队列 (async_queue)
| 参数名 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| **size** | Int | `4096` | 队列大小。 |
| **full_policy** | String | `Discard` | 背压策略: `Discard` (丢弃), `Block` (阻塞), `DiscardLowLevel` (丢弃低优)。ERROR 级永不丢弃。 |

### 6.2 输出源 (Appenders)
位于 `appenders` 节点。所有 Appender 均包含 `name` 属性。

#### 滚动文件 (RollingFile)
| 参数 | 说明 | 示例 |
| :--- | :--- | :--- |
| **type** | `RollingFile` | |
| **fileName** | 日志路径 | `logs/app.log` |
| **filePattern** | 归档模式 | `logs/app-%d{yyyy-MM-dd}-%i.log.gz` |
| **policies** | 滚动策略 | `size_based` (`size`), `time_based` (`interval`) |
| **strategy** | 保留策略 | `max` (保留数量), `use_multiprocess_lock` |

#### 其他类型
| 类型 | 关键参数 |
| :--- | :--- |
| **Console** | `target` (SYSTEM_OUT/SYSTEM_ERR) |
| **Socket** | `host`, `port`, `protocol` (TCP/UDP) |
| **HTTP** | `url`, `method` (POST), `headers` |
| **Kafka** | `bootstrap_servers`, `topic`, `async_send` |

### 6.3 布局 (Layouts)

#### 模式布局 (pattern_layout)
支持 Log4j2 风格占位符：
| 占位符 | 说明 | 示例 |
| :--- | :--- | :--- |
| `%d` | 时间 | `%d{HH:mm:ss.SSS}` |
| `%p` / `%-5level` | 级别 | `INFO`, `ERROR` |
| `%t` | 线程名 | `MainThread` |
| `%c` / `%logger` | Logger名 | `my.module` |
| `%m` / `%msg` | 消息 | |
| `%n` | 换行 | |

#### JSON布局 (json_layout)
| 参数 | 说明 |
| :--- | :--- |
| **compact** | 是否压缩为单行 (true/false) |
| **masked_keys** | [V2] 脱敏字段列表 (如 `["password", "token"]`) |

---
*PyLog Team - 2026*
