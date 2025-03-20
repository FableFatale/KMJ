import pandas as pd
import numpy as np
import akshare as ak
import datetime
import json

def get_stock_data(stock_code):
    """
    获取股票数据，包括历史价格、均线和成交量
    """
    try:
        # 确保股票代码格式正确
        if not stock_code.startswith(('6', '0', '3')):
            return {"error": "股票代码格式不正确，请输入正确的股票代码"}
            
        # 添加市场标识
        if stock_code.startswith('6'):
            full_code = f"{stock_code}.SH"
        else:
            full_code = f"{stock_code}.SZ"
            
        # 获取股票历史数据
        stock_data = ak.stock_zh_a_hist(symbol=full_code, period="daily", 
                                      start_date=(datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y%m%d'),
                                      end_date=datetime.datetime.now().strftime('%Y%m%d'), 
                                      adjust="qfq")
        
        # 计算技术指标
        # 20日均线
        stock_data['MA20'] = stock_data['收盘'].rolling(window=20).mean()
        # 120日成交量均线
        stock_data['VOL120'] = stock_data['成交量'].rolling(window=120).mean()
        
        # 获取最新数据
        latest_data = stock_data.iloc[-1]
        prev_data = stock_data.iloc[-2]
        
        # 计算与20日均线的关系
        above_ma20 = latest_data['收盘'] > latest_data['MA20']
        
        # 计算连续4天收盘价高于20日均线
        days_above_ma20 = 0
        for i in range(1, min(5, len(stock_data))):
            if stock_data.iloc[-i]['收盘'] > stock_data.iloc[-i]['MA20']:
                days_above_ma20 += 1
            else:
                break
        
        # 计算成交量与120日均量线的关系
        vol_above_ma120 = latest_data['成交量'] > latest_data['VOL120']
        
        # 计算连续3天成交量高于120日均量线
        days_vol_above_ma120 = 0
        for i in range(1, min(4, len(stock_data))):
            if stock_data.iloc[-i]['成交量'] > stock_data.iloc[-i]['VOL120']:
                days_vol_above_ma120 += 1
            else:
                break
        
        # 计算量价齐升情况
        price_up = latest_data['收盘'] > prev_data['收盘']
        vol_up = latest_data['成交量'] > prev_data['成交量']
        price_vol_up = price_up and vol_up
        
        # 获取股票基本信息
        stock_info = ak.stock_individual_info_em(symbol=full_code)
        
        # 构建结果
        result = {
            "股票代码": stock_code,
            "股票名称": stock_info.iloc[0, 1] if not stock_info.empty else "未知",
            "当前价格": float(latest_data['收盘']),
            "涨跌幅": float(latest_data['涨跌幅']),
            "成交量": float(latest_data['成交量']),
            "成交额": float(latest_data['成交额']),
            "技术指标": {
                "MA20": float(latest_data['MA20']) if not np.isnan(latest_data['MA20']) else None,
                "VOL120": float(latest_data['VOL120']) if not np.isnan(latest_data['VOL120']) else None,
                "高于20日均线": bool(above_ma20),
                "连续高于20日均线天数": int(days_above_ma20),
                "高于120日均量线": bool(vol_above_ma120),
                "连续高于120日均量线天数": int(days_vol_above_ma120),
                "量价齐升": bool(price_vol_up)
            },
            "杨凯指标": {
                "多头持股条件": {
                    "均线系统": days_above_ma20 >= 4,
                    "量能系统": days_vol_above_ma120 >= 3,
                    "量价齐升": price_vol_up,
                    "满足条件": days_above_ma20 >= 4 and days_vol_above_ma120 >= 3 and price_vol_up
                },
                "空头观望条件": {
                    "均线系统": not above_ma20,
                    "量能系统": not vol_above_ma120,
                    "满足条件": not above_ma20 or not vol_above_ma120
                }
            }
        }
        
        # 获取行业信息
        try:
            industry_info = ak.stock_industry_category_cninfo(symbol=stock_code)
            if not industry_info.empty:
                result["行业"] = industry_info.iloc[0, 2]
        except:
            result["行业"] = "未知"
        
        # 获取市盈率等估值指标
        try:
            valuation = ak.stock_a_lg_indicator(symbol=full_code)
            if not valuation.empty:
                result["市盈率"] = float(valuation['pe'].iloc[0]) if not np.isnan(valuation['pe'].iloc[0]) else None
                result["市净率"] = float(valuation['pb'].iloc[0]) if not np.isnan(valuation['pb'].iloc[0]) else None
                result["市销率"] = float(valuation['ps'].iloc[0]) if not np.isnan(valuation['ps'].iloc[0]) else None
        except:
            pass
        
        return result
    
    except Exception as e:
        return {"error": f"获取股票数据失败: {str(e)}"}

def main(arg1: str, arg2: str) -> dict:
    """
    代码执行器入口函数
    arg1: 股票代码
    arg2: 未使用
    """
    stock_code = arg1.strip()
    result = get_stock_data(stock_code)
    return {"result": json.dumps(result, ensure_ascii=False)}