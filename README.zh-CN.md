# Log Framework V7 🚀

**[English](README.md)** | **[中文](README.zh-CN.md)**

一个生产就绪、高性能的Python异步日志框架，具备企业级特性。

## 📦 安装

### 从PyPI安装

```bash
pip install log-framework
```

### 从源码安装

```bash
git clone https://github.com/your-repo/log-framework.git
cd log-framework
pip install .
```

### 开发模式安装

```bash
pip install -e .
```

## 🌟 核心特性

### ⚡ 高性能模式 (V7新增)
- **自适应采样**：根据队列压力自动调整指标采样率（0.1% - 10%）
- **性能监控**：缓冲指标数据，减少I/O开销，1秒批量刷新
- **智能队列管理**：有界队列（10K）配合"丢弃最旧"策略，防止内存溢出

### 🏗️ 核心架构
- **异步日志**：使用QueueHandler + QueueListener模式实现零阻塞I/O
- **线程安全MDC**：基于contextvars的映射诊断上下文，支持异步环境
- **结构化日志**：内置JSON格式化器，完美适配ELK/Splunk
- **容错机制**：高负载下的异常隔离和优雅降级

### 🛡️ 企业级安全
- **敏感数据过滤**：自动检测和屏蔽密码、令牌等敏感信息
- **文件保护**：Windows下隐藏日志文件，权限控制
- **资源管理**：有界队列、内存保护、完善的资源清理

### 📊 监控与可观测性
- **实时指标**：队列大小、丢弃数量、错误率、采样率
- **健康检查**：内置性能监控和告警机制
- **自适应控制**：基于系统压力的动态调整

## 🚀 快速开始

### 1. 基本用法

```python
from log_framework import Slf4j, MDC

# 使用@Slf4j装饰器自动初始化
@Slf4j
class UserService:
    def process_user(self, user_id: str):
        MDC.put("user_id", user_id)
        MDC.put("request_id", "req-12345")
        
        self.logger.info("Processing user request")
        self.logger.debug(f"User data: {user_id}")
        
        # 请求完成后自动清理MDC
        MDC.clear()
```

### 2. 高性能模式配置

```python
from log_framework import LogManager

# 启用高性能模式（V7默认开启）
LogManager.load_config(async_mode=True, performance_mode=True)

# 获取指标进行监控
from log_framework.metrics import LogMetrics
metrics = LogMetrics.get_metrics()
print(f"Queue size: {metrics['queue_size']}")
print(f"Sampling rate: {metrics['sample_rate']:.2%}")
```

### 3. FastAPI集成

```python
from fastapi import FastAPI, Request
from log_framework import MDC

app = FastAPI()

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # 设置请求上下文
    MDC.put("path", str(request.url.path))
    MDC.put("method", request.method)
    MDC.put("request_id", str(uuid.uuid4()))
    
    try:
        response = await call_next(request)
        return response
    finally:
        MDC.clear()  # 始终清理上下文
```

## 📈 性能基准测试

### V7高性能模式测试结果

| 测试场景 | 吞吐量 | 延迟 | 内存使用 |
|---------------|------------|---------|--------------|
| **单线程** | **70,000 msgs/sec** | 0.014ms | 稳定 |
| **多线程(5)** | **15,600 msgs/sec** | 0.064ms | 高效 |
| **突发负载** | 自适应 | 动态 | 受保护 |
| **持续负载** | 稳定 | <1ms P99 | 有界 |

### 与其他Python日志框架对比

| 框架 | 吞吐量 | 特性 | 企业级支持 |
|-----------|------------|----------|------------------|
| **Log Framework V7** | **70K/s** | **完整** | **✅ 是** |
| Loguru | 50K/s | 良好 | 有限 |
| Structlog | 30K/s | 结构化 | 有限 |
| 标准logging | 20K/s | 基础 | 否 |

## ⚙️ 配置

### 高性能模式设置

```yaml
# log_config.yaml
version: 1
performance:
  mode: high_performance    # 启用V7特性
  queue_size: 10000        # 有界队列大小
  sampling:
    base_rate: 0.01        # 基础采样率1%
    adaptive: true         # 启用自适应采样
    max_rate: 0.10        # 高负载下最大10%
  monitoring:
    enabled: true          # 启用性能监控
    flush_interval: 1.0    # 指标刷新间隔(秒)

handlers:
  json_file:
    class: logging.handlers.TimedRotatingFileHandler
    formatter: json
    filename: ./logs/app.log
    when: "midnight"
    backupCount: 7
```

### 环境变量

```bash
# 启用高性能模式
export LOG_PERFORMANCE_MODE=high
export LOG_QUEUE_SIZE=10000
export LOG_SAMPLING_RATE=0.01

# 设置日志级别
export PYLOG_LEVEL=INFO
```

## 🔧 高级用法

### 1. 自定义性能监控

```python
from log_framework.metrics import PerformanceMonitor, LogMetrics

# 记录自定义指标
PerformanceMonitor.record_metric("custom_metric", 42.0)

# 获取详细指标
metrics = LogMetrics.get_metrics()
print(f"队列利用率: {metrics['queue_size']/10000:.1%}")
print(f"当前采样率: {metrics['sample_rate']:.2%}")
```

### 2. 自适应采样控制

```python
# 监控自适应行为
import time

# 正常负载
for i in range(1000):
    logger.info(f"Normal message {i}")

# 高负载突发
print("Starting high load burst...")
burst_start = time.time()
for i in range(50000):
    logger.info(f"Burst message {i}")

# 检查突发后的指标
metrics = LogMetrics.get_metrics()
print(f"突发期间丢弃: {metrics['dropped_total']}")
print(f"最终采样率: {metrics['sample_rate']:.2%}")
```

