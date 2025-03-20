import schedule
import time
from datetime import datetime
import yfinance as yf
import pandas as pd
import akshare as ak
import asyncio
import aiohttp
import numpy as np
from typing import Dict, List, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import webbrowser
import sys
import argparse

def parse_arguments():
    parser = argparse.ArgumentParser(description='日经ETF分析工具')
    parser.add_argument('--immediate', action='store_true', help='立即执行一次分析')
    parser.add_argument('--cost', type=float, required=True, help='持仓成本价')
    parser.add_argument('--position', type=int, required=True, help='持仓数量')
    return parser.parse_args()

async def get_etf_data(symbol: str, session: aiohttp.ClientSession) -> Dict:
    try:
        etf = yf.Ticker(symbol)
        etf_hist = etf.history(period="7d")
        
        if etf_hist.empty:
            return {
                'change': 0,
                'week_change': 0,
                'current_price': None
            }
        
        current_price = etf.info.get('regularMarketPrice')
        change = ((etf_hist['Close'].iloc[-1] - etf_hist['Close'].iloc[-2]) / etf_hist['Close'].iloc[-2]) * 100
        week_change = ((etf_hist['Close'].iloc[-1] - etf_hist['Close'].iloc[0]) / etf_hist['Close'].iloc[0]) * 100
        
        return {
            'change': change,
            'week_change': week_change,
            'current_price': current_price
        }
    except Exception as e:
        print(f"获取ETF数据失败: {str(e)}")
        return {
            'change': 0,
            'week_change': 0,
            'current_price': None
        }

async def calculate_technical_indicators(df: pd.DataFrame) -> Dict:
    try:
        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rs = rs.replace([np.inf, -np.inf], np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)  # 使用中性值填充NaN
        
        # KDJ
        low_min = df['Low'].rolling(window=9).min()
        high_max = df['High'].rolling(window=9).max()
        rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
        rsv = rsv.fillna(50)  # 使用中性值填充NaN
        k = rsv.rolling(window=3).mean().fillna(50)
        d = k.rolling(window=3).mean().fillna(50)
        j = 3 * k - 2 * d
        
        return {
            'macd': float(macd.iloc[-1]),
            'macd_signal': float(signal.iloc[-1]),
            'macd_hist': float((macd - signal).iloc[-1]),
            'rsi': float(rsi.iloc[-1]),
            'kdj_k': float(k.iloc[-1]),
            'kdj_d': float(d.iloc[-1]),
            'kdj_j': float(j.iloc[-1])
        }
    except Exception as e:
        print(f"计算技术指标时发生错误: {str(e)}")
        return {}

def generate_grid_trading_suggestion(current_price: float, base_price: float, indicators: Dict) -> str:
    try:
        grid_size = 0.05  # 网格大小（5%）
        grids = 5  # 网格数量
        
        # 基于技术指标判断趋势
        trend = "上涨" if (
            indicators.get('macd', 0) > indicators.get('macd_signal', 0) and
            indicators.get('rsi', 0) > 50 and
            indicators.get('kdj_k', 0) > indicators.get('kdj_d', 0)
        ) else "下跌"
        
        # 计算买入和卖出网格价格
        buy_grid_prices = []
        sell_grid_prices = []
        buy_grid_shares = []
        sell_grid_shares = []
        base_shares = 100  # 基础交易数量
        
        for i in range(grids):
            # 买入网格价格和数量
            buy_price = base_price * (1 - grid_size * (i + 1))
            buy_grid_prices.append(buy_price)
            buy_grid_shares.append(base_shares * (i + 1))
            
            # 卖出网格价格和数量
            sell_price = base_price * (1 + grid_size * (i + 1))
            sell_grid_prices.append(sell_price)
            sell_grid_shares.append(base_shares * (i + 1))
        
        # 计算止盈止损位
        stop_loss = base_price * 0.92  # 8%止损
        take_profit = base_price * 1.15  # 15%止盈
        
        # 生成建议
        suggestion = [f"当前趋势研判：{trend}"]
        suggestion.append("\n市场分析：")
        
        # 添加技术指标分析
        macd_signal = "MACD金叉" if indicators.get('macd', 0) > indicators.get('macd_signal', 0) else "MACD死叉"
        kdj_signal = "KDJ金叉" if indicators.get('kdj_k', 0) > indicators.get('kdj_d', 0) else "KDJ死叉"
        rsi_status = "超买" if indicators.get('rsi', 0) > 70 else "超卖" if indicators.get('rsi', 0) < 30 else "中性"
        
        suggestion.append(f"- 技术信号：{macd_signal}，{kdj_signal}，RSI {rsi_status}({indicators.get('rsi', 0):.1f})")
        
        suggestion.append("\n交易建议：")
        suggestion.append("买入网格：")
        for i, (price, shares) in enumerate(zip(buy_grid_prices, buy_grid_shares)):
            suggestion.append(f"  网格{i+1}: {price:.3f} (建议买入: {shares}股)")
        
        suggestion.append("\n卖出网格：")
        for i, (price, shares) in enumerate(zip(sell_grid_prices, sell_grid_shares)):
            suggestion.append(f"  网格{i+1}: {price:.3f} (建议卖出: {shares}股)")
        
        suggestion.append(f"\n止盈位：{take_profit:.3f}（建议设置条件单）")
        suggestion.append(f"止损位：{stop_loss:.3f}（建议设置条件单）")
        
        return "\n".join(suggestion)
    except Exception as e:
        return "无法生成网格交易建议"

