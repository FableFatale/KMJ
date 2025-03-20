#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
应用程序启动脚本
先运行测试，如果测试通过则启动应用程序
"""

import os
import sys
import subprocess
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """主函数：运行测试并启动应用"""
    # 设置工作目录为脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print("=" * 50)
    print("自动选股系统启动脚本")
    print("=" * 50)
    
    # 运行测试
    print("\n[1/2] 运行自动化测试...")
    success = run_tests()
    
    if not success:
        print("\n❌ 测试失败，请修复上述问题后再运行应用。")
        sys.exit(1)
    
    # 如果测试通过，启动应用
    print("\n✅ 所有测试通过!")
    print("\n[2/2] 启动应用程序...")
    
    try:
        # 使用subprocess调用streamlit run app.py
        subprocess.run(["streamlit", "run", "app.py"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"启动应用程序失败: {e}")
        print(f"\n❌ 启动应用程序失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ 应用程序被用户中断")
    except Exception as e:
        logger.error(f"发生未知错误: {e}")
        print(f"\n❌ 发生未知错误: {e}")
        sys.exit(1)

def run_tests():
    """运行测试并返回是否成功"""
    try:
        # 从test_stock_data_fetcher.py导入run_tests函数
        # 如果导入失败，使用pytest运行所有测试
        try:
            from test_stock_data_fetcher import run_tests as run_fetcher_tests
            return run_fetcher_tests()
        except ImportError:
            logger.warning("无法导入test_stock_data_fetcher.py中的run_tests函数，尝试使用pytest")
            import pytest
            result = pytest.main(["-v"])
            return result == 0
    except Exception as e:
        logger.error(f"运行测试失败: {e}")
        print(f"运行测试失败: {e}")
        return False

if __name__ == "__main__":
    main() 