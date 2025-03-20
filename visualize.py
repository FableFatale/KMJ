import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_stock_dashboard(data, status, suggestion):
    """创建股票分析仪表板"""
    # 创建子图
    fig = make_subplots(rows=2, cols=1, 
                       subplot_titles=('价格走势', '成交量分析'),
                       vertical_spacing=0.1,
                       row_heights=[0.7, 0.3])

    # 添加K线图
    fig.add_trace(go.Candlestick(x=data.index,
                                open=data['Open'],
                                high=data['High'],
                                low=data['Low'],
                                close=data['Close'],
                                name='K线'),
                 row=1, col=1)

    # 添加20日均线
    fig.add_trace(go.Scatter(x=data.index, 
                            y=data['MA20'],
                            name='20日均线',
                            line=dict(color='orange')),
                 row=1, col=1)

    # 添加成交量柱状图 - 根据是否高于均量线着色
    colors = ['red' if vol > avg else 'green' for vol, avg in zip(data['Volume'], data['VOL120'])]
    fig.add_trace(go.Bar(x=data.index,
                        y=data['Volume'],
                        name='成交量',
                        marker_color=colors),
                 row=2, col=1)

    # 添加120日均量线
    fig.add_trace(go.Scatter(x=data.index,
                            y=data['VOL120'],
                            name='120日均量线',
                            line=dict(color='black', dash='dash')),
                 row=2, col=1)

    # 更新布局
    fig.update_layout(
        title={
            'text': f'股票分析仪表板 - 杨凯方法论分析结果: {status}',
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title='日期',
        yaxis_title='价格',
        xaxis2_title='日期',
        yaxis2_title='成交量',
        showlegend=True,
        annotations=[
            dict(
                x=0.5,
                y=-0.15,
                xref="paper",
                yref="paper",
                text=f"投资建议: {suggestion}",
                showarrow=False,
                font=dict(size=14)
            )
        ]
    )

    # 添加杨凯方法论规则验证结果
    price_above_ma20 = (data['Close'] > data['MA20']).rolling(4).min().iloc[-1] == 1
    volume_above_vol120 = (data['Volume'] > data['VOL120']).rolling(3).min().iloc[-1] == 1
    ma20_trend = data['MA20'].iloc[-1] > data['MA20'].iloc[-5]
    
    rules_text = [
        f"规则1: 价格连续4天位于20日均线上方 - {'✓' if price_above_ma20 else '✗'}",
        f"规则2: 成交量连续3天位于120日均量线上方 - {'✓' if volume_above_vol120 else '✗'}",
        f"规则3: 20日均线呈上升趋势 - {'✓' if ma20_trend else '✗'}"
    ]
    
    for i, text in enumerate(rules_text):
        fig.add_annotation(
            x=1.0,
            y=0.95 - i*0.05,
            xref="paper",
            yref="paper",
            text=text,
            showarrow=False,
            align="right",
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="black",
            borderwidth=1
        )

    return fig

def create_analysis_dashboard(analyzer):
    """创建完整的分析仪表板"""
    # 获取分析结果
    status, suggestion = analyzer.check_yang_kai_rules()
    
    # 创建仪表板
    dashboard = create_stock_dashboard(analyzer.data, status, suggestion)
    
    return dashboard, status, suggestion