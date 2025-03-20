import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.core.stock_data_fetcher import get_stock_list, get_stock_data
from src.core.kmj_indicator import calculate_kmj_indicators, get_kmj_signals

# 行业分类
INDUSTRY_CATEGORIES = {
    '银行': ['银行', '保险'],
    '房地产': ['房地产', '建筑', '建材'],
    '医药生物': ['医药生物', '医疗器械', '生物制品'],
    '科技': ['计算机', '通信', '电子', '传媒'],
    '消费': ['食品饮料', '家用电器', '纺织服装', '商业贸易', '休闲服务'],
    '制造业': ['机械设备', '电气设备', '国防军工', '汽车', '交通运输'],
    '能源': ['石油化工', '煤炭', '有色金属', '钢铁', '电力', '采掘'],
    '金融': ['证券', '多元金融', '保险'],
    '公用事业': ['公用事业', '环保', '水务'],
    '农林牧渔': ['农林牧渔'],
    '其他': ['综合']
}

# 获取行业标准分类
def get_industry_category(industry):
    """将行业名称映射到标准行业分类"""
    if industry is None or pd.isna(industry):
        return '其他'
    
    industry_str = str(industry).lower()
    for category, industries in INDUSTRY_CATEGORIES.items():
        for ind in industries:
            if ind.lower() in industry_str:
                return category
    return '其他'

