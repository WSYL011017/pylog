# PyLog 架构设计报告（可直接开发版）

**版本**: 1.0  
**日期**: 2026-01-06  
**用途**: 工程落地指导，拿来即可开始开发与测试

## 1. 目标与范围
- 复现 Log4j2 的核心使用体验：异步、结构化 JSON、MDC、标记与过滤、Failover、组合配置与热重载。
- 面向生产可用与易维护，适配 Python 特性与跨平台环境。
- 非目标：Disruptor 无锁环缓、Memory-mapped/RandomAccess 文件写、JMX 原生管理；采用工程化替代方案。

## 2. 技术栈与依赖
- 必选：Python 3.8+；标准库 logging、contextvars、threading；PyYAML（配置）、orjson（JSON 序列化优先）、watchdog（热重载）。
- 可选：portalocker（跨进程文件锁）、prometheus_client（指标）、aiohttp/requests（HTTP）、confluent-kafka（Kafka）、SQLAlchemy/pymongo（数据库）。
- 原则：核心零强依赖，可选能力以独立模块提供。

## 3. 架构分层
- 表现层（API）
  - get_logger(name|class)、LogManager.load_config/basic_config
  - Marker 与 ThreadContext(MDC)
- 核心层（Core）
  - Logger/LoggerContext、AsyncQueueHandler（后台队列写）、Router、Filters、Markers、Level 扩展、延迟求值。
- IO 层（Data）
  - Formatter：JSONFormatter（字段映射、MDC/extra 注入、异常序列化）。
  - Appenders：Console、File、Rolling（单进程优先）、Socket、Null；FailoverHandler 包装主备。
  - 可选：Kafka、HTTP、DB、Syslog（独立模块）。
- 基础设施（Infra）
  - ConfigLoader（YAML/JSON/XML/Properties）、Composite Merge、变量插值。
  - HotReloader（watchdog）、Metrics/管理端点、文件锁策略。

## 4. 核心数据结构与契约
- LogEvent
  - 字段：timestamp, level, logger_name, message|callable, args, marker, context(MDC), extra, exc_info
  - 行为：lazy_eval() 在级别启用时执行 Callable；to_dict() 提供结构化输出。

- ThreadContext(MDC)
  - 接口：put(key,val), get(key), remove(key), clear(), scope(**kv), inject(**kv)
  - 说明：基于 contextvars；scope 为上下文管理器；inject 为装饰器，支持 async/sync。

- Marker
  - 字段：name, parents[]；用于 Filter/路由维度；支持继承。

- AsyncQueueHandler
  - 接口：enqueue(event), run(), flush(), stop()
  - 策略：批量出队写入；队列满策略（丢弃/阻塞/降级同步）；ERROR+ 强制写入保障。

- Formatter.JSONFormatter
  - 行为：orjson dumps；支持字段映射；序列化 extra/MDC 与异常堆栈。

- Appender 接口
  - append(event), start(), stop()
  - 默认内置：Console（stdout/stderr, JSON）、File、Rolling（时间/大小+压缩后台）、Socket、Null。
  - FailoverHandler：包装 primary/secondaries，健康检测、指数退避重试、自动切回。

## 5. API 与用法示例

```python
import pylog
from pylog import LogManager, ThreadContext, Marker

# 初始化
LogManager.load_config(["base.yaml", "env.yaml"], monitor_interval=30)

# 获取 logger
logger = pylog.get_logger(__name__)

# 上下文（MDC）
with ThreadContext.scope(req_id="r-123", user_id="u-1"):
    logger.info("order processed", order_id=1001, amount=9.9)

# 延迟求值
logger.debug("expensive: {}", lambda: compute())

# 标记与路由
SECURITY = Marker("SECURITY")
logger.info("user login", marker=SECURITY, user="alice")
```

## 6. 配置规范（YAML）

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

    failover:
      name: Failover
      primary: Kafka
      retryIntervalSeconds: 30
      failovers:
        - RollingFile

  loggers:
    root:
      level: info
      appender_refs:
        - ref: Console
        - ref: Failover

    logger:
      - name: "service.payment"
        level: debug
        additivity: false
        appender_refs:
          - ref: RollingFile
