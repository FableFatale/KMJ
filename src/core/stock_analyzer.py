import pandas as pd
import numpy as np
from .kmj_indicator import calculate_kmj_indicators, get_kmj_signals

def calculate_technical_score(data):
    """计算技术分析得分"""
    try:
        if data is None or data.empty:
            return 0.0
            
        # 确保KMJ指标已计算
        if 'KMJ2' not in data.columns or 'KMJ3' not in data.columns:
            data = calculate_kmj_indicators(data)
            data = get_kmj_signals(data)
            
        # 获取最新的数据
        latest = data.iloc[-1]
        
        # 基础分数为50分
        score = 50.0
        
        # 趋势得分 (最高30分)
        if 'KMJ_TREND' in latest:
            if latest['KMJ_TREND'] == 1:  # 上涨趋势
                score += 30
            elif latest['KMJ_TREND'] == -1:  # 下跌趋势
                score -= 30
                
        # KMJ指标得分 (最高20分)
        if 'KMJ2' in latest and 'KMJ3' in latest:
            # KMJ2与KMJ3的距离，距离越大表示趋势越强
            kmj_diff = abs(latest['KMJ2'] - latest['KMJ3']) / latest['KMJ3'] * 100
            kmj_score = min(20, kmj_diff)
            score += kmj_score
            
        # 动量得分 (最高20分)
        if len(data) > 5:
            # 最近5天的涨幅
            price_change = (latest['close'] / data.iloc[-6]['close'] - 1) * 100
            if price_change > 0:
                score += min(20, price_change)
            else:
                score -= min(20, abs(price_change))
                
        # 成交量得分 (最高10分)
        if 'volume' in data.columns and len(data) > 5:
            # 最近5天的平均成交量
            avg_vol = data['volume'].tail(5).mean()
            # 与前5天平均成交量相比
            prev_avg_vol = data['volume'].iloc[-10:-5].mean() if len(data) > 10 else data['volume'].mean()
            
            if not np.isnan(avg_vol) and not np.isnan(prev_avg_vol) and prev_avg_vol > 0:
                vol_change = (avg_vol / prev_avg_vol - 1) * 100
                if vol_change > 0:
                    score += min(10, vol_change)
                else:
                    score -= min(10, abs(vol_change))
                    
        # 确保分数在0-100之间
        return round(max(0, min(100, score)), 2)
    except Exception as e:
        print(f"计算技术得分时发生错误：{str(e)}")
        return 0.0 