# 🎓 极简上手指南 (Examples)

欢迎使用 **Python Enterprise Log Framework**！
这里有 4 个最简单的例子，帮你 1 分钟上手。

## 📂 目录

1.  **[1_simple_usage.py](./1_simple_usage.py)** 🟢 **Hello World**
    *   最简单的用法。
    *   只需加上 `@Slf4j`，然后用 `self.logger.info(...)`。
2.  **[2_context_magic.py](./2_context_magic.py)** 🟡 **上下文魔法**
    *   展示了如何给日志自动加上 `user_id` 或 `req_id`。
    *   不用在每行日志里都手动写参数！
3.  **[3_web_server_demo.py](./3_web_server_demo.py)** 🔵 **Web 服务模拟**
    *   模拟真实的 Web 服务器场景。
    *   展示了如何追踪请求、处理错误堆栈。
4.  **[4_use_config.py](./4_use_config.py)** 🟣 **使用配置文件**
    *   教你如何用 `logging.yaml` 控制日志级别和输出格式。

## 🏃 如何运行？

直接在终端里运行 Python 脚本即可：

```bash
# 进入 examples 目录
cd examples

# 运行第一个例子
python 1_simple_usage.py

# 运行第二个例子
python 2_context_magic.py
```

运行后，你会在控制台看到日志，也会在 `logs/` 目录下看到生成的日志文件。
