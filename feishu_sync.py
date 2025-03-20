import requests
import json
from datetime import datetime

# 获取飞书应用Token和表格ID的步骤说明
"""
1. 获取飞书应用Token（app_token）：
   a. 访问飞书开放平台：https://open.feishu.cn/
   b. 点击「开始使用」并登录
   c. 在顶部菜单选择「开发者后台」
   d. 点击「创建企业自建应用」
   e. 填写应用名称（如：日经ETF数据同步）和应用描述
   f. 在应用功能中开启「多维表格」
   g. 在「权限管理」中添加以下权限：
      - bitable:record:read（读取多维表格记录）
      - bitable:record:write（写入多维表格记录）
   h. 在「凭证与基础信息」页面获取 App ID 和 App Secret
   i. 使用 App ID 和 App Secret 调用获取 app_token 的API：
      POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/
      {"app_id": "your_app_id", "app_secret": "your_app_secret"}

2. 获取表格ID（table_id）：
   a. 在飞书工作台创建一个新的多维表格
   b. 在表格中创建以下字段：
      - 更新时间（文本型）
      - 日经指数变动（文本型）
      - 周度变动（文本型）
      - 价格区间（文本型）
      - 均价（文本型）
      - ETF涨跌幅（文本型）
      - ETF周度涨跌（文本型）
      - 成交量比（文本型）
      - 溢价率（文本型）
      - 日元汇率（文本型）
      - 汇率趋势（文本型）
      - 纳指变动（文本型）
      - 标普500变动（文本型）
      - 美股趋势（文本型）
      - 持仓成本（文本型）
      - 当前价格（文本型）
      - 持仓数量（文本型）
      - 浮动盈亏（文本型）
   c. 从表格URL中获取table_id：
      - 打开多维表格
      - 从URL中提取table_id，格式如：
        https://your-company.feishu.cn/base/xxx/table/tblxxx
      - 其中的'tblxxx'就是table_id
"""

class FeishuTableSync:
    def __init__(self, app_token, table_id):
        self.app_token = app_token
        self.table_id = "tbloccdrRleM9Oa4"
        self.base_url = 'https://open.feishu.cn/open-apis/bitable/v1/apps/cli_a75ba2206e7c100e/'
        self.headers = {
            'Authorization': f'Bearer {self.app_token}',
            'Content-Type': 'application/json'
        }
    
    def sync_nikkei_data(self, market_data, position_data):
        """同步日经ETF数据到飞书多维表格"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 构建记录数据
            record = {
                'fields': {
                    '更新时间': current_time,
                    '日经指数变动': f"{market_data['nikkei_trend']} ({market_data['nikkei_change']:.2f}%)",
                    '周度变动': f"{market_data['nikkei_week_change']:.2f}%",
                    '价格区间': f"{market_data['nikkei_low']:.0f} - {market_data['nikkei_high']:.0f}",
                    '均价': f"{market_data['nikkei_avg']:.0f}",
                    'ETF涨跌幅': f"{market_data['etf_change']:.2f}%" if market_data['etf_change'] is not None else '获取失败',
                    'ETF周度涨跌': f"{market_data['etf_week_change']:.2f}%" if market_data['etf_week_change'] is not None else '获取失败',
                    '成交量比': f"{market_data['etf_volume_ratio']:.2f}" if market_data['etf_volume_ratio'] is not None else '获取失败',
                    '溢价率': f"{market_data['premium_rate']:.2f}%" if market_data['premium_rate'] is not None else '获取失败',
                    '日元汇率': f"{market_data['jpy_rate']:.4f}",
                    '汇率趋势': f"日元{market_data['jpy_trend']}",
                    '纳指变动': f"{market_data['nasdaq_change']:.2f}%",
                    '标普500变动': f"{market_data['sp500_change']:.2f}%",
                    '美股趋势': market_data['us_market_trend'],
                    '持仓成本': position_data['cost_price'],
                    '当前价格': position_data['current_price'] if position_data['current_price'] else '获取失败',
                    '持仓数量': position_data['position'],
                    '浮动盈亏': f"{position_data['profit_loss']:,.2f}元 ({position_data['profit_loss_rate']:.2f}%)" if position_data['profit_loss'] is not None else '无法计算'
                }
            }
            
            # 发送请求创建记录
            url = f"{self.base_url}{self.table_id}/records"
            response = requests.post(url, headers=self.headers, json=record)
            
            if response.status_code == 200:
                print("数据已成功同步到飞书多维表格")
                return True
            else:
                print(f"同步数据失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"同步数据时发生错误: {str(e)}")
            return False