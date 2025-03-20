import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.core.kmj_indicator import calculate_kmj_indicators, get_kmj_signals
from src.core.stock_data_fetcher import get_stock_data
from src.core.stock_analyzer import calculate_technical_score

class TestKMJSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """测试开始前的准备工作"""
        # 创建测试数据
        cls.test_data = pd.DataFrame({
            'date': pd.date_range(start='2024-01-01', periods=30),
            'open': np.random.uniform(10, 20, 30),
            'high': np.random.uniform(15, 25, 30),
            'low': np.random.uniform(5, 15, 30),
            'close': np.random.uniform(10, 20, 30),
            'volume': np.random.uniform(1000000, 5000000, 30)
        })
        # 确保high总是最高价，low总是最低价
        cls.test_data['high'] = cls.test_data[['open', 'close', 'high']].max(axis=1)
        cls.test_data['low'] = cls.test_data[['open', 'close', 'low']].min(axis=1)

    def test_kmj_indicators_calculation(self):
        """测试KMJ指标计算"""
        # 计算KMJ指标
        data = calculate_kmj_indicators(self.test_data)
        
        # 验证KMJ1计算
        self.assertTrue('KMJ1' in data.columns)
        self.assertTrue(all(~pd.isna(data['KMJ1'])))
        
        # 验证KMJ2计算（前20个值应该是NaN）
        self.assertTrue('KMJ2' in data.columns)
        self.assertTrue(all(pd.isna(data['KMJ2'][:20])))
        self.assertTrue(all(~pd.isna(data['KMJ2'][20:])))
        
        # 验证KMJ3计算（前24个值应该是NaN）
        self.assertTrue('KMJ3' in data.columns)
        self.assertTrue(all(pd.isna(data['KMJ3'][:24])))
        self.assertTrue(all(~pd.isna(data['KMJ3'][24:])))

    def test_kmj_signals(self):
        """测试KMJ信号生成"""
        # 计算KMJ指标和信号
        data = calculate_kmj_indicators(self.test_data)
        data = get_kmj_signals(data)
        
        # 验证信号列存在
        self.assertTrue('KMJ_TREND' in data.columns)
        self.assertTrue('KMJ_BUY_SIGNAL' in data.columns)
        self.assertTrue('KMJ_SELL_SIGNAL' in data.columns)
        
        # 验证信号值是否合法
        valid_trends = [-1, 0, 1]
        self.assertTrue(all(x in valid_trends for x in data['KMJ_TREND'].dropna()))
        self.assertTrue(all(isinstance(x, bool) for x in data['KMJ_BUY_SIGNAL'].dropna()))
        self.assertTrue(all(isinstance(x, bool) for x in data['KMJ_SELL_SIGNAL'].dropna()))

    def test_technical_score(self):
        """测试技术得分计算"""
        # 计算技术得分
        score = calculate_technical_score(self.test_data)
        
        # 验证得分范围（0-100分）
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        
        # 验证得分精度（保留2位小数）
        self.assertEqual(score, round(score, 2))
        
        # 测试极端情况
        # 创建一个理想的上涨趋势数据
        perfect_data = self.test_data.copy()
        perfect_data['close'] = np.linspace(10, 20, 30)  # 完美上涨趋势
        perfect_data['volume'] = np.ones(30) * 5000000   # 放量
        perfect_score = calculate_technical_score(perfect_data)
        self.assertGreater(perfect_score, 50)  # 强势股票应该得到高分
        
        # 创建一个下跌趋势数据
        bad_data = self.test_data.copy()
        bad_data['close'] = np.linspace(20, 10, 30)  # 下跌趋势
        bad_data['volume'] = np.ones(30) * 1000000   # 缩量
        bad_score = calculate_technical_score(bad_data)
        self.assertLess(bad_score, 50)  # 弱势股票应该得到低分

    def test_data_fetcher(self):
        """测试数据获取功能"""
        # 获取示例股票数据
        data = get_stock_data('000001', days=30)
        
        # 验证数据结构
        self.assertIsNotNone(data)
        self.assertIsInstance(data, pd.DataFrame)
        
        # 验证必要的列
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            self.assertIn(col, data.columns)

    def test_edge_cases(self):
        """测试边缘情况"""
        # 测试空数据
        empty_df = pd.DataFrame()
        with self.assertRaises(ValueError):
            calculate_kmj_indicators(empty_df)
        
        # 测试数据量不足
        small_df = self.test_data.head(10)
        data = calculate_kmj_indicators(small_df)
        self.assertTrue(all(pd.isna(data['KMJ2'])))
        self.assertTrue(all(pd.isna(data['KMJ3'])))
        
        # 测试含有NaN的数据
        nan_df = self.test_data.copy()
        nan_df.loc[5:10, 'close'] = np.nan
        data = calculate_kmj_indicators(nan_df)
        self.assertTrue(any(pd.isna(data['KMJ1'])))

def run_tests():
    """运行所有测试"""
    unittest.main(argv=[''], verbosity=2, exit=False)

if __name__ == '__main__':
    run_tests() 