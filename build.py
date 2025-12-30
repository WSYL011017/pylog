#!/usr/bin/env python
"""
构建脚本
用于打包 log-framework 项目
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示描述"""
    print(f"\n>>> {description}")
    print(f"执行命令: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True, cwd=os.getcwd())
        print("✓ 命令执行成功")
        if result.stdout:
            print(f"输出:\n{result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 命令执行失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def main():
    print("=== Log Framework 打包工具 ===")
    print(f"当前工作目录: {os.getcwd()}")
    
    # 检查必要文件
    required_files = ['setup.py', 'pyproject.toml', 'log_framework/__init__.py']
    missing_files = [f for f in required_files if not Path(f).exists()]
    
    if missing_files:
        print(f"错误: 缺少必要文件: {missing_files}")
        return 1
    
    print("\n开始构建过程...")
    
    # 1. 安装构建依赖
    if not run_command("pip install --upgrade setuptools wheel", 
                      "安装/升级构建工具"):
        return 1
    
    # 2. 清理之前的构建产物
    run_command("rmdir /s /q build dist *.egg-info 2>nul || echo 清理完成", 
                "清理之前的构建产物")
    
    # 3. 构建源码分发包和wheel包
    if not run_command("python setup.py sdist bdist_wheel", 
                      "构建源码分发包和wheel包"):
        return 1
    
    print("\n=== 构建完成 ===")
    print("构建产物位置:")
    print("- 源码包: dist/*.tar.gz")
    print("- Wheel包: dist/*.whl")
    
    # 检查构建产物
    dist_path = Path("dist")
    if dist_path.exists():
        print("\n生成的文件:")
        for file in dist_path.glob("*"):
            print(f"  - {file}")
    
    print("\n现在您可以使用以下命令安装:")
    print("  pip install dist/log_framework-*.whl")
    print("\n或者上传到PyPI:")
    print("  pip install twine")
    print("  twine upload dist/*")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())