### 3. 内存高效批量日志

```python
# 高效的批量处理
def process_large_dataset(dataset):
    batch_size = 1000
    
    for i, record in enumerate(dataset):
        # 使用MDC添加上下文
        MDC.put("record_id", str(record.id))
        MDC.put("batch_index", str(i // batch_size))
        
        logger.info(f"Processing record: {record.name}")
        
        # 每批清理一次，防止MDC累积
        if i % batch_size == 0:
            MDC.clear()
    
    MDC.clear()  # 最终清理
```

## 🛡️ 安全最佳实践

### 敏感数据保护

```python
from log_framework.logger_setup import SensitiveDataFilter

# 配置敏感数据过滤
filter = SensitiveDataFilter()
logger.addFilter(filter)

# 自动屏蔽:
# - password=secret123 → password=***
# - Authorization: Bearer token123 → Authorization: Bearer ***
```

### 安全配置

```yaml
# 生产环境安全设置
security:
  sensitive_patterns:
    - "password=[^&\\s]+"
    - "token=[^&\\s]+"
    - "Authorization:\\s*Bearer\\s+[^\\s]+"
  
  file_permissions:
    mode: 0o600  # 严格的文件权限
    hidden: true  # Windows下隐藏日志文件
```

## 📊 监控与告警

### 与Prometheus集成

```python
# 导出指标到Prometheus
from log_framework.metrics import LogMetrics
from prometheus_client import Gauge, Counter

# 创建Prometheus指标
queue_gauge = Gauge('log_queue_size', '当前日志队列大小')
drop_counter = Counter('log_dropped_total', '总丢弃日志消息数')
sample_gauge = Gauge('log_sampling_rate', '当前采样率')

# 更新指标
def update_prometheus_metrics():
    metrics = LogMetrics.get_metrics()
    queue_gauge.set(metrics['queue_size'])
    drop_counter.inc(metrics['dropped_total'])
    sample_gauge.set(metrics['sample_rate'])
```

### 健康检查端点

```python
# FastAPI健康检查
@app.get("/health/logs")
async def log_health_check():
    metrics = LogMetrics.get_metrics()
    
    # 检查系统是否健康
    is_healthy = (
        metrics['queue_size'] < 8000 and  # 80%阈值
        metrics['sample_rate'] < 0.05 and   # 非极限压力
        metrics['error_count'] < 10          # 低错误率
    )
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "metrics": metrics,
        "thresholds": {
            "queue_size": {"current": metrics['queue_size'], "max": 8000},
            "sampling_rate": {"current": f"{metrics['sample_rate']:.2%}", "max": "5%"},
            "error_count": {"current": metrics['error_count'], "max": 10}
        }
    }
```

## 🔍 故障排查

### 高丢弃率问题

```python
# 诊断高丢弃率
metrics = LogMetrics.get_metrics()

if metrics['dropped_total'] > 1000:
    print("⚠️ 检测到高丢弃率!")
    print(f"队列大小: {metrics['queue_size']}/10000")
    print(f"采样率: {metrics['sample_rate']:.2%}")
    
    # 建议
    if metrics['queue_size'] > 8000:
        print("💡 考虑增加队列大小或减少日志量")
    if metrics['sample_rate'] > 0.05:
        print("💡 系统压力较大，考虑扩容")
```

### 性能优化

```python
# 根据用例优化
def optimize_logging():
    # 高吞吐量场景
    LogManager.load_config(
        async_mode=True,
        performance_mode=True,
        queue_size=20000,  # 更大的队列处理突发
        sampling_rate=0.005  # 更低的基础采样率
    )
    
    # 低延迟场景
    LogManager.load_config(
        async_mode=True,
        performance_mode=True,
        queue_size=5000,  # 更小的队列降低延迟
        sampling_rate=0.02  # 更高的采样率便于监控
    )
```

## 🚀 部署

### Docker部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 复制框架
COPY log_framework/ ./log_framework/
COPY requirements.txt .

# 安装依赖
RUN pip install -r requirements.txt

# 设置性能环境变量
ENV LOG_PERFORMANCE_MODE=high
ENV LOG_QUEUE_SIZE=10000
ENV PYLOG_LEVEL=INFO

# 运行应用
COPY your_app.py .
CMD ["python", "your_app.py"]
```

### Kubernetes配置

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: log-config
data:
  log_config.yaml: |
    version: 1
    performance:
      mode: high_performance
      queue_size: 10000
    
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: your-app
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: app
        image: your-app:latest
        env:
        - name: LOG_PERFORMANCE_MODE
          value: "high"
        - name: PYLOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: log_level
        volumeMounts:
        - name: log-config
          mountPath: /app/log_config.yaml
          subPath: log_config.yaml
      volumes:
      - name: log-config
        configMap:
          name: log-config
```

## 📚 文档

- [English Documentation](README.md)
- [API参考](docs/api.md)
- [架构指南](docs/architecture.md)
- [性能调优](docs/performance.md)
- [安全指南](docs/security.md)

## 🤝 贡献

我们欢迎贡献！请查看[CONTRIBUTING.md](CONTRIBUTING.md)获取指南。

## 📄 许可证

本项目采用MIT许可证 - 详见[LICENSE](LICENSE)文件。

## 🙏 致谢

- 受Java生态Log4j2和Logback的启发
- 基于Python强大的日志框架构建
- 社区驱动的开发和改进

---

**⭐ 如果您觉得这个项目有帮助，请给它一个星标！**