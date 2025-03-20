import pandas as pd
import numpy as np
from typing import Dict, List, Optional

def calculate_kmj_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算KMJ指标"""
    if len(df) < 25:
        return df
        
    # KMJ1 = (LOW + HIGH + OPEN + 3*CLOSE) / 6
    df['KMJ1'] = (df['low'] + df['high'] + df['open'] + 3 * df['close']) / 6
    
    # KMJ2 = 加权移动平均 (21天)
    weights = np.array(range(21, 0, -1))  # 21, 20, ..., 1
    weights = weights / weights.sum()
    
    # 使用rolling window计算加权平均
    df['KMJ2'] = df['KMJ1'].rolling(window=21).apply(
        lambda x: np.sum(weights[-len(x):] * x) if len(x) > 0 else np.nan
    )
    
    # KMJ3 = 5日均线
    df['KMJ3'] = df['KMJ2'].rolling(window=5).mean()
    
    # 填充NaN值
    df['KMJ2'] = df['KMJ2'].fillna(method='ffill')
    df['KMJ3'] = df['KMJ3'].fillna(method='ffill')
    
    return df

def calculate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """计算交易信号"""
    if len(df) < 25:
        return df
        
    # 趋势信号
    df['trend'] = np.where(df['KMJ2'] > df['KMJ3'], 1, -1)
    
    # 买入信号：KMJ2上穿KMJ3
    df['buy_signal'] = (df['KMJ2'] > df['KMJ3']) & (df['KMJ2'].shift(1) <= df['KMJ3'].shift(1))
    
    # 卖出信号：KMJ2下穿KMJ3
    df['sell_signal'] = (df['KMJ2'] < df['KMJ3']) & (df['KMJ2'].shift(1) >= df['KMJ3'].shift(1))
    
    # 涨停信号
    df['limit_up'] = df['close'] > df['close'].shift(1) * 1.0985
    
    return df

def calculate_technical_score(df: pd.DataFrame) -> float:
    """计算技术分析得分（0-10分）"""
    try:
        if len(df) < 25:
            return 0
            
        # 计算指标
        df = calculate_kmj_indicators(df)
        df = calculate_signals(df)
        
        # 1. 趋势得分 (0-4分)
        trend_score = 0
        if df['KMJ2'].iloc[-1] > df['KMJ3'].iloc[-1]:  # 当前趋势向上
            trend_score += 2
            if df['KMJ2'].iloc[-5:].mean() > df['KMJ3'].iloc[-5:].mean():  # 近5日趋势向上
                trend_score += 1
            if df['KMJ2'].iloc[-10:].mean() > df['KMJ3'].iloc[-10:].mean():  # 近10日趋势向上
                trend_score += 1
                
        # 2. 动量得分 (0-2分)
        momentum = (df['close'].iloc[-1] / df['close'].iloc[-5] - 1) * 100
        momentum_score = min(2, max(0, momentum / 5))  # 每5%得1分，最高2分
        
        # 3. 成交量得分 (0-2分)
        volume_score = 0
        recent_vol_avg = df['volume'].iloc[-5:].mean()
        prev_vol_avg = df['volume'].iloc[-10:-5].mean()
        if recent_vol_avg > prev_vol_avg:
            volume_score += 1
        if df['volume'].iloc[-1] > recent_vol_avg:
            volume_score += 1
            
        # 4. 波动率得分 (0-2分)
        volatility = df['close'].pct_change().std() * np.sqrt(252)
        volatility_score = min(2, max(0, 2 - volatility))  # 波动率越小分数越高
        
        total_score = trend_score + momentum_score + volume_score + volatility_score
        return round(total_score, 2)
        
    except Exception as e:
        print(f"Error calculating technical score: {str(e)}")
        return 0

def analyze_stock(df: pd.DataFrame, industry: str) -> Dict:
    """分析股票并返回结果"""
    try:
        if len(df) < 25:
            return {
                'score': 0,
                'trend': "数据不足",
                'signals': [],
                'analysis': "数据不足，无法分析"
            }
            
        # 计算指标
        df = calculate_kmj_indicators(df)
        df = calculate_signals(df)
        
        # 计算技术得分
        score = calculate_technical_score(df)
        
        # 获取当前趋势
        current_trend = "上涨" if df['trend'].iloc[-1] > 0 else "下跌"
        
        # 获取最新信号
        signals = []
        if df['buy_signal'].iloc[-1]:
            signals.append("买入")
        if df['sell_signal'].iloc[-1]:
            signals.append("卖出")
        if df['limit_up'].iloc[-1]:
            signals.append("涨停")
            
        # 生成分析文本
        analysis = f"""技术分析结果：
1. 行业：{industry}
2. 趋势：目前处于{current_trend}趋势
3. 技术得分：{score}分
4. KMJ指标：
   - KMJ2（{df['KMJ2'].iloc[-1]:.2f}）
   - KMJ3（{df['KMJ3'].iloc[-1]:.2f}）
5. 最新信号：{'、'.join(signals) if signals else '无'}
"""
        
        return {
            'score': score,
            'trend': current_trend,
            'signals': signals,
            'analysis': analysis
        }
        
    except Exception as e:
        print(f"Error analyzing stock: {str(e)}")
        return {
            'score': 0,
            'trend': "未知",
            'signals': [],
            'analysis': f"分析出错：{str(e)}"
        }

def get_industry_stocks(df: pd.DataFrame, industry: str) -> pd.DataFrame:
    """获取行业内的股票"""
    try:
        if industry == '全部':
            return df
            
        # 确保industry列存在
        if 'industry' not in df.columns:
            df['industry'] = '其他'
            
        # 处理空值和无效值
        df['industry'] = df['industry'].fillna('其他')
        df['industry'] = df['industry'].replace('', '其他')
        
        # 获取指定行业的股票
        industry_stocks = df[df['industry'] == industry].copy()
        return industry_stocks if not industry_stocks.empty else pd.DataFrame()
        
    except Exception as e:
        print(f"Error getting industry stocks: {str(e)}")
        return pd.DataFrame()

def get_industry_rank(df: pd.DataFrame, industry: str, min_score: float = 0) -> pd.DataFrame:
    """获取行业排名"""
    try:
        # 获取行业股票
        stocks = get_industry_stocks(df, industry)
        if stocks.empty:
            return pd.DataFrame()
            
        # 确保technical_score列存在
        if 'technical_score' not in stocks.columns:
            stocks['technical_score'] = 0.0
            
        # 筛选达到最小分数的股票
        ranked_stocks = stocks[stocks['technical_score'] >= min_score]
        if ranked_stocks.empty:
            return pd.DataFrame()
            
        # 按技术得分排序
        return ranked_stocks.sort_values('technical_score', ascending=False)
        
    except Exception as e:
        print(f"Error getting industry rank: {str(e)}")
        return pd.DataFrame() 