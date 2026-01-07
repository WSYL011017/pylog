# GitHub Actions Workflows Guide

本项目已配置自动化 CI/CD 流程，基于 GitHub Actions 实现。

## 1. 自动化测试与代码检查 (CI)

**文件**: `.github/workflows/ci.yml`

每次推送到 `main` 分支或提交 Pull Request 时触发。

**包含步骤**:
- **多版本测试**: 在 Python 3.8 - 3.12 环境下运行测试。
- **代码检查**: 使用 `flake8` 检查语法错误和代码风格。
- **单元测试**: 运行 `pytest` 测试套件。

## 2. 自动发布 (Release)

**文件**: `.github/workflows/release.yml`

当推送以 `v` 开头的标签（如 `v2.2.0`）时触发。

**包含步骤**:
- **构建**: 生成 Wheel 和 Source Tarball。
- **发布到 PyPI**: 将包上传到 Python Package Index。
- **GitHub Release**: 自动创建 GitHub Release 页面并上传构建产物。

### 配置要求
要在 GitHub 上启用发布功能，您需要在仓库的 `Settings > Secrets and variables > Actions` 中添加以下密钥：

| Secret Name | 描述 |
| :--- | :--- |
| `PYPI_API_TOKEN` | PyPI 的 API Token (从 pypi.org 获取) |

## 启用方式

1. 将 `.github` 目录推送到 GitHub 仓库。
2. 只要推送代码，CI 就会自动运行。
3. 要发布新版本：
   ```bash
   git tag v2.2.0
   git push origin v2.2.0
   ```
