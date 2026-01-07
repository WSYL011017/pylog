# PyLog v2.2.0 Release Notes

We are excited to announce the release of **PyLog v2.2.0**! This release brings significant flexibility to log formatting with the new **Pattern Layout** support, allowing developers to define custom log message structures similar to Log4j2's PatternLayout.

## 🚀 New Features (新特性)

### 1. Custom Pattern Layout (自定义日志格式)
You can now customize your log output format using a pattern string, moving beyond the default JSON format.
- **Class**: `pylog.formatters.pattern_formatter.PatternFormatter`
- **Config Key**: `pattern_layout`

**Supported Placeholders:**
- `%d`: Timestamp (ISO8601) (时间)
- `%t`: Thread Name (线程名)
- `%p`: Log Level (日志级别)
- `%c`: Logger Name (Logger名称/类名)
- `%m`: Log Message (消息)
- `%n`: Newline (换行)
- `%F`: File Name (文件名)
- `%L`: Line Number (行号)
- `%M`: Method/Function Name (方法/函数名)

### 2. Enhanced Context Capture (增强上下文采集)
The core Logger has been upgraded to automatically capture rich context information for every log event:
- **Caller Info**: Automatically detects the calling file, line number, and function name.
- **Thread & Process**: Automatically captures current thread and process names.

## 🛠 Improvements (改进)

- **Configuration Loader**: Updated to support `pattern_layout` in YAML configuration files.
- **Robustness**: Improved stack walking mechanism to accurately identify caller frames, ignoring internal logger frames.

## 📦 Installation (安装)

You can install the latest version from PyPI (once uploaded) or directly from the wheel file:

```bash
pip install pylog==2.2.0
```

Or install from the built wheel:

```bash
pip install dist/pylog-2.2.0-py3-none-any.whl
```

## 📝 Configuration Example (配置示例)

To use the new Pattern Layout, update your `pylog_config.yaml`:

```yaml
appenders:
  console:
    type: Console
    target: SYSTEM_OUT
    pattern_layout:
      # Example: 2026-01-07 10:00:00 [MainThread] INFO MyClass.run:42 - Processing started
      pattern: "%d [%t] %p %c.%M:%L - %m%n"

loggers:
  root:
    level: INFO
    appender_refs:
      - ref: console
```

## 🤝 Contributors

- PyLog Team