def generate_suggestion(data):
    try:
        # 计算利好因素
        positive_factors = 0
        if data.get('nikkei_trend', '') == "上涨":
            positive_factors += 1
        if data.get('etf_data', {}).get('change', 0) > 0:
            positive_factors += 1
        
        # 根据技术指标判断
        tech_indicators = data.get('technical_indicators', {})
        if tech_indicators.get('rsi', 0) > 50:
            positive_factors += 1
        if tech_indicators.get('macd', 0) > tech_indicators.get('macd_signal', 0):
            positive_factors += 1
        
        # 生成建议
        if positive_factors >= 3:
            return "综合分析偏多，建议持有或择机加仓"
        elif positive_factors == 2:
            return "市场中性，建议观望"
        else:
            return "综合分析偏空，建议减仓或观望"
    except Exception as e:
        print(f"生成建议时发生错误: {str(e)}")
        return "无法生成建议，请检查数据"

def generate_nikkei_message(market_data, position_data, grid_suggestion):
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if not market_data:
            return "获取市场数据失败，请稍后重试"
        
        tech_indicators = market_data.get('technical_indicators', {})
        
        # 生成控制台输出内容
        console_output = [
            "\n=== 日经ETF（159866）分析报告 ===",
            f"生成时间：{current_time}\n",
            "--- 日经225指数分析 ---",
            f"当日变动：{market_data.get('nikkei_trend', '未知')} ({market_data.get('nikkei_change', 0):.2f}%)",
            f"周度变动：{market_data.get('nikkei_week_change', 0):.2f}%",
            f"价格区间：{market_data.get('nikkei_low', 0):.0f} - {market_data.get('nikkei_high', 0):.0f}",
            f"均价：{market_data.get('nikkei_avg', 0):.0f}\n",
            "--- 技术指标分析 ---",
            f"MACD：{tech_indicators.get('macd', 0):.3f}",
            f"RSI：{tech_indicators.get('rsi', 0):.2f}",
            "KDJ指标：",
            f"K：{tech_indicators.get('kdj_k', 0):.2f}",
            f"D：{tech_indicators.get('kdj_d', 0):.2f}",
            f"J：{tech_indicators.get('kdj_j', 0):.2f}\n",
            "--- 持仓分析 ---",
            f"持仓成本：{position_data.get('cost_price', 0):.3f}",
            f"当前价格：{f'{position_data.get('current_price', 0):.3f}' if position_data.get('current_price') else '获取失败'}",
            f"持仓数量：{position_data.get('position', 0):,d}股",
            f"浮动{'盈利' if position_data.get('profit_loss', 0) > 0 else '亏损'}：{f'{position_data.get('profit_loss', 0):,.2f}元 ({position_data.get('profit_loss_rate', 0):.2f}%)' if position_data.get('profit_loss') is not None else '无法计算'}\n",
            "--- 网格交易建议 ---",
            grid_suggestion
        ]
        
        # 打印控制台输出
        print('\n'.join(console_output))
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>日经ETF（159866）分析报告</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
            margin-bottom: 20px;
        }}
        h1 {{
            color: #1a73e8;
            border-bottom: 2px solid #1a73e8;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        h2 {{
            color: #1a73e8;
            margin-top: 25px;
            margin-bottom: 15px;
        }}
        .grid-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .grid-item {{
            background-color: #f8f9fa;
            border-left: 4px solid #1a73e8;
            padding: 15px;
            border-radius: 4px;
            transition: transform 0.2s;
        }}
        .grid-item:hover {{
            transform: translateY(-2px);
        }}
        .indicator {{
            margin-bottom: 10px;
        }}
        .grid-suggestion {{
            background-color: #e8f0fe;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            line-height: 1.8;
        }}
        .warning {{
            color: #d93025;
            font-weight: bold;
        }}
        .success {{
            color: #188038;
            font-weight: bold;
        }}
        .timestamp {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 20px;
        }}
        .suggestion-title {{
            font-weight: bold;
            color: #1a73e8;
            margin: 10px 0;
        }}
        .suggestion-content {{
            padding-left: 15px;
            border-left: 3px solid #1a73e8;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>日经ETF（159866）分析报告</h1>
        <div class="timestamp">生成时间：{current_time}</div>
        
        <h2>日经225指数分析</h2>
        <div class="grid-container">
            <div class="grid-item">
                <div class="indicator">当日变动：<span class="{{'success' if market_data.get('nikkei_trend') == '上涨' else 'warning'}}">{market_data.get('nikkei_trend', '未知')} ({market_data.get('nikkei_change', 0):.2f}%)</span></div>
                <div class="indicator">周度变动：<span class="{{'success' if market_data.get('nikkei_week_change', 0) > 0 else 'warning'}}">{market_data.get('nikkei_week_change', 0):.2f}%</span></div>
            </div>
            <div class="grid-item">
                <div class="indicator">价格区间：{market_data.get('nikkei_low', 0):.0f} - {market_data.get('nikkei_high', 0):.0f}</div>
                <div class="indicator">均价：{market_data.get('nikkei_avg', 0):.0f}</div>
            </div>
        </div>

        <h2>技术指标分析</h2>
        <div class="grid-container">
            <div class="grid-item">
                <div class="indicator">MACD：{tech_indicators.get('macd', 0):.3f}</div>
                <div class="indicator">RSI：{tech_indicators.get('rsi', 0):.2f}</div>
            </div>
            <div class="grid-item">
                <div class="indicator">KDJ指标：</div>
                <div class="indicator">K：{tech_indicators.get('kdj_k', 0):.2f}</div>
                <div class="indicator">D：{tech_indicators.get('kdj_d', 0):.2f}</div>
                <div class="indicator">J：{tech_indicators.get('kdj_j', 0):.2f}</div>
            </div>
        </div>

        <h2>持仓分析</h2>
        <div class="grid-container">
            <div class="grid-item">
                <div class="indicator">持仓成本：{position_data.get('cost_price', 0):.3f}</div>
                <div class="indicator">当前价格：{f"{position_data.get('current_price', 0):.3f}" if position_data.get('current_price') else "获取失败"}</div>
            </div>
            <div class="grid-item">
                <div class="indicator">持仓数量：{position_data.get('position', 0):,d}股</div>
                <div class="indicator">浮动{"盈利" if position_data.get('profit_loss', 0) > 0 else "亏损"}：
                    <span class="{{'success' if position_data.get('profit_loss', 0) > 0 else 'warning'}}">
                        {f"{position_data.get('profit_loss', 0):,.2f}元 ({position_data.get('profit_loss_rate', 0):.2f}%)" if position_data.get('profit_loss') is not None else "无法计算"}
                    </span>
                </div>
            </div>
        </div>

        <h2>网格交易建议</h2>
        <div class="grid-suggestion">
            {grid_suggestion.replace('\n', '<br>').replace('市场分析：', '<div class="suggestion-title">市场分析：</div><div class="suggestion-content">').replace('交易建议：', '</div><div class="suggestion-title">交易建议：</div><div class="suggestion-content">') + '</div>'}
        </div>
    </div>
</body>
</html>
"""
        
        # 保存HTML报告
        with open('report.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 在浏览器中打开报告
        webbrowser.open('report.html')
        
        return "分析报告已生成并打开"
    except Exception as e:
        return f"生成报告时发生错误: {str(e)}"

async def get_nikkei_data_async():
    try:
        async with aiohttp.ClientSession() as session:
            # 获取日经225指数数据
            nikkei = yf.Ticker("^N225")
            nikkei_hist = nikkei.history(period="7d")
            
            if nikkei_hist.empty or len(nikkei_hist) < 2:
                try:
                    nikkei_ak = ak.index_investing_global(symbol="日经225指数", period="1周")
                    if not nikkei_ak.empty:
                        nikkei_hist = nikkei_ak.rename(columns={
                            '收盘': 'Close',
                            '最高': 'High',
                            '最低': 'Low'
                        })
                except Exception as e:
                    print(f"备用数据源获取失败: {str(e)}")
                    raise ValueError("无法获取有效的日经指数数据")
            
            # 计算技术指标
            tech_indicators = await calculate_technical_indicators(nikkei_hist)
            
            # 计算其他指标
            nikkei_change = ((nikkei_hist['Close'].iloc[-1] - nikkei_hist['Close'].iloc[-2]) / nikkei_hist['Close'].iloc[-2]) * 100
            nikkei_trend = "上涨" if nikkei_change > 0 else "下跌"
            nikkei_week_change = ((nikkei_hist['Close'].iloc[-1] - nikkei_hist['Close'].iloc[0]) / nikkei_hist['Close'].iloc[0]) * 100
            nikkei_high = nikkei_hist['High'].max()
            nikkei_low = nikkei_hist['Low'].min()
            nikkei_avg = nikkei_hist['Close'].mean()
            
            # 获取ETF数据
            etf_data = await get_etf_data("159866.SZ", session)
            
            return {
                'nikkei_change': nikkei_change,
                'nikkei_trend': nikkei_trend,
                'nikkei_week_change': nikkei_week_change,
                'nikkei_high': nikkei_high,
                'nikkei_low': nikkei_low,
                'nikkei_avg': nikkei_avg,
                'etf_data': etf_data,
                'technical_indicators': tech_indicators,
                'nikkei_hist': nikkei_hist  # 添加历史数据用于绘图
            }
    except Exception as e:
        print(f"获取数据时发生错误: {str(e)}")
        return None

def should_run_task():
    """判断是否应该执行定时任务"""
    try:
        now = datetime.now()
        # 判断是否是工作日
        if now.weekday() >= 5:  # 5是周六，6是周日
            print("当前为周末，不执行任务")
            return False
            
        # 判断是否在交易时间内（9:30-15:00）
        current_time = now.time()
        start_time = datetime.strptime("09:30", "%H:%M").time()
        end_time = datetime.strptime("15:00", "%H:%M").time()
        
        # 添加午休时间判断（11:30-13:00）
        lunch_start = datetime.strptime("11:30", "%H:%M").time()
        lunch_end = datetime.strptime("13:00", "%H:%M").time()
        
        if lunch_start <= current_time <= lunch_end:
            print("当前为午休时间，不执行任务")
            return False
            
        if not (start_time <= current_time <= end_time):
            print(f"当前时间 {current_time.strftime('%H:%M')} 不在交易时间内")
            return False
            
        return True
    except Exception as e:
        print(f"判断交易时间时发生错误: {str(e)}")
        return False

def generate_html_report(message: str, market_data: Dict, position_data: Dict) -> str:
    try:
        # 创建图表
        fig = make_subplots(rows=2, cols=1, subplot_titles=('日经225指数走势', '技术指标'),
                          row_heights=[0.7, 0.3], vertical_spacing=0.12)
        
        # 添加K线图
        nikkei_hist = market_data.get('nikkei_hist')
        if nikkei_hist is not None:
            fig.add_trace(
                go.Candlestick(
                    x=nikkei_hist.index,
                    open=nikkei_hist['Open'],
                    high=nikkei_hist['High'],
                    low=nikkei_hist['Low'],
                    close=nikkei_hist['Close'],
                    name='日经225',
                    increasing_line_color='#e94235',
                    decreasing_line_color='#34a853'
                ),
                row=1, col=1
            )
            
            # 添加技术指标
            tech_indicators = market_data.get('technical_indicators', {})
            if tech_indicators:
                # 添加RSI
                fig.add_trace(
                    go.Scatter(
                        x=nikkei_hist.index,
                        y=[tech_indicators.get('rsi', 50)] * len(nikkei_hist),
                        name='RSI',
                        line=dict(color='#4285f4', width=2)
                    ),
                    row=2, col=1
                )
                
                # 添加MACD
                fig.add_trace(
                    go.Bar(
                        x=nikkei_hist.index,
                        y=[tech_indicators.get('macd_hist', 0)] * len(nikkei_hist),
                        name='MACD Histogram',
                        marker_color='#fbbc04'
                    ),
                    row=2, col=1
                )
        
        # 更新布局
        fig.update_layout(
            title={
                'text': '日经ETF技术分析图表',
                'font': {'size': 24, 'color': '#1a73e8'},
                'y': 0.95
            },
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            template="plotly_white",
            height=800,
            margin=dict(t=100)
        )
        
        # 更新x轴和y轴样式
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#f5f5f5')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f5f5f5')
        
        # 生成HTML报告
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>日经ETF分析报告</title>
            <style>
                :root {{
                    --primary-color: #1a73e8;
                    --success-color: #34a853;
                    --warning-color: #fbbc04;
                    --danger-color: #ea4335;
                    --text-color: #202124;
                    --secondary-text: #5f6368;
                    --background: #ffffff;
                    --secondary-background: #f8f9fa;
                    --border-color: #dadce0;
                }}
                
                body {{
                    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                    line-height: 1.6;
                    color: var(--text-color);
                    margin: 0;
                    padding: 0;
                    background-color: var(--secondary-background);
                }}
                
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 2rem;
                }}
                
                .report-header {{
                    background-color: var(--background);
                    padding: 2rem;
                    border-radius: 8px;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                    margin-bottom: 2rem;
                }}
                
                .chart-container {{
                    background-color: var(--background);
                    padding: 2rem;
                    border-radius: 8px;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                    margin-bottom: 2rem;
                }}
                
                .analysis-container {{
                    background-color: var(--background);
                    padding: 2rem;
                    border-radius: 8px;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                }}
                
                h1 {{
                    color: var(--primary-color);
                    margin: 0 0 1rem 0;
                    font-size: 2rem;
                }}
                
                h2 {{
                    color: var(--text-color);
                    margin: 1.5rem 0 1rem 0;
                    font-size: 1.5rem;
                }}
                
                .grid-container {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 1rem;
                    margin: 1rem 0;
                }}
                
                .indicator-card {{
                    background-color: var(--secondary-background);
                    padding: 1.5rem;
                    border-radius: 8px;
                    border-left: 4px solid var(--primary-color);
                    transition: transform 0.2s;
                }}
                
                .indicator-card:hover {{
                    transform: translateY(-2px);
                }}
                
                .indicator-label {{
                    color: var(--secondary-text);
                    font-size: 0.9rem;
                    margin-bottom: 0.5rem;
                    font-weight: 500;
                }}
                
                .indicator-value {{
                    color: var(--text-color);
                    font-size: 1.4rem;
                    font-weight: 600;
                    margin-bottom: 0.5rem;
                }}
                
                .indicator-change {{
                    font-size: 0.9rem;
                    font-weight: 500;
                }}
                
                .trend-up {{
                    color: var(--success-color);
                }}
                
                .trend-down {{
                    color: var(--danger-color);
                }}
                
                .grid-trading {{
                    margin-top: 2rem;
                    padding: 1.5rem;
                    background-color: var(--secondary-background);
                    border-radius: 8px;
                }}
                
                .grid-level {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 1rem;
                    margin: 0.5rem 0;
                    background-color: var(--background);
                    border-radius: 4px;
                    border-left: 4px solid var(--primary-color);
                }}
                
                .grid-price {{
                    font-weight: 600;
                    font-size: 1.1rem;
                }}
                
                .grid-position {{
                    color: var(--secondary-text);
                }}
                
                .disclaimer {{
                    margin-top: 2rem;
                    padding: 1.5rem;
                    background-color: var(--secondary-background);
                    border-radius: 8px;
                    font-size: 0.9rem;
                    color: var(--secondary-text);
                    line-height: 1.8;
                }}
                
                .technical-indicators {{
                    display: flex;
                    gap: 1rem;
                    flex-wrap: wrap;
                    margin: 1rem 0;
                }}
                
                .tech-indicator {{
                    flex: 1;
                    min-width: 150px;
                    padding: 1rem;
                    background-color: var(--background);
                    border-radius: 8px;
                    text-align: center;
                }}
                
                .tech-value {{
                    font-size: 1.2rem;
                    font-weight: 600;
                    margin: 0.5rem 0;
                }}
                
                .tech-label {{
                    color: var(--secondary-text);
                    font-size: 0.9rem;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="report-header">
                    <h1>日经ETF分析报告</h1>
                    <div class="grid-container">
                        <div class="indicator-card">
                            <div class="indicator-label">当前价格</div>
                            <div class="indicator-value">{position_data.get('current_price', '-')}</div>
                            <div class="indicator-change {{'trend-up' if position_data.get('profit_loss_rate', 0) > 0 else 'trend-down'}}">
                                {f"{position_data.get('profit_loss_rate', 0):.2f}%"}
                            </div>
                        </div>
                        <div class="indicator-card">
                            <div class="indicator-label">持仓成本</div>
                            <div class="indicator-value">{position_data.get('cost_price', '-')}</div>
                            <div class="indicator-change">
                                持仓: {position_data.get('position', 0):,}股
                            </div>
                        </div>
                        <div class="indicator-card">
                            <div class="indicator-label">浮动盈亏</div>
                            <div class="indicator-value {{'trend-up' if position_data.get('profit_loss', 0) > 0 else 'trend-down'}}">
                                {f"{position_data.get('profit_loss', 0):.2f}元"}
                            </div>
                        </div>
                    </div>
                    
                    <div class="technical-indicators">
                        <div class="tech-indicator">
                            <div class="tech-label">RSI</div>
                            <div class="tech-value">{market_data.get('technical_indicators', {}).get('rsi', '-')}</div>
                        </div>
                        <div class="tech-indicator">
                            <div class="tech-label">MACD</div>
                            <div class="tech-value">{market_data.get('technical_indicators', {}).get('macd', '-')}</div>
                        </div>
                        <div class="tech-indicator">
                            <div class="tech-label">KDJ</div>
                            <div class="tech-value">
                                K:{market_data.get('technical_indicators', {}).get('k', '-')}
                                D:{market_data.get('technical_indicators', {}).get('d', '-')}
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="chart-container">
                    {fig.to_html(full_html=False, include_plotlyjs='cdn')}
                </div>
                
                <div class="analysis-container">
                    <pre>{message}</pre>
                    
                    <div class="disclaimer">
                        <strong>风险提示：</strong>本分析报告仅供参考，投资决策请结合个人风险偏好及市场整体环境。过往表现不代表未来收益，投资需谨慎。
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
    except Exception as e:
        print(f"生成HTML报告时发生错误: {str(e)}")
        return f"<pre>生成图表失败\n\n{message}</pre>"

async def main():
    try:
        args = parse_arguments()
        
        async def run_analysis():
            try:
                # 获取市场数据
                market_data = await get_nikkei_data_async()
                if not market_data:
                    print("获取市场数据失败")
                    return
                
                # 计算持仓数据
                position_data = {
                    'cost_price': args.cost,
                    'position': args.position,
                    'current_price': market_data['etf_data'].get('current_price')
                }
                
                if position_data['current_price']:
                    position_data['profit_loss'] = (position_data['current_price'] - position_data['cost_price']) * position_data['position']
                    position_data['profit_loss_rate'] = (position_data['profit_loss'] / (position_data['cost_price'] * position_data['position'])) * 100
                
                # 生成网格交易建议
                grid_suggestion = generate_grid_trading_suggestion(
                    current_price=position_data['current_price'] or position_data['cost_price'],
                    base_price=position_data['cost_price'],
                    indicators=market_data['technical_indicators']
                )
                
                # 生成分析报告
                message = generate_nikkei_message(market_data, position_data, grid_suggestion)
                
                # 生成HTML报告
                html_content = generate_html_report(message, market_data, position_data)
                
                # 保存HTML报告
                report_path = os.path.join(os.path.dirname(__file__), 'report.html')
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                # 打开报告
                webbrowser.open('file://' + os.path.abspath(report_path))
                
                print(message)
                
            except Exception as e:
                print(f"执行分析时发生错误: {str(e)}")
        
        if args.immediate:
            # 立即执行一次
            await run_analysis()
        else:
            # 设置定时任务
            schedule.every(5).minutes.do(lambda: asyncio.run(run_analysis()))
            
            while True:
                if should_run_task():
                    schedule.run_pending()
                time.sleep(60)
                
    except Exception as e:
        print(f"程序运行时发生错误: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())