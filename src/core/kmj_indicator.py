import pandas as pd
import numpy as np

def calculate_kmj_indicators(data):
    """
    计算KMJ指标
    KMJ1 = (最低价 + 最高价 + 开盘价 + 3×收盘价) / 6
    KMJ2 = KMJ1的20日加权移动平均
    KMJ3 = KMJ2的5日简单移动平均
    """
    if data is None or data.empty:
        raise ValueError("输入数据不能为空")
        
    try:
        df = data.copy()
        
        # 计算KMJ1
        df['KMJ1'] = (df['low'] + df['high'] + df['open'] + 3 * df['close']) / 6
        
        # 计算KMJ2 (20日加权移动平均)
        weights = np.array([1/(i+1) for i in range(20)])
        weights = weights[::-1]  # 反转权重，使最近的数据权重最大
        weights = weights / weights.sum()  # 归一化权重
        
        df['KMJ2'] = pd.Series(index=df.index, dtype=float)
        for i in range(len(df)):
            if i < 20:
                df.iloc[i, df.columns.get_loc('KMJ2')] = np.nan
            else:
                values = df['KMJ1'].iloc[i-20:i].values
                df.iloc[i, df.columns.get_loc('KMJ2')] = np.sum(values * weights)
        
        # 计算KMJ3 (5日简单移动平均)
        df['KMJ3'] = df['KMJ2'].rolling(window=5).mean()
        
        # 计算趋势
        df['KMJ_TREND'] = 0
        df.loc[df['KMJ2'] > df['KMJ3'], 'KMJ_TREND'] = 1
        df.loc[df['KMJ2'] < df['KMJ3'], 'KMJ_TREND'] = -1
        
        return df
    except Exception as e:
        print(f"计算KMJ指标时发生错误：{str(e)}")
        return data

def get_kmj_signals(data):
    """
    获取KMJ指标的买卖信号
    买入信号：KMJ2上穿KMJ3
    卖出信号：KMJ2下穿KMJ3
    """
    try:
        df = data.copy()
        
        # 计算KMJ指标
        if 'KMJ2' not in df.columns or 'KMJ3' not in df.columns:
            df = calculate_kmj_indicators(df)
        
        # 初始化买卖信号列
        df['KMJ_BUY_SIGNAL'] = False
        df['KMJ_SELL_SIGNAL'] = False
        
        # 计算交叉信号
        for i in range(1, len(df)):
            # 上穿（买入信号）
            if df['KMJ2'].iloc[i-1] < df['KMJ3'].iloc[i-1] and \
               df['KMJ2'].iloc[i] > df['KMJ3'].iloc[i]:
                df.loc[df.index[i], 'KMJ_BUY_SIGNAL'] = True
            # 下穿（卖出信号）
            elif df['KMJ2'].iloc[i-1] > df['KMJ3'].iloc[i-1] and \
                 df['KMJ2'].iloc[i] < df['KMJ3'].iloc[i]:
                df.loc[df.index[i], 'KMJ_SELL_SIGNAL'] = True
        
        return df
    except Exception as e:
        print(f"计算KMJ信号时发生错误：{str(e)}")
        return data 