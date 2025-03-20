import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def create_stock_chart(data, title="股票走势图"):
    """
    创建股票K线图和技术指标图表
    
    Args:
        data (pd.DataFrame): 包含OHLCV数据和技术指标的DataFrame
        title (str): 图表标题
    
    Returns:
        plotly.graph_objects.Figure: 完整的图表对象
    """
    # 创建子图
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(title, "成交量"),
        row_heights=[0.7, 0.3]
    )

    # 添加K线图
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name="K线"
        ),
        row=1, col=1
    )

    # 添加KMJ指标
    if 'KMJ1' in data.columns:
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data['KMJ1'],
                name="KMJ1",
                line=dict(color='blue')
            ),
            row=1, col=1
        )
    
    if 'KMJ2' in data.columns:
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data['KMJ2'],
                name="KMJ2",
                line=dict(color='orange')
            ),
            row=1, col=1
        )
    
    if 'KMJ3' in data.columns:
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data['KMJ3'],
                name="KMJ3",
                line=dict(color='red')
            ),
            row=1, col=1
        )

    # 添加成交量图
    colors = ['red' if row['close'] >= row['open'] else 'green' for idx, row in data.iterrows()]
    fig.add_trace(
        go.Bar(
            x=data.index,
            y=data['volume'],
            name="成交量",
            marker_color=colors
        ),
        row=2, col=1
    )

    # 更新布局
    fig.update_layout(
        height=800,
        xaxis_rangeslider_visible=False,
        template="plotly_white"
    )

    return fig

def create_industry_distribution_chart(stocks_df):
    """
    创建行业分布饼图
    
    Args:
        stocks_df (pd.DataFrame): 包含股票信息的DataFrame
    
    Returns:
        plotly.graph_objects.Figure: 饼图对象
    """
    industry_counts = stocks_df['industry_category'].value_counts()
    
    fig = go.Figure(data=[go.Pie(
        labels=industry_counts.index,
        values=industry_counts.values,
        hole=.3
    )])
    
    fig.update_layout(
        title="行业分布",
        height=400,
        template="plotly_white"
    )
    
    return fig

def create_score_distribution_chart(stocks_df):
    """
    创建技术得分分布直方图
    
    Args:
        stocks_df (pd.DataFrame): 包含股票信息的DataFrame
    
    Returns:
        plotly.graph_objects.Figure: 直方图对象
    """
    fig = go.Figure(data=[go.Histogram(
        x=stocks_df['technical_score'],
        nbinsx=20,
        name="得分分布"
    )])
    
    fig.update_layout(
        title="技术得分分布",
        xaxis_title="得分",
        yaxis_title="数量",
        height=400,
        template="plotly_white"
    )
    
    return fig 