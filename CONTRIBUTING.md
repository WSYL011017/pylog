# 贡献指南

欢迎你为 `pylog` 项目贡献代码！本指南将帮助你快速开始。

## 🚀 开始之前
1. **Fork 本仓库**到你自己的GitHub账号。
2. **克隆仓库**到本地：
   ```bash
   git clone https://github.com/你的用户名/pylog.git
   cd pylog
   ```
3. **添加上游远程仓库**（以便同步主仓库更新）：
   ```bash
   git remote add upstream https://github.com/WSYL011017/pylog.git
   ```

## 🌿 分支策略
所有开发工作都应在**特性分支**上进行，**切勿在 `main` 分支上直接修改**。

### 1. 创建新分支
**分支命名必须严格遵循格式：** `<类型>_<简短描述>_<日期>`。

| 类型 | 用途 | 正确示例 |
| :--- | :--- | :--- |
| `feature_` | 开发新功能 | `feature_add_async_handler_20240515` |
| `fix_` | 修复bug | `fix_race_condition_in_logger_20240510` |
| `docs_` | 修改文档 | `docs_update_readme_examples_20240512` |
| `refactor_` | 代码重构 | `refactor_config_parser_20240514` |
| `test_` | 增加或修改测试 | `test_coverage_for_filters_20240513` |

**创建分支示例：**
```bash
# 首先，确保你的本地 main 分支是最新的
git checkout main
git pull upstream main

# 基于最新的 main 分支创建你的特性分支
git checkout -b feature_your_feature_$(date +%Y%m%d)
```

### 2. 代码与提交规范
为了保持代码库的整洁和可读性，请遵循以下规范：

*   **代码格式化**：提交前，请使用 [Black](https://github.com/psf/black) 自动格式化你的Python代码。
    ```bash
    # 安装开发依赖（如果项目有requirements-dev.txt）
    # pip install -r requirements-dev.txt

    # 格式化所有代码
    black .

    # 或者只格式化你修改的文件
    black path/to/your/file.py
    ```
*   **代码质量**：建议使用 [Ruff](https://github.com/astral-sh/ruff) 或 [Flake8](https://flake8.pycqa.org/) 进行代码风格检查，确保没有明显的代码质量问题。
*   **提交信息**：请撰写清晰、简洁的提交信息。我们推荐采用[约定式提交](https://www.conventionalcommits.org/zh-hans/v1.0.0/)的格式：
    ```
    <类型>[可选 范围]: <描述>

    [可选 正文]

    [可选 脚注]
    ```
    **示例**：
    ```
    feat: 添加基于文件大小的日志轮转处理器

    - 新增 `RotatingFileHandler` 类
    - 添加了相应的单元测试
    - 更新了配置文档

    修复 #12
    ```

### 3. 处理代码冲突
当你准备提交Pull Request时，你的分支可能已经落后于上游的 `main` 分支。**你有责任解决所有合并冲突**。

**推荐使用 `rebase`（变基）** 来同步更新，这能使提交历史保持线性清晰。

```bash
# 1. 切换到你的特性分支
git checkout feature_your_feature_20240515

# 2. 获取上游 main 分支的最新更改
git fetch upstream main

# 3. 执行交互式变基，将你的修改“重放”在最新代码之上
git rebase -i upstream/main

# 如果在变基过程中出现冲突，Git会暂停。
# 4. 解决冲突：编辑标记为“CONFLICT”的文件，保留所需代码，删除冲突标记（<<<<, ====, >>>>）。
# 5. 标记冲突已解决并继续变基：
git add 已解决的文件
git rebase --continue

# 如果中途想取消变基，使用：
git rebase --abort

# 6. 变基完成后，强制推送到你的Fork仓库（因为你改写了历史）
git push --force-with-lease origin feature_your_feature_20240515
```
> **注意**：`--force-with-lease` 比 `--force` 更安全，它会检查远程分支是否已被他人更新。

### 4. 发起 Pull Request (PR)
1.  将你的分支推送到你的Fork仓库。
2.  在GitHub上，从你的分支向主仓库的 `main` 分支发起Pull Request。
3.  **请使用我们提供的PR模板**，清晰描述你的变更内容、动机以及相关的Issue编号。
4.  确保所有CI检查（如果配置了）通过。
5.  项目维护者将会审查你的代码，并可能提出修改意见。请及时跟进讨论。

## ❓ 需要帮助？
如果你有任何疑问：
*   可以先查看项目的 [README.md](./README.md)。
*   在相关的GitHub Issue中进行讨论。
*   如果你发现了Bug或有新功能建议，欢迎**先创建一个新的Issue**进行讨论，然后再开始编码。

感谢你的宝贵贡献！🎉
```

这个文件已经整合了你要求的所有关键要素：
- ✅ 严格的分支命名规则：`<类型>_<简短描述>_<日期>`
- ✅ 详细的代码冲突解决流程（使用`rebase`）
- ✅ Python项目特定的开发规范（Black格式化、代码质量检查）
- ✅ 完整的贡献流程指引

你可以直接复制上面的全部内容，在你的仓库根目录创建`CONTRIBUTING.md`文件。如果需要调整任何部分，请告诉我。
