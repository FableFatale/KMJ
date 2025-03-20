#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
股票分析模块
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_kmj_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """计算KMJ指标系统"""
    if len(data) < 25:
        return pd.DataFrame()  # 数据不足，返回空DataFrame
        
    # 1. 计算KMJ1：加权价格均值
    data['KMJ1'] = (data['low'] + data['high'] + data['open'] + 3 * data['close']) / 6
    
    # 2. 计算KMJ2：21天加权移动均线
    weights = np.array(range(21, 0, -1))  # 权重从21递减到1
    weights_sum = np.sum(weights)  # 权重之和
    
    kmj2_values = []
    for i in range(len(data)):
        if i < 20:
            kmj2_values.append(np.nan)
            continue
            
        # 获取最近21天的KMJ1值
        window = data['KMJ1'].iloc[i-20:i+1].values
        # 计算加权平均
        kmj2 = np.sum(window * weights) / weights_sum
        kmj2_values.append(kmj2)
    
    data['KMJ2'] = kmj2_values
    
    # 3. 计算KMJ3：KMJ2的5日均线
    data['KMJ3'] = data['KMJ2'].rolling(window=5).mean()
    
    return data

def calculate_signals(data: pd.DataFrame) -> pd.DataFrame:
    """计算交易信号"""
    # 1. 趋势信号
    data['trend'] = np.where(data['KMJ2'] >= data['KMJ3'], 1, -1)  # 1表示上涨趋势，-1表示下跌趋势
    
    # 2. 买卖信号
    data['buy_signal'] = (data['KMJ2'] > data['KMJ3']) & (data['KMJ2'].shift(1) <= data['KMJ3'].shift(1))
    data['sell_signal'] = (data['KMJ2'] < data['KMJ3']) & (data['KMJ2'].shift(1) >= data['KMJ3'].shift(1))
    
    # 3. 涨停信号
    data['limit_up'] = data['close'] > (data['close'].shift(1) * 1.0985)
    
    # 4. K线形态
    data['k_color'] = np.where(data['close'] >= data['open'], 'red', 'blue')
    
    return data

def calculate_technical_score(data: pd.DataFrame) -> float:
    """
    计算股票的技术分析得分（100分制）
    
    评分标准：
    1. 趋势得分（30分）
       - KMJ2位于KMJ3上方：30分
       - KMJ2位于KMJ3下方：0分
    
    2. 买入信号（40分）
       - KMJ2上穿KMJ3：40分
       - 其他情况：0分
    
    3. 成交量确认（15分）
       - 当日成交量 > 20日均量×1.5：15分
       - 当日成交量 > 20日均量×1.2：10分
       - 其他情况：0分
    
    4. 动量得分（15分）
       - 5日涨幅 > 8%：15分
       - 5日涨幅 > 5%：10分
       - 5日涨幅 > 3%：5分
       - 其他情况：0分
    """
    try:
        if len(data) < 25:  # 需要至少25天的数据来计算指标
            return 0.0
            
        # 计算KMJ指标
        kmj1, kmj2, kmj3 = calculate_kmj_indicators(data)
        
        # 初始化得分
        score = 0.0
        
        # 1. 趋势得分（30分）
        if kmj2[-1] > kmj3[-1]:
            score += 30.0
            
        # 2. 买入信号（40分）
        signals = get_kmj_signals(kmj2, kmj3)
        if signals[-1] == 1:  # 买入信号
            score += 40.0
            
        # 3. 成交量确认（15分）
        volume = data['volume'].values
        volume_ma20 = pd.Series(volume).rolling(20).mean().values
        if volume[-1] > volume_ma20[-1] * 1.5:
            score += 15.0
        elif volume[-1] > volume_ma20[-1] * 1.2:
            score += 10.0
            
        # 4. 动量得分（15分）
        close = data['close'].values
        returns_5d = (close[-1] / close[-6] - 1) * 100  # 5日涨跌幅
        if returns_5d > 8:
            score += 15.0
        elif returns_5d > 5:
            score += 10.0
        elif returns_5d > 3:
            score += 5.0
            
        return round(score, 2)
        
    except Exception as e:
        logger.error(f"计算技术得分时发生错误: {str(e)}")
        return 0.0

