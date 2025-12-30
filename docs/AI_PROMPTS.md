# 🤖 AI Co-Pilot Prompts for Framework Development

This collection contains the specific prompts and interaction strategies used to build, refine, and optimize this Enterprise Log Framework. Use these prompts to guide an AI assistant (like ChatGPT, Claude, or Trae) in maintaining or extending the project.

## 🏗️ 1. Architecture Design Prompts

**Context**: Initial setup and high-level design.

> **Prompt**:
> "Act as a Senior Python Architect. I need to design a high-performance, asynchronous logging framework for Python that mimics Java's Log4j2/Logback capabilities.
>
> **Requirements**:
> 1. **Non-blocking I/O**: Use `QueueHandler` and `QueueListener`.
> 2. **Context Propagation**: Must support `contextvars` for async/await (MDC equivalent).
> 3. **Structured Logging**: Native JSON output support.
> 4. **Developer Experience**: Provide a `@Slf4j` style decorator for logger injection.
>
> Please provide a high-level class diagram (Mermaid) and the core project structure. Explain how you will handle the 'Context Loss' problem in async execution."

## 🔍 2. Code Review & Refactoring Prompts

**Context**: Improving code quality and thread safety.

> **Prompt**:
> "Review the following Python logging code for **Thread Safety** and **Asyncio Compatibility**.
>
> **Focus Areas**:
> 1. Are there any race conditions in the `LogManager` initialization?
> 2. Will `MDC.put()` work correctly if called inside `asyncio.create_task`?
> 3. Is the `QueueListener` shutdown process graceful?
>
> **Code**:
> [Paste Code Here]
>
> Provide a 'Critical Issues' list and a refactored version of the `add_async_handler` method using appropriate locking mechanisms."

## 🚀 3. Performance Optimization Prompts

**Context**: Solving bottlenecks (e.g., `qsize()` lock contention).

> **Prompt**:
> "I have a Python `QueueHandler` that calls `queue.qsize()` on every log record to update metrics. In high concurrency (10k QPS), this is causing significant lock contention.
>
> **Task**:
> Propose an optimization strategy to monitor queue size without locking on every write.
>
> **Constraints**:
> - Must maintain reasonable accuracy (e.g., +/- 10%).
> - Cannot introduce external dependencies like Redis.
>
> **Ideas**:
> - Probabilistic Sampling?
> - Atomic Counters?
>
> Please implement the 'Adaptive Sampling' solution in Python."

## 🛡️ 4. Security Implementation Prompts

**Context**: Implementing sensitive data masking.

> **Prompt**:
> "Implement a `SensitiveDataFilter` for the Python logging module.
>
> **Requirements**:
> 1. It must be a standard `logging.Filter`.
> 2. It should use regex to identify patterns like `password=...`, `token=...`, `Bearer ...`.
> 3. It must replace the sensitive value with `***`.
> 4. **Performance**: Compile regex patterns only once.
>
> **Bonus**: How can we make this filter configurable via a YAML file?"

## 🧪 5. Unit Testing Prompts

**Context**: Generating robust test cases.

> **Prompt**:
> "Write a `pytest` test suite for the `LogManager` class.
>
> **Scenarios to Cover**:
> 1. **Concurrency**: 10 threads trying to call `LogManager.load_config()` simultaneously.
> 2. **Hot Reload**: Modifying the YAML file and calling `reload_config()` to verify level changes.
> 3. **Context Isolation**: Verify that `MDC` set in Thread A does not leak into Thread B.
>
> Use `unittest.mock` to mock file system operations where appropriate."

## 📝 6. Documentation Generation Prompts

**Context**: Creating the README and User Guide.

> **Prompt**:
> "Generate a comprehensive `README.md` for this library 'log_framework'.
>
> **Sections Required**:
> 1. **Features**: Bullet points of key capabilities (Async, MDC, etc.).
> 2. **Quick Start**: 3-step installation and usage guide.
> 3. **Configuration**: A sample `logging.yaml` file with comments.
> 4. **Architecture**: A Mermaid diagram explaining the data flow.
> 5. **Best Practices**: When to use Async vs Sync logging.
>
> Tone: Professional, Enterprise-grade."
