---
name: 🐛 报告缺陷
about: 创建一份缺陷报告以帮助我们改进 PyLog
title: '[BUG] '
labels: ['bug', 'needs-triage']
assignees: ''

---

**缺陷描述**
请清晰而简洁地描述缺陷是什么。

**重现步骤**
1. 配置情况：'...'
2. 执行代码：'...'
3. 触发条件：'...'
4. 观察到的错误行为：'...'

**预期行为**
清晰而简洁地描述你期望发生的正确行为。

**日志输出/错误回溯**
如果可能，请粘贴完整的错误回溯信息或异常的日志输出。
```python
# 触发问题的代码示例（如果相关）
import pylog
logger = pylog.getLogger(__name__)
# 触发问题的调用
logger.error("这里出错了", exc_info=True)
```

**配置文件示例**
如果你的问题与配置相关，请提供你的 `pylog` 配置文件（YAML/JSON/字典）的**简化示例**。
```yaml
# 例如：pylog_config.yaml
configuration:
  appenders:
    console:
      type: Console
      target: SYSTEM_OUT
      json_layout:
        compact: false
  loggers:
    root:
      level: DEBUG
      appender_refs:
        - ref: console
```

**运行环境**
请提供以下关键信息：
 - **操作系统**: [例如: Ubuntu 22.04, macOS Sonoma 14.4, Windows 11 23H2]
 - **Python 版本**: [例如: 3.8.10, 3.11.6] （可通过 `python --version` 获取）
 - **PyLog 版本**: [例如: 2.0.0] （可通过 `pip show pylog-4j` 或 `pylog.__version__` 获取）
 - **相关依赖版本**（如果问题可能涉及）:
   - `pyyaml` 版本: [如果通过YAML配置]
   - `concurrent-log-handler` 等: [如果使用特定Appender]

**可能的原因分析与附加信息**
如果你对问题的原因有任何猜测、调查线索，或者可以补充其他可能有助于诊断的上下文（例如：该问题在多线程/异步环境下才会出现、在特定日志级别下发生、与某个特定Appender或Filter相关等），请在此处说明。

**检查清单**
- [ ] 我已确认在 `CONTRIBUTING.md` 中搜索过类似问题。
- [ ] 我已提供尽可能详细的重现步骤。
- [ ] 我已提供相关的配置、代码和日志信息。
- [ ] 我已确认提供的环境信息准确无误。
