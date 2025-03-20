#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
KMJ指标计算模块
基于通达信KMJ公式实现：
KMJ1:=(LOW+HIGH+OPEN+3*CLOSE)/6;
KMJ2:=加权移动平均;
KMJ3:=MA(KMJ2,5);
"""

import pandas as pd
import numpy as np
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_kmj1(df):
    """
    计算KMJ1指标
    KMJ1:=(LOW+HIGH+OPEN+3*CLOSE)/6;
    """
    try:
        if df is None or df.empty:
            return df
        
        required_columns = ['low', 'high', 'open', 'close']
        if not all(col in df.columns for col in required_columns):
            logger.error(f"Missing required columns for KMJ1 calculation. Required: {required_columns}")
            return df
        
        # 创建副本避免修改原始数据
        df_copy = df.copy()
        
        # 确保数据类型是数值型
        for col in required_columns:
            df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
        
        # 计算KMJ1
        df_copy['KMJ1'] = (df_copy['low'] + df_copy['high'] + df_copy['open'] + 3 * df_copy['close']) / 6
        
        return df_copy
    
    except Exception as e:
        logger.error(f"Error calculating KMJ1: {str(e)}")
        return df

def calculate_kmj2(df, period=21):
    """
    计算KMJ2指标，使用加权移动平均
    """
    try:
        if df is None or df.empty or 'KMJ1' not in df.columns:
            logger.error("KMJ1 column is required for KMJ2 calculation")
            return df
        
        # 创建副本避免修改原始数据
        df_copy = df.copy()
        
        # 确保KMJ1是数值型
        df_copy['KMJ1'] = pd.to_numeric(df_copy['KMJ1'], errors='coerce')
        
        # 计算权重 (线性递减权重)
        weights = np.arange(1, period + 1)
        
        # 加权移动平均计算
        df_copy['KMJ2'] = df_copy['KMJ1'].rolling(window=period, min_periods=1).apply(
            lambda x: np.sum(x * weights[:len(x)]) / np.sum(weights[:len(x)]),
            raw=True
        )
        
        return df_copy
    
    except Exception as e:
        logger.error(f"Error calculating KMJ2: {str(e)}")
        if 'df_copy' in locals():
            # 如果出错但已创建df_copy，确保KMJ2列存在但值为NaN
            if 'KMJ2' not in df_copy.columns:
                df_copy['KMJ2'] = np.nan
            return df_copy
        return df

def calculate_kmj3(df, period=5):
    """
    计算KMJ3指标
    KMJ3:=MA(KMJ2,5);
    """
    try:
        if df is None or df.empty or 'KMJ2' not in df.columns:
            logger.error("KMJ2 column is required for KMJ3 calculation")
            return df
        
        # 创建副本避免修改原始数据
        df_copy = df.copy()
        
        # 确保KMJ2是数值型
        df_copy['KMJ2'] = pd.to_numeric(df_copy['KMJ2'], errors='coerce')
        
        # 计算KMJ3
        df_copy['KMJ3'] = df_copy['KMJ2'].rolling(window=period, min_periods=1).mean()
        
        return df_copy
    
    except Exception as e:
        logger.error(f"Error calculating KMJ3: {str(e)}")
        if 'df_copy' in locals():
            # 如果出错但已创建df_copy，确保KMJ3列存在但值为NaN
            if 'KMJ3' not in df_copy.columns:
                df_copy['KMJ3'] = np.nan
            return df_copy
        return df

def calculate_kmj_indicators(df):
    """
    计算所有KMJ指标
    """
    try:
        if df is None or df.empty:
            logger.error("Empty dataframe, cannot calculate KMJ indicators")
            return df
        
        # 按照顺序计算KMJ指标
        df_with_kmj1 = calculate_kmj1(df)
        df_with_kmj2 = calculate_kmj2(df_with_kmj1)
        df_with_kmj = calculate_kmj3(df_with_kmj2)
        
        # 添加趋势指标
        df_with_kmj = add_trend_indicator(df_with_kmj)
        
        return df_with_kmj
    
    except Exception as e:
        logger.error(f"Error calculating KMJ indicators: {str(e)}")
        return df

def add_trend_indicator(df):
    """
    根据KMJ2和KMJ3的关系添加趋势指标
    KMJ_TREND:
    1 = 上升趋势 (KMJ2 > KMJ3)
    -1 = 下降趋势 (KMJ2 < KMJ3)
    0 = 盘整 (KMJ2 ≈ KMJ3)
    """
    try:
        if df is None or df.empty or 'KMJ2' not in df.columns or 'KMJ3' not in df.columns:
            logger.error("KMJ2 and KMJ3 columns are required for trend indicator")
            return df
        
        # 创建副本避免修改原始数据
        df_copy = df.copy()
        
        # 确保KMJ2和KMJ3是数值型
        df_copy['KMJ2'] = pd.to_numeric(df_copy['KMJ2'], errors='coerce')
        df_copy['KMJ3'] = pd.to_numeric(df_copy['KMJ3'], errors='coerce')
        
        # 初始化趋势列
        df_copy['KMJ_TREND'] = 0
        
        # 盘整阈值 (KMJ2与KMJ3相差不超过0.1%视为盘整)
        threshold = 0.001
        
        # 计算KMJ2与KMJ3的相对差异
        valid_mask = ~df_copy['KMJ3'].isna() & (df_copy['KMJ3'] != 0)
        rel_diff = df_copy.loc[valid_mask, 'KMJ2'] / df_copy.loc[valid_mask, 'KMJ3'] - 1
        
        # 设置趋势
        df_copy.loc[valid_mask & (rel_diff > threshold), 'KMJ_TREND'] = 1  # 上升趋势
        df_copy.loc[valid_mask & (rel_diff < -threshold), 'KMJ_TREND'] = -1  # 下降趋势
        # 默认为0表示盘整
        
        return df_copy
    
    except Exception as e:
        logger.error(f"Error adding trend indicator: {str(e)}")
        return df

def get_kmj_signals(df):
    """
    根据KMJ指标系统获取买入和卖出信号
    """
    try:
        if df is None or df.empty or 'KMJ2' not in df.columns or 'KMJ3' not in df.columns:
            logger.error("KMJ2 and KMJ3 columns are required for signals")
            return df
        
        # 创建副本避免修改原始数据
        df_copy = df.copy()
        
        # 确保KMJ2和KMJ3是数值型
        df_copy['KMJ2'] = pd.to_numeric(df_copy['KMJ2'], errors='coerce')
        df_copy['KMJ3'] = pd.to_numeric(df_copy['KMJ3'], errors='coerce')
        
        # 初始化信号列
        df_copy['KMJ_BUY_SIGNAL'] = False
        df_copy['KMJ_SELL_SIGNAL'] = False
        
        # 避免警告：创建一个有效数据的掩码
        valid_data = ~df_copy['KMJ2'].isna() & ~df_copy['KMJ3'].isna()
        
        if len(df_copy) < 2 or not valid_data.any():
            return df_copy
        
        # 仅对有效数据进行操作
        valid_df = df_copy[valid_data].copy()
        
        # 计算KMJ2与KMJ3的交叉
        valid_df['KMJ2_prev'] = valid_df['KMJ2'].shift(1)
        valid_df['KMJ3_prev'] = valid_df['KMJ3'].shift(1)
        
        # 忽略首行，因为它没有前一个值
        for i in range(1, len(valid_df)):
            row = valid_df.iloc[i]
            prev_row = valid_df.iloc[i-1]
            
            # 金叉：KMJ2从下方穿过KMJ3 (买入信号)
            if prev_row['KMJ2'] < prev_row['KMJ3'] and row['KMJ2'] > row['KMJ3']:
                valid_df.iloc[i, valid_df.columns.get_loc('KMJ_BUY_SIGNAL')] = True
            
            # 死叉：KMJ2从上方穿过KMJ3 (卖出信号)
            if prev_row['KMJ2'] > prev_row['KMJ3'] and row['KMJ2'] < row['KMJ3']:
                valid_df.iloc[i, valid_df.columns.get_loc('KMJ_SELL_SIGNAL')] = True
        
        # 将信号从有效数据复制回原始数据框
        for col in ['KMJ_BUY_SIGNAL', 'KMJ_SELL_SIGNAL']:
            df_copy.loc[valid_data, col] = valid_df[col]
        
        return df_copy
    
    except Exception as e:
        logger.error(f"Error generating KMJ signals: {str(e)}")
        # 确保信号列存在
        if 'df_copy' in locals():
            if 'KMJ_BUY_SIGNAL' not in df_copy.columns:
                df_copy['KMJ_BUY_SIGNAL'] = False
            if 'KMJ_SELL_SIGNAL' not in df_copy.columns:
                df_copy['KMJ_SELL_SIGNAL'] = False
            return df_copy
        return df 