import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_stock_list():
    """获取股票列表"""
    try:
        # 登录系统
        lg = bs.login()
        if lg.error_code != '0':
            logger.error('login error: %s' % lg.error_msg)
            return pd.DataFrame()
            
        # 获取股票基础信息
        logger.info("Getting stock list from baostock...")
        rs = bs.query_stock_basic()
        if rs.error_code != '0':
            logger.error(f'query_stock_basic error: {rs.error_msg}')
            return pd.DataFrame()
            
        # 获取数据
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        # 创建DataFrame
        stocks_df = pd.DataFrame(data_list, columns=rs.fields)
        
        # 获取行业信息
        industry_df = get_industry_data()
        if not industry_df.empty:
            stocks_df = stocks_df.merge(industry_df, on='code', how='left')
            
        # 初始化技术得分列
        stocks_df['technical_score'] = 0.0
        
        # 只保留A股
        stocks_df = stocks_df[stocks_df['type'] == '1']
        
        # 确保必要的列存在
        required_columns = ['code', 'code_name', 'industry']
        for col in required_columns:
            if col not in stocks_df.columns:
                stocks_df[col] = ''
                
        # 重命名列
        stocks_df = stocks_df.rename(columns={
            'code': 'symbol',
            'code_name': 'name'
        })
        
        # 清理股票代码（去掉市场前缀）
        stocks_df['symbol'] = stocks_df['symbol'].apply(lambda x: x.split('.')[-1])
        
        return stocks_df
        
    except Exception as e:
        logger.error(f"Error getting stock list: {str(e)}")
        return pd.DataFrame()
    finally:
        bs.logout()

def get_industry_data():
    """获取行业数据"""
    try:
        # 登录系统
        lg = bs.login()
        if lg.error_code != '0':
            logger.error('login error: %s' % lg.error_msg)
            return pd.DataFrame()
            
        # 获取行业分类数据
        rs = bs.query_stock_industry()
        if rs.error_code != '0':
            logger.error(f'query_stock_industry error: {rs.error_msg}')
            return pd.DataFrame()
            
        # 获取数据
        industry_list = []
        while (rs.error_code == '0') & rs.next():
            industry_list.append(rs.get_row_data())
            
        # 创建DataFrame
        if industry_list:
            industry_df = pd.DataFrame(industry_list, columns=rs.fields)
            logger.info(f"Available industry columns: {industry_df.columns.tolist()}")
            
            # 确保必要的列存在
            if 'industry' not in industry_df.columns:
                industry_df['industry'] = '其他'
                
            # 处理空值和无效值
            industry_df['industry'] = industry_df['industry'].fillna('其他')
            industry_df['industry'] = industry_df['industry'].replace('', '其他')
            
            # 清理股票代码
            industry_df['code'] = industry_df['code'].apply(lambda x: x.split('.')[-1])
            
            return industry_df[['code', 'industry']]
            
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Error getting industry data: {str(e)}")
        return pd.DataFrame()
    finally:
        bs.logout()

def get_stock_data(stock_code, days=30):
    """获取股票历史数据"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 尝试从baostock获取数据
        lg = bs.login()
        if lg.error_code != '0':
            logger.error('login error: %s' % lg.error_msg)
            return pd.DataFrame()
            
        # 添加市场前缀
        if stock_code.startswith('6'):
            bs_code = f"sh.{stock_code}"
        else:
            bs_code = f"sz.{stock_code}"
            
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,open,high,low,close,volume",
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            frequency="d",
            adjustflag="3"
        )
        
        if rs.error_code != '0':
            logger.error(f'query_history_k_data_plus error: {rs.error_msg}')
            return pd.DataFrame()
            
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
            
        if data_list:
            df = pd.DataFrame(data_list, columns=rs.fields)
            # 转换数据类型
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
            df['date'] = pd.to_datetime(df['date'])
            return df
            
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Error getting stock data: {str(e)}")
        return pd.DataFrame()
    finally:
        bs.logout()

# 确保程序退出时登出baostock
import atexit
atexit.register(bs.logout) 