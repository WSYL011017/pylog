# PyLog V2 开发规划与改进指南

**版本**: 2.0 (Released)
**基线**: V1.0 (已发布)
**日期**: 2026-01-07
**状态**: ✅ Production Ready (已发布)

## 1. 概述与目标
基于 V1.0 版本的测试与评估报告，PyLog 核心架构已验证可行。V2 版本已达成**可靠性与安全性**的发布标准。后续 V2.1 将专注于**性能极限优化**（如 IO Batching）。

## 2. 核心问题与未实现特性 (Gap Analysis) - 已解决

根据 [PYLOG_TEST_REPORT.md](PYLOG_TEST_REPORT.md) 与 [PYLOG_DEVELOPMENT_REPORT.md](PYLOG_DEVELOPMENT_REPORT.md) 的反馈，以下关键领域已在 V2.0 中完成修复：

### 2.1 可靠性风险 (Reliability Risks) - ✅ Fixed
- **CRITICAL**: `RollingFileAppender` 现已支持历史文件保留策略（Retention Policy），消除了磁盘写满风险。
- **HIGH**: `AsyncQueueHandler` 新增了 `full_policy` 背压策略，并强制保障 ERROR/CRITICAL 级别日志不丢失。
- **HIGH**: `FailoverAppender` 已集成运行状态指标与告警回调。

### 2.2 功能缺陷 (Functional Gaps) - ✅ Fixed
- **时间滚动精度**: 支持秒级/分钟级/小时级滚动（基于正则匹配）。
- **配置鲁棒性**: `ConfigLoader` 增加了对未知日志级别的容错处理。
- **路径安全**: 增强了路径解析。

### 2.3 性能优化空间 (Performance)
- **I/O 吞吐**: V2.1 计划引入 Batching。
- **多进程支持**: 建议在文档中推荐使用 `SocketAppender`。

## 3. V2 核心特性规划 (Feature Roadmap)

### 3.1 增强型滚动策略 (Enhanced Rolling)
- **目标**: 实现完整的生命周期管理。
- **任务**:
  - [x] 实现 `DefaultRolloverStrategy` 的 `max` 参数逻辑，按修改时间或索引自动清理旧文件。
  - [x] 解析 `filePattern` 中的日期格式（如 `%d{yyyy-MM-dd-HH}`），支持分钟/小时级滚动。
  - [x] 增加 `DeleteAction`，支持按文件龄期（Age）或总大小清理归档。

### 3.2 智能背压策略 (Smart Backpressure)
- **目标**: 在高负载下保护系统同时保障关键数据。
- **任务**:
  - [x] 为 `AsyncQueueHandler` 增加 `full_policy` 配置项：
    - `Discard` (默认): 丢弃并计数。
    - `Block`: 阻塞生产者（主线程），适用于数据绝对不能丢的场景。
    - `DiscardLowLevel`: 仅丢弃 INFO 及以下级别，保留 WARN/ERROR。
  - [x] **强制保障**: ERROR/CRITICAL 级别日志始终绕过丢弃策略，强制入队或同步降级写入。

### 3.3 可观测性集成 (Observability)
- **目标**: 让日志系统本身可监控。
- **任务**:
  - [x] 引入 `MetricsRegistry`，暴露以下指标：
    - `pylog_queue_size`: 当前队列长度。
    - `pylog_events_dropped_total`: 因队列满丢弃的事件数。
    - `pylog_failover_switch_total`: 主备切换次数。
  - [x] 为 `FailoverAppender` 增加 `on_switch` 回调钩子，支持集成外部告警。

### 3.4 性能与并发 (Performance & Concurrency)
- **目标**: 提升吞吐量与多进程安全性。
- **任务**:
  - [x] 引入可选依赖 `portalocker`，实现跨进程文件锁（Inter-process Locking）。
  - [ ] (移至 V2.1) 提供 `BufferingAppender` 包装器，为任意 Appender 增加内存缓冲能力。
  - [ ] (移至 V2.1) `BatchingStrategy`：消费者线程支持聚合多条日志一次性写入。

### 3.5 生态扩展 (Ecosystem)
- **目标**: 融入现代云原生环境。
- **任务**:
  - [ ] (移至 V2.1) 实现 `KafkaAppender`（基于 `confluent-kafka`），支持异步批量发送。
  - [x] 实现 `SocketAppender`（TCP/UDP），支持重连与缓冲。
  - [x] 完善 `JSONFormatter`，支持字段掩码（Masking）以保护敏感数据（如密码、Token）。

## 4. 架构调整建议
- **配置层**: 已增强 `ConfigLoader` 健壮性。
- **接口层**: 统一 `LifeCycle` 接口。

## 5. 质量保障计划
- **测试增强**:
  - [x] 增加长时间运行的稳定性测试（Soak Testing）。
  - [x] 增加故障注入测试（Chaos Testing）。
- **基准测试**:
  - [x] 建立标准 Benchmark Suite。

## 6. 交付物清单
1.  PyLog V2 核心库源码 (Completed)
2.  更新后的 API 文档与配置手册 (Completed)
3.  性能对比报告 (Completed)
4.  迁移指南 (Completed)

---
**Prepared for**: PyLog Development Team

## 7. 行动项表与排期（Action Items）

- **Must Haves（立即修复，发布前完成） - ✅ ALL DONE**
  - [x] 实现滚动文件保留与清理（Retention/Max Files）
  - [x] 增强异步队列背压策略（Discard/Block/DiscardLowLevel）
  - [x] 敏感字段保护（JSONFormatter 字段黑名单/掩码）
  - [x] 日志级别解析显式映射

- **Should Haves（短期优化） - ✅ ALL DONE**
  - [x] 时间滚动精度提升
  - [x] 可观测性指标：队列长度、丢弃计数、Failover 切换次数

- **V2.1 Performance Pack（性能专项） - 🕒 Scheduled**
  - [ ] 批量写与缓冲（Batching/Buffering）

- **Could Haves（中期演进） - 🔄 Partial**
  - [x] 跨进程文件锁（portalocker，可选）
  - [x] SocketAppender
  - [ ] Kafka/HTTP/DB/Syslog 独立模块
  - [ ] 配置强校验（Pydantic）

- **验收与度量标准**
  - [x] 可靠性：关键级别零丢失 (Verified)
  - [x] 性能：异步入队耗时 (Verified)
  - [x] 稳健性：队列丢弃计数、文件保留 (Verified)
