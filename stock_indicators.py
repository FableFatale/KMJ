#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
技术指标计算模块
"""

import pandas as pd
import numpy as np
import MyTT
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_signals(df):
    """
    计算技术指标和交易信号
    
    Args:
        df: 包含OHLC数据的DataFrame
        
    Returns:
        DataFrame: 添加了技术指标的DataFrame
    """
    try:
        if df is None or df.empty:
            return None
            
        # 确保数据类型正确
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 计算MACD
        df['MACD'], df['MACDsignal'], df['MACDhist'] = MyTT.MACD(df['close'])
        
        # 计算KDJ
        df['K'], df['D'], df['J'] = MyTT.KDJ(df['high'], df['low'], df['close'])
        
        # 计算布林带
        df['BOLL_UPPER'], df['BOLL_MIDDLE'], df['BOLL_LOWER'] = MyTT.BOLL(df['close'])
        
        # 计算成交量指标
        df['VOLUME_MA5'] = MyTT.MA(df['volume'], 5)
        df['VOLUME_MA10'] = MyTT.MA(df['volume'], 10)
        
        # 计算RSI
        df['RSI'] = MyTT.RSI(df['close'])
        
        # 计算趋势
        df['TREND'] = np.where(df['close'] > df['BOLL_MIDDLE'], 1, -1)
        
        # 计算买卖信号
        df['BUY_SIGNAL'] = ((df['MACD'] > df['MACDsignal']) & 
                           (df['MACD'].shift(1) <= df['MACDsignal'].shift(1))).astype(int)
        df['SELL_SIGNAL'] = ((df['MACD'] < df['MACDsignal']) & 
                            (df['MACD'].shift(1) >= df['MACDsignal'].shift(1))).astype(int)
        
        # 计算涨停信号 (9.85%)
        df['LIMIT_UP'] = (df['close'] > (df['close'].shift(1) * 1.0985)).astype(int)
        
        return df
        
    except Exception as e:
        logger.error(f"Error calculating signals: {str(e)}")
        return df

def screen_stocks(df):
    """
    根据技术指标筛选股票
    
    Args:
        df: 包含技术指标的DataFrame
        
    Returns:
        float: 技术分析得分 (0-100)
    """
    try:
        if df is None or df.empty:
            return 0.0
            
        # 获取最新的指标值
        latest = df.iloc[-1]
        
        # 基础分数为50分
        score = 50.0
        
        # 趋势得分 (最高30分)
        if 'TREND' in latest:
            if latest['TREND'] == 1:  # 上涨趋势
                score += 30
            elif latest['TREND'] == -1:  # 下跌趋势
                score -= 20
                
        # MACD得分 (最高20分)
        if 'MACD' in latest and 'MACDsignal' in latest:
            if latest['MACD'] > latest['MACDsignal']:
                score += 20
            elif latest['MACD'] < latest['MACDsignal']:
                score -= 15
                
        # RSI得分 (最高20分)
        if 'RSI' in latest:
            if 30 <= latest['RSI'] <= 70:  # 正常区间
                score += 20
            elif latest['RSI'] < 30:  # 超卖
                score += 10
            elif latest['RSI'] > 70:  # 超买
                score -= 10
                
        # 成交量得分 (最高20分)
        if 'VOLUME_MA5' in latest and 'VOLUME_MA10' in latest:
            if latest['volume'] > latest['VOLUME_MA5'] > latest['VOLUME_MA10']:
                score += 20
            elif latest['volume'] < latest['VOLUME_MA5'] < latest['VOLUME_MA10']:
                score -= 15
                
        # 确保分数在0-100之间
        return max(0, min(100, score))
        
    except Exception as e:
        logger.error(f"Error screening stocks: {str(e)}")
        return 0.0 