# Page config
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
    """加载股票列表，带有重试机制"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            stocks_df = get_stock_list()
            if stocks_df is not None and not stocks_df.empty:
                logger.info(f"Successfully loaded {len(stocks_df)} stocks")
                
                # 初始化技术分析得分
                stocks_df['technical_score'] = 0.0
                
                # 标准化行业分类
                if 'industry' in stocks_df.columns:
                    # 确保industry列存在，否则添加默认值
                    stocks_df['industry'] = stocks_df['industry'].fillna('其他')
                    
                    # 为空行业添加基本分类（根据股票代码特征）
                    mask_unknown = stocks_df['industry'].isin(['其他', '未知']) | stocks_df['industry'].isna()
                    
                    # 使用字符串方法而不是正则表达式进行匹配
                    # 银行股
                    bank_mask = mask_unknown & (
                        stocks_df['symbol'].str.startswith(('600', '601'), na=False) & 
                        stocks_df['name'].str.contains('银行', na=False)
                    )
                    stocks_df.loc[bank_mask, 'industry'] = '银行'
                    
                    # 券商股
                    securities_mask = mask_unknown & stocks_df['name'].str.contains('证券', na=False)
                    stocks_df.loc[securities_mask, 'industry'] = '证券'
                    
                    # 保险股
                    insurance_mask = mask_unknown & stocks_df['name'].str.contains('保险', na=False)
                    stocks_df.loc[insurance_mask, 'industry'] = '保险'
                    
                    # 房地产
                    real_estate_keywords = ['地产', '房产', '置业']
                    real_estate_mask = mask_unknown & stocks_df['name'].str.contains('|'.join(real_estate_keywords), na=False)
                    stocks_df.loc[real_estate_mask, 'industry'] = '房地产'
                    
                    # 医药生物
                    pharma_keywords = ['医药', '生物', '制药']
                    pharma_mask = mask_unknown & stocks_df['name'].str.contains('|'.join(pharma_keywords), na=False)
                    stocks_df.loc[pharma_mask, 'industry'] = '医药生物'
                    
                    # 通信
                    comm_keywords = ['通信', '电信', '移动']
                    comm_mask = mask_unknown & stocks_df['name'].str.contains('|'.join(comm_keywords), na=False)
                    stocks_df.loc[comm_mask, 'industry'] = '通信'
                    
                    # 电子
                    electronics_keywords = ['电子', '芯片', '半导体']
                    electronics_mask = mask_unknown & stocks_df['name'].str.contains('|'.join(electronics_keywords), na=False)
                    stocks_df.loc[electronics_mask, 'industry'] = '电子'
                    
                    # 计算机
                    computer_keywords = ['软件', '网络', '计算机']
                    computer_mask = mask_unknown & stocks_df['name'].str.contains('|'.join(computer_keywords), na=False)
                    stocks_df.loc[computer_mask, 'industry'] = '计算机'
                    
                    # 添加行业分类列
                    stocks_df['industry_category'] = stocks_df['industry'].apply(get_industry_category)
                    
                    # 输出行业分类统计，帮助调试
                    logger.info(f"行业分类统计: {stocks_df['industry_category'].value_counts().to_dict()}")
                    logger.info(f"细分行业样例: {stocks_df['industry'].head(10).tolist()}")
                else:
                    stocks_df['industry'] = '其他'
                    stocks_df['industry_category'] = '其他'
                
                # 计算部分股票的技术评分
                try:
                    # 优先选择主板股票，大市值公司
                    sample_stocks = stocks_df[stocks_df['symbol'].str.startswith(('000', '600'), na=False)].head(30)
                    logger.info(f"Calculating technical scores for {len(sample_stocks)} stocks")
                    
                    for idx, row in sample_stocks.iterrows():
                        try:
                            data = get_stock_data(row['ts_code'], days=30)
                            if data is not None and not data.empty:
                                score = calculate_technical_score(data)
                                stocks_df.loc[stocks_df['ts_code'] == row['ts_code'], 'technical_score'] = score
                                logger.info(f"Calculated score for {row['ts_code']}: {score}")
                        except Exception as e:
                            logger.error(f"Error calculating score for {row['ts_code']}: {str(e)}")
                    
                    logger.info("Finished calculating technical scores")
                except Exception as e:
                    logger.error(f"Error during technical score calculation: {str(e)}")
                
                return stocks_df
            time.sleep(retry_delay)
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}: Failed to load stock list - {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                st.error(f"获取股票列表失败: {str(e)}")
                return pd.DataFrame(columns=['symbol', 'name', 'industry', 'industry_category', 'ts_code', 'technical_score'])
    
    return pd.DataFrame(columns=['symbol', 'name', 'industry', 'industry_category', 'ts_code', 'technical_score'])

def calculate_technical_score(data):
    """计算技术分析得分"""
    try:
        if data is None or data.empty:
            return 0.0
            
        # 确保KMJ指标已计算
        if 'KMJ1' not in data.columns:
            data = calculate_kmj_indicators(data)
            
        # 获取最新的数据
        latest = data.iloc[-1]
        
        # 基础分数为50分
        score = 50.0
        
        # 趋势得分 (最高30分)
        if 'KMJ_TREND' in latest:
            if latest['KMJ_TREND'] == 1:  # 上涨趋势
                score += 30
            elif latest['KMJ_TREND'] == -1:  # 下跌趋势
                score -= 20
                
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
                    score += min(10, vol_change / 2)
                else:
                    score -= min(10, abs(vol_change) / 2)
                    
        # 确保分数在0-100之间
        return max(0, min(100, score))
    except Exception as e:
        logger.error(f"Error calculating technical score: {str(e)}")
        return 0.0

def get_stock_boards(symbol):
    """获取股票所属板块"""
    if symbol.startswith('600') or symbol.startswith('601') or symbol.startswith('603'):
        return '上证主板'
    elif symbol.startswith('000'):
        return '深证主板'
    elif symbol.startswith('002'):
        return '中小板'
    elif symbol.startswith('300'):
        return '创业板'
    elif symbol.startswith('688'):
        return '科创板'
    else:
        return '其他'

def screen_stocks(stocks_df, min_score=0, selected_industry_category='全部', selected_board='全部', max_stocks=50):
    """筛选股票"""
    # 按技术分数筛选
    filtered_stocks = stocks_df[stocks_df['technical_score'] >= min_score]
    
    # 按行业分类筛选
    if selected_industry_category != '全部':
        filtered_stocks = filtered_stocks[filtered_stocks['industry_category'] == selected_industry_category]
    
    # 按板块筛选
    if selected_board != '全部':
        if selected_board == '主板':
            # 上交所主板(600, 601, 603)或深交所主板(000)
            filtered_stocks = filtered_stocks[
                filtered_stocks['symbol'].str.startswith(('600', '601', '603', '000'))
            ]
        elif selected_board == '创业板':
            # 创业板(300)
            filtered_stocks = filtered_stocks[filtered_stocks['symbol'].str.startswith('300')]
        elif selected_board == '科创板':
            # 科创板(688)
            filtered_stocks = filtered_stocks[filtered_stocks['symbol'].str.startswith('688')]
        elif selected_board == '中小板':
            # 中小板(002)
            filtered_stocks = filtered_stocks[filtered_stocks['symbol'].str.startswith('002')]
    
    # 按技术得分排序并限制数量
    filtered_stocks = filtered_stocks.nlargest(max_stocks, 'technical_score')
    
    return filtered_stocks

def get_stock_data_with_indicators(stock_code, days=60):
    """获取带有技术指标的股票数据"""
    data = get_stock_data(stock_code, days=days)
    if data is not None and not data.empty:
        # 计算KMJ指标
        try:
            data = calculate_kmj_indicators(data)
            data = get_kmj_signals(data)
        except Exception as e:
            logger.error(f"Error calculating KMJ indicators: {str(e)}")
            st.warning("计算KMJ指标时出错，可能会影响分析结果")
    return data

def main():
    # 初始化session_state
    if 'filtered_stocks' not in st.session_state:
        st.session_state['filtered_stocks'] = None
    
    if 'selected_board' not in st.session_state:
        st.session_state['selected_board'] = '全部'
        
    if 'selected_industry_category' not in st.session_state:
        st.session_state['selected_industry_category'] = '全部'
        
    if 'selected_industry' not in st.session_state:
        st.session_state['selected_industry'] = '全部'
        
    if 'min_score' not in st.session_state:
        st.session_state['min_score'] = 0
        
    if 'max_stocks' not in st.session_state:
        st.session_state['max_stocks'] = 50
        
    if 'sort_by' not in st.session_state:
        st.session_state['sort_by'] = '技术得分'
    
    # 获取股票列表
    with st.spinner('正在获取股票列表...'):
        try:
            stocks_df = load_stock_list()
            if not stocks_df.empty:
                st.success(f"成功获取到 {len(stocks_df)} 只股票")
                
                # 设置侧边栏
                with st.sidebar:
                    st.title("配置")
                    
                    # 板块选择
                    selected_board = st.selectbox(
                        "选择板块",
                        ['全部', '主板', '创业板', '科创板', '中小板'],
                        index=['全部', '主板', '创业板', '科创板', '中小板'].index(st.session_state['selected_board'])
                    )
                    st.session_state['selected_board'] = selected_board
                    
                    # 行业大类选择
                    industry_categories = ['全部'] + sorted(list(INDUSTRY_CATEGORIES.keys()))
                    selected_industry_category = st.selectbox(
                        "选择行业大类",
                        industry_categories,
                        index=industry_categories.index(st.session_state['selected_industry_category']) if st.session_state['selected_industry_category'] in industry_categories else 0
                    )
                    st.session_state['selected_industry_category'] = selected_industry_category
                    
                    # 细分行业选择
                    if selected_industry_category != '全部' and 'industry_category' in stocks_df.columns:
                        # 获取该大类下的所有细分行业
                        category_stocks = stocks_df[stocks_df['industry_category'] == selected_industry_category]
                        
                        if not category_stocks.empty:
                            # 确保所有行业值都是字符串，并消除空值
                            category_industries = [str(ind) for ind in category_stocks['industry'].unique() if ind and not pd.isna(ind)]
                            
                            if category_industries:
                                industry_options = ['全部'] + sorted(category_industries)
                                selected_industry = st.selectbox(
                                    "选择细分行业",
                                    industry_options,
                                    index=industry_options.index(st.session_state['selected_industry']) if st.session_state['selected_industry'] in industry_options else 0
                                )
                                st.session_state['selected_industry'] = selected_industry
                                
                                # 显示debug信息
                                if st.checkbox("显示行业调试信息", key="debug_industries", value=False):
                                    st.write(f"当前行业大类: {selected_industry_category}")
                                    st.write(f"该大类包含 {len(category_industries)} 个细分行业")
                                    st.write(f"细分行业示例: {category_industries[:5]}")
                            else:
                                st.info(f"'{selected_industry_category}'类别下没有细分行业")
                                selected_industry = '全部'
                                st.session_state['selected_industry'] = selected_industry
                        else:
                            st.info(f"没有找到'{selected_industry_category}'类别的股票")
                            selected_industry = '全部'
                            st.session_state['selected_industry'] = selected_industry
                    else:
                        selected_industry = '全部'
                        st.session_state['selected_industry'] = selected_industry
                    
                    # 技术分析得分
                    min_score = st.slider("最小技术得分", 0, 100, st.session_state['min_score'], 5)
                    st.session_state['min_score'] = min_score
                    
                    # 最大显示数量
                    max_stocks = st.slider("最大显示数量", 10, 100, st.session_state['max_stocks'], 5)
                    st.session_state['max_stocks'] = max_stocks
                    
                    # 排序方式
                    sort_by = st.selectbox(
                        "排序方式",
                        ['技术得分', '代码', '名称'],
                        index=['技术得分', '代码', '名称'].index(st.session_state['sort_by'])
                    )
                    st.session_state['sort_by'] = sort_by
                    
                    # 开始筛选按钮
                    start_screening = st.button("开始筛选", type="primary")
                    
                    # 分隔线
                    st.divider()
                    
                    # 根据筛选条件过滤股票
                    if start_screening or st.session_state['filtered_stocks'] is None:
                        filtered_stocks = screen_stocks(
                            stocks_df, 
                            min_score=min_score, 
                            selected_industry_category=selected_industry_category,
                            selected_board=selected_board,
                            max_stocks=max_stocks
                        )
                        
                        # 按细分行业筛选
                        if selected_industry != '全部':
                            filtered_stocks = filtered_stocks[filtered_stocks['industry'] == selected_industry]
                        
                        # 按选择的方式排序
                        if sort_by == '技术得分':
                            filtered_stocks = filtered_stocks.sort_values('technical_score', ascending=False)
                        elif sort_by == '代码':
                            filtered_stocks = filtered_stocks.sort_values('symbol')
                        elif sort_by == '名称':
                            filtered_stocks = filtered_stocks.sort_values('name')
                            
                        st.session_state['filtered_stocks'] = filtered_stocks
                    else:
                        filtered_stocks = st.session_state['filtered_stocks']
                    
                    # 股票选择
                    st.subheader("股票选择")
                    if not filtered_stocks.empty:
                        st.success(f"找到 {len(filtered_stocks)} 只符合条件的股票")
                        
                        stock_options = [''] + filtered_stocks.apply(
                            lambda x: f"{x['symbol']} - {x['name']}", axis=1
                        ).tolist()
                        
                        selected_stock = st.selectbox(
                            "选择股票查看详情",
                            stock_options
                        )
                    else:
                        st.warning("没有符合条件的股票")
                        stock_options = ['']
                        selected_stock = ''
                
                # 创建主页面的两列布局
                col1, col2 = st.columns([3, 1])
                
                with col2:
                    # 显示排名 (如果有技术得分)
                    st.subheader(f"{'全市场' if selected_industry_category == '全部' else selected_industry_category}技术评分排名")
                    
                    # 为了避免technical_score不存在的错误，确保它存在
                    if 'technical_score' not in stocks_df.columns:
                        stocks_df['technical_score'] = 0.0
                        st.info("股票评分尚未计算")
                    
                    # 显示筛选结果
                    try:
                        if filtered_stocks is not None and not filtered_stocks.empty:
                            # 创建排名表格
                            ranking_df = filtered_stocks[['symbol', 'name', 'technical_score']].copy()
                            # 添加排名列
                            ranking_df.insert(0, '排名', range(1, len(ranking_df) + 1))
                            
                            # 重命名列为中文
                            ranking_df = ranking_df.rename(columns={
                                'symbol': '代码',
                                'name': '名称', 
                                'technical_score': '技术评分'
                            })
                            
                            # 应用格式化并显示
                            st.dataframe(
                                ranking_df.style.format({
                                    '技术评分': '{:.2f}'
                                }),
                                use_container_width=True,
                                height=400
                            )
                        else:
                            st.info("没有符合条件的股票")
                    except Exception as e:
                        logger.error(f"Error displaying ranking: {str(e)}")
                        st.error("显示排名时出错")
                    
                    # 添加刷新按钮
                    if st.button("刷新数据"):
                        st.cache_data.clear()
                        st.rerun()
                
                with col1:
                    # 只有当选择了具体股票时才显示K线图和分析结果
                    if selected_stock and selected_stock != '':
                        # 提取股票代码
                        stock_code = selected_stock.split(' - ')[0]
                        stock_info = stocks_df[stocks_df['symbol'] == stock_code].iloc[0]
                        
                        # 获取股票数据
                        with st.spinner('正在获取历史数据...'):
                            data = get_stock_data_with_indicators(stock_code, days=60)
                            
                            if data is not None and not data.empty:
                                # 计算KMJ指标
                                try:
                                    data = calculate_kmj_indicators(data)
                                    
                                    # 添加信号
                                    data = get_kmj_signals(data)
                                except Exception as e:
                                    logger.error(f"Error calculating KMJ indicators: {str(e)}")
                                    st.warning("计算KMJ指标时出错，可能会影响分析结果")
                                
                                # 计算单支股票的技术得分
                                technical_score = calculate_technical_score(data)
                                
                                # 更新股票列表中的技术评分
                                stocks_df.loc[stocks_df['symbol'] == stock_code, 'technical_score'] = technical_score
                                
                                # 显示股票基本信息
                                st.subheader(f"{selected_stock} - 基本信息")
                                info_cols = st.columns(4)
                                
                                with info_cols[0]:
                                    st.metric("技术分析得分", f"{technical_score:.2f}分")
                                
                                with info_cols[1]:
                                    board = get_stock_boards(stock_code)
                                    st.metric("所属板块", board)
                                    
                                with info_cols[2]:
                                    industry_cat = stock_info['industry_category'] if 'industry_category' in stock_info else '未知'
                                    st.metric("行业大类", industry_cat)
                                    
                                with info_cols[3]:
                                    industry = stock_info['industry'] if 'industry' in stock_info else '未知'
                                    st.metric("细分行业", industry)
                                
                                # 显示分析结果
                                st_col1, st_col2 = st.columns([3, 1])
                                
                                with st_col1:
                                    # 创建K线图
                                    fig = go.Figure(data=[go.Candlestick(
                                        x=data['date'],
                                        open=data['open'],
                                        high=data['high'],
                                        low=data['low'],
                                        close=data['close'],
                                        name='K线'
                                    )])
                                    
                                    # 添加KMJ指标
                                    if 'KMJ2' in data.columns and 'KMJ3' in data.columns:
                                        # 过滤掉NaN值
                                        valid_data = data.dropna(subset=['KMJ2', 'KMJ3'])
                                        
                                        if not valid_data.empty:
                                            fig.add_trace(go.Scatter(
                                                x=valid_data['date'],
                                                y=valid_data['KMJ2'],
                                                name='KMJ2',
                                                line=dict(color='purple')
                                            ))
                                            fig.add_trace(go.Scatter(
                                                x=valid_data['date'],
                                                y=valid_data['KMJ3'],
                                                name='KMJ3',
                                                line=dict(color='blue')
                                            ))
                                        else:
                                            st.warning("KMJ指标数据缺失，无法显示趋势线")
                                    
                                    # 添加买入信号
                                    if 'KMJ_BUY_SIGNAL' in data.columns:
                                        buy_signals = data[data['KMJ_BUY_SIGNAL'] == True]
                                        if not buy_signals.empty:
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
                                    
                                    # 添加卖出信号
                                    if 'KMJ_SELL_SIGNAL' in data.columns:
                                        sell_signals = data[data['KMJ_SELL_SIGNAL'] == True]
                                        if not sell_signals.empty:
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
                                        title=f"{selected_stock} K线图",
                                        yaxis_title="价格",
                                        xaxis_title="日期",
                                        template="plotly_dark",
                                        height=500
                                    )
                                    
                                    st.plotly_chart(fig, use_container_width=True)
                                
                                with st_col2:
                                    # 显示技术分析结果
                                    st.subheader("技术指标")
                                    
                                    if 'KMJ_TREND' in data.columns:
                                        latest_trend = data.iloc[-1]['KMJ_TREND']
                                        if pd.notna(latest_trend):
                                            trend_text = "上涨" if latest_trend == 1 else "下跌" if latest_trend == -1 else "横盘"
                                            trend_delta = "↗" if latest_trend == 1 else "↘" if latest_trend == -1 else "→"
                                            delta_color = "normal" if latest_trend == 1 else "inverse" if latest_trend == -1 else "off"
                                            st.metric("当前趋势", trend_text, delta=trend_delta, delta_color=delta_color)
                                        else:
                                            st.metric("当前趋势", "数据不足")
                                    
                                    # 显示最新信号
                                    signals = []
                                    if 'KMJ_BUY_SIGNAL' in data.columns and data.iloc[-1]['KMJ_BUY_SIGNAL'] == True:
                                        signals.append("买入")
                                    if 'KMJ_SELL_SIGNAL' in data.columns and data.iloc[-1]['KMJ_SELL_SIGNAL'] == True:
                                        signals.append("卖出")
                                    if 'LIMIT_UP' in data.columns and data.iloc[-1]['LIMIT_UP'] == True:
                                        signals.append("涨停")
                                    
                                    if signals:
                                        st.metric("最新信号", "、".join(signals))
                                    else:
                                        st.metric("最新信号", "无")
                                    
                                    # 显示数据摘要
                                    latest = data.iloc[-1]
                                    prev5 = data.iloc[-6] if len(data) > 5 else None
                                    
                                    if prev5 is not None:
                                        price_change_5d = (latest['close'] / prev5['close'] - 1) * 100
                                        delta_color = "normal" if price_change_5d >= 0 else "inverse"
                                        st.metric("5日涨跌幅", f"{price_change_5d:.2f}%", 
                                                 delta=f"{price_change_5d:.2f}%",
                                                 delta_color=delta_color)
                                    
                                    # 显示价格/成交量
                                    st.metric("最新价", f"{latest['close']:.2f}")
                                    if 'volume' in latest and pd.notna(latest['volume']) and latest['volume'] > 0:
                                        st.metric("成交量", format_volume(latest['volume']))
                                    else:
                                        st.metric("成交量", "无数据")
                                
                                # 显示详细分析
                                st.subheader("详细分析")
                                
                                # 生成分析文本
                                analysis_text = []
                                
                                # KMJ分析
                                if 'KMJ2' in data.columns and 'KMJ3' in data.columns:
                                    latest = data.iloc[-1]
                                    if pd.notna(latest['KMJ2']) and pd.notna(latest['KMJ3']) and latest['KMJ3'] != 0:
                                        if latest['KMJ2'] > latest['KMJ3']:
                                            diff_pct = (latest['KMJ2'] / latest['KMJ3'] - 1) * 100
                                            analysis_text.append(f"KMJ2高于KMJ3 {diff_pct:.2f}%，处于上升趋势")
                                        else:
                                            diff_pct = (latest['KMJ3'] / latest['KMJ2'] - 1) * 100
                                            analysis_text.append(f"KMJ2低于KMJ3 {diff_pct:.2f}%，处于下降趋势")
                                    else:
                                        analysis_text.append("KMJ指标数据不足，无法分析趋势")
                                
                                # 价格分析
                                if len(data) > 5:
                                    price_change_5d = (latest['close'] / data.iloc[-6]['close'] - 1) * 100
                                    analysis_text.append(f"近5日涨跌幅: {price_change_5d:.2f}%")
                                
                                if len(data) > 20:
                                    price_change_20d = (latest['close'] / data.iloc[-21]['close'] - 1) * 100
                                    analysis_text.append(f"近20日涨跌幅: {price_change_20d:.2f}%")
                                
                                # 成交量分析
                                if 'volume' in data.columns and len(data) > 5:
                                    vol_5d = data['volume'].tail(5).mean()
                                    vol_prev_5d = data['volume'].iloc[-10:-5].mean() if len(data) > 10 else data['volume'].mean()
                                    
                                    if pd.notna(vol_5d) and pd.notna(vol_prev_5d) and vol_prev_5d > 0:
                                        if vol_5d > vol_prev_5d:
                                            vol_change = (vol_5d / vol_prev_5d - 1) * 100
                                            analysis_text.append(f"近5日成交量增加 {vol_change:.2f}%")
                                        else:
                                            vol_change = (vol_prev_5d / vol_5d - 1) * 100
                                            analysis_text.append(f"近5日成交量减少 {vol_change:.2f}%")
                                    else:
                                        analysis_text.append("成交量数据不足，无法分析")
                                
                                # 显示分析结果
                                if analysis_text:
                                    st.text("\n".join(analysis_text))
                                else:
                                    st.text("无法生成详细分析")
                                
                                # 显示数据表格
                                with st.expander("查看历史数据"):
                                    display_data = data.copy()
                                    # 只显示重要列
                                    columns_to_show = ['date', 'open', 'high', 'low', 'close', 'volume']
                                    
                                    # 添加KMJ指标列
                                    if 'KMJ1' in display_data.columns:
                                        columns_to_show.append('KMJ1')
                                    if 'KMJ2' in display_data.columns:
                                        columns_to_show.append('KMJ2')
                                    if 'KMJ3' in display_data.columns:
                                        columns_to_show.append('KMJ3')
                                        
                                    # 显示数据
                                    st.dataframe(
                                        display_data[columns_to_show].style.format({
                                            'open': '{:.2f}',
                                            'high': '{:.2f}',
                                            'low': '{:.2f}',
                                            'close': '{:.2f}',
                                            'volume': '{:,.0f}',
                                            'KMJ1': '{:.2f}',
                                            'KMJ2': '{:.2f}',
                                            'KMJ3': '{:.2f}'
                                        })
                                    )
                            else:
                                st.error(f"无法获取 {selected_stock} 的数据，请尝试其他股票")
                    else:
                        st.info("👈 请从侧边栏选择一只股票进行分析")
            else:
                st.error("未能获取股票列表，请检查网络连接")
        except Exception as e:
            logger.error(f"Error in main: {str(e)}")
            st.error(f"发生错误：{str(e)}")
            st.info("请尝试刷新页面重试")

def format_volume(volume):
    """格式化成交量显示"""
    if volume is None or pd.isna(volume) or volume == 0:
        return "无数据"
    elif volume < 10000:
        return f"{volume:.2f}手"
    elif volume < 100000000:
        return f"{volume/10000:.2f}万手"
    else:
        return f"{volume/100000000:.2f}亿手"

if __name__ == "__main__":
    main()