# KMJ指标选股系统

基于KMJ技术指标的A股选股系统，使用Streamlit构建Web界面。

## 项目结构

```
项目根目录/
├── src/                    # 源代码目录
│   ├── core/              # 核心功能模块
│   │   ├── kmj_indicator.py     # KMJ指标计算
│   │   ├── stock_analyzer.py    # 股票分析逻辑
│   │   ├── stock_data_fetcher.py # 数据获取模块
│   │   └── stock_indicators.py   # 技术指标计算
│   └── utils/             # 工具类
│       ├── visualize.py        # 数据可视化
│       ├── code_executor.py    # 代码执行器
│       └── feishu_sync.py      # 飞书同步工具
├── docs/                   # 文档目录
│   ├── guides/            # 使用指南
│   │   ├── AutoStock.md       # 自动选股说明
│   │   └── 杨凯.md            # 开发文档
│   ├── knowledge/         # 知识库
│   │   └── 股票知识学习.md     # 股票知识文档
│   └── reports/           # 报告文档
│       ├── report.html        # 分析报告
│       └── stock_analysis_report.html # 股票分析报告
├── tests/                  # 测试目录
│   ├── run_tests.py          # 测试运行器
│   └── test_stock_data_fetcher.py # 数据获取测试
├── charts/                 # 图表目录
│   ├── stock/             # 股票图表
│   │   ├── price_ma20_chart.html
│   │   ├── volume_vol120_chart.html
│   │   └── stock_analysis_chart.html
│   └── nikkei/            # 日经指数相关
│       └── rijing.py          # 日经指数分析
├── static/                 # 静态资源
│   └── images/            # 图片资源
├── config/                 # 配置文件
│   └── requirements.txt    # 项目依赖
├── .streamlit/            # Streamlit配置
│   └── config.toml        # Streamlit配置文件
├── app.py                 # 应用主文件
├── main.py               # 入口文件
└── run.py                # 运行脚本
```

## 功能特点

- KMJ指标体系（趋势跟踪）
- 自动识别买卖信号
- 行业分类分析
- 技术分析评分（100分制）
- 实时数据更新
- 可视化分析结果

## 安装说明

1. 克隆项目：
```bash
git clone [项目地址]
cd [项目目录]
```

2. 安装依赖：
```bash
pip install -r config/requirements.txt
```

3. 运行应用：
```bash
streamlit run main.py
```

## 使用方法

1. 在侧边栏输入Tushare Token
2. 选择板块和行业
3. 设置技术分析分数阈值
4. 等待系统计算技术得分
5. 查看筛选结果

## 技术得分说明

- 90-100分：极强势
- 70-89分：强势
- 50-69分：中性偏强
- 30-49分：中性偏弱
- 0-29分：弱势

## 开发说明

- 主要依赖：Python 3.12
- Web框架：Streamlit 1.31.1
- 数据源：Tushare API
- 图表库：Plotly

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License 