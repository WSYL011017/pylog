"""
验证 log_framework 是否正确安装的测试脚本
"""

def test_import():
    """测试基本导入功能"""
    try:
        from log_framework import LogManager, Slf4j, MDC, LogMetrics
        print("✓ 成功导入 log_framework 模块")
        print(f"  版本号: {log_framework.__version__}")
        return True
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False

def test_basic_logging():
    """测试基本日志功能"""
    try:
        import logging
        from log_framework import LogManager
        
        # 获取一个logger并测试
        logger = LogManager.get_logger("test_logger")
        logger.info("这是一条测试日志 - Info")
        logger.warning("这是一条测试日志 - Warning")
        logger.error("这是一条测试日志 - Error")
        
        print("✓ 基本日志功能正常")
        return True
    except Exception as e:
        print(f"✗ 基本日志功能测试失败: {e}")
        return False

def test_decorator():
    """测试 Slf4j 装饰器功能"""
    try:
        from log_framework import Slf4j
        
        @Slf4j
        class TestClass:
            def test_method(self):
                self.logger.info("通过装饰器注入的logger测试")
        
        test_obj = TestClass()
        test_obj.test_method()
        
        print("✓ Slf4j 装饰器功能正常")
        return True
    except Exception as e:
        print(f"✗ Slf4j 装饰器功能测试失败: {e}")
        return False

def test_mdc():
    """测试MDC功能"""
    try:
        from log_framework import MDC
        
        # 测试MDC功能
        MDC.put("test_key", "test_value")
        all_context = MDC.getAll()
        
        if "test_key" in all_context and all_context["test_key"] == "test_value":
            print("✓ MDC 功能正常")
            MDC.clear()  # 清理测试数据
            return True
        else:
            print("✗ MDC 功能异常")
            return False
    except Exception as e:
        print(f"✗ MDC 功能测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("="*50)
    print("Log Framework 安装验证测试")
    print("="*50)
    
    tests = [
        ("基本导入", test_import),
        ("基本日志", test_basic_logging),
        ("装饰器", test_decorator),
        ("MDC功能", test_mdc),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n测试 {test_name}...")
        if test_func():
            passed += 1
    
    print("\n" + "="*50)
    print(f"测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！Log Framework 安装成功且功能正常。")
    else:
        print("⚠️  部分测试未通过，请检查安装配置。")
    
    print("="*50)

if __name__ == "__main__":
    # 需要先导入以访问版本号
    import log_framework
    main()