```

## 7. 数据与控制流
- 生产者（应用线程）：级别检查 → 构造 LogEvent（Callable 保留） → 异步 enqueue → 立即返回。
- 消费者（写线程）：批量出队 → Filter/Marker 过滤 → Formatter 序列化 → Appender 写入。
- 背压策略：队列满时丢弃低级别/阻塞/降级同步；ERROR/CRITICAL 强制写入。
- 热重载：watchdog 检测变更，重建配置并在安全点原子替换 Appender 集。

## 8. 错误处理与故障转移
- FailoverHandler：主路由失败自动降级到备份；健康恢复后自动切回；重试采用指数退避。
- 降级：不可恢复时降级到 stderr，记录指标与原因；关键级别支持双写（主+本地）。

## 9. 性能与可观测性
- 目标：主线程阻塞 < 0.05ms（异步 enqueue + 延迟求值 + orjson）；批量写降低系统调用。
- 指标（可选）：吞吐量、队列长度、丢弃数、失败/重试次数；Prometheus 集成。
- 管理端点（可选）：动态调级、查看队列与路由状态、触发滚动与切换。

## 10. 默认 Appender 策略
- 默认内置：Console、File、Rolling（单进程优先）、Socket、Null、FailoverHandler 包装。
- 可选安装：Kafka/HTTP/DB/Syslog，与 Failover 协同。
- 跨进程文件：文件锁或按进程分片；容器场景推荐 Console+采集器。

## 11. 安全与脚本化
- 脚本化（默认关闭）：受限 AST 白名单表达式，禁止 I/O/网络；仅用于简单规则。
- 配置安全：PyYAML/defusedxml 安全解析；禁用不可信插件来源。

## 12. 测试与验收
- 微基准：10k/100k 调用耗时分布（p50/p99）；队列满与多级别组合测试。
- 压力与故障注入：Kafka/HTTP 失败、磁盘满、网络抖动；验证 Failover/重试与降级。
- 并发文件：多线程/多进程滚动写入；锁策略与丢失/重复评估；容器场景 stdout 验证。
- 上下文传播：线程池/协程边界 MDC 传递与自动清理；scope/inject 正确性。
- 热重载：高吞吐下修改配置，检查平滑切换与事件保障。
- 验收标准：满足 NFR（阻塞 < 0.05ms、异常不崩坏业务、兼容 3.8+/asyncio）；功能项覆盖。

## 13. 迭代计划与交付
- 阶段1（骨架与核心）：Logger/LoggerContext、AsyncQueueHandler、ThreadContext(MDC)、JSONFormatter；Console/File/Rolling/Socket/Null；Filter/Marker；配置加载与组合。
- 阶段2（可靠性与可观测性）：FailoverHandler、队列满策略、watchdog 热重载、Metrics/管理端点。
- 阶段3（生态与平台）：Kafka/HTTP/DB/Syslog 模块、文件锁策略、后台压缩清理优化、受限脚本引擎（默认关闭）。
- 每阶段交付：API 文档、示例配置、单元+集成测试、性能与故障报告。

## 14. 参考文档
- 项目总览与目标：[README.md](file:///c:/Users/123/Desktop/pylog/README.md)
- 需求规格：[PYLOG_REQUIREMENTS.md](file:///c:/Users/123/Desktop/pylog/PYLOG_REQUIREMENTS.md)
- API 设计：[PYLOG_API_DESIGN.md](file:///c:/Users/123/Desktop/pylog/PYLOG_API_DESIGN.md)
- 技术分析：[LOG4J2_ANALYSIS.md](file:///c:/Users/123/Desktop/pylog/LOG4J2_ANALYSIS.md)；[log4j2 框架深度技术分析与实践指南.md](file:///c:/Users/123/Desktop/pylog/log4j2%20框架深度技术分析与实践指南.md)

