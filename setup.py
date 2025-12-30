import os
from setuptools import setup, find_packages

# 读取 README 文件内容作为 long_description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# 读取 requirements（如果有的话）
def get_requirements():
    # 检查是否存在 requirements.txt 文件
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(requirements_path):
        with open(requirements_path, "r", encoding="utf-8") as fh:
            return [line.strip() for line in fh if line.strip() and not line.startswith("#")]
    else:
        # 默认的依赖列表
        return [
            "PyYAML>=5.4.0",
        ]

setup(
    name="log-framework",
    version="1.0.0",
    author="",
    author_email="",
    description="A production-ready asynchronous logging framework for Python with Log4j2-like features",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/log-framework",  # 请替换为实际的仓库地址
    packages=find_packages(include=['log_framework', 'log_framework.*']),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Logging",
    ],
    python_requires=">=3.7",
    install_requires=get_requirements(),
    include_package_data=True,
    package_data={
        'log_framework': ['log_config.yaml'],
    },
    entry_points={
        'console_scripts': [
            # 如果有命令行工具，可以在这里添加
        ],
    },
)