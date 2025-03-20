import unittest
import pandas as pd
import numpy as np
from src.core.stock_data_fetcher import get_stock_list, get_stock_data

class TestStockDataFetcher(unittest.TestCase):
    def test_stock_list_structure(self):
        """测试股票列表的数据结构"""
        stocks = get_stock_list()
        self.assertIsInstance(stocks, pd.DataFrame)
        required_columns = ['symbol', 'name']
        for col in required_columns:
            self.assertIn(col, stocks.columns)
            
    def test_stock_code_format(self):
        """测试股票代码格式"""
        stocks = get_stock_list()
        if len(stocks) > 0:
            # 测试股票代码格式
            self.assertTrue(all(stocks['symbol'].str.match(r'^\d{6}$')))
            
    def test_stock_data_structure(self):
        """测试股票数据结构"""
        stocks = get_stock_list()
        if len(stocks) > 0:
            # 测试第一个股票的数据
            test_stock = stocks.iloc[0]['symbol']
            data = get_stock_data(test_stock)
            if data is not None:
                required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                for col in required_columns:
                    self.assertIn(col, data.columns)
                    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效的股票代码
        invalid_data = get_stock_data('000000')
        self.assertTrue(invalid_data.empty)
            
    def test_valid_stock(self):
        """测试有效股票数据获取"""
        # 测试一个已知的股票代码
        data = get_stock_data('000001')  # 平安银行
        self.assertIsNotNone(data)
        if data is not None:
            self.assertFalse(data.empty)
            
def run_tests():
    """运行所有测试"""
    print("Starting automated tests...")
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestStockDataFetcher)
    test_result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    return test_result.wasSuccessful()

if __name__ == '__main__':
    run_tests() 