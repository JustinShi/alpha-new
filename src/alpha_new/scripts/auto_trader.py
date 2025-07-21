import asyncio
import json
import signal
import time
from datetime import datetime, timedelta
from typing import Any, Optional
import websockets
from alpha_new.api.alpha_api import AlphaAPI
from alpha_new.utils.logger import get_api_logger, get_order_data_logger
from alpha_new.utils.websocket import BinanceWebSocket
from alpha_new.utils.error_handler import ErrorHandler, ErrorType, global_error_handler
from sqlalchemy.ext.asyncio import async_sessionmaker
from alpha_new.db.models import init_db
from alpha_new.db.ops import get_all_user_ids, get_user_by_id, get_valid_users
import toml
from typing import Tuple
from decimal import Decimal, ROUND_DOWN

logger = get_api_logger()
order_data_logger = get_order_data_logger()

# 系统配置常量
class TradingConfig:
    # 文件路径
    DEFAULT_DB_URL = "sqlite+aiosqlite:///data/alpha_users.db"
    DEFAULT_CONFIG_PATH = "config/auto_trader_config.toml"
    DEFAULT_TOKEN_INFO_PATH = "data/token_info.json"
    
    # 默认值
    DEFAULT_TARGET_TOKEN = "BR"
    DEFAULT_MIN_AMOUNT = 1.0
    DEFAULT_BUY_AMOUNT = 10.0
    
    # 系统配置（从配置文件加载）
    QUOTE_CURRENCY = "USDT"
    BUY_PAYMENT_TYPE = "CARD"
    SELL_PAYMENT_TYPE = "ALPHA"
    TRADING_FEE_RATE = Decimal('0.0001')
    MIN_SELL_QUANTITY = Decimal('0.01')
    PRICE_PRECISION = Decimal('0.00000001')
    QUANTITY_PRECISION = Decimal('0.01')
    ORDER_WAIT_TIMEOUT = 2.0
    WEBSOCKET_SETUP_DELAY = 2.0
    DEFAULT_MAX_RETRY = 5

    ENABLE_AUTO_SELL_ON_INSUFFICIENT_BALANCE = True
    MIN_BALANCE_THRESHOLD = Decimal('0.01')
    
    @classmethod
    def load_from_config(cls):
        """从配置文件加载系统配置"""
        try:
            with open(cls.DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
                config = toml.load(f)
            system_config = config.get("system", {})
            
            cls.QUOTE_CURRENCY = system_config.get("quote_currency", cls.QUOTE_CURRENCY)
            cls.BUY_PAYMENT_TYPE = system_config.get("buy_payment_type", cls.BUY_PAYMENT_TYPE)
            cls.SELL_PAYMENT_TYPE = system_config.get("sell_payment_type", cls.SELL_PAYMENT_TYPE)
            cls.TRADING_FEE_RATE = Decimal(str(system_config.get("trading_fee_rate", cls.TRADING_FEE_RATE)))
            cls.MIN_SELL_QUANTITY = Decimal(str(system_config.get("min_sell_quantity", cls.MIN_SELL_QUANTITY)))
            cls.PRICE_PRECISION = Decimal(str(system_config.get("price_precision", cls.PRICE_PRECISION)))
            cls.QUANTITY_PRECISION = Decimal(str(system_config.get("quantity_precision", cls.QUANTITY_PRECISION)))
            cls.ORDER_WAIT_TIMEOUT = system_config.get("order_wait_timeout", cls.ORDER_WAIT_TIMEOUT)
            cls.WEBSOCKET_SETUP_DELAY = system_config.get("websocket_setup_delay", cls.WEBSOCKET_SETUP_DELAY)
            cls.DEFAULT_MAX_RETRY = system_config.get("max_retry", cls.DEFAULT_MAX_RETRY)

            cls.ENABLE_AUTO_SELL_ON_INSUFFICIENT_BALANCE = system_config.get("enable_auto_sell_on_insufficient_balance", cls.ENABLE_AUTO_SELL_ON_INSUFFICIENT_BALANCE)
            cls.MIN_BALANCE_THRESHOLD = Decimal(str(system_config.get("min_balance_threshold", cls.MIN_BALANCE_THRESHOLD)))
            
            logger.info("系统配置已从配置文件加载")
        except Exception as e:
            logger.warning(f"加载系统配置失败，使用默认值: {e}")

# 自动交易策略
class AutoTrader:
    def __init__(self, user_id: int, api: AlphaAPI, ws_client: BinanceWebSocket, token: str, token_symbol: str, min_amount: float, buy_amount: float, target_total_amount: Optional[float] = None, max_retry: Optional[int] = None):
        self.user_id = user_id
        self.api = api
        self.ws_client = ws_client
        self.token = token  # alphaId
        self.token_symbol = token_symbol  # 代币符号，如MPLX
        self.min_amount = min_amount
        self.buy_amount = buy_amount
        self.target_total_amount = target_total_amount  # 目标总金额
        self.max_retry = max_retry if max_retry is not None else TradingConfig.DEFAULT_MAX_RETRY
        # 交易统计
        self.total_traded_amount = 0.0  # 已交易总金额
        self.trade_count = 0  # 交易次数
        # 历史订单统计
        self.cumulative_buy_amount = 0.0  # 累计买入总额（从订单历史查询）
        self.remaining_cycles = 0  # 剩余循环次数
        # 交易状态跟踪
        self.current_trading_state = "idle"  # idle, buying, selling
        self.current_order_id = None  # 当前订单ID
        self.last_trade_time = None  # 最后交易时间
        # 错误恢复标记
        self._balance_insufficient_logged = False
        self._consecutive_errors = 0
        # 错误处理器
        self.error_handler = ErrorHandler()

    async def initialize_cumulative_amount(self) -> bool:
        """
        初始化累计买入总额，判断是否需要启动交易

        Returns:
            True: 需要启动交易, False: 已达标，不需要交易
        """
        try:
            # 如果没有设置目标总金额，使用原有逻辑
            if not self.target_total_amount:
                logger.info(f"用户{self.user_id}未设置目标总金额，使用无限循环模式")
                return True

            # 查询累计买入总额
            self.cumulative_buy_amount = await get_user_cumulative_buy_amount(
                self.api, self.token_symbol
            )

            logger.info(f"用户{self.user_id} {self.token_symbol}累计买入总额: {self.cumulative_buy_amount:.2f} USDT")
            logger.info(f"用户{self.user_id} {self.token_symbol}目标买入总额: {self.target_total_amount:.2f} USDT")

            # 检查是否已达标
            if self.cumulative_buy_amount >= self.target_total_amount:
                logger.info(f"用户{self.user_id}已达标，累计买入{self.cumulative_buy_amount:.2f} >= 目标{self.target_total_amount:.2f}，不启动交易")
                return False

            # 计算剩余需要买入的金额
            remaining_amount = self.target_total_amount - self.cumulative_buy_amount

            # 计算循环次数
            self.remaining_cycles = max(1, int(remaining_amount / self.buy_amount))

            logger.info(f"用户{self.user_id}需要继续交易，剩余金额: {remaining_amount:.2f} USDT")
            logger.info(f"用户{self.user_id}计算循环次数: {self.remaining_cycles}次")

            return True

        except Exception as e:
            logger.error(f"用户{self.user_id}初始化累计金额失败: {e}")
            # 出错时默认启动交易，使用原有逻辑
            return True

    async def check_target_reached(self) -> bool:
        """
        检查是否达到目标金额

        Returns:
            True: 已达标, False: 未达标
        """
        try:
            # 如果没有设置目标总金额，不检查
            if not self.target_total_amount:
                return False

            # 重新查询累计买入总额
            current_cumulative = await get_user_cumulative_buy_amount(
                self.api, self.token_symbol
            )

            logger.info(f"用户{self.user_id}当前累计买入总额: {current_cumulative:.2f} USDT")

            if current_cumulative >= self.target_total_amount:
                logger.info(f"用户{self.user_id}已达标！累计买入{current_cumulative:.2f} >= 目标{self.target_total_amount:.2f}")
                return True

            # 更新剩余循环次数
            remaining_amount = self.target_total_amount - current_cumulative
            self.remaining_cycles = max(1, int(remaining_amount / self.buy_amount))

            logger.info(f"用户{self.user_id}未达标，剩余金额: {remaining_amount:.2f} USDT，继续{self.remaining_cycles}次循环")
            return False

        except Exception as e:
            logger.error(f"用户{self.user_id}检查目标金额失败: {e}")
            # 出错时继续交易
            return False

    async def run(self, stop_flag: asyncio.Event, buy_slippage: float, sell_slippage: float):
        # 初始化累计买入总额，检查是否需要启动交易
        if not await self.initialize_cumulative_amount():
            logger.info(f"用户{self.user_id}已达标，不启动交易")
            return

        # 使用循环次数控制的交易逻辑
        while not stop_flag.is_set() and (not self.target_total_amount or self.remaining_cycles > 0):
            if self.target_total_amount:
                logger.info(f"用户{self.user_id}开始第{self.remaining_cycles}次循环")

                # 检查是否达到目标总金额（每次循环开始时检查）
                if await self.check_target_reached():
                    logger.info(f"用户{self.user_id}已达标，停止交易")
                    break
            # 1. 买入
            base_price = Decimal(str(await self.get_latest_price()))
            buy_slip = Decimal(str(buy_slippage))
            buy_price = (base_price * (Decimal('1') + buy_slip)).quantize(TradingConfig.PRICE_PRECISION, rounding=ROUND_DOWN)
            buy_amount = Decimal(str(self.buy_amount))
            buy_quantity = buy_amount / buy_price
            # 计算买入数量，保留一位小数（Decimal）
            buy_quantity = buy_quantity.quantize(Decimal('0.1'), rounding=ROUND_DOWN)
            if buy_quantity < 1:
                logger.warning(f"用户{self.user_id}买入数量不足1，跳过本轮")
                continue
            try:
                actual_amount = (buy_price * buy_quantity).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
                payment_details = [{"amount": float(actual_amount), "paymentWalletType": TradingConfig.BUY_PAYMENT_TYPE}]
                order_data_logger.info(json.dumps({
                    "user_id": self.user_id,
                    "action": "buy_order_param",
                    "token": self.token,
                    "token_symbol": self.token_symbol,
                    "price": float(buy_price),
                    "quantity": float(buy_quantity),
                    "amount": float(actual_amount),
                    "slippage": float(buy_slippage),
                    "payment_details": payment_details
                }, ensure_ascii=False))
                order = await self.api.place_limit_order(self.token, TradingConfig.QUOTE_CURRENCY, "BUY", float(buy_price), float(buy_quantity), payment_details)
                order_data_logger.info(f"用户{self.user_id} 买入订单API返回: {json.dumps(order, ensure_ascii=False)}")
                if order.get("success") and order.get("data"):
                    order_id = order.get("data")
                    # 🔧 优雅退出：更新交易状态
                    self.current_trading_state = "buying"
                    self.current_order_id = order_id
                    self.last_trade_time = datetime.now()

                    order_data_logger.info(f"用户{self.user_id} 买入订单创建成功: {order_id}, 价格: {float(buy_price)}, 数量: {float(buy_quantity)}, 金额: {float(actual_amount)}")
                else:
                    error_msg = f"买入下单失败: {order.get('message', '未知错误')}"
                    logger.error(f"用户{self.user_id} 订单ID: 无, {error_msg}")
                    raise Exception(error_msg)
            except Exception as e:
                context = {
                    "operation": "buy_order",
                    "token_symbol": self.token_symbol,
                    "buy_amount": self.buy_amount,
                    "buy_price": float(buy_price),
                    "quantity": float(buy_quantity)
                }
                result = await self.error_handler.handle_error(e, self.user_id, context)
                if result["error_type"] == ErrorType.INSUFFICIENT_BALANCE.value:
                    token_balance = await self.get_cached_token_balance(self.token_symbol)
                    if token_balance < TradingConfig.MIN_BALANCE_THRESHOLD:
                        logger.warning(f"用户{self.user_id}买入失败：余额不足，{self.token_symbol}余额({token_balance})小于最小阈值({TradingConfig.MIN_BALANCE_THRESHOLD})，跳过卖出")
                        continue
                    if token_balance > 0 and TradingConfig.ENABLE_AUTO_SELL_ON_INSUFFICIENT_BALANCE:
                        logger.info(f"用户{self.user_id}买入失败：余额不足，检测到{self.token_symbol}余额: {token_balance}，执行卖出")
                        await self.sell_all_balance(sell_slippage, int(token_balance))
                    else:
                        logger.warning(f"用户{self.user_id}买入失败：余额不足，且无{self.token_symbol}代币或自动卖出已禁用")
                        continue
                elif result["action"] == "retry":
                    logger.warning(f"用户{self.user_id}买入下单需要重试: {result['error_message']}")
                    await asyncio.sleep(result["retry_after"])
                    continue
                elif result["action"] == "wait":
                    logger.warning(f"用户{self.user_id}买入下单需要等待: {result['error_message']}")
                    await asyncio.sleep(result["retry_after"])
                    continue
                else:
                    logger.error(f"用户{self.user_id}买入下单异常: {e}")
                    continue
            filled_qty = 0
            try:
                # 优化：买入后直接监听订单状态，区分完全成交和部分成交
                status, filled_qty = await self.wait_order_filled_detail(order_id, "BUY")
                # 🔧 优雅退出：买入完成，更新状态
                if status == "FILLED":
                    self.current_trading_state = "selling"
                    self.current_order_id = None
            except Exception as e:
                context = {
                    "operation": "buy_wait",
                    "order_id": order_id,
                    "side": "BUY"
                }
                result = await self.error_handler.handle_error(e, self.user_id, context)
                logger.error(f"用户{self.user_id}买入等待异常: {e}")
                try:
                    await self.api.cancel_order(order_id, self.token, TradingConfig.QUOTE_CURRENCY)
                except Exception as cancel_error:
                    logger.warning(f"用户{self.user_id}撤销订单失败（可能已成交）: {cancel_error}")
                continue
            if status == "FILLED":
                # 完全成交，等待0.3秒再卖出
                await asyncio.sleep(0.3)
                await self.sell_all_balance(sell_slippage, filled_qty)
            elif status == "PARTIALLY_FILLED":
                # 部分成交，撤单，等待0.3秒再卖出本次实际成交部分
                try:
                    await self.api.cancel_order(order_id, self.token, TradingConfig.QUOTE_CURRENCY)
                except Exception as cancel_error:
                    logger.warning(f"用户{self.user_id}撤销部分成交订单失败（可能已成交）: {cancel_error}")
                logger.info(f"用户{self.user_id}买入部分成交，撤单，卖出已成交部分: {filled_qty}")
                await asyncio.sleep(0.3)
                await self.sell_all_balance(sell_slippage, filled_qty)
            else:
                # 未成交，撤单，跳过卖出
                try:
                    await self.api.cancel_order(order_id, self.token, TradingConfig.QUOTE_CURRENCY)
                except Exception as cancel_error:
                    logger.warning(f"用户{self.user_id}撤销未成交订单失败: {cancel_error}")
                logger.info(f"用户{self.user_id}买入未成交，撤单，跳过本轮卖出")
                continue

    async def wait_order_filled_with_timeout(self, order_id: str, side: str, timeout: float) -> tuple[str, float]:
        """等待订单完全成交，超时返回部分成交数量"""
        filled_qty = 0.0
        try:
            task = asyncio.create_task(self.wait_order_filled_detail(order_id, side))
            done, pending = await asyncio.wait(
                [task],
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED
            )
            if done:
                status, qty = done.pop().result()
                return status, qty
            else:
                # 超时，主动查单获取部分成交数量
                qty = await self.query_filled_qty(order_id)
                return "TIMEOUT", float(qty)
        except Exception as e:
            logger.error(f"等待订单成交异常: {e}")
            return "ERROR", 0.0

    async def wait_order_filled_detail(self, order_id: str, side: str) -> tuple[str, float]:
        """
        监听订单推送，返回(成交状态, 实际到账数量)
        对于买入订单，会自动扣除手续费，返回实际到账数量
        """
        while True:
            data = await self.ws_client.order_queue.get()
            # 新增：保存ws推送订单数据到日志
            order_data_logger.info(json.dumps({
                "user_id": self.user_id,
                "action": "ws_order_data",
                "order_id": order_id,
                "side": side,
                "ws_data": data
            }, ensure_ascii=False))
            d = data.get("data", {})
            if d.get("i") == order_id and d.get("S") == side:
                if d.get("X") == "FILLED":
                    # 获取成交数量和手续费
                    filled_qty = float(d.get("z", 0))  # 成交数量
                    commission = float(d.get("n", 0))  # 手续费

                    if side == "BUY":
                        # 买入：实际到账 = 成交数量 - 手续费
                        actual_qty = filled_qty - commission
                        logger.info(f"买入完全成交: 成交{filled_qty}, 手续费{commission}, 实际到账{actual_qty}")
                    else:
                        # 卖出：返回成交数量即可
                        actual_qty = filled_qty
                        logger.info(f"卖出完全成交: 成交{filled_qty}")

                    return "FILLED", actual_qty
                elif d.get("X") == "PARTIALLY_FILLED":
                    # 部分成交同样需要处理手续费
                    filled_qty = float(d.get("z", 0))  # 累计成交数量
                    commission = float(d.get("n", 0))  # 累计手续费

                    if side == "BUY":
                        actual_qty = filled_qty - commission
                        logger.info(f"买入部分成交: 成交{filled_qty}, 手续费{commission}, 实际到账{actual_qty}")
                    else:
                        actual_qty = filled_qty
                        logger.info(f"卖出部分成交: 成交{filled_qty}")

                    return "PARTIALLY_FILLED", actual_qty
                elif d.get("X") == "CANCELED":
                    # 撤单：返回已成交的实际数量
                    filled_qty = float(d.get("z", 0))
                    commission = float(d.get("n", 0))

                    if side == "BUY" and filled_qty > 0:
                        actual_qty = filled_qty - commission
                        logger.info(f"买入撤单: 已成交{filled_qty}, 手续费{commission}, 实际到账{actual_qty}")
                    else:
                        actual_qty = filled_qty
                        logger.info(f"撤单: 已成交{filled_qty}")

                    return "CANCELED", actual_qty

    async def wait_order_filled_detail_with_z(self, order_id: str, side: str) -> tuple[str, float, float]:
        """
        监听订单推送，返回(成交状态, 本次成交数量, 累计成交量z)
        """
        z_acc = 0.0
        while True:
            data = await self.ws_client.order_queue.get()
            order_data_logger.info(json.dumps({
                "user_id": self.user_id,
                "action": "ws_order_data",
                "order_id": order_id,
                "side": side,
                "ws_data": data
            }, ensure_ascii=False))
            d = data.get("data", {})
            if d.get("i") == order_id and d.get("S") == side:
                z_str = d.get("z", "0")
                z_acc = float(z_str)
                if d.get("X") == "FILLED":
                    qty = float(z_str)
                    return "FILLED", qty, z_acc
                elif d.get("X") == "PARTIALLY_FILLED":
                    l_str = d.get("l", "0")
                    qty = float(l_str)
                    return "PARTIALLY_FILLED", qty, z_acc
                elif d.get("X") == "CANCELED":
                    l_str = d.get("l", "0")
                    qty = float(l_str)
                    return "CANCELED", qty, z_acc

    async def query_filled_qty(self, order_id: str) -> float:
        # 兜底：用钱包余额API查当前币种余额
        try:
            data = await self.api.get_wallet_balance()
            for asset in data.get("data", []):
                if asset.get("asset") == self.token_symbol:  # 从配置中获取
                    amount = asset.get("amount", "0")
                    qty = float(Decimal(amount))
                    return qty
            return 0.0
        except Exception as e:
            logger.error(f"查单兜底失败: {e}")
            return 0.0

    async def sell_all_balance(self, sell_slippage: float, buy_filled_qty: float):
        retry = 0
        remain_qty = float(buy_filled_qty)
        min_precision = float(TradingConfig.QUANTITY_PRECISION)
        first_sell = True

        # 🔧 修复：卖出前验证实际余额，防止"余额不足"死循环
        logger.info(f"用户{self.user_id}开始卖出，预期数量: {buy_filled_qty}")

        # 等待余额更新（买入成交后可能有延迟）
        await asyncio.sleep(1)

        # 查询实际余额
        actual_balance = await self.get_cached_token_balance(self.token_symbol)
        logger.info(f"用户{self.user_id}实际余额: {actual_balance}, 预期卖出: {buy_filled_qty}")

        # 使用实际余额和预期数量的较小值，并留出0.1%的安全余量
        safe_qty = min(actual_balance * 0.999, buy_filled_qty)
        remain_qty = float(safe_qty)

        if remain_qty < TradingConfig.MIN_SELL_QUANTITY:
            logger.warning(f"用户{self.user_id}可卖出数量({remain_qty})小于最小卖出量({TradingConfig.MIN_SELL_QUANTITY})，跳过卖出")
            return

        logger.info(f"用户{self.user_id}调整后卖出数量: {remain_qty}")

        # 防死循环：限制481020错误重试次数
        balance_error_count = 0
        max_balance_errors = 3
        while remain_qty >= TradingConfig.MIN_SELL_QUANTITY:
            # 判断是否为最后一次补单（remain_qty小于最小下单量，或补单次数到达上限）
            is_last_retry = remain_qty < TradingConfig.MIN_SELL_QUANTITY * 2 or retry >= self.max_retry - 1
            if is_last_retry:
                # 最后一次补单，查余额全仓卖出
                balance = await self.get_cached_token_balance(self.token_symbol)
                sell_quantity = Decimal(str(balance)).quantize(Decimal('0.1'), rounding=ROUND_DOWN)
                order_data_logger.info(json.dumps({
                    "user_id": self.user_id,
                    "action": "final_sell_all",
                    "token": self.token,
                    "token_symbol": self.token_symbol,
                    "final_sell_quantity": float(sell_quantity)
                }, ensure_ascii=False))
                if sell_quantity < TradingConfig.MIN_SELL_QUANTITY:
                    order_data_logger.info(f"用户{self.user_id} 最后一次补单余额({float(sell_quantity)})低于最小下单量，跳过")
                    break

                # 计算最后一次补单的卖出价格
                base_price = Decimal(str(await self.get_latest_price()))
                sell_slip = Decimal(str(sell_slippage))
                sell_price = (base_price * (Decimal('1') - sell_slip)).quantize(TradingConfig.PRICE_PRECISION, rounding=ROUND_DOWN)

                payment_details = [{"amount": float(sell_quantity), "paymentWalletType": TradingConfig.SELL_PAYMENT_TYPE}]
                try:
                    order = await self.api.place_limit_order(self.token, TradingConfig.QUOTE_CURRENCY, "SELL", float(sell_price), float(sell_quantity), payment_details)
                    order_data_logger.info(f"用户{self.user_id} 最后一次补单全仓卖出: {json.dumps(order, ensure_ascii=False)}")
                except Exception as e:
                    order_data_logger.warning(f"用户{self.user_id} 最后一次补单全仓卖出异常: {e}")
                break
            base_price = Decimal(str(await self.get_latest_price()))
            sell_slip = Decimal(str(sell_slippage))
            sell_price = (base_price * (Decimal('1') - sell_slip)).quantize(TradingConfig.PRICE_PRECISION, rounding=ROUND_DOWN)
            sell_quantity = Decimal(str(remain_qty)).quantize(TradingConfig.QUANTITY_PRECISION, rounding=ROUND_DOWN)
            # 计算卖出数量，保留一位小数（Decimal）
            sell_quantity = sell_quantity.quantize(Decimal('0.1'), rounding=ROUND_DOWN)
            if sell_quantity > Decimal(str(remain_qty)):
                sell_quantity = Decimal(str(remain_qty))
            payment_details = [{"amount": float(sell_quantity), "paymentWalletType": TradingConfig.SELL_PAYMENT_TYPE}]
            order_data_logger.info(json.dumps({
                "user_id": self.user_id,
                "action": "sell_order_param",
                "token": self.token,
                "token_symbol": self.token_symbol,
                "price": float(sell_price),
                "quantity": float(sell_quantity),
                "remain_qty": float(remain_qty),
                "slippage": float(sell_slippage),
                "payment_details": payment_details
            }, ensure_ascii=False))
            try:
                order = await self.api.place_limit_order(self.token, TradingConfig.QUOTE_CURRENCY, "SELL", float(sell_price), float(sell_quantity), payment_details)
                order_data_logger.info(f"用户{self.user_id} 卖出订单API返回: {json.dumps(order, ensure_ascii=False)}")

                # 🔧 修复：检查481020余额不足错误
                if not order.get("success") and order.get("code") == "481020":
                    balance_error_count += 1
                    logger.warning(f"用户{self.user_id}卖出余额不足(481020)，第{balance_error_count}次，卖出数量: {float(sell_quantity)}")

                    if balance_error_count >= max_balance_errors:
                        logger.error(f"用户{self.user_id}连续{max_balance_errors}次余额不足，停止卖出避免死循环")
                        break

                    # 重新查询余额并调整卖出数量
                    current_balance = await self.get_cached_token_balance(self.token_symbol)
                    logger.info(f"用户{self.user_id}重新查询余额: {current_balance}")

                    if current_balance < TradingConfig.MIN_SELL_QUANTITY:
                        logger.warning(f"用户{self.user_id}余额({current_balance})小于最小卖出量，停止卖出")
                        break

                    # 使用实际余额的99%作为新的卖出数量
                    remain_qty = current_balance * 0.99
                    logger.info(f"用户{self.user_id}调整卖出数量为: {remain_qty}")
                    continue

                # 🔧 修复：检查481013最小金额错误
                if not order.get("success") and order.get("code") == "481013":
                    logger.warning(f"用户{self.user_id}卖出金额过小(481013)，卖出数量: {float(sell_quantity)}, 金额: {float(sell_quantity * sell_price):.4f} USDT")

                    # 计算满足最小金额要求的数量
                    min_usdt_amount = 0.1  # 最小交易金额0.1 USDT
                    min_required_quantity = min_usdt_amount / float(sell_price)

                    logger.info(f"用户{self.user_id}最小需要数量: {min_required_quantity:.4f}, 当前剩余: {float(remain_qty):.4f}")

                    if float(remain_qty) < min_required_quantity:
                        logger.warning(f"用户{self.user_id}剩余数量不足以满足最小交易金额，停止卖出")
                        break

                    # 使用剩余的全部数量进行卖出
                    remain_qty = float(remain_qty)
                    logger.info(f"用户{self.user_id}调整为全部卖出: {remain_qty}")
                    continue

                if order.get("success") and order.get("data"):
                    order_id = order.get("data")
                    order_data_logger.info(f"用户{self.user_id} 卖出订单创建成功: {order_id}, 价格: {float(sell_price)}, 数量: {float(sell_quantity)}, 金额: {float(sell_quantity * Decimal(str(sell_price)))}")
                    # 监听WebSocket订单状态
                    status, filled_qty, z_acc = await self.wait_order_filled_detail_with_z(order_id, "SELL")
                    if z_acc == 0:
                        # 没有任何成交，直接退出，避免死循环
                        break
                    remain_qty -= z_acc  # 递减本次补单的实际成交量
                    if remain_qty < float(TradingConfig.MIN_SELL_QUANTITY):
                        break
                    if status == "FILLED":
                        # 🔧 优雅退出：卖出完成，更新状态
                        self.current_trading_state = "idle"
                        self.current_order_id = None

                        # 更新交易统计
                        self.total_traded_amount += float(sell_quantity * Decimal(str(sell_price)))
                        self.trade_count += 1
                        if self.target_total_amount:
                            self.remaining_cycles -= 1  # 减少剩余循环次数
                            logger.info(f"用户{self.user_id}完成第{self.trade_count}次交易，剩余循环: {self.remaining_cycles}次")
                        else:
                            logger.info(f"用户{self.user_id}完成第{self.trade_count}次交易")
                        await asyncio.sleep(0.3)
                        break
                    elif status == "PARTIALLY_FILLED":
                        await asyncio.sleep(0.3)
                        continue
                    else:
                        break
            except Exception as e:
                context = {
                    "operation": "sell_order",
                    "token_symbol": self.token_symbol,
                    "sell_qty": float(sell_quantity),
                    "remain_qty": float(remain_qty)
                }
                result = await self.error_handler.handle_error(e, self.user_id, context)
                if result["error_type"] == ErrorType.INSUFFICIENT_BALANCE.value:
                    logger.warning(f"用户{self.user_id}卖出失败：{self.token_symbol}代币不足，当前余额: {float(remain_qty)}")
                    break
                elif result["action"] == "retry":
                    logger.warning(f"用户{self.user_id}卖出下单需要重试: {result['error_message']}")
                    await asyncio.sleep(result["retry_after"])
                    continue
                else:
                    break
        # 补单循环结束后，自动查一次钱包余额并写入日志
        try:
            balance = await self.get_cached_token_balance(self.token_symbol)
            order_data_logger.info(json.dumps({
                "user_id": self.user_id,
                "action": "sell_post_balance",
                "token": self.token,
                "token_symbol": self.token_symbol,
                "final_balance": float(balance)
            }, ensure_ascii=False))
        except Exception as e:
            order_data_logger.warning(f"用户{self.user_id} 查询卖出后余额异常: {e}")

        # 循环结束后，最终检查是否达标
        if self.target_total_amount:
            logger.info(f"用户{self.user_id}交易循环结束，进行最终检查")
            if await self.check_target_reached():
                logger.info(f"用户{self.user_id}最终检查：已达标")
            else:
                logger.info(f"用户{self.user_id}最终检查：未达标，但循环已结束")

    async def get_latest_price(self) -> float:
        # 从WebSocket实时获取最新价格
        while True:
            data = await self.ws_client.price_queue.get()
            price = data.get("data", {}).get("k", {}).get("c")
            if price:
                return float(price)

    async def wait_order_filled(self, order_id: str, side: str) -> bool:
        # 监听订单推送，判断是否完全成交
        while True:
            data = await self.ws_client.order_queue.get()
            d = data.get("data", {})
            if d.get("i") == order_id and d.get("S") == side and d.get("X") == "FILLED":
                return True
            if d.get("i") == order_id and d.get("S") == side and d.get("X") == "CANCELED":
                return False

    async def get_token_balance(self, token_symbol: str) -> float:
        """获取指定代币的余额"""
        data = await self.api.get_wallet_balance()
        for asset in data.get("data", []):
            if asset.get("asset") == token_symbol:
                return float(asset.get("amount", 0))
        return 0.0

    async def get_cached_token_balance(self, token_symbol: str) -> float:
        """获取代币余额（直接调用，无缓存）"""
        return await self.get_token_balance(token_symbol)

    async def get_balance(self) -> float:
        data = await self.api.get_wallet_balance()
        for asset in data.get("data", []):
            if asset.get("asset") == TradingConfig.QUOTE_CURRENCY:
                # 使用amount字段获取USDT余额
                return float(asset.get("amount", 0))
        return 0.0

async def build_users(user_api_params, price_stream, enabled_user_ids):
    users = []
    for user_id, api in user_api_params:
        # 只加载配置文件中enabled=true的用户
        if user_id not in enabled_user_ids:
            logger.info(f"用户{user_id}在配置中未启用，跳过")
            continue
            
        # 从API中提取认证信息
        headers = api.headers if hasattr(api, 'headers') else {}
        cookies = api.cookies if hasattr(api, 'cookies') else None
        
        if not headers:
            logger.warning(f"用户{user_id}缺少认证信息，跳过")
            continue
            
        users.append((user_id, api, headers, cookies, price_stream))
    return users

# 辅助函数: 将dict的key/value从bytes转str
def decode_dict(d) -> dict[str, str]:
    if not d:
        return {}
    return {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in d.items()}

async def load_user_api_params(db_url: str) -> list:
    engine = await init_db(db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    user_api_params = []
    async with async_session() as session:
        users = await get_valid_users(session)
        for user in users:
            headers = decode_dict(user.headers) if user.headers is not None else {}
            cookies = decode_dict(user.cookies) if user.cookies is not None else None
            api = AlphaAPI(headers=headers, cookies=cookies)
            user_api_params.append((user.id, api))
    return user_api_params

def get_alpha_id_from_token(token_symbol: str, token_info_path: Optional[str] = None) -> str:
    """根据代币符号获取alphaId"""
    import json
    if token_info_path is None:
        token_info_path = TradingConfig.DEFAULT_TOKEN_INFO_PATH
    with open(token_info_path, "r", encoding="utf-8") as f:
        tokens = json.load(f)
    for t in tokens:
        if t.get("symbol") == token_symbol:
            alpha_id = t.get("alphaId")
            if alpha_id:
                return alpha_id
    raise ValueError(f"未找到代币 {token_symbol} 的alphaId")

def get_price_stream_from_token(token_symbol: str, token_info_path: Optional[str] = None) -> str:
    import json
    if token_info_path is None:
        token_info_path = TradingConfig.DEFAULT_TOKEN_INFO_PATH
    with open(token_info_path, "r", encoding="utf-8") as f:
        tokens = json.load(f)
    for t in tokens:
        if t.get("symbol") == token_symbol:
            contract = t.get("contractAddress")
            chain_id = t.get("chainId") or t.get("chainID") or "56"
            return f"came@{contract}@{chain_id}@kline_1s"
    raise ValueError(f"未找到代币 {token_symbol} 的行情订阅参数")

def get_time_range():
    """
    获取以每天上午8点为分界点的时间范围

    Returns:
        tuple: (start_time_ms, end_time_ms) 毫秒时间戳
    """
    now = datetime.now()
    today_8 = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now < today_8:
        start = (today_8 - timedelta(days=1))
        end = today_8
    else:
        start = today_8
        end = today_8 + timedelta(days=1)
    # 转为毫秒时间戳
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)

async def fetch_all_orders(api: AlphaAPI, base_asset: str, side: str, start_time: int, end_time: int) -> list:
    """
    获取所有订单数据，支持多页合并

    Args:
        api: API客户端
        base_asset: 基础资产，如 "ALPHA_259"
        side: 订单方向，"BUY" 或 "SELL"
        start_time: 开始时间戳（毫秒）
        end_time: 结束时间戳（毫秒）

    Returns:
        所有订单的列表
    """
    all_orders = []
    page = 1
    max_pages = 10  # 防止无限循环

    logger.info(f"开始查询{side}订单，时间范围: {start_time} ~ {end_time}")

    while page <= max_pages:
        params = {
            "page": page,
            "rows": 500,
            "baseAsset": base_asset,
            "quoteAsset": "USDT",
            "side": side,
            "startTime": start_time,
            "endTime": end_time
        }

        logger.info(f"查询第{page}页{side}订单...")
        response = await api.get_order_history(params)

        if response.get("code") != "000000":
            logger.error(f"查询第{page}页{side}订单失败: {response}")
            break

        orders = response.get("data", [])
        if not orders:
            logger.info(f"第{page}页{side}订单为空，查询结束")
            break

        logger.info(f"第{page}页获取到{len(orders)}个{side}订单")
        all_orders.extend(orders)

        # 如果返回的订单数量少于请求的数量，说明已经是最后一页
        if len(orders) < 500:
            logger.info(f"第{page}页{side}订单数量({len(orders)})少于500，已是最后一页")
            break

        page += 1

    logger.info(f"总共获取到{len(all_orders)}个{side}订单")
    return all_orders

# 🔧 优雅退出：全局变量和信号处理
graceful_shutdown = False
shutdown_reason = ""

def signal_handler(signum, frame):
    """信号处理器：处理SIGINT和SIGTERM信号"""
    global graceful_shutdown, shutdown_reason
    signal_names = {signal.SIGINT: "SIGINT (Ctrl+C)", signal.SIGTERM: "SIGTERM"}
    shutdown_reason = signal_names.get(signum, f"Signal {signum}")
    graceful_shutdown = True
    logger.info(f"🛑 接收到退出信号: {shutdown_reason}")
    logger.info("🔄 开始优雅退出流程...")

async def wait_for_current_trades_completion(traders: list, timeout: float = 30.0) -> dict:
    """
    等待当前交易完成

    Args:
        traders: 交易器列表
        timeout: 超时时间（秒）

    Returns:
        交易状态统计
    """
    logger.info("⏳ 等待当前交易完成...")

    start_time = time.time()
    status_summary = {
        "idle": 0,
        "buying": 0,
        "selling": 0,
        "completed": 0,
        "timeout": 0
    }

    while time.time() - start_time < timeout:
        all_idle = True
        status_summary = {"idle": 0, "buying": 0, "selling": 0, "completed": 0, "timeout": 0}

        for trader, _, _ in traders:
            state = trader.current_trading_state
            status_summary[state] = status_summary.get(state, 0) + 1

            if state != "idle":
                all_idle = False
                logger.info(f"用户{trader.user_id}: {state}, 订单ID: {trader.current_order_id}")

        if all_idle:
            logger.info("✅ 所有交易已完成")
            status_summary["completed"] = len(traders)
            return status_summary

        await asyncio.sleep(1)

    # 超时处理
    logger.warning(f"⚠️ 等待交易完成超时({timeout}秒)")
    for trader, _, _ in traders:
        if trader.current_trading_state != "idle":
            status_summary["timeout"] += 1
            logger.warning(f"用户{trader.user_id}交易未完成: {trader.current_trading_state}, 订单: {trader.current_order_id}")

    return status_summary

async def cleanup_resources(traders: list, ws_clients: list, apis: list):
    """
    清理所有资源

    Args:
        traders: 交易器列表
        ws_clients: WebSocket客户端列表
        apis: API客户端列表
    """
    logger.info("🧹 开始清理资源...")

    # 1. 停止WebSocket连接
    logger.info("🔌 关闭WebSocket连接...")
    for i, ws_client in enumerate(ws_clients):
        try:
            ws_client.stop()
            logger.info(f"✅ WebSocket {i+1} 已关闭")
        except Exception as e:
            logger.error(f"❌ 关闭WebSocket {i+1} 失败: {e}")

    # 2. 关闭API客户端
    logger.info("🔗 关闭API连接...")
    for i, api in enumerate(apis):
        try:
            await api.close()
            logger.info(f"✅ API客户端 {i+1} 已关闭")
        except Exception as e:
            logger.error(f"❌ 关闭API客户端 {i+1} 失败: {e}")

    logger.info("✅ 资源清理完成")

async def log_final_status(traders: list, start_time: float):
    """
    记录最终状态

    Args:
        traders: 交易器列表
        start_time: 开始时间
    """
    runtime = time.time() - start_time
    logger.info("=" * 60)
    logger.info("📊 最终交易统计")
    logger.info("=" * 60)

    total_trades = 0
    total_amount = 0.0

    for trader, _, _ in traders:
        logger.info(f"用户{trader.user_id}:")
        logger.info(f"  - 完成交易: {trader.trade_count}次")
        logger.info(f"  - 交易金额: {trader.total_traded_amount:.2f} USDT")
        logger.info(f"  - 最后状态: {trader.current_trading_state}")
        if trader.target_total_amount:
            logger.info(f"  - 剩余循环: {trader.remaining_cycles}次")
            logger.info(f"  - 累计买入: {trader.cumulative_buy_amount:.2f} USDT")
            logger.info(f"  - 目标金额: {trader.target_total_amount:.2f} USDT")

        total_trades += trader.trade_count
        total_amount += trader.total_traded_amount

    logger.info("=" * 60)
    logger.info(f"📈 总计: {total_trades}次交易, {total_amount:.2f} USDT")
    logger.info(f"⏱️ 运行时间: {runtime:.1f}秒")
    logger.info(f"🛑 退出原因: {shutdown_reason}")
    logger.info("=" * 60)

async def get_user_cumulative_buy_amount(api: AlphaAPI, token_symbol: str) -> float:
    """
    查询用户指定代币的累计买入总额（USDT）- 使用8点分界的时间范围

    Args:
        api: API客户端
        token_symbol: 代币符号，如 "CROSS"

    Returns:
        累计买入总额（USDT）
    """
    try:
        # 获取时间范围（以8点为分界的24小时）
        start_time, end_time = get_time_range()

        # 记录查询时间范围
        start_dt = datetime.fromtimestamp(start_time / 1000)
        end_dt = datetime.fromtimestamp(end_time / 1000)
        logger.info(f"查询{token_symbol}累计买入总额，时间范围: {start_dt} ~ {end_dt}")

        # 根据代币符号映射到base_asset
        token_mapping = {
            "CROSS": "ALPHA_259",
            "MPLX": "ALPHA_XXX",  # 需要根据实际情况填写
            "BR": "ALPHA_XXX",    # 需要根据实际情况填写
            # 可以添加更多代币映射
        }

        base_asset = token_mapping.get(token_symbol)
        if not base_asset:
            logger.error(f"不支持的代币符号: {token_symbol}")
            return 0.0

        # 查询买入订单（支持多页合并）
        buy_orders = await fetch_all_orders(api, base_asset, "BUY", start_time, end_time)

        total_buy_amount = 0.0
        buy_count = 0

        for order in buy_orders:
            # 只统计已完成的买入订单
            if order.get("orderStatus") == "FILLED" or order.get("status") == "FILLED":
                # 计算买入金额 = 价格 × 数量
                price = float(order.get("avgPrice", 0))
                filled_qty = float(order.get("executedQty", 0))
                buy_amount = price * filled_qty
                total_buy_amount += buy_amount
                buy_count += 1

        logger.info(f"查询到{token_symbol}累计买入: {buy_count}笔订单, 总额: {total_buy_amount:.2f} USDT")
        return total_buy_amount

    except Exception as e:
        logger.error(f"查询累计买入总额失败: {e}")
        return 0.0

async def get_token_order_history_by_time_range(api: AlphaAPI, token_symbol: str) -> dict:
    """
    使用时间范围查询配置文件指定代币的历史订单

    Args:
        api: API客户端
        token_symbol: 代币符号，如 "CROSS"

    Returns:
        包含订单统计信息的字典
    """
    try:
        # 获取时间范围（以8点为分界的24小时）
        start_time, end_time = get_time_range()

        # 记录查询时间范围
        start_dt = datetime.fromtimestamp(start_time / 1000)
        end_dt = datetime.fromtimestamp(end_time / 1000)
        logger.info(f"查询{token_symbol}订单历史，时间范围: {start_dt} ~ {end_dt}")

        # 根据代币符号映射到base_asset
        token_mapping = {
            "CROSS": "ALPHA_259",
            "MPLX": "ALPHA_XXX",  # 需要根据实际情况填写
            # 可以添加更多代币映射
        }

        base_asset = token_mapping.get(token_symbol)
        if not base_asset:
            logger.error(f"不支持的代币符号: {token_symbol}")
            return {"error": f"不支持的代币符号: {token_symbol}"}

        # 查询买入订单
        buy_params = {
            "page": 1,
            "rows": 500,
            "baseAsset": base_asset,
            "quoteAsset": "USDT",
            "side": "BUY",
            "startTime": start_time,
            "endTime": end_time
        }
        buy_orders_response = await api.get_order_history(buy_params)

        # 查询卖出订单
        sell_params = {
            "page": 1,
            "rows": 500,
            "baseAsset": base_asset,
            "quoteAsset": "USDT",
            "side": "SELL",
            "startTime": start_time,
            "endTime": end_time
        }
        sell_orders_response = await api.get_order_history(sell_params)

        # 统计数据
        stats = {
            "token_symbol": token_symbol,
            "base_asset": base_asset,
            "time_range": {
                "start": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "end": end_dt.strftime("%Y-%m-%d %H:%M:%S")
            },
            "buy_orders": {
                "count": 0,
                "total_amount": 0.0,
                "total_quantity": 0.0,
                "orders": []
            },
            "sell_orders": {
                "count": 0,
                "total_amount": 0.0,
                "total_quantity": 0.0,
                "orders": []
            }
        }

        # 处理买入订单
        if buy_orders_response.get("code") == "000000" and buy_orders_response.get("data"):
            buy_orders = buy_orders_response["data"]
            for order in buy_orders:
                if order.get("orderStatus") == "FILLED":
                    price = float(order.get("avgPrice", 0))
                    quantity = float(order.get("executedQty", 0))
                    amount = price * quantity

                    stats["buy_orders"]["count"] += 1
                    stats["buy_orders"]["total_amount"] += amount
                    stats["buy_orders"]["total_quantity"] += quantity
                    stats["buy_orders"]["orders"].append({
                        "orderId": order.get("orderId"),
                        "price": price,
                        "quantity": quantity,
                        "amount": amount,
                        "time": order.get("time")
                    })

        # 处理卖出订单
        if sell_orders_response.get("code") == "000000" and sell_orders_response.get("data"):
            sell_orders = sell_orders_response["data"]
            for order in sell_orders:
                if order.get("orderStatus") == "FILLED":
                    price = float(order.get("avgPrice", 0))
                    quantity = float(order.get("executedQty", 0))
                    amount = price * quantity

                    stats["sell_orders"]["count"] += 1
                    stats["sell_orders"]["total_amount"] += amount
                    stats["sell_orders"]["total_quantity"] += quantity
                    stats["sell_orders"]["orders"].append({
                        "orderId": order.get("orderId"),
                        "price": price,
                        "quantity": quantity,
                        "amount": amount,
                        "time": order.get("time")
                    })

        # 计算净值
        stats["net_amount"] = stats["buy_orders"]["total_amount"] - stats["sell_orders"]["total_amount"]
        stats["net_quantity"] = stats["buy_orders"]["total_quantity"] - stats["sell_orders"]["total_quantity"]

        # 记录统计结果
        logger.info(f"{token_symbol}订单统计:")
        logger.info(f"  买入: {stats['buy_orders']['count']}笔, 总额: {stats['buy_orders']['total_amount']:.2f} USDT")
        logger.info(f"  卖出: {stats['sell_orders']['count']}笔, 总额: {stats['sell_orders']['total_amount']:.2f} USDT")
        logger.info(f"  净额: {stats['net_amount']:.2f} USDT")

        return stats

    except Exception as e:
        logger.error(f"查询{token_symbol}订单历史失败: {e}")
        return {"error": str(e)}

def load_trader_config(config_path: Optional[str] = None) -> Tuple[dict, dict]:
    if config_path is None:
        config_path = TradingConfig.DEFAULT_CONFIG_PATH
    with open(config_path, "r", encoding="utf-8") as f:
        config = toml.load(f)
    # 处理全局和用户配置合并
    global_conf = {
        "target_token": config.get("target_token", TradingConfig.DEFAULT_TARGET_TOKEN),
        "buy_amount": config.get("buy_amount", 10.0),
        "target_total_amount": config.get("target_total_amount", 100.0)
    }
    user_confs = {}
    for user in config.get("users", []):
        uid = user["user_id"]
        if not user.get("enabled", True):
            continue
        merged = global_conf.copy()
        merged.update(user)
        user_confs[uid] = merged
    return global_conf, user_confs

# 多用户主流程
async def main():
    # 🔧 优雅退出：注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 记录开始时间
    start_time = time.time()

    # 加载系统配置
    TradingConfig.load_from_config()

    # 加载配置
    global_conf, user_confs = load_trader_config()
    db_url = TradingConfig.DEFAULT_DB_URL
    user_api_params = await load_user_api_params(db_url)
    token_symbol = global_conf["target_token"]
    alpha_id = get_alpha_id_from_token(token_symbol)
    price_stream = get_price_stream_from_token(token_symbol)


    
    # 获取配置中启用的用户ID
    enabled_user_ids = list(user_confs.keys())
    
    users = await build_users(user_api_params, price_stream, enabled_user_ids)
    stop_flag = asyncio.Event()
    ws_clients = []
    traders = []
    
    # 第一步：查询所有用户的累计买入总额，过滤已达标用户
    logger.info("=" * 60)
    logger.info(f"开始查询所有用户的累计买入总额（基于8点分界的时间范围）")
    logger.info("=" * 60)

    active_users = []  # 需要启动交易的用户

    for user_id, api, headers, cookies, price_stream in users:
        conf = user_confs.get(user_id, global_conf)
        min_amount = TradingConfig.DEFAULT_MIN_AMOUNT
        buy_amount = conf.get("buy_amount", global_conf.get("buy_amount", 10.0))
        buy_slippage = conf.get("buy_slippage", global_conf.get("buy_slippage", 0.002))
        sell_slippage = conf.get("sell_slippage", global_conf.get("sell_slippage", 0.002))
        target_total_amount = conf.get("target_total_amount", global_conf.get("target_total_amount", None))

        # 查询累计买入总额
        if target_total_amount:
            cumulative_amount = await get_user_cumulative_buy_amount(api, token_symbol)
            logger.info(f"用户{user_id}: 累计买入 {cumulative_amount:.2f} USDT / 目标 {target_total_amount:.2f} USDT")

            if cumulative_amount >= target_total_amount:
                logger.info(f"用户{user_id}已达标，跳过启动")
                continue

            # 计算剩余需要买入的金额和循环次数
            remaining_amount = target_total_amount - cumulative_amount
            remaining_cycles = max(1, int(remaining_amount / buy_amount))
            logger.info(f"用户{user_id}需要继续交易，剩余金额: {remaining_amount:.2f} USDT，预计循环: {remaining_cycles}次")
        else:
            logger.info(f"用户{user_id}未设置目标总金额，使用无限循环模式")

        # 创建交易器
        ws_client = BinanceWebSocket()
        ws_clients.append(ws_client)
        trader = AutoTrader(user_id, api, ws_client, alpha_id, token_symbol, min_amount, buy_amount, target_total_amount)
        traders.append((trader, buy_slippage, sell_slippage))
        active_users.append((user_id, api, headers, cookies, price_stream))

    if not active_users:
        logger.info("所有用户都已达标，无需启动交易")
        return

    logger.info("=" * 60)
    logger.info(f"共有 {len(active_users)} 个用户需要启动交易")
    logger.info("=" * 60)
    
    # 启动所有WebSocket连接
    ws_tasks = []
    for i, (user_id, api, headers, cookies, price_stream) in enumerate(active_users):
        ws_client = ws_clients[i]
        order_task = asyncio.create_task(ws_client.subscribe_order(headers, cookies))
        price_task = asyncio.create_task(ws_client.subscribe_price(price_stream))
        ws_tasks.extend([order_task, price_task])
    
    # 等待WebSocket连接建立
    await asyncio.sleep(TradingConfig.WEBSOCKET_SETUP_DELAY)
    
    # 启动所有自动交易
    trader_tasks = []
    for trader, buy_s, sell_s in traders:
        task = asyncio.create_task(trader.run(stop_flag, buy_s, sell_s))
        trader_tasks.append(task)

    try:
        # 🔧 优雅退出：主循环监控
        while not graceful_shutdown and not stop_flag.is_set():
            # 检查所有任务是否完成
            done_tasks = [task for task in trader_tasks if task.done()]
            if len(done_tasks) == len(trader_tasks):
                logger.info("✅ 所有交易任务已完成")
                break

            # 短暂等待，避免CPU占用过高
            await asyncio.sleep(1)

        # 如果收到优雅退出信号
        if graceful_shutdown:
            logger.info(f"🛑 收到退出信号: {shutdown_reason}")
            stop_flag.set()

            # 等待当前交易完成
            status_summary = await wait_for_current_trades_completion(traders, timeout=30.0)
            logger.info(f"📊 交易完成状态: {status_summary}")

        # 等待所有任务完成或被取消
        await asyncio.gather(*trader_tasks, return_exceptions=True)

    except KeyboardInterrupt:
        logger.info("🛑 收到键盘中断信号，开始优雅退出...")
        stop_flag.set()

        # 等待当前交易完成
        status_summary = await wait_for_current_trades_completion(traders, timeout=30.0)
        logger.info(f"📊 交易完成状态: {status_summary}")

    except Exception as e:
        logger.error(f"❌ 主循环异常: {e}")
        stop_flag.set()

    finally:
        # 🔧 优雅退出：统一资源清理
        logger.info("🧹 开始清理资源...")

        # 输出错误统计信息
        logger.info("=== 错误统计信息 ===")
        error_stats = global_error_handler.get_error_stats()
        for error_type, stats in error_stats.items():
            if stats["count"] > 0:
                logger.info(f"{error_type}: {stats['count']}次, 最后发生: {stats['time_since_last']:.1f}秒前")

        # 使用统一的资源清理函数
        apis = [api for user_id, api, headers, cookies, price_stream in active_users]
        await cleanup_resources(traders, ws_clients, apis)

        # 等待任务清理
        logger.info("⏳ 等待任务清理...")
        for task in ws_tasks + trader_tasks:
            task.cancel()

        try:
            await asyncio.wait_for(asyncio.gather(*ws_tasks, *trader_tasks, return_exceptions=True), timeout=5)
        except asyncio.TimeoutError:
            logger.warning("⚠️ 任务清理超时")

        # 记录最终状态
        await log_final_status(traders, start_time)

if __name__ == "__main__":
    asyncio.run(main()) 