def analyze_stock(df, industry=None):
    """
    分析股票数据，生成分析报告
    
    Args:
        df: 包含股票数据的DataFrame
        industry: 股票所属行业
        
    Returns:
        dict: 包含分析结果的字典
    """
    try:
        if df is None or df.empty:
            return {
                'trend': '未知',
                'signals': [],
                'analysis': '无法获取数据'
            }
            
        # 获取最新的数据
        latest = df.iloc[-1]
        
        # 计算趋势
        if 'TREND' in latest:
            trend = '上涨' if latest['TREND'] == 1 else '下跌'
        else:
            trend = '未知'
            
        # 收集交易信号
        signals = []
        if latest.get('BUY_SIGNAL', 0) == 1:
            signals.append('买入信号')
        if latest.get('SELL_SIGNAL', 0) == 1:
            signals.append('卖出信号')
        if latest.get('LIMIT_UP', 0) == 1:
            signals.append('涨停')
            
        # 生成分析报告
        analysis = []
        
        # 趋势分析
        if 'TREND' in latest:
            analysis.append(f"当前趋势：{trend}")
            
        # MACD分析
        if 'MACD' in latest and 'MACDsignal' in latest:
            if latest['MACD'] > latest['MACDsignal']:
                analysis.append("MACD指标显示上涨趋势")
            else:
                analysis.append("MACD指标显示下跌趋势")
                
        # RSI分析
        if 'RSI' in latest:
            rsi = latest['RSI']
            if rsi > 70:
                analysis.append("RSI指标显示超买")
            elif rsi < 30:
                analysis.append("RSI指标显示超卖")
            else:
                analysis.append("RSI指标处于正常区间")
                
        # 成交量分析
        if 'VOLUME_MA5' in latest and 'VOLUME_MA10' in latest:
            if latest['volume'] > latest['VOLUME_MA5'] > latest['VOLUME_MA10']:
                analysis.append("成交量呈现放大趋势")
            elif latest['volume'] < latest['VOLUME_MA5'] < latest['VOLUME_MA10']:
                analysis.append("成交量呈现萎缩趋势")
                
        # 布林带分析
        if 'BOLL_UPPER' in latest and 'BOLL_LOWER' in latest:
            if latest['close'] > latest['BOLL_UPPER']:
                analysis.append("价格突破布林带上轨，可能超买")
            elif latest['close'] < latest['BOLL_LOWER']:
                analysis.append("价格跌破布林带下轨，可能超卖")
                
        # 如果没有分析结果，添加默认信息
        if not analysis:
            analysis.append("无法生成详细分析")
            
        return {
            'trend': trend,
            'signals': signals,
            'analysis': '\n'.join(analysis)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing stock: {str(e)}")
        return {
            'trend': '未知',
            'signals': [],
            'analysis': f'分析过程中发生错误：{str(e)}'
        }

def get_industry_stocks(stocks_df, industry):
    """
    获取指定行业的股票
    
    Args:
        stocks_df: 股票列表DataFrame
        industry: 行业名称
        
    Returns:
        DataFrame: 指定行业的股票列表
    """
    try:
        if stocks_df is None or stocks_df.empty:
            return pd.DataFrame()
            
        return stocks_df[stocks_df['industry'] == industry].copy()
        
    except Exception as e:
        logger.error(f"Error getting industry stocks: {str(e)}")
        return pd.DataFrame()

def get_industry_rank(stocks_df):
    """
    获取行业排名
    
    Args:
        stocks_df: 股票列表DataFrame
        
    Returns:
        DataFrame: 行业排名数据
    """
    try:
        if stocks_df is None or stocks_df.empty:
            return pd.DataFrame()
            
        # 按行业分组计算平均得分
        industry_rank = stocks_df.groupby('industry')['technical_score'].agg([
            'mean',
            'count',
            'max',
            'min'
        ]).reset_index()
        
        # 重命名列
        industry_rank.columns = ['行业', '平均得分', '股票数量', '最高得分', '最低得分']
        
        # 按平均得分排序
        industry_rank = industry_rank.sort_values('平均得分', ascending=False)
        
        # 添加排名列
        industry_rank.insert(0, '排名', range(1, len(industry_rank) + 1))
        
        return industry_rank
        
    except Exception as e:
        logger.error(f"Error getting industry rank: {str(e)}")
        return pd.DataFrame() 