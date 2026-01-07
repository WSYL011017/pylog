# PyLog 功能需求规格说明书 (Functional Requirements Document)

**版本**: 1.0
**日期**: 2026-01-06
**来源**: 基于 Log4j2 深度分析报告

## 1. 核心架构需求 (Core Architecture)

### FR-01: 异步核心 (Async Core)
*   **需求描述**: 实现基于生产者-消费者模型的异步日志记录。
*   **实现要求**:
    *   主线程将 `LogRecord` 推入 `multiprocessing.Queue` 或 `queue.SimpleQueue`。
    *   独立后台线程（Worker）负责从队列拉取并分发给 Handler。
    *   必须提供 `AsyncQueueFullPolicy`（丢弃/阻塞/降级）。
    *   **优化**: 借鉴 LMAX Disruptor 思想，使用预分配对象池和无锁/低锁队列优化吞吐量。
*   **对标 Log4j2**: Asynchronous Loggers / Disruptor。

### FR-02: 上下文感知 (Context Awareness)
*   **需求描述**: 实现跨协程/线程的上下文数据传递。
*   **实现要求**:
    *   基于 `contextvars` 实现 `MDC` (Mapped Diagnostic Context)。
    *   提供 `put(key, val)`, `get(key)`, `clear()` 接口。
    *   Formatter 自动提取上下文数据注入日志。
    *   **兼容性**: 确保在 ThreadPoolExecutor 和 ProcessPoolExecutor 中上下文不丢失（需提供上下文传播装饰器）。
*   **对标 Log4j2**: ThreadContext (MDC)。

### FR-03: 插件化架构 (Plugin Architecture)
*   **需求描述**: 允许用户通过配置或装饰器注册自定义组件。
*   **实现要求**:
    *   实现注册机制，支持动态加载自定义的 Handler, Formatter, Filter。
    *   **实现细节**: 使用 Python Entry Points 或自定义装饰器 `@Plugin(name="MyHandler")` 自动发现组件。
*   **对标 Log4j2**: Plugin System。

## 2. 高级特性需求 (Advanced Features)

### FR-04: 延迟求值 (Lazy Evaluation)
*   **需求描述**: 避免在日志级别未开启时执行昂贵计算。
*   **实现要求**:
    *   API 支持传入 `Callable` (lambda)。
    *   仅在 `isEnabledFor(level)` 为真时执行 `callable()`。
    *   **优化**: 使用 `__slots__` 优化 LogRecord 内存占用。
*   **对标 Log4j2**: Lambda Support。

### FR-05: 结构化布局 (Structured Layouts)
*   **需求描述**: 开箱即用的 JSON 输出。
*   **实现要求**:
    *   提供 `JSONFormatter`。
    *   支持自定义字段映射 (Field Mapping)。
    *   自动序列化 `extra` 字典和 `MDC` 内容。
    *   **性能**: 优先使用 `orjson` 或 `ujson` 进行序列化。
*   **对标 Log4j2**: JSON Layout。

### FR-06: 滚动策略 (Rolling Policies)
*   **需求描述**: 生产级文件管理。
*   **实现要求**:
    *   同时支持按时间 (`TimeBased`) 和大小 (`SizeBased`) 滚动。
    *   支持滚动后自动压缩 (`.gz`, `.zip`)。
    *   支持最大文件保留数 (`MaxHistory` / `MaxFiles`)。
    *   **可靠性**: 滚动操作应是原子性的，避免多进程写入冲突。
*   **对标 Log4j2**: RollingFileAppender。

### FR-07: 组合配置 (Composite Configuration)
*   **需求描述**: 多配置文件合并。
*   **实现要求**:
    *   加载器支持传入文件列表 `['base.yaml', 'prod.yaml']`。
    *   后加载的配置覆盖先加载的配置（Deep Merge）。
    *   **灵活性**: 支持 XML, JSON, YAML, Properties 四种格式。
*   **对标 Log4j2**: Composite Configuration / Multiple Formats。

### FR-08: 动态重载 (Hot Reloading)
*   **需求描述**: 无重启更新配置。
*   **实现要求**:
    *   启动文件监控器 (Watchdog)。
    *   检测到配置文件变更时，自动重新初始化 Logging 系统。
*   **对标 Log4j2**: MonitorInterval。

### FR-09: 标记 (Markers)
*   **需求描述**: 细粒度日志分类。
*   **实现要求**:
    *   API 增加 `marker` 参数: `logger.info("msg", marker="AUDIT")`。
    *   Filter 支持按 Marker 过滤。
*   **对标 Log4j2**: Markers。

### FR-12: 脚本化逻辑 (Scripting Support)
*   **需求描述**: 允许在配置中嵌入动态逻辑。
*   **实现要求**:
    *   配置支持引用 Python 函数或表达式。
    *   支持在 Filter 中执行简单逻辑（如 `user.id > 1000`）。
*   **对标 Log4j2**: Scripting.

### FR-13: 自定义级别 (Custom Levels)
*   **需求描述**: 支持业务自定义日志级别。
*   **实现要求**:
    *   提供 `addLevelName` 的配置化封装。
    *   确保自定义级别能被 Formatter 和 Filter 正确识别。
*   **对标 Log4j2**: Custom Log Levels.

## 3. 扩展性需求 (Ecosystem & Extensibility)

### FR-10: 丰富的 Appenders
*   **需求描述**: 对接现代基础设施。
*   **实现要求**:
    *   **KafkaHandler**: 异步写入 Kafka (基于 `confluent-kafka` 或 `kafka-python`)。
    *   **HTTPHandler**: 异步 POST JSON 到指定 URL。
    *   **DatabaseHandler**: 通用数据库写入接口 (SQLAlchemy/MongoDB)。
    *   **SocketHandler**: 支持 TCP/UDP 发送。
*   **对标 Log4j2**: Kafka/Http/Jdbc/NoSql/Socket Appenders。

### FR-11: 故障转移 (Failover)
*   **需求描述**: 高可用保障。
*   **实现要求**:
    *   实现 `FailoverHandler` 包装器。
    *   当 Primary Handler 抛出异常时，自动降级到 Secondary Handler。
    *   定期重试 Primary Handler。
*   **对标 Log4j2**: FailoverAppender。

### FR-14: 监控与管理 (Monitoring/JMX)
*   **需求描述**: 运行时监控。
*   **实现要求**:
    *   暴露简单的指标接口 (Metrics API)，统计日志吞吐量、丢弃数、队列长度。
    *   （可选）提供 Prometheus Exporter 集成。
*   **对标 Log4j2**: JMX Integration.

## 4. 接口契约 (API Contract)

```python
# 必须兼容标准 logging 库，但提供增强入口
import pylog

# 上下文
pylog.MDC.put("req_id", "123")

# 延迟求值
logger.info("Result: {}", lambda: heavy_calc())

# 标记
logger.info("User login", marker="SECURITY")
```

## 5. 非功能性需求 (NFR)

*   **NFR-01 性能**: 异步模式下，主线程阻塞时间 < 0.05ms。
*   **NFR-02 可靠性**: 内部异常不崩坏业务，默认回退到 stderr。
*   **NFR-03 兼容性**: 完美支持 Python 3.8+ 及 asyncio。
