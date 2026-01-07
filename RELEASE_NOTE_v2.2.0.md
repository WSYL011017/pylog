# PyLog v2.2.0 Release Notes

## 新特性 (New Features)
- **自定义日志格式 (PatternLayout)**: 引入了 `PatternFormatter`，支持用户通过字符串模板自定义日志输出格式。
  - 支持占位符：`%d` (时间), `%t` (线程名), `%p` (日志级别), `%c` (Logger名), `%m` (消息), `%n` (换行), `%F` (文件名), `%L` (行号), `%M` (方法名)。
  - 示例配置：`pattern: "%d [%t] %p %c - %m%n"`。
- **增强的元数据采集**: `LogEvent` 现在默认捕获线程名、进程名、文件名、行号及函数名，为调试提供更多上下文。
- **配置加载器更新**: `ConfigLoader` 已更新以支持 `pattern_layout` 配置项。

## 改进 (Improvements)
- **包名变更**: 项目包名已正式更改为 `pylog-4j`，以避免 PyPI 命名冲突并明确项目定位。
- **调用栈优化**: 优化了 `Logger` 内部的堆栈遍历逻辑，确保在包装方法（如 `warn`）中也能正确获取调用者信息。

## 修复 (Bug Fixes)
- 修复了 `warn` 方法调用栈深度不正确导致无法获取准确行号的问题。

## 安装 (Installation)
```bash
pip install pylog-4j
```
