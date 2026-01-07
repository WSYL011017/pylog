# PyLog V2.1 开发规划与性能优化指南

**版本**: 2.1 (Planned)
**基线**: V2.0 (Production Ready)
**日期**: 2026-01-07
**主题**: 极致性能 (Extreme Performance) & 生态扩展

## 1. 概述与目标

在 V2.0 解决了可靠性与功能完备性问题后，V2.1 将致力于将 PyLog 打造成 Python 生态中**吞吐量最高**的日志框架。

**核心目标**:
1.  **I/O 吞吐翻倍**: 通过 Batching 技术，将磁盘/网络 I/O 次数降低 90% 以上。
2.  **低延迟**: 优化热点代码路径，减少内存分配。
3.  **生态集成**: 提供生产级 Kafka 集成，支持海量日志上报。

## 2. 核心特性规划 (Feature Specification)

### 2.1 I/O 批处理策略 (Batching Strategy)

目前 V2.0 的 Appender 采用逐条写入（Event-by-Event），在高并发下频繁触发 `write()` 系统调用，成为性能瓶颈。

**设计方案**:
引入 `BatchingStrategy`，支持 "积攒" 日志后一次性写入。

-   **触发条件 (OR 逻辑)**:
    1.  **缓冲区满**: 达到 `batch_size` (e.g., 4KB 或 100条)。
    2.  **超时刷盘**: 达到 `flush_interval` (e.g., 100ms)，防止低频写入时日志滞留。

-   **配置示例**:
    ```yaml
    appenders:
      rolling:
        type: RollingFileAppender
        batch_size: 100      # 积攒 100 条
        flush_interval: 0.5  # 或 0.5 秒刷一次
        buffered_io: true    # 开启缓冲
    ```

-   **实现路径**:
    -   抽象 `BufferingMixin` 或 `BatchingAppender` 装饰器。
    -   在 `Appender.append()` 中维护 buffer list。
    -   利用后台线程或下一次 append 触发 flush。

### 2.2 Kafka Appender (生态扩展)

针对微服务架构，提供高性能的 Kafka 投递能力。

-   **技术选型**: 基于 `confluent-kafka` (librdkafka C binding) 而非 `kafka-python`，以获得最佳性能。
-   **特性**:
    -   **异步发送**: 利用 librdkafka 内部队列，不阻塞主线程。
    -   **回调确认**: 支持 `on_delivery` 回调统计成功率。
    -   **Partition 策略**: 支持按 Logger Name 或 Context ID 分片。

-   **配置示例**:
    ```yaml
    appenders:
      kafka:
        type: KafkaAppender
        bootstrap_servers: "10.0.0.1:9092"
        topic: "app-logs"
        async_send: true
    ```

### 2.3 零拷贝与序列化优化 (Zero-Copy & Serialization)

-   **JSON 序列化加速**:
    -   检测环境，优先使用 `orjson` 或 `ujson` (如果安装)，回退到 `json`。
    -   `orjson` 能够提供 5-10 倍于标准库的序列化速度。
-   **字符串拼接优化**:
    -   减少 f-string 在未开启日志级别的开销（Lazy Evaluation 已在 V1 实现，需强化）。

## 3. 架构调整 (Architecture Changes)

### 3.1 引入 `BufferingAppender` 包装器
不再修改每个 Appender，而是提供一个通用的包装器：

```python
# 逻辑示意
class BufferingAppender(Appender):
    def __init__(self, target_appender, buffer_size=4096):
        self.target = target_appender
        self.buffer = BytesIO()
    
    def append(self, event):
        data = self.layout.format(event)
        self.buffer.write(data)
        if self.buffer.tell() >= self.buffer_size:
            self.flush()
```

### 3.2 依赖管理
-   新增 `extras_require`:
    -   `pylog[kafka]`: 引入 `confluent-kafka`
    -   `pylog[speed]`: 引入 `orjson`

## 4. 性能基准测试计划 (Benchmark Plan)

建立标准的压测脚本 `tests/benchmark_v2.1.py`，对比以下场景的 **EPS (Events Per Second)**：

| 场景 | V2.0 (Baseline) | V2.1 (Target) | 提升目标 |
| :--- | :--- | :--- | :--- |
| **同步文件写入** | ~15k EPS | ~100k EPS | **6x** (Batching) |
| **异步队列写入** | ~80k EPS | ~150k EPS | **2x** (Optimization) |
| **JSON 序列化** | ~50k EPS | ~200k EPS | **4x** (orjson) |

## 5. 行动项表 (Action Items)

### Phase 1: 核心优化 (Week 1)
- [ ] 集成 `orjson` 并实现 `JSONFormatter` 的自动适配。
- [ ] 实现 `BufferingAppender` 及其基于大小/时间的 Flush 逻辑。
- [ ] 编写 Batching 性能对比测试脚本。

### Phase 2: Kafka 集成 (Week 2)
- [ ] 封装 `confluent-kafka` Producer。
- [ ] 实现 KafkaAppender 的重连与错误处理。
- [ ] 验证高吞吐下的 Kafka 投递稳定性。

### Phase 3: 综合调优 (Week 3)
- [ ] 全链路 Profiling (使用 `cProfile` / `py-spy`) 消除热点。
- [ ] 发布 V2.1 Release Candidate。

---
**Prepared by**: PyLog Solution Architect
