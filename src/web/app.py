import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

from stock_data_fetcher import get_stock_list, get_stock_data
from stock_indicators import calculate_signals, screen_stocks
from stock_analyzer import analyze_stock, get_industry_stocks, get_industry_rank

# 必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="自动选股系统",
    layout="wide"
)

# Title and description
st.title("📈 自动选股系统")
st.markdown("""
本系统基于KMJ指标体系进行自动选股。主要特点：
- KMJ指标体系（趋势跟踪）
- 自动识别买卖信号
- 行业分类分析
- 技术分析评分
""")

@st.cache_data(ttl=3600)
def load_stock_list():
    return get_stock_list()

def main():
    st.title("自动荐股系统")
    
    # 侧边栏设置
    with st.sidebar:
        st.header("分析设置")
        
        # 获取行业列表
        try:
            stocks_df = get_stock_list()
            industries = ['全部'] + sorted(stocks_df['industry'].unique().tolist())
        except Exception as e:
            st.error(f"获取股票列表失败: {str(e)}")
            return
            
        # 行业选择
        selected_industry = st.selectbox(
            "选择行业",
            industries,
            index=0,
            key="industry_selector"  # 添加唯一的key
        )
        
        # 技术分析参数
        min_score = st.slider(
            "最低技术得分",
            min_value=0.0,
            max_value=10.0,
            value=6.0,
            step=0.5,
            help="只显示技术得分大于等于此值的股票"
        )
        
        days = st.number_input(
            "分析天数",
            min_value=30,
            max_value=120,
            value=60,
            step=5,
            help="用于技术分析的历史数据天数"
        )
    
    # 主界面布局
    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.subheader("股票列表")
        
        # 获取行业排名
        try:
            ranked_stocks = get_industry_rank(stocks_df, selected_industry, min_score)
            
            if ranked_stocks.empty:
                st.warning(f"没有找到符合条件的股票（行业：{selected_industry}，最低得分：{min_score}）")
            else:
                # 显示股票列表
                st.dataframe(
                    ranked_stocks[['symbol', 'name', 'technical_score']].rename(columns={
                        'symbol': '代码',
                        'name': '名称',
                        'technical_score': '技术得分'
                    }),
                    height=600
                )
                
                # 选择股票进行详细分析
                selected_stock = st.selectbox(
                    "选择股票查看详细分析",
                    ranked_stocks['symbol'].tolist(),
                    format_func=lambda x: f"{x} - {ranked_stocks[ranked_stocks['symbol'] == x]['name'].iloc[0]}",
                    key="stock_selector"  # 添加唯一的key
                )
        except Exception as e:
            st.error(f"获取行业排名失败: {str(e)}")
            return
    
    with col2:
        if 'selected_stock' in locals():
            st.subheader("股票分析")
            
            try:
                # 获取股票数据
                stock_data = get_stock_data(selected_stock, days)
                if stock_data.empty:
                    st.warning("无法获取股票数据")
                    return
                    
                # 分析股票
                stock_info = ranked_stocks[ranked_stocks['symbol'] == selected_stock].iloc[0]
                analysis_result = analyze_stock(stock_data, stock_info['industry'])
                
                # 显示分析结果
                st.markdown(f"### {stock_info['name']} ({selected_stock})")
                st.markdown(analysis_result['analysis'])
                
                # 显示K线图
                st.line_chart(stock_data[['close', 'KMJ2', 'KMJ3']])
                
                # 显示成交量
                st.bar_chart(stock_data['volume'])
                
            except Exception as e:
                st.error(f"分析股票失败: {str(e)}")
                return

def plot_stock_chart(df):
    fig = go.Figure()
    
    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='K线'
    ))
    
    # Add KMJ2 and KMJ3 lines
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['kmj2'],
        name='KMJ2',
        line=dict(color='purple')
    ))
    
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['kmj3'],
        name='KMJ3',
        line=dict(color='blue')
    ))
    
    # Add buy signals
    buy_signals = df[df['buy_signal']]
    fig.add_trace(go.Scatter(
        x=buy_signals['date'],
        y=buy_signals['low'] * 0.99,
        mode='markers',
        name='买入信号',
        marker=dict(
            symbol='triangle-up',
            size=10,
            color='red'
        )
    ))
    
    # Add sell signals
    sell_signals = df[df['sell_signal']]
    fig.add_trace(go.Scatter(
        x=sell_signals['date'],
        y=sell_signals['high'] * 1.01,
        mode='markers',
        name='卖出信号',
        marker=dict(
            symbol='triangle-down',
            size=10,
            color='green'
        )
    ))
    
    fig.update_layout(
        title='股票走势与信号',
        yaxis_title='价格',
        xaxis_title='日期',
        height=600
    )
    
    return fig

if __name__ == "__main__":
    main()