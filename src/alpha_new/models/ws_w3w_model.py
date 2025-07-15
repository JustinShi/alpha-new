from pydantic import BaseModel

# WebSocket相关常量
PRICE_WS_URL = "wss://nbstream.binance.com/w3w/wsa/stream"  # 价格推送WebSocket地址
ORDER_WS_URL = "wss://nbstream.binance.com/w3w/stream"  # 订单推送WebSocket地址
LISTEN_KEY_URL = "https://www.binance.com/bapi/defi/v1/private/alpha-trade/get-listen-key"  # listenKey获取接口（实际可用的路径）


# 订单推送数据模型
class OrderPushData(BaseModel):
    s: str  # 交易对, 如 ALPHA_118USDT
    c: str  # 客户端订单ID
    S: str  # 买卖方向(BUY/SELL)
    o: str  # 订单类型(如 LIMIT)
    f: str  # 有效方式(如 GTC)
    q: str  # 订单数量
    p: str  # 订单价格
    ap: str  # 成交均价
    P: str  # 触发价
    x: str  # 当前订单状态(如 TRADE)
    X: str  # 订单状态(如 FILLED)
    i: str  # 订单ID
    # last_executed_quantity: str   # 本次成交数量 (原 l) - 移除
    z: str  # 累计成交数量
    last_executed_price: str  # 本次成交价格 (原 L)
    n: str | None = None  # 手续费数量
    N: str | None = None  # 手续费资产
    t: str  # 成交ID
    m: bool  # 是否为主动成交
    ot: str  # 原始订单类型
    st: int  # 订单状态码
    order_creation_time: int  # 订单创建时间 (原 O)
    Z: str  # 累计成交金额
    Y: str  # 累计成交金额(可能与Z相同)
    Q: str  # 报单数量
    ba: str  # 基础资产
    qa: str  # 报价资产
    id: int  # 订单唯一ID
    e: str  # 事件类型(如 executionReport)
    T: int  # 成交时间
    u: int  # 更新时间
    E: int  # 事件时间


class OrderPushModel(BaseModel):
    """订单推送消息的顶层结构"""

    stream: str  # 订阅流名
    data: OrderPushData  # 订单详细数据


# 价格推送数据模型(示例, 字段可根据实际推送内容补充)
class PriceKlineData(BaseModel):
    ot: int  # 开始时间
    ct: int  # 结束时间
    i: str  # K线周期
    o: float  # 开盘价
    c: float  # 收盘价
    h: float  # 最高价
    l: float  # 最低价
    v: float  # 成交量


class PricePushData(BaseModel):
    e: str  # 事件类型(如 kline)
    ca: str  # 合约地址@链ID
    k: PriceKlineData  # K线数据


class PricePushModel(BaseModel):
    """价格推送消息的顶层结构"""

    stream: str  # 订阅流名
    data: PricePushData  # 价格详细数据
