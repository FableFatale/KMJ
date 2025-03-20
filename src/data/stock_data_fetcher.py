import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json
import requests
import baostock as bs
import time
import re

# Load environment variables
load_dotenv()

def ensure_baostock_login():
    """Ensure baostock is logged in before making queries"""
    try:
        bs.logout()  # Logout first to ensure clean state
    except:
        pass
    
    login_result = bs.login()
    if login_result.error_code != '0':
        raise Exception(f"Failed to login to baostock: {login_result.error_msg}")
    return login_result

# Initialize baostock
ensure_baostock_login()

def format_stock_code(code):
    """Format stock code for different data sources"""
    # Remove any existing prefixes or suffixes
    code = re.sub(r'^s[hz]\.?|\.S[SZ]$', '', code)
    
    # Ensure 6 digits
    if len(code) > 6:
        code = code[-6:]
    elif len(code) < 6:
        code = code.zfill(6)
    
    # Determine market
    is_sh = code.startswith('6')
    
    # Format for different sources
    baostock_code = f"{'sh' if is_sh else 'sz'}.{code}"  # sh.600000 or sz.000001
    yfinance_code = f"{code}.{'SS' if is_sh else 'SZ'}"  # 600000.SS or 000001.SZ
    
    return baostock_code, yfinance_code

def get_stock_list_from_sina():
    """从新浪财经获取股票列表"""
    try:
        url = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=4000&sort=symbol&asc=1&node=hs_a"
        response = requests.get(url, timeout=10)
        stocks_data = json.loads(response.text)
        
        if not isinstance(stocks_data, list) or not stocks_data:
            return None
            
        stocks = pd.DataFrame(stocks_data)
        
        # 重命名列
        column_mappings = {
            'symbol': 'symbol',
            'code': 'symbol',
            'name': 'name',
            'trade': 'price',
            'changepercent': 'change'
        }
        
        # 只保留需要的列
        stocks = stocks.rename(columns=column_mappings)
        stocks = stocks[['symbol', 'name']]
        
        # 清理股票代码
        stocks['symbol'] = stocks['symbol'].apply(lambda x: x.replace('sh', '').replace('sz', ''))
        
        return stocks
        
    except Exception as e:
        print(f"Error getting stock list from Sina: {str(e)}")
        return None

def get_industry_data():
    """获取行业数据"""
    try:
        # 登录系统
        lg = bs.login()
        if lg.error_code != '0':
            print('login error: %s' % lg.error_msg)
            return pd.DataFrame()
            
        # 获取行业分类数据
        rs = bs.query_stock_industry()
        if rs.error_code != '0':
            print(f'query_stock_industry error: {rs.error_msg}')
            return pd.DataFrame()
            
        # 获取数据
        industry_list = []
        while (rs.error_code == '0') & rs.next():
            industry_list.append(rs.get_row_data())
            
        # 创建DataFrame
        if industry_list:
            industry_df = pd.DataFrame(industry_list, columns=rs.fields)
            print(f"Available industry columns: {industry_df.columns.tolist()}")
            
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
        print(f"Error getting industry data: {str(e)}")
        return pd.DataFrame()
    finally:
        bs.logout()

def get_stock_list():
    """获取股票列表"""
    try:
        # 登录系统
        lg = bs.login()
        if lg.error_code != '0':
            print('login error: %s' % lg.error_msg)
            return pd.DataFrame()
            
        # 获取股票基础信息
        print("Getting stock list from baostock...")
        rs = bs.query_stock_basic()
        if rs.error_code != '0':
            print(f'query_stock_basic error: {rs.error_msg}')
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
        
        # 更新技术得分
        for idx, row in stocks_df.iterrows():
            try:
                # 获取股票数据
                stock_data = get_stock_data(row['symbol'], days=60)
                if not stock_data.empty:
                    # 计算技术得分
                    from stock_analyzer import calculate_technical_score
                    score = calculate_technical_score(stock_data)
                    stocks_df.loc[idx, 'technical_score'] = score
            except Exception as e:
                print(f"Error calculating technical score for {row['symbol']}: {str(e)}")
                continue
                
        return stocks_df
        
    except Exception as e:
        print(f"Error getting stock list: {str(e)}")
        return pd.DataFrame()
    finally:
        bs.logout()

def get_stock_data_baostock(symbol, days=60):
    """Get stock data using baostock"""
    try:
        ensure_baostock_login()
        
        # Format stock code for baostock
        baostock_code, _ = format_stock_code(symbol)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days*2)
        
        rs = bs.query_history_k_data_plus(
            baostock_code,
            "date,open,high,low,close,volume",
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            frequency="d",
            adjustflag="3"
        )
        
        if rs.error_code != '0':
            print(f"Baostock error for {baostock_code}: {rs.error_msg}")
            return None
        
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())
        
        if not data_list:
            print(f"No data received from baostock for {baostock_code}")
            return None
        
        df = pd.DataFrame(data_list, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        
        # Convert data types
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d')
        
        if len(df) > days:
            df = df.tail(days)
        
        return df.reset_index(drop=True)
        
    except Exception as e:
        print(f"Error fetching data from baostock for {symbol}: {str(e)}")
        return None

def get_stock_data(stock_code, days=60):
    """获取股票历史数据"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 尝试从baostock获取数据
        lg = bs.login()
        if lg.error_code != '0':
            print('login error: %s' % lg.error_msg)
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
            print(f'query_history_k_data_plus error: {rs.error_msg}')
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
            
            # 计算KMJ指标
            from stock_analyzer import calculate_kmj_indicators
            df = calculate_kmj_indicators(df)
            
            return df
            
        return pd.DataFrame()
        
    except Exception as e:
        print(f"Error getting stock data: {str(e)}")
        return pd.DataFrame()
    finally:
        bs.logout()

def get_realtime_quotes(ts_codes, max_retries=3, retry_delay=2):
    """Get current day's data for multiple stocks"""
    results = []
    for ts_code in ts_codes:
        # For A-shares, try baostock first
        if re.match(r'^[0-9]{6}\.(SS|SZ)$', ts_code):
            try:
                ensure_baostock_login()
                baostock_code, _ = format_stock_code(ts_code)
                
                rs = bs.query_history_k_data_plus(
                    baostock_code,
                    "date,open,high,low,close,volume",
                    start_date=datetime.now().strftime('%Y-%m-%d'),
                    end_date=datetime.now().strftime('%Y-%m-%d'),
                    frequency="d",
                    adjustflag="3"
                )
                
                if rs.error_code == '0':
                    data_list = []
                    while (rs.error_code == '0') and rs.next():
                        data_list.append(rs.get_row_data())
                    
                    if data_list:
                        today_data = pd.DataFrame(data_list, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
                        today_data['ts_code'] = ts_code
                        results.append(today_data)
                        continue
            except Exception as e:
                print(f"Error fetching data from baostock for {ts_code}: {str(e)}")
        
        # Try yfinance as backup
        for attempt in range(max_retries):
            try:
                _, yf_code = format_stock_code(ts_code)
                
                stock = yf.Ticker(yf_code)
                today_data = stock.history(period='1d')
                
                if not today_data.empty:
                    today_data = today_data.reset_index()
                    today_data['ts_code'] = ts_code
                    results.append(today_data)
                    break
                else:
                    raise ValueError(f"No data available from yfinance for {ts_code}")
                
            except Exception as e:
                print(f"Attempt {attempt + 1}/{max_retries} - Error fetching data from yfinance for {ts_code}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
    
    if results:
        try:
            df = pd.concat(results, ignore_index=True)
            df = df.rename(columns={
                'Date': 'date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
            
        except Exception as e:
            print(f"Error processing realtime quotes data: {str(e)}")
            return None
    
    return None

# Ensure baostock logout on program exit
import atexit
atexit.register(bs.logout)
