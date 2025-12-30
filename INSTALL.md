# Log Framework 安装说明

## 安装方式

### 1. 从 PyPI 安装（推荐）

```bash
pip install log-framework
```

### 2. 从源码安装

#### 2.1 直接从 GitHub 安装

```bash
pip install git+https://github.com/your-repo/log-framework.git
```

#### 2.2 本地安装

```bash
# 克隆或下载源码后
cd log-framework
pip install .
```

#### 2.3 开发模式安装

```bash
pip install -e .
```

### 3. 构建并安装

```bash
# 构建包
python setup.py sdist bdist_wheel

# 安装构建的包
pip install dist/log_framework-*.whl
```

## 依赖项

- Python >= 3.7
- PyYAML >= 5.4.0

## 验证安装

安装完成后，可以通过以下方式验证：

```python
from log_framework import LogManager, Slf4j

# 测试导入
print("Log Framework 安装成功!")

# 测试基本功能
@Slf4j
class TestClass:
    def test_log(self):
        self.logger.info("测试日志功能")

test = TestClass()
test.test_log()
```

## 升级

```bash
pip install --upgrade log-framework
```

## 卸载

```bash
pip uninstall log-